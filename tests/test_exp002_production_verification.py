"""Independent production-format evidence verification on bounded public fixtures.

The fixture is 78 candidate evaluations under public master 0 in the engineering
KAT domain. No production seed, quota, QA2, E001 reconstruction or full hashing runs.
"""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import io
import json
import logging
import shutil
import subprocess
import sys
import traceback

import pytest

from hashlab.experiments import exp002_kernel_bounded as bounded
from hashlab.experiments import exp002_kernel_evidence as binary
from hashlab.experiments import exp002_kernel_plan as plans
from hashlab.experiments import exp002_kernel as kernel
from hashlab.experiments.exp002 import Exclusions, HammingPopulation, a2_key, a2_prefix
from hashlab.experiments.exp002_controls import Feistel64, control_keys, inverse_history
from hashlab.experiments.exp002_foundation import Plan, canonical
from hashlab.experiments.exp002_kernel_disclosure import KernelFailure
from hashlab.experiments.exp002_s14 import VerifiedS14
from e002_verify import production as v
from e002_verify import production_evidence as ev
from e002_verify import core as ref_core
from e002_verify import controls as ref_controls

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO/'results/e001-s14-audit-20261012-01'
SEED = canonical(dict(schema=ev.SEED_RECORD_SCHEMA, kind='public-engineering', master='0', domain='experiment-002-kat'))
RANKS = (0, 1, 2, 3, 32, 63, 127, 4095, 5000)


def unit_inputs(monkeypatch, *, extra_values=()):
    """Unit-only injected history (nine A3 ranks and three historical values); never measured evidence."""
    history = VerifiedS14(Exclusions(RANKS, HammingPopulation()))
    n, two = control_keys(0, 'experiment-002-kat')
    prp = Feistel64(n)
    values = [HammingPopulation().unrank(r) for r in RANKS] + [prp.forward(0), prp.forward(2**63), prp.forward(2**63)]
    values += list(extra_values)
    inverse = inverse_history(prp, [x.to_bytes(8, 'big') for x in values], identity={'unit_only': True})
    key = a2_key(0, 'experiment-002-kat')
    prefixes = tuple(a2_prefix(key, j) for j in range(3000))
    inputs = history, prp, inverse, two, prefixes
    monkeypatch.setattr(bounded, '_bounded_inputs', lambda *a: inputs)
    monkeypatch.setattr(ref_core, 'load_history', lambda *a: (set(RANKS), history.identity()))
    monkeypatch.setattr(ref_controls, 'load_history', lambda *a: (set(values), inverse.identity, len(values)))
    return inputs


@pytest.fixture
def inputs(monkeypatch):
    return unit_inputs(monkeypatch)


@pytest.fixture(scope='module')
def original(tmp_path_factory):
    root = tmp_path_factory.mktemp('bounded')/'run'
    with pytest.MonkeyPatch.context() as mp:
        unit_inputs(mp)
        outcome = bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
    return root, outcome.completion_sha256


@pytest.fixture
def evidence(tmp_path, original, inputs):
    root = tmp_path/'copy'
    shutil.copytree(original[0], root)
    return root, original[1]


def verify(root, pin, **kw):
    kw.setdefault('geometry_name', 'bounded-fixture')
    kw.setdefault('seed_record', SEED)
    return ev.verify_evidence(root, completion_sha256=pin, audit_root=AUDIT, repository_root=REPO, **kw)


# ----------------------------------------------------- reading/rewriting rows

def read_rows(root):
    rows = []
    for line in (root/'chunks.jsonl').read_bytes().splitlines():
        entry = json.loads(line)
        source = io.BytesIO((root/entry['name']).read_bytes()[binary.HEADER.size:])
        for _ in range(entry['rows']):
            _, attempt, raw, effective, _ = binary.decode_row(source)
            rows.append([attempt, raw, effective])
    return rows


