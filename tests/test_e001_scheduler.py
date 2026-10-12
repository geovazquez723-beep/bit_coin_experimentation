"""S1.1 synthetic scheduling only; <=4096 attempted occurrences per test."""
from dataclasses import replace
from hashlib import blake2b
import tracemalloc

import pytest

from e001_verify import MT19937
from hashlab.experiments import e001_scheduler as s
from hashlab.experiments.e001_phase_b import FixturePlan, KINDS


def plan(ordinal=0, d=3, v=2):
    return FixturePlan(((ordinal, KINDS[ordinal]),), d, v)


def test_historical_metadata_without_generators(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('metadata advanced/constructed a generator')
    monkeypatch.setattr(s, 'build_generator', forbidden)
    streams = s.historical_schedule()
    assert len(streams) == 14
    assert sum(x.attempts for x in streams) == 7000000
    assert [(x.ordinal, x.phase) for x in streams] == [
        (o, p) for o in (0, 2, 4, 6, 7, 8, 9) for p in ('discovery', 'validation')]
    seeds = {2: (11563638942429927757, 17448145370022348540),
             9: (710289665967761509, 8231496708541735395)}
    names = ('seq-be-w8', 'uniform-be-w8', 'pattern-bytes-w8', 'struct-gray-w8',
             'struct-stride-w8', 'struct-bitrev-w8', 'random-bytes-w8')
    for number, stream in enumerate(streams):
        assert stream.generator == names[number // 2]
        assert stream.attempts == 500000
        assert stream.seed == (seeds[stream.ordinal][number % 2] if stream.ordinal in seeds else None)
        assert stream.start_index == (500000 if number % 2 and stream.ordinal not in seeds else 0)
        assert stream.phase_behavior == ('phase-seed-restart' if stream.ordinal in seeds else 'seedless-continuation')
        assert (stream.source, stream.configuration, stream.historical_contract, stream.manifest) == (
            s.SOURCE, s.CONFIG, s.CONTRACT, s.MANIFEST)
        assert stream.scope == 'historical-metadata-only'
    with pytest.raises(ValueError):
        s.iter_fixture(streams)
    with pytest.raises(ValueError):
        s.Occurrence(streams[0], 0, 0, bytes(8))


def expected(ordinal, d, v):
    """Reference formulas; no scheduler or production candidate helper calls."""
    if ordinal == 2:
        return [MT_output(seed, n) for seed, n in ((1, d), (2, v))]
    if ordinal == 9:
        def outputs(seed, n):
            blocks = b''.join(blake2b(i.to_bytes(16, 'big'), key=seed.to_bytes(16, 'big')).digest()
                              for i in range((n + 7) // 8))
            return [blocks[8*i:8*i+8] for i in range(n)]
        return [outputs(1, d), outputs(2, v)]
    def encode(i):
        if ordinal == 0:
            value = i
        elif ordinal == 6:
            value = i ^ (i // 2)
        elif ordinal == 7:
            value = 11400714819323198485 * i % 2**64
        elif ordinal == 8:
            value = sum(((i >> bit) & 1) * 2**(63-bit) for bit in range(64))
        elif ordinal == 4:
            # Explicit independent period-1/period-2 transition, omitting 00/00.
            return bytes([i]) * 8 if i < 256 else bytes([0, i - 255]) * 4
        return value.to_bytes(8, 'big')
    values = [encode(i) for i in range(d + v)]
    return [values[:d], values[d:]]


def MT_output(seed, n):
    rng = MT19937(seed)  # separate accepted MT implementation; shared authorship disclosed
    return [rng.getrandbits(64).to_bytes(8, 'big') for _ in range(n)]


@pytest.mark.parametrize('ordinal', (0, 2, 4, 6, 7, 8, 9))
def test_independent_phase_outputs_and_indices(ordinal):
    d, v = (255, 5) if ordinal == 4 else (17, 9)
    p = plan(ordinal, d, v)
    rows = list(s.iter_fixture(p))
    reference = expected(ordinal, d, v)
    assert [r.candidate for r in rows] == reference[0] + reference[1]
    assert [r.index for r in rows] == list(range(d)) + list(range(v))
    assert [r.enumeration_index for r in rows] == (
        list(range(d)) + list(range(v)) if ordinal in (2, 9) else list(range(d+v)))
    assert all(r.stream.ordinal == ordinal for r in rows)
    assert [r.stream.phase for r in rows] == ['discovery'] * d + ['validation'] * v
    accounting = s.FixtureAccounting(p)
    assert len(list(accounting.observations(iter(rows)))) == d + v
    summary = accounting.snapshot()
    assert summary.status == 'fixture-complete'
    assert all(c.unique == c.attempted and c.within == c.cross == 0 for c in summary.counts)
    assert summary.e_audit_passed is summary.final_acceptance is False


def test_global_windows_first_last_empty_and_phase_boundaries(monkeypatch):
    p = FixturePlan(((0, 'sequential'), (6, 'gray')), 3, 2)
    rows = list(s.iter_fixture(p, start=2, count=5))
    assert [(r.stream.ordinal, r.stream.phase, r.index, r.enumeration_index) for r in rows] == [
        (0, 'discovery', 2, 2), (0, 'validation', 0, 3), (0, 'validation', 1, 4),
        (6, 'discovery', 0, 0), (6, 'discovery', 1, 1)]
    assert next(s.iter_fixture(p)).candidate == bytes(8)
    last = next(s.iter_fixture(p, start=9, count=1))
    assert (last.stream.ordinal, last.stream.phase, last.index) == (6, 'validation', 1)
    monkeypatch.setattr(s, 'build_generator', lambda *a: pytest.fail('empty window constructed generator'))
    assert list(s.iter_fixture(p, start=10)) == []
    assert list(s.iter_fixture(p, count=0)) == []


@pytest.mark.parametrize('d,v', [(0, 3), (3, 0)])
def test_empty_phase(d, v):
    p = plan(2, d, v)
    rows = list(s.iter_fixture(p))
    assert [r.index for r in rows] == [0, 1, 2]
    a = s.FixtureAccounting(p)
    list(a.observations(rows))
    assert a.snapshot().status == 'fixture-complete'
    assert [c.attempted for c in a.snapshot().counts] == [d, v]


def repeated_rows(p):
    for stream in s.fixture_schedule(p):
        values = (1, 1, 2) if stream.phase == 'discovery' else (1, 1, 3, 3)
        for index, value in enumerate(values):
            yield s.Occurrence(stream, index, stream.start_index + index, value.to_bytes(8, 'big'))


def test_dedup_precedence_per_generator_and_no_topup():
    p = FixturePlan(((2, 'uniform'), (9, 'random_bytes')), 3, 4)
    a = s.FixtureAccounting(p)
    observed = list(a.observations(repeated_rows(p)))
    assert [x.outcome for x in observed] == ['unique', 'within', 'unique', 'cross', 'cross', 'unique', 'within'] * 2
    assert [(c.attempted, c.unique, c.within, c.cross) for c in a.snapshot().counts] == [(3, 2, 1, 0), (4, 1, 1, 2)] * 2
    assert a.snapshot().checked == 14
    # Both repeats of a discovery value in V remain cross-phase, never within.
    assert a.snapshot().status == 'fixture-complete'


def test_original_auto_dedup_bypass_for_unique_by_construction():
    p = plan(0, 3, 4)
    a = s.FixtureAccounting(p)
    assert all(o.outcome == 'unique' for o in a.observations(repeated_rows(p)))
    assert [c.unique for c in a.snapshot().counts] == [3, 4]
    # This proves original bypass semantics, not validity of injected generator bytes.


@pytest.mark.parametrize('failure', ['short', 'extra', 'extra-none', 'order', 'wrong-stream', 'interrupt'])
def test_fail_closed(failure):
    p = plan()
    rows = list(s.iter_fixture(p))
    if failure == 'short':
        rows.pop()
    elif failure == 'extra':
        rows.append(rows[-1])
    elif failure == 'extra-none':
        rows.append(None)
    elif failure == 'order':
        rows[0], rows[1] = rows[1], rows[0]
    elif failure == 'wrong-stream':
        rows[0] = replace(rows[0], stream=replace(rows[0].stream, generator='wrong-generator'))
    else:
        first = rows[0]
        def interrupted():
            yield first
            raise OSError('synthetic interruption')
        rows = interrupted()
    a = s.FixtureAccounting(p)
    with pytest.raises((ValueError, OSError)):
        list(a.observations(rows))
    summary = a.snapshot()
    assert summary.status == ('interrupted' if failure == 'interrupt' else 'invalid')
    assert not summary.e_audit_passed and not summary.final_acceptance
    with pytest.raises(ValueError, match='one-use'):
        a.observations(())


def test_consumer_interruption_and_last_yield_not_complete():
    p = plan()
    a = s.FixtureAccounting(p)
    iterator = a.observations(s.iter_fixture(p))
    for _ in range(5):
        next(iterator)
    assert a.snapshot().checked == a.snapshot().expected == 5
    assert a.snapshot().status == 'incomplete'  # extra-row check has not run
    iterator.close()
    assert a.snapshot().status == 'interrupted'
    assert not a.snapshot().e_audit_passed


def test_partial_consumption_stays_incomplete():
    a = s.FixtureAccounting(plan())
    iterator = a.observations(s.iter_fixture(plan()))
    next(iterator)
    before = a.snapshot()
    assert before.status == 'incomplete' and before.checked == 1
    iterator.close()
    assert before.status == 'incomplete'  # snapshot has no mutable counter aliases
    assert a.snapshot().status == 'interrupted'


def test_lazy_construction_and_exact_draw_budget(monkeypatch):
    calls = []
    class Generator:
        def stream(self, seed, start):
            calls.append(('stream', seed, start))
            for i in range(start, 100):
                calls.append(('draw', i))
                yield bytes(8)  # repeats are retained; no replacement draws
    def factory(spec):
        calls.append(('build', spec['id']))
        return Generator()
    monkeypatch.setattr(s, 'build_generator', factory)
    iterator = s.iter_fixture(plan())
    assert calls == []
    next(iterator)
    assert len([c for c in calls if c[0] == 'draw']) == 1
    iterator.close()
    calls.clear()
    a = s.FixtureAccounting(plan(2))
    list(a.observations(s.iter_fixture(plan(2))))
    assert len([c for c in calls if c[0] == 'draw']) == 5
    assert [(c.unique, c.within, c.cross) for c in a.snapshot().counts] == [(1, 2, 0), (0, 0, 2)]


def test_premature_generator_exhaustion(monkeypatch):
    class Short:
        def stream(self, seed, start):
            return iter([bytes(8)])
    monkeypatch.setattr(s, 'build_generator', lambda spec: Short())
    a = s.FixtureAccounting(plan())
    with pytest.raises(ValueError, match='premature'):
        list(a.observations(s.iter_fixture(plan())))
    assert a.snapshot().status == 'invalid'


@pytest.mark.parametrize('kwargs', [dict(start=True), dict(start=-1), dict(start=6), dict(count=6), dict(count=True)])
def test_window_rejections(kwargs):
    with pytest.raises(ValueError):
        s.iter_fixture(plan(), **kwargs)


def test_fixture_cap_and_no_historical_entrypoint():
    with pytest.raises(ValueError):
        plan(d=4096, v=1)
    assert sum(x.attempts for x in s.fixture_schedule(plan(d=4096, v=0))) == 4096
    assert not hasattr(s, 'run_experiment')
    assert not hasattr(s, 'candidates')


def test_bounded_iteration_memory():
    peaks = []
    for n in (32, 1900):  # 1932 total synthetic attempts, no materialized row arrays
        a = s.FixtureAccounting(plan(2, n, 0))
        tracemalloc.start()
        for _ in a.observations(s.iter_fixture(plan(2, n, 0))):
            pass
        peaks.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        assert a.snapshot().checked == n
    print('scheduler Python traced peaks (32,1900):', peaks)
    assert max(peaks) < 2_000_000  # bounded set is allowed; no production-memory claim


def test_no_hash_engine_or_seed_derivation(monkeypatch):
    from hashlab.hashing.sha256 import SHA256Engine
    from hashlab.candidates import base
    def forbidden(*args, **kwargs):
        raise AssertionError('hash engine or seed derivation invoked')
    monkeypatch.setattr(SHA256Engine, 'digest', forbidden)
    monkeypatch.setattr(base, 'derive_seed', forbidden)
    p = FixturePlan(tuple(KINDS.items()), 2, 2)
    a = s.FixtureAccounting(p)
    list(a.observations(s.iter_fixture(p)))
    assert a.snapshot().status == 'fixture-complete'


def test_patterned_lexicographic_carry_and_primitive_rejection():
    # 256 period-1 values, then 00/01..00/ff (255), then 01/00, skip 01/01.
    p = plan(4, 510, 4)
    rows = list(s.iter_fixture(p, start=509, count=5))
    assert [r.candidate for r in rows] == [bytes(motif) * 4 for motif in
                                         ((0, 254), (0, 255), (1, 0), (1, 2), (1, 3))]
    assert [(r.stream.phase, r.index) for r in rows] == [
        ('discovery', 509), ('validation', 0), ('validation', 1),
        ('validation', 2), ('validation', 3)]


def test_downstream_exclusion_does_not_request_replacements(monkeypatch):
    calls = []
    original = s.build_generator
    def factory(spec):
        gen = original(spec)
        class Counted:
            def stream(self, seed, start):
                for raw in gen.stream(seed, start):
                    calls.append(raw)
                    yield raw
        return Counted()
    monkeypatch.setattr(s, 'build_generator', factory)
    p = plan()
    # E001 has no exclusion filter. A downstream consumer can drop a raw value,
    # but the scheduler still stops at the exact raw attempt budget.
    retained = [r for r in s.iter_fixture(p) if r.candidate != bytes(8)]
    assert len(calls) == 5 and len(retained) == 4


@pytest.mark.parametrize('field,value', [('source', 'x'), ('attempts', True),
                                        ('seed', True), ('historical_contract', 'x')])
def test_invalid_stream_metadata(field, value):
    stream = s.fixture_schedule(plan(2))[0]
    with pytest.raises(ValueError):
        replace(stream, **{field: value})


@pytest.mark.parametrize('candidate', [b'', bytes(7), bytearray(8), '00000000'])
def test_invalid_candidate(candidate):
    with pytest.raises(ValueError):
        s.Occurrence(s.fixture_schedule(plan())[0], 0, 0, candidate)


def test_historical_disagreement_is_not_reconciled(monkeypatch):
    original = s.contract
    def conflict():
        c = original()
        c['counts']['pattern-bytes-w8']['validation']['start_index'] = 0
        return c
    monkeypatch.setattr(s, 'contract', conflict)
    with pytest.raises(ValueError, match='disagreement'):
        s.historical_schedule()


def test_seedless_full_fixture_never_replays_discovery_prefix(monkeypatch):
    draws = 0
    class Counted:
        def stream(self, seed, start):
            nonlocal draws
            assert seed is None and start == 0
            for i in range(4097):
                draws += 1
                if draws > 4096:
                    raise AssertionError('fixture replay exceeded total draw cap')
                yield i.to_bytes(8, 'big')
    monkeypatch.setattr(s, 'build_generator', lambda spec: Counted())
    p = plan(4, 2048, 2048)
    a = s.FixtureAccounting(p)
    for observation in a.observations(s.iter_fixture(p)):
        assert int.from_bytes(observation.occurrence.candidate, 'big') == draws - 1
    assert draws == 4096 and a.snapshot().status == 'fixture-complete'
