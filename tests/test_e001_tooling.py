"""S1.2 bounded synthetic qualification; no historical candidate evaluation."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import ast
import json
import sqlite3
import tracemalloc

import pytest

from hashlab.experiments import e001_scheduler as scheduler
from hashlab.experiments import e001_tooling as tooling
from hashlab.experiments.e001_phase_b import FixturePlan, KINDS
from hashlab.experiments.exp002 import HammingPopulation
from e001_verify.occurrences import verify_fixture, verify_manual_fixture


def plan(specs=((2, 'uniform'),), d=3, v=4, seeds=(1, 2)):
    return FixturePlan(specs, d, v, seeds)


def run(tmp_path, p, rows=None, **options):
    with tooling.DiskAccounting(tmp_path / 'audit.sqlite', p, **options) as db:
        observations = list(db.observations(tooling.fixture_occurrences(p) if rows is None else rows))
        return observations, db.report()


def verify(p, observations, report):
    return verify_fixture(p.specs, p.discovery, p.validation, p.seeds, observations, report)


@pytest.mark.parametrize('ordinal', KINDS)
def test_all_families_independent_bytes_phases_and_accounting(tmp_path, ordinal):
    p = plan(((ordinal, KINDS[ordinal]),), 510 if ordinal == 4 else 17, 9)
    observations, report = run(tmp_path, p)
    result = verify(p, observations, report)
    assert result['verification'] == 'independently-verified-synthetic'
    assert result['reference'] == 'algorithmic'
    assert not result['historical_complete'] and not result['final_acceptance']
    if ordinal == 4:
        assert [r['candidate'] for r in observations[509:514]] == [bytes(m)*4 for m in
                ((0, 254), (0, 255), (1, 0), (1, 2), (1, 3))]


@pytest.mark.parametrize('ordinal', (2, 9))
def test_seeded_restart_same_synthetic_seed_cross_precedence(tmp_path, ordinal):
    p = plan(((ordinal, KINDS[ordinal]),), 4, 4, (1, 1))
    observations, report = run(tmp_path, p)
    assert [r['outcome'] for r in observations] == ['unique']*4 + ['cross']*4
    assert [r['enumeration_index'] for r in observations] == list(range(4))*2
    assert verify(p, observations, report)['unique_evaluated'] == 4


def injected(p, values):
    source = iter(values)
    for s in scheduler.fixture_schedule(p):
        for i in range(s.attempts):
            yield scheduler.Occurrence(s, i, s.start_index+i, next(source))


def test_manual_exclusions_ranks_digest_and_duplicate_boundaries(tmp_path):
    # Explicit boundaries: A1 low/high, A3 weight 1/2/6, rejected weight 7.
    a, b, c = 1 << 32, 1 << 63, (1 << 32) | 1
    last = ((1 << 6)-1) << 58
    values = (a, a, 1 << 20, (1 << 32)-1, a, a, b, b,
              c, c, last, (1 << 20)-1, c, b, ((1 << 7)-1) << 57, 0)
    raw = tuple(v.to_bytes(8, 'big') for v in values)
    p = plan(((2, 'uniform'), (9, 'random_bytes')), 4, 4)
    observations, report = run(tmp_path, p, injected(p, raw), batch_size=3)
    verified = verify_manual_fixture(p.specs, 4, 4, p.seeds, observations, report, raw)
    assert verified['reference'] == 'manual'
    assert [r['outcome'] for r in observations] == [
        'unique', 'within', 'unique', 'unique', 'cross', 'cross', 'unique', 'within',
        'unique', 'within', 'unique', 'unique', 'cross', 'unique', 'unique', 'unique']
    assert (report['raw_attempted'], report['unique_evaluated'], report['qualifying_a1'],
            report['qualifying_a3'], report['distinct_excluded_a3']) == (16, 10, 2, 5, 4)
    # Independent combinatorial totals: weight-one ranks 0..31; first weight-two
    # eligible rank 32; final weight-six rank size-1. Numeric order differs.
    from math import comb
    size = sum(comb(64, w)-comb(32, w) for w in range(1, 7))
    assert report['a3_ranks'] == [0, 31, 32, size-1]
    assert report['a3_values_numeric_hex'] == [v.to_bytes(8, 'big').hex() for v in (a, c, b, last)]
    serialization = b''.join(v.to_bytes(8, 'big') for v in (a, c, b, last))
    assert report['exclusion_sha256'] == sha256(serialization).hexdigest()
    # Also calculated with .NET SHA256.HashData on a literal 32-byte message.
    assert report['exclusion_sha256'] == 'd65c8c02efc910c357685ed6a2f1b3a23711458121c052624dbfbc9483891b49'
    # Cross-generator b is evaluated twice but excluded once.
    assert HammingPopulation().unrank(size-1) == last
    with pytest.raises(ValueError):
        verify(p, observations, report)  # injected bytes are not algorithmic replay


def test_auto_bypass_and_exact_blob_schema(tmp_path):
    p = plan(((0, 'sequential'),), 2, 2)
    with tooling.DiskAccounting(tmp_path/'audit.sqlite', p) as db:
        observations = list(db.observations(injected(p, (bytes(8),)*4)))
        assert all(r['outcome'] == 'unique' for r in observations)
        assert db.db.execute('SELECT count(*) FROM seen').fetchone() == (0,)
        with pytest.raises(sqlite3.IntegrityError):
            db.db.execute("INSERT INTO seen VALUES (2,'12345678','discovery')")
    p = plan(d=2, v=0)
    with tooling.DiskAccounting(tmp_path/'second.sqlite', p) as db:
        list(db.observations(injected(p, (bytes(8), b'\xff'*8))))
        assert db.db.execute('SELECT typeof(candidate),length(candidate) FROM seen').fetchall() == [('blob', 8)]*2


@pytest.mark.parametrize('failure', ['short', 'extra', 'extra-none', 'order', 'stream', 'offset', 'interrupt'])
def test_accounting_fail_closed(tmp_path, failure):
    p = plan()
    rows = list(tooling.fixture_occurrences(p))
    if failure == 'short': rows.pop()
    elif failure == 'extra': rows.append(rows[-1])
    elif failure == 'extra-none': rows.append(None)
    elif failure == 'order': rows[0], rows[1] = rows[1], rows[0]
    elif failure == 'stream': rows[0] = replace(rows[0], stream=replace(rows[0].stream, generator='wrong'))
    elif failure == 'offset':
        forged = replace(rows[0])
        object.__setattr__(forged, 'enumeration_index', 99)
        rows[0] = forged
    else:
        first = rows[0]
        def broken():
            yield first
            raise OSError('synthetic interruption')
        rows = broken()
    with tooling.DiskAccounting(tmp_path/'audit.sqlite', p, batch_size=2) as db:
        with pytest.raises((ValueError, OSError)):
            list(db.observations(rows))
        with pytest.raises(ValueError, match='incomplete'):
            db.report()
        with pytest.raises(ValueError, match='one-use'):
            db.observations(())
        assert db.db.execute('SELECT status FROM run').fetchone() == ('incomplete',)


@pytest.mark.parametrize('field,value', [('candidate', bytes(8)), ('index', 1),
    ('enumeration_index', 99), ('start_index', 99), ('family', 'wrong'),
    ('generator', 'wrong'), ('source', '0'*40), ('configuration', '0'*64),
    ('phase', 'validation'), ('outcome', 'within'), ('ordinal', True), ('seed', 99)])
def test_independent_tampering_rejection(tmp_path, field, value):
    p = plan()
    observations, report = run(tmp_path, p)
    observations[0][field] = value
    with pytest.raises(ValueError): verify(p, observations, report)


@pytest.mark.parametrize('failure', ['missing', 'extra', 'extra-none', 'reorder', 'missing-generator'])
def test_independent_termination(tmp_path, failure):
    p = plan(((0, 'sequential'), (2, 'uniform')))
    observations, report = run(tmp_path, p)
    if failure == 'missing': observations.pop()
    elif failure == 'extra': observations.append(observations[-1])
    elif failure == 'extra-none': observations.append(None)
    elif failure == 'reorder': observations[0], observations[1] = observations[1], observations[0]
    else: observations = observations[:7]
    with pytest.raises(ValueError): verify(p, observations, report)


@pytest.mark.parametrize('field,value', [('status', 'incomplete'), ('historical_complete', True),
    ('final_acceptance', True), ('unique_evaluated', 0), ('raw_attempted', True),
    ('qualifying_a1', 1), ('exclusion_sha256', '0'*64), ('a3_ranks', [0]),
    ('a3_values_numeric_hex', ['0000000100000000']),
    ('accounting', []), ('verification', 'independently-verified-synthetic')])
def test_independent_report_tampering(tmp_path, field, value):
    p = plan()
    observations, report = run(tmp_path, p)
    report[field] = value
    with pytest.raises(ValueError): verify(p, observations, report)


def test_transaction_failure_rolls_back_and_poisoned_attempt(tmp_path, monkeypatch):
    p = plan(d=3, v=0)
    with tooling.DiskAccounting(tmp_path/'audit.sqlite', p, batch_size=2) as db:
        def fail(): raise OSError('injected commit failure')
        monkeypatch.setattr(db, '_commit', fail)
        with pytest.raises(OSError): list(db.observations(tooling.fixture_occurrences(p)))
        assert db.db.execute('SELECT count(*) FROM seen').fetchone() == (0,)
        assert db.db.execute('SELECT sum(attempted) FROM counts').fetchone() == (0,)
        with pytest.raises(ValueError): db.report()
    with pytest.raises(FileExistsError): tooling.DiskAccounting(tmp_path/'audit.sqlite', p)


def test_partial_batches_crash_and_final_yield_are_incomplete(tmp_path):
    p = plan(d=3, v=0)
    db = tooling.DiskAccounting(tmp_path/'audit.sqlite', p, batch_size=2)
    iterator = db.observations(tooling.fixture_occurrences(p))
    for _ in range(3): next(iterator)
    with pytest.raises(ValueError): db.report()
    iterator.close()
    assert db.db.execute('SELECT sum(attempted) FROM counts').fetchone() == (2,)
    db.close()
    # Read-only diagnostic inspection does not resume, recover or repair the store.
    with sqlite3.connect(f'file:{tmp_path / "audit.sqlite"}?mode=ro', uri=True) as saved:
        assert saved.execute('SELECT status FROM run').fetchone() == ('incomplete',)


def test_context_close_abandons_consumer_and_rolls_back(tmp_path):
    p = plan()
    with tooling.DiskAccounting(tmp_path/'audit.sqlite', p) as db:
        iterator = db.observations(tooling.fixture_occurrences(p))
        next(iterator)
    assert db.status == 'interrupted'
    assert list(iterator) == []
    with sqlite3.connect(f'file:{tmp_path / "audit.sqlite"}?mode=ro', uri=True) as saved:
        assert saved.execute('SELECT sum(attempted) FROM counts').fetchone() == (0,)


def test_separate_attempts_cannot_mix_generators_or_reopen(tmp_path):
    p = plan(((2, 'uniform'), (9, 'random_bytes')), 1, 0)
    raw = ((1 << 32).to_bytes(8, 'big'),)*2
    observations, report = run(tmp_path, p, injected(p, raw))
    assert [r['outcome'] for r in observations] == ['unique', 'unique']
    assert report['qualifying_a3'] == 2 and report['distinct_excluded_a3'] == 1
    with pytest.raises(FileExistsError): tooling.DiskAccounting(tmp_path/'audit.sqlite', p)
    with tooling.DiskAccounting(tmp_path/'fresh.sqlite', p) as db:
        assert all(r['outcome'] == 'unique' for r in db.observations(injected(p, raw)))


def test_actual_producer_disagreement_is_rejected(tmp_path, monkeypatch):
    class WrongGenerator:
        def stream(self, seed, start):
            yield from (bytes(8),)*7
    monkeypatch.setattr(scheduler, 'build_generator', lambda spec: WrongGenerator())
    p = plan()
    observations, report = run(tmp_path, p)
    with pytest.raises(ValueError, match='independent occurrence'):
        verify(p, observations, report)


def test_lazy_provider_resource_ceiling_and_no_historical_activation(tmp_path, monkeypatch):
    draws = []
    class Generator:
        def stream(self, seed, start):
            for i in range(4097):
                draws.append(i)
                assert len(draws) <= 4096
                yield i.to_bytes(8, 'big')
    monkeypatch.setattr(scheduler, 'build_generator', lambda spec: Generator())
    p = plan(((4, 'patterned'),), 2048, 2048)
    source = tooling.fixture_occurrences(p)
    assert draws == []
    with tooling.DiskAccounting(tmp_path/'audit.sqlite', p) as db:
        tracemalloc.start()
        for _ in db.observations(source): pass
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        assert db.report()['raw_attempted'] == len(draws) == 4096
        assert peak < 2_000_000
        assert db.db.execute('PRAGMA cache_size').fetchone() == (-64,)
        assert db.db.execute('PRAGMA max_page_count').fetchone() == (2048,)
    print('S1.2 disk accounting traced Python peak:', peak)
    with pytest.raises(ValueError): plan(d=4096, v=1)
    with pytest.raises(ValueError): tooling.fixture_occurrences(scheduler.historical_schedule())
    with pytest.raises(ValueError): tooling.DiskAccounting(tmp_path/'historical.sqlite', scheduler.historical_schedule())
    with pytest.raises(ValueError): verify_fixture(((0,'sequential'),),4097,0,(1,2),(),{})


@pytest.mark.parametrize('d,v', [(0, 3), (3, 0)])
def test_empty_phase(tmp_path, d, v):
    p = plan(d=d, v=v)
    observations, report = run(tmp_path, p)
    assert verify(p, observations, report)['raw_attempted'] == 3


def test_no_research_hashing_or_seed_derivation(tmp_path, monkeypatch):
    from hashlab.hashing.sha256 import SHA256Engine
    from hashlab.candidates import base
    def forbidden(*a, **k): pytest.fail('research engine/seed derivation invoked')
    monkeypatch.setattr(SHA256Engine, 'digest', forbidden)
    monkeypatch.setattr(base, 'derive_seed', forbidden)
    p = plan(tuple(KINDS.items()), 2, 2)
    observations, report = run(tmp_path, p)
    assert verify(p, observations, report)['raw_attempted'] == 28


def test_independent_import_isolation_and_no_dispatcher():
    import e001_verify.occurrences as independent
    tree = ast.parse(Path(independent.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): assert all(not a.name.startswith('hashlab') for a in node.names)
        if isinstance(node, ast.ImportFrom): assert not (node.module or '').startswith('hashlab')
    for name in ('run_history', 'historical_occurrences', 'main', 'run_experiment'):
        assert not hasattr(tooling, name) and not hasattr(independent, name)


def test_sealed_output_rejected_before_creation(tmp_path):
    (tmp_path/'manifest.sha256').write_text('synthetic sealed marker')
    with pytest.raises(ValueError, match='sealed'):
        tooling.DiskAccounting(tmp_path/'forbidden.sqlite', plan())
    assert not (tmp_path/'forbidden.sqlite').exists()


def test_accepted_sources_and_sealed_evidence_unchanged():
    from hashlab.experiments.e001_reconstruction import validate_history
    from hashlab.evidence.manifest import verify_manifest
    sealed = Path('results/20261011T205056Z-exp001-fc1d75fc')
    validate_history(sealed, Path.cwd())
    assert verify_manifest(sealed) == []
    # Session snapshot is local qualification evidence, not historical provenance.
    snapshot = Path('results-smoke/e001-s12-qualification/before.json')
    if snapshot.exists():
        before = json.loads(snapshot.read_text())
        for inventory in (before['sealed'], before['protected']):
            for name, entry in inventory.items():
                p = Path(name)
                assert p.stat().st_size == entry['size']
                assert p.stat().st_mtime_ns == entry['mtime_ns']
                assert sha256(p.read_bytes()).hexdigest() == entry['sha256']