def reseal(root):
    """Recompute every transport pin so only semantic corruption remains."""
    report = json.loads((root/'complete.json').read_bytes())
    entries = []
    for line in (root/'chunks.jsonl').read_bytes().splitlines():
        entry = json.loads(line)
        raw = (root/entry['name']).read_bytes()
        entry.update(size=len(raw), sha256=sha256(raw).hexdigest())
        entries.append(entry)
    (root/'chunks.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in entries))
    for name, key in (('plan.json', 'plan'), ('history.json', 'history'), ('environment.json', 'environment'),
                      ('accounting.json', 'accounting'), ('chunks.jsonl', 'index')):
        raw = (root/name).read_bytes()
        report[key] = dict(size=len(raw), sha256=sha256(raw).hexdigest())
    if 'plan_sha256' in report:
        report['plan_sha256'] = report['plan']['sha256']
    raw = canonical(report)
    (root/'complete.json').write_bytes(raw)
    return sha256(raw).hexdigest()


def rewrite(root, rows):
    for p in list(root.glob('chunk-*.bin')) + [root/'chunks.jsonl']:
        p.unlink()
    writer = binary.ChunkWriter(root)
    for attempt, raw, effective in rows:
        writer.add(attempt, raw, effective)
    info = writer.finish()
    report = json.loads((root/'complete.json').read_bytes())
    report.update(chunks=info['chunks'], attempts=info['attempts'])
    (root/'complete.json').write_bytes(canonical(report))
    return reseal(root)


# ---------------------------------------------------------------- agreement

def test_producer_and_independent_reconstruction_agree_on_every_attempt(evidence):
    root, pin = evidence
    report = verify(root, pin)
    coverage = report['coverage']
    assert (coverage['attempts_reconstructed'], coverage['candidates_rehashed'], coverage['compression_blocks']) == (80, 78, 106)
    assert coverage['rejections'] == dict(A1=0, A2=0, A3=0, N1=1, N2=0, P1=1, **{'P2+': 0, 'P2-': 0})
    assert report['claims']['external_receipt'] is False and report['claims']['execution_authorized'] is False
    assert report['claims']['disclosure_authorized'] is False and report['claims']['g1'] is False
    assert report['bindings']['completion_sha256'] == pin and report['scope'] == 'bounded-fixture'
    # Public report: no success counts, histograms, cluster counts, ratios or p-values as keys.
    def keys(value):
        if isinstance(value, dict):
            for k, x in value.items():
                yield k
                yield from keys(x)
        elif isinstance(value, list):
            for x in value:
                yield from keys(x)
    names = set(keys(report))
    assert not names & {'successes', 'first_byte', 'last_byte', 'leading_zero_bits', 'cluster_successes',
                        'ratio', 'p_value', 'discovery_count', 'validation_count'}


def test_bounded_stream_exercises_production_domain_boundaries(evidence):
    root, pin = evidence
    verify(root, pin)
    rows = read_rows(root)
    arms = [r[0].arm for r in rows]
    assert arms == ['A1']*12 + ['A2']*16 + ['A3']*12 + ['N1']*13 + ['N2']*12 + ['P1']*3 + ['P2+']*6 + ['P2-']*6
    a1 = [r[0] for r in rows if r[0].arm == 'A1']
    assert max(a.population_rank for a in a1) > 2**20     # sparse sampling over the full A1 population
    n1 = [r[0] for r in rows if r[0].arm == 'N1']
    assert [a.stage for a in n1].count('D') >= 6 and n1[-1].stage == 'V'
    assert [a.reasons for a in n1 if a.reasons] == [('E001',)]
    p = [r[0] for r in rows if r[0].arm.startswith('P')]
    assert [a.source_index for a in p][:3] == [2**63, 2**63+1, 2**63+2] and p[0].reasons == ('E001',)
    n2 = [r[0] for r in rows if r[0].arm == 'N2']
    assert [a.stage for a in n2] == ['D']*6 + ['V']*6 and [a.cluster for a in n2] == [0]*6 + [1500]*6
    assert [a.byte_offset for a in n2] == [80*i for i in range(12)]
    a2 = [r[0] for r in rows if r[0].arm == 'A2']
    assert [a.cluster for a in a2] == [0]*8 + [1500]*8 and [a.accepted_index for a in a2] == list(range(8))*2
    a3 = [r[0] for r in rows if r[0].arm == 'A3']
    assert not {a.population_rank for a in a3} & set(RANKS)


def test_deterministic_replay_is_byte_identical_and_hashes_once_per_accepted_candidate(tmp_path, evidence, monkeypatch):
    root, pin = evidence
    calls = []
    real = bounded.SHA256Engine.digest
    monkeypatch.setattr(bounded.SHA256Engine, 'digest', lambda self, raw: (calls.append(len(raw)), real(self, raw))[1])
    repeat = tmp_path/'repeat'
    outcome = bounded.run_bounded(repeat, audit_root=AUDIT, repository_root=REPO)
    assert outcome.completion_sha256 == pin and len(calls) == 78 and sum((n+72)//64 for n in calls) == 106
    assert {p.name: p.read_bytes() for p in root.iterdir()} == {p.name: p.read_bytes() for p in repeat.iterdir()}
    assert verify(repeat, outcome.completion_sha256) == verify(root, pin)


def test_plan_file_is_the_fixed_bounded_fixture_and_matches_independent_restatement(evidence):
    root, _ = evidence
    assert (root/'plan.json').read_bytes() == ev.encode(ev.bounded_plan()) == bounded.BoundedPlan().serialize()
    plan = json.loads((root/'plan.json').read_bytes())
    assert plan['scope'] == 'bounded-fixture' and plan['confirmatory_complete'] is False and plan['qa2'] is False
    with pytest.raises(TypeError):
        bounded.BoundedPlan(geometry='production')
    with pytest.raises(TypeError):
        bounded.run_bounded(Path('x'), audit_root=AUDIT, repository_root=REPO, seed=1)


# -------------------------------------------------- resealed semantic faults

def semantic(mutator):
    def apply(rows):
        rows = [list(r) for r in rows]
        mutator(rows)
        return rows
    return apply


def first(rows, arm, stage=None, accepted=True):
    return next(i for i, r in enumerate(rows) if r[0].arm == arm and (stage is None or r[0].stage == stage)
                and bool(r[0].reasons) != accepted)


MUTATIONS = {
    'omit-first-a1': lambda rows: rows.pop(0),
    'omit-middle': lambda rows: rows.pop(first(rows, 'A3')),
    'omit-last': lambda rows: rows.pop(),
    'omit-historical-rejection': lambda rows: rows.pop(first(rows, 'N1', accepted=False)),
    'omit-positive-rejection': lambda rows: rows.pop(first(rows, 'P1', accepted=False)),
    'duplicate': lambda rows: rows.insert(5, list(rows[5])),
    'duplicate-last': lambda rows: rows.append(list(rows[-1])),
    'reorder-adjacent': lambda rows: rows.__setitem__(slice(3, 5), [rows[4], rows[3]]),
    'reorder-across-arms': lambda rows: rows.__setitem__(slice(0, 13), rows[12:13] + rows[0:12]),
    'candidate': lambda rows: rows[2].__setitem__(0, replace(rows[2][0], candidate=(int.from_bytes(rows[2][0].candidate, 'big')+1).to_bytes(8, 'big'))),
    'rank': lambda rows: rows[2].__setitem__(0, replace(rows[2][0], population_rank=rows[2][0].population_rank+1)),
    'stage': lambda rows: rows[2].__setitem__(0, replace(rows[2][0], stage='V' if rows[2][0].stage == 'D' else 'D')),
    'accepted-index': lambda rows: rows[3].__setitem__(0, replace(rows[3][0], accepted_index=rows[3][0].accepted_index+1)),
    'raw-digest': lambda rows: rows[4].__setitem__(1, bytes([rows[4][1][0] ^ 1]) + rows[4][1][1:]),
    'effective-digest': lambda rows: rows[4].__setitem__(2, bytes([rows[4][2][0] ^ 1]) + rows[4][2][1:]),
    'n1-source': lambda rows: rows.__setitem__(first(rows, 'N1'), [replace(rows[first(rows, 'N1')][0], source_index=999)] + rows[first(rows, 'N1')][1:]),
    'n2-offset': lambda rows: rows.__setitem__(first(rows, 'N2'), [replace(rows[first(rows, 'N2')][0], byte_offset=1)] + rows[first(rows, 'N2')][1:]),
    'n2-stage-early-v': lambda rows: rows.__setitem__(first(rows, 'N2'), [replace(rows[first(rows, 'N2')][0], stage='V', cluster=1500)] + rows[first(rows, 'N2')][1:]),
    'rejection-reason': lambda rows: rows.__setitem__(first(rows, 'N1', accepted=False), [replace(rows[first(rows, 'N1', accepted=False)][0], reasons=('C1',))] + rows[first(rows, 'N1', accepted=False)][1:]),
    'p-cursor': lambda rows: rows.__setitem__(first(rows, 'P2+'), [replace(rows[first(rows, 'P2+')][0], source_index=2**63+50)] + rows[first(rows, 'P2+')][1:]),
}


@pytest.mark.parametrize('name', sorted(MUTATIONS))
def test_resealed_semantic_corruption_is_detected_independently(evidence, name):
    root, _ = evidence
    rows = read_rows(root)
    MUTATIONS[name](rows)
    pin = rewrite(root, rows)
    with pytest.raises(ValueError):
        verify(root, pin)


def test_repack_without_change_still_verifies(evidence):
    root, _ = evidence
    pin = rewrite(root, read_rows(root))
    assert verify(root, pin)['coverage']['candidates_rehashed'] == 78


@pytest.mark.parametrize('mutation', ['accounting', 'plan', 'history', 'environment-source', 'environment-runtime',
                                     'success-claim', 'rejection-claim', 'scope', 'index-bool'])
def test_resealed_metadata_corruption_is_detected(evidence, mutation):
    root, _ = evidence
    if mutation == 'accounting':
        obj = json.loads((root/'accounting.json').read_bytes())
        obj['streams'][0]['successes'] += 1
        (root/'accounting.json').write_bytes(canonical(obj))
    elif mutation == 'plan':
        obj = json.loads((root/'plan.json').read_bytes())
        obj['geometry']['a3_stage'] = 7
        (root/'plan.json').write_bytes(canonical(obj))
    elif mutation == 'history':
        obj = json.loads((root/'history.json').read_bytes())
        obj['historical_occurrences'] += 1
        (root/'history.json').write_bytes(canonical(obj))
    elif mutation.startswith('environment'):
        obj = json.loads((root/'environment.json').read_bytes())
        if mutation.endswith('source'):
            obj['sources'].pop()
        else:
            obj['runtime']['platform'] = ''
        (root/'environment.json').write_bytes(canonical(obj))
    elif mutation in ('success-claim', 'rejection-claim', 'scope'):
        obj = json.loads((root/'complete.json').read_bytes())
        if mutation == 'success-claim':
            obj['successes'] += 1
        elif mutation == 'rejection-claim':
            obj['rejections']['A1'] = 3
        else:
            obj['scope'] = 'production'
        (root/'complete.json').write_bytes(canonical(obj))
    else:
        entry = json.loads((root/'chunks.jsonl').read_bytes())
        entry['sequence'] = False
        (root/'chunks.jsonl').write_bytes(canonical(entry)+b'\n')
    pin = reseal(root) if mutation not in ('success-claim', 'rejection-claim', 'scope') else sha256((root/'complete.json').read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        verify(root, pin)


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'marker', 'truncate', 'bitflip', 'failure', 'torn-complete',
                                     'wrong-pin', 'empty-index'])
def test_transport_tampering_fails(evidence, mutation):
    root, pin = evidence
    chunk = root/'chunk-00000000.bin'
    if mutation == 'missing':
        chunk.unlink()
    elif mutation == 'extra':
        (root/'unexpected').write_bytes(b'x')
    elif mutation == 'marker':
        (root/'INCOMPLETE').write_bytes(b'x')
    elif mutation == 'truncate':
        chunk.write_bytes(chunk.read_bytes()[:-1])
    elif mutation == 'bitflip':
        raw = bytearray(chunk.read_bytes())
        raw[60] ^= 1
        chunk.write_bytes(raw)
    elif mutation == 'failure':
        (root/'failure.json').write_bytes(b'{}')
    elif mutation == 'torn-complete':
        (root/'complete.json').write_bytes(b'{')
    elif mutation == 'empty-index':
        (root/'chunks.jsonl').write_bytes(b'')
    else:
        pin = '0'*64
    with pytest.raises((ValueError, OSError)):
        verify(root, pin)


# -------------------------------------------------- bindings and boundaries

def test_wrong_or_malformed_seed_records_are_rejected(evidence):
    root, pin = evidence
    beacon = canonical(dict(schema=ev.SEED_RECORD_SCHEMA, kind='beacon', precommit='0'*40, round='1',
                            randomness_hex='0'*64, master=str(v.master_from_beacon('0'*40, 1, '0'*64)),
                            domain='experiment-002-kat'))
    for bad in (beacon,                                     # different master => different stream
                canonical(dict(schema=ev.SEED_RECORD_SCHEMA, kind='public-engineering', master='1', domain='experiment-002-kat')),
                canonical(dict(schema=ev.SEED_RECORD_SCHEMA, kind='public-engineering', master='0', domain='experiment-002')),
                canonical(dict(schema=ev.SEED_RECORD_SCHEMA, kind='public-engineering', master='0', domain='experiment-002-kat', extra=1)),
                canonical(dict(schema='other', kind='public-engineering', master='0', domain='experiment-002-kat')),
                SEED.replace(b'public-engineering', b'beacon'), b'{}', b'', b'[]', SEED+b'\n', b'x'*5000):
        with pytest.raises(ValueError):
            verify(root, pin, seed_record=bad)
    good = verify(root, pin)
    assert good['bindings']['seed_record_sha256'] == sha256(SEED).hexdigest()


@pytest.mark.parametrize('record', [
    dict(kind='beacon', precommit='0'*39, round='1', randomness_hex='0'*64, master='1'),
    dict(kind='beacon', precommit='0'*40, round='0', randomness_hex='0'*64, master='1'),
    dict(kind='beacon', precommit='0'*40, round='1', randomness_hex='0'*64, master='1'),
    dict(kind='beacon', precommit='0'*40, round=1, randomness_hex='0'*64, master='1'),
    dict(kind='public-engineering', master='0')])
def test_production_geometry_rejects_malformed_beacon_and_engineering_seed_records(record):
    body = dict(record, schema=ev.SEED_RECORD_SCHEMA, domain='experiment-002')
    with pytest.raises(ValueError):
        ev.parse_seed_record(canonical(body), v.FROZEN)


SIGNATURE = 'ab'*48
SCHEDULED = 1692803367 + 999*3


def beacon_record(**changes):
    from hashlab.experiments import exp002_finalization as producer
    raw = producer.beacon_seed_record('0'*40, 1000, SIGNATURE, witness_receipt_sha256='9'*64, witnessed_unix=SCHEDULED-90000,
                                      preregistration_bundle_sha256=sha256(producer.preregistration_bundle(producer_plan(), 1000)).hexdigest())
    record = json.loads(raw)
    for path, value in changes.items():
        target = record
        *parents, leaf = path.split('.')
        for q in parents:
            target = target[q]
        target[leaf] = value
    return canonical(record)


def test_valid_beacon_seed_record_reconciles_s1_to_s5_and_producer_bytes_agree():
    raw = beacon_record()
    master, digest, facts = ev.parse_seed_record(raw, v.FROZEN)
    record = json.loads(raw)
    assert master == v.master_from_beacon('0'*40, 1000, record['beacon']['randomness_hex']) == int(record['master'])
    assert digest == sha256(raw).hexdigest() and facts['beacon_signature'].startswith('not-verified')
    assert facts['witness_receipt'].startswith('not-verified') and facts['c_pre'] == '0'*40
    assert record['beacon']['scheduled_unix'] == str(SCHEDULED) and record['beacon']['chain_hash'] == ev.BEACON['chain_hash']
    with pytest.raises(ValueError):                         # bounded fixture domain mismatch
        ev.parse_seed_record(raw, v.BOUNDED)


@pytest.mark.parametrize('changes', [
    {'c_pre': 'A'*40}, {'c_pre': '0'*39}, {'beacon.round': '0'}, {'beacon.round': '01000'}, {'beacon.round': '18446744073709551616'},
    {'beacon.round': '1001'}, {'beacon.scheduled_unix': str(SCHEDULED+3)}, {'beacon.chain_hash': '0'*64},
    {'beacon.scheme': 'pedersen-bls-chained'}, {'beacon.beacon_id': 'default'}, {'beacon.period': '30'},
    {'beacon.genesis_unix': '1'}, {'beacon.public_key_hex': '0'*192}, {'beacon.signature_hex': 'cd'*48},
    {'beacon.signature_hex': 'ab'*47}, {'beacon.randomness_hex': '0'*64}, {'master': '1'}, {'master': '01'},
    {'witness.witnessed_unix': str(SCHEDULED-86399)}, {'witness.witnessed_unix': '-1'}, {'witness.receipt_sha256': 'x'},
    {'witness.bundle_sha256': 'x'}, {'witness.bundle_sha256': 'A'*64},
    {'domain': 'experiment-002-kat'}, {'kind': 'public-engineering'}, {'schema': 'other'}])
def test_seed_record_field_validation_rules(changes):
    with pytest.raises(ValueError):
        ev.parse_seed_record(beacon_record(**changes), v.FROZEN)


def test_seed_record_extra_missing_and_noncanonical_fields_fail():
    record = json.loads(beacon_record())
    for bad in (dict(record, extra=1), {k: x for k, x in record.items() if k != 'witness'},
                dict(record, beacon={k: x for k, x in record['beacon'].items() if k != 'round'}),
                beacon_record() + b' ', b'', b'[]'):
        with pytest.raises(ValueError):
            ev.parse_seed_record(bad if isinstance(bad, bytes) else canonical(bad), v.FROZEN)


def test_seed_commitment_matches_producer_and_independent_restatement_of_full_plan_binding():
    from hashlab.experiments import exp002_finalization as producer
    plan = producer_plan()
    raw = beacon_record()
    master, digest, facts = ev.parse_seed_record(raw, v.FROZEN)
    commitment = producer.seed_commitment(plan, raw)
    parsed = ev.parse_seed_commitment(commitment, seed_record_sha=digest, facts=facts, master=master, code_commit=plan.code_commit)
    binding = producer.full_binding(plan, raw)
    assert parsed['full_plan_sha256'] == binding.fingerprint and parsed['seeded_config_sha256'] == binding.resolved_config_sha256
    assert parsed['seedless_plan_sha256'] == binding.seedless_sha256 and parsed['seed_record_sha256'] == binding.seed_record_sha256
    assert parsed['seeded_config_sha256'] != parsed['config_sha256']                  # seed inserted into the configuration
    for key in parsed:
        mutated = dict(json.loads(commitment))
        mutated[key] = '0'*40 if key == 'c_pre' else 'f'*64 if key.endswith('sha256') else '1'
        if mutated[key] == json.loads(commitment)[key]:
            continue
        with pytest.raises(ValueError):
            ev.parse_seed_commitment(canonical(mutated), seed_record_sha=digest, facts=facts, master=master, code_commit=plan.code_commit)
    with pytest.raises(ValueError):
        ev.parse_seed_commitment(commitment, seed_record_sha=digest, facts=facts, master=master, code_commit='b'*40)
    with pytest.raises(ValueError):
        ev.parse_seed_commitment(commitment + b' ', seed_record_sha=digest, facts=facts, master=master, code_commit=plan.code_commit)


def test_c_seed_must_be_a_commit_containing_the_exact_documents(tmp_path):
    repo, commit = tiny_repo(tmp_path)
    (repo/'seed-record.json').write_bytes(b'record')
    for args in (['add', '.'], ['commit', '-q', '-m', 'seed']):
        subprocess.run(['git', '-c', 'user.name=unit', '-c', 'user.email=unit@example.invalid', *args], cwd=repo, check=True, capture_output=True)
    c_seed = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    ev.verify_c_seed(repo, c_seed, {'seed-record.json': b'record'})
    for bad in ({'seed-record.json': b'other'}, {'missing.json': b'x'}):
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            ev.verify_c_seed(repo, c_seed, bad)
    with pytest.raises(ValueError):
        ev.verify_c_seed(repo, 'zz', {})
    with pytest.raises(subprocess.CalledProcessError):
        ev.verify_c_seed(repo, 'b'*40, {'seed-record.json': b'record'})


def test_production_verification_requires_beacon_record_commitment_and_c_seed(evidence):
    root, pin = evidence
    with pytest.raises(ValueError):
        verify(root, pin, geometry_name='production', seed_record=beacon_record(domain='experiment-002'))
    with pytest.raises(ValueError):
        verify(root, pin, geometry_name='production', seed_record=SEED)       # engineering record refused for production


def test_scope_geometry_cross_use_and_modes_are_rejected(evidence):
    root, pin = evidence
    with pytest.raises(ValueError):
        verify(root, pin, geometry_name='production', seed_record=canonical(dict(
            schema=ev.SEED_RECORD_SCHEMA, kind='public-engineering', master='0', domain='experiment-002')))
    with pytest.raises(ValueError):
        verify(root, pin, geometry_name='unknown')
    for mode in ('sampled', 'success-plus-sample', 'quick', ''):
        with pytest.raises(ValueError, match='only full'):
            verify(root, pin, mode=mode)


def test_runtime_observation_binding_is_optional_but_exact(evidence):
    root, pin = evidence
    runtime = json.loads((root/'environment.json').read_bytes())['runtime']
    assert verify(root, pin, expected_runtime=runtime)['independence']['runtime_independently_observed'] is True
    assert verify(root, pin)['independence']['runtime_independently_observed'] is False
    with pytest.raises(ValueError):
        verify(root, pin, expected_runtime=dict(runtime, platform='other'))


def test_source_checkout_difference_is_detected(evidence, monkeypatch):
    root, pin = evidence
    monkeypatch.setattr(ev, 'observe_sources', lambda repo: [dict(path='x', size=1, sha256='0'*64)])
    with pytest.raises(ValueError):
        verify(root, pin)


def test_failed_attempt_retains_evidence_and_cannot_be_verified_or_resumed(tmp_path, inputs, monkeypatch, capsys):
    secret = 'PRIVATE_V_SUCCESS_91827'
    logger = logging.getLogger('bounded-adversarial')
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    real = bounded.SHA256Engine.digest
    state = {'n': 0}

    def failing(self, raw):
        state['n'] += 1
        if state['n'] == 30:
            print(secret)
            logger.critical(secret)
            raise RuntimeError(secret)
        return real(self, raw)
    monkeypatch.setattr(bounded.SHA256Engine, 'digest', failing)
    root = tmp_path/'failed'
    try:
        with pytest.raises(KernelFailure) as failure:
            bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
    finally:
        logger.removeHandler(handler)
    observed = capsys.readouterr()
    assert secret not in observed.out + observed.err + str(failure.value) + ''.join(traceback.format_exception(failure.value))
    assert failure.value.__context__ is None
    assert (root/'INCOMPLETE').exists() and (root/'failure.json').exists() and not (root/'complete.json').exists()
    assert secret.encode() not in (root/'failure.json').read_bytes()
    retained = {p.name: p.read_bytes() for p in root.iterdir()}
    assert any(name.startswith('chunk-') for name in retained)
    with pytest.raises(ValueError):
        verify(root, '0'*64)
    monkeypatch.setattr(bounded.SHA256Engine, 'digest', real)
    with pytest.raises(KernelFailure):                       # no resume, no replacement, no repair
        bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
    assert {p.name: p.read_bytes() for p in root.iterdir()} == retained


@pytest.mark.parametrize('fault', ['gap', 'duplicate', 'drop', 'reorder', 'wrong-cluster'])
def test_producer_continuity_faults_cannot_complete(tmp_path, inputs, monkeypatch, fault):
    original = bounded._scheduled

    def broken(*args):
        rows = list(original(*args))
        if fault == 'gap':
            rows[0] = replace(rows[0], accepted_index=1)
        elif fault == 'duplicate':
            rows.insert(1, rows[0])
        elif fault == 'drop':
            rows.pop()
        elif fault == 'reorder':
            rows[0], rows[13] = rows[13], rows[0]
        else:
            j = next(i for i, a in enumerate(rows) if a.arm == 'A2' and a.stage == 'V')
            rows[j] = replace(rows[j], stage='D', cluster=0)
        yield from rows
    monkeypatch.setattr(bounded, '_scheduled', broken)
    root = tmp_path/'bad'
    with pytest.raises(KernelFailure):
        bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
    assert not (root/'complete.json').exists()


def test_allowed_finalization_extras_are_explicit(evidence):
    root, pin = evidence
    (root/'verification.json').write_bytes(b'{}')
    with pytest.raises(ValueError):
        verify(root, pin)
    assert verify(root, pin, allowed_extra=('verification.json',))['coverage']['candidates_rehashed'] == 78


# --------------------------------------------------- production plan binding

def producer_plan():
    runtime = plans.RuntimeBinding('CPython 3.13.0 engineering identity', 'unit-platform', '1'*64, (('PyYAML', '6.0.3', '2'*64),))
    return plans.ProductionPlan('16f8b30ae30a9ef3ffc0f2868e9508e70c8007cd',
        tuple(plans.Artifact(p, 1, '3'*64) for p in sorted(plans.REQUIRED_SOURCES)), runtime)


def test_independently_restated_production_plan_is_byte_identical_to_the_producer_plan():
    plan = producer_plan()
    rebuilt = ev.production_plan(plan.code_commit, [x.to_dict() for x in plan.sources], plan.runtime.to_dict())
    assert ev.encode(rebuilt) == plan.serialize()
    assert ev.seedless_sha256(plan.code_commit) == Plan(plan.code_commit).fingerprint
    from hashlab.experiments.exp002 import Config
    assert sha256(ev.encode(ev.config())).hexdigest() == sha256(canonical(Config().to_dict())).hexdigest()
    assert ev.encode(ev.science(plan.code_commit)) == canonical(plan.to_dict()['science'])
    assert plan.fingerprint == sha256(ev.encode(rebuilt)).hexdigest()


@pytest.mark.parametrize('mutation', [
    lambda p: p['science']['config'].update(per_stage=32), lambda p: p['seed'].update(domain='experiment-002-kat'),
    lambda p: p['controls'].update(n1_stop_exclusive=31000000), lambda p: p['restrictions'].update(execution_enabled=True),
    lambda p: p['history'].update(occurrences=60721), lambda p: p['identities'].update(governance='x'),
    lambda p: p['science']['streams'].pop(), lambda p: p['sources'].pop(), lambda p: p['runtime'].update(platform='x')])
def test_altered_production_plan_differs_from_the_independent_restatement(mutation):
    plan = producer_plan()
    obj = json.loads(plan.serialize())
    mutation(obj)
    assert ev.encode(obj) != ev.encode(ev.production_plan(plan.code_commit, [x.to_dict() for x in plan.sources],
                                                          plan.runtime.to_dict()))


def test_production_scope_rejects_bounded_evidence_shapes_before_any_generation(evidence, monkeypatch):
    root, pin = evidence
    def touched(*a, **k):
        pytest.fail('production-geometry verification generated candidates for bounded evidence')
    monkeypatch.setattr(v, 'attempts', touched)
    record = canonical(dict(schema=ev.SEED_RECORD_SCHEMA, kind='beacon', precommit='0'*40, round='1',
                            randomness_hex='0'*64, master=str(v.master_from_beacon('0'*40, 1, '0'*64)), domain='experiment-002'))
    with pytest.raises(ValueError):
        verify(root, pin, geometry_name='production', seed_record=record)


def test_off_machine_import_boundary_for_all_independent_production_modules():
    script = ("import sys;sys.path.insert(0,sys.argv[1]);import e002_verify.production,e002_verify.production_evidence,"
              "e002_verify.production_statistics;assert not any(n=='hashlab' or n.startswith('hashlab.') for n in sys.modules)")
    result = subprocess.run([sys.executable, '-B', '-c', script, str(REPO/'src')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_production_execution_remains_disabled_and_authentication_unavailable(tmp_path, evidence):
    root, pin = evidence
    for kwargs in ({}, {'master': 0}, {'enabled': True}, {'per_stage': 32}):
        with pytest.raises(PermissionError):
            kernel.run_production(tmp_path/'forbidden', **kwargs)
    assert not (tmp_path/'forbidden').exists()
    with pytest.raises(PermissionError):
        kernel.authenticate_capture(root, plan=producer_plan(), completion_sha256=pin)
    with pytest.raises(ValueError):
        kernel.authenticate_capture(root, plan=plans.EngineeringPlan(), completion_sha256=pin)


# ---------------------------------------- production binding contract (git-backed)

RUNTIME = {'python_version': 'CPython 3.13.0 test', 'platform': 'unit', 'interpreter_sha256': '1'*64,
           'dependencies': [['PyYAML', '6.0.3', '2'*64]]}


def tiny_repo(tmp_path):
    repo = tmp_path/'repo'
    (repo/'src/hashlab/experiments').mkdir(parents=True)
    (repo/'src/hashlab/__init__.py').write_text('x = 1\n')
    (repo/'src/hashlab/experiments/e001_contract.json').write_text('{}\n')
    def git(*args):
        return subprocess.run(['git', '-c', 'user.name=unit', '-c', 'user.email=unit@example.invalid', *args],
                              cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    git('init', '-q')
    git('add', '.')
    git('commit', '-q', '-m', 'unit')
    return repo, git('rev-parse', 'HEAD')


def production_binding(repo, commit, **changes):
    sources = ev.observe_sources(repo)
    plan = ev.encode(ev.production_plan(commit, sources, RUNTIME))
    environment = dict(schema=ev.SCOPES['production'], scope='production', runtime=RUNTIME, sources=sources,
                       source_commit_correspondence='committed;git-verified', runtime_approval='not-claimed')
    environment.update(changes)
    return plan, environment


def test_production_binding_accepts_only_committed_sources_and_the_restated_plan(tmp_path):
    repo, commit = tiny_repo(tmp_path)
    plan, environment = production_binding(repo, commit)
    assert ev.check_binding(v.FROZEN, plan, environment, repo, RUNTIME)[0] == commit
    assert ev.check_binding(v.FROZEN, plan, environment, repo)[0] == commit
    for bad_plan in (plan.replace(b'"per_stage":15000000', b'"per_stage":32'), plan[:-1], plan + b' ',
                     ev.encode(dict(json.loads(plan), extra=1))):
        with pytest.raises(ValueError):
            ev.check_binding(v.FROZEN, bad_plan, environment, repo)
    for change in (dict(schema=ev.SCOPES['bounded-fixture']), dict(scope='bounded-fixture'), dict(runtime_approval='approved'),
                   dict(source_commit_correspondence='unqualified;engineering-working-copy'),
                   dict(runtime=dict(RUNTIME, platform='')), dict(sources=[])):
        bad_plan, bad_env = production_binding(repo, commit, **change)
        with pytest.raises(ValueError):
            ev.check_binding(v.FROZEN, plan, bad_env, repo)
    with pytest.raises(ValueError):
        ev.check_binding(v.FROZEN, plan, environment, repo, dict(RUNTIME, platform='other'))
    wrong_commit, wrong_env = production_binding(repo, 'b'*40)
    with pytest.raises(ValueError):                              # HEAD is not the bound commit
        ev.check_binding(v.FROZEN, wrong_commit, wrong_env, repo)
    (repo/'src/hashlab/__init__.py').write_text('x = 2\n')       # working tree differs from the committed blob and the env
    with pytest.raises(ValueError):
        ev.check_binding(v.FROZEN, plan, environment, repo)
    changed_plan, changed_env = production_binding(repo, commit)
    with pytest.raises(ValueError, match='bound commit'):        # consistent but uncommitted source cannot qualify
        ev.check_binding(v.FROZEN, changed_plan, changed_env, repo)


def test_bounded_binding_never_claims_commit_correspondence(tmp_path):
    repo, commit = tiny_repo(tmp_path)
    environment = dict(schema=ev.SCOPES['bounded-fixture'], scope='bounded-fixture', runtime=RUNTIME,
                       sources=ev.observe_sources(repo), source_commit_correspondence='unqualified;engineering-working-copy',
                       runtime_approval='not-claimed')
    assert ev.check_binding(v.BOUNDED, ev.encode(ev.bounded_plan()), environment, repo) == (None, environment['sources'])
    with pytest.raises(ValueError):
        ev.check_binding(v.BOUNDED, ev.encode(ev.bounded_plan()), dict(environment, source_commit_correspondence='committed;git-verified'), repo)


def test_report_shape_matches_what_the_producer_side_parser_expects(evidence):
    from test_exp002_finalization import synthetic_report
    root, pin = evidence
    real, synthetic = verify(root, pin), synthetic_report()
    assert set(real) == set(synthetic)
    assert set(real['bindings']) == set(synthetic['bindings']) and set(real['coverage']) >= set(synthetic['coverage']) - {'chunks'}
    assert real['claims'] == synthetic['claims']
    assert real['schema'] == synthetic['schema'] and real['mode'] == synthetic['mode'] and real['verification'] == synthetic['verification']


# ------------------------------------------------------------------ SHA-256 status

def test_sha256_known_answers_and_declared_non_independence(evidence):
    import hashlib
    vectors = {b'': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
               b'abc': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
               b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq':
                   '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1',
               b'a'*1_000_000: 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0'}
    assert all(hashlib.sha256(m).hexdigest() == d for m, d in vectors.items())
    from hashlab.hashing.sha256 import SHA256Engine
    assert SHA256Engine().digest(b'abc').hex() == vectors[b'abc']
    root, pin = evidence
    backend = verify(root, pin)['independence']['sha256']
    assert backend['shared_with_producer'] is True and backend['r8_3_9_independent_implementation'] is False
    assert backend['implementation'] == 'hashlib.sha256' and 'known-answer' in backend['remaining_requirement']
    import inspect
    assert 'hashlib.sha256' in inspect.getsource(SHA256Engine)            # same library on the producer side


# ------------------------------------------------ D2: bundle and C_pre relationship

def commitment_inputs():
    from hashlab.experiments import exp002_finalization as producer
    plan = producer_plan()
    raw = beacon_record()
    master, digest, facts = ev.parse_seed_record(raw, v.FROZEN)
    commitment = ev.parse_seed_commitment(producer.seed_commitment(plan, raw), seed_record_sha=digest, facts=facts,
                                          master=master, code_commit=plan.code_commit)
    return producer, plan, facts, commitment


def test_bundle_binds_round_chain_and_frozen_seedless_identities():
    producer, plan, facts, commitment = commitment_inputs()
    bundle = producer.preregistration_bundle(plan, 1000)
    assert ev.parse_preregistration_bundle(bundle, facts=facts, commitment=commitment)['reveal_round'] == '1000'
    assert commitment['preregistration_bundle_sha256'] == facts['bundle_sha256'] == sha256(bundle).hexdigest()
    wrong = [producer.preregistration_bundle(plan, 1001), bundle + b' ', b'{}', b'x'*9000,
             canonical(dict(json.loads(bundle), chain_hash='0'*64)),
             canonical(dict(json.loads(bundle), seedless_plan_sha256='f'*64)),
             canonical(dict(json.loads(bundle), config_sha256=commitment['seeded_config_sha256'])),   # seeded digest in a frozen field
             canonical(dict(json.loads(bundle), extra=1))]
    for raw in wrong:
        with pytest.raises(ValueError):
            ev.parse_preregistration_bundle(raw, facts=facts, commitment=commitment)
    forged = dict(facts, bundle_sha256=sha256(wrong[5]).hexdigest())          # self-consistent digest, wrong content
    with pytest.raises(ValueError):
        ev.parse_preregistration_bundle(wrong[5], facts=forged, commitment=commitment)
    with pytest.raises(ValueError):
        ev.parse_preregistration_bundle(bundle, facts=dict(facts, round='1001'), commitment=commitment)
    with pytest.raises(ValueError):                                           # seeded == seedless would hide a missing seed
        ev.parse_preregistration_bundle(bundle, facts=facts, commitment=dict(commitment, seeded_config_sha256=commitment['config_sha256']))


def test_retained_bundle_must_be_the_exact_content_of_the_c_pre_commit(tmp_path):
    producer, plan, facts, commitment = commitment_inputs()
    bundle = producer.preregistration_bundle(plan, 1000)
    repo, _ = tiny_repo(tmp_path)
    (repo/'preregistration.json').write_bytes(bundle)
    for args in (['add', '.'], ['commit', '-q', '-m', 'c_pre']):
        subprocess.run(['git', '-c', 'user.name=unit', '-c', 'user.email=unit@example.invalid', *args], cwd=repo, check=True, capture_output=True)
    c_pre = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    ev.verify_c_seed(repo, c_pre, {'preregistration.json': bundle})
    with pytest.raises(ValueError):
        ev.verify_c_seed(repo, c_pre, {'preregistration.json': producer.preregistration_bundle(plan, 1001)})


def test_production_verification_also_requires_the_retained_bundle(evidence):
    root, pin = evidence
    producer, plan, facts, commitment = commitment_inputs()
    with pytest.raises(ValueError):
        verify(root, pin, geometry_name='production', seed_record=beacon_record(domain='experiment-002'),
               seed_commitment=producer.seed_commitment(plan, beacon_record()), c_seed='5'*40)
