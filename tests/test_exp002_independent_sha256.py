"""Independent candidate-evaluation SHA-256 (Revision 8 section 3.9): algorithmic qualification only.

Bounded vectors and the 78-evaluation fixture; no production audit, QA2 or E002 run. Operational
(full-scale) feasibility is a separate, open question documented in the handoff.
"""
from hashlib import sha256 as openssl_sha256
from pathlib import Path
import json
import os
import random
import subprocess
import sys

import pytest

from hashlab.hashing.sha256 import SHA256Engine
from e002_verify import production as v
from e002_verify import production_evidence as ev
from e002_verify import sha256_independent as ind
from e002_verify import sha256_reference as reference
from e002_verify.core import empty_accounting

from test_exp002_production_verification import AUDIT, REPO, SEED, evidence, inputs, original, unit_inputs, verify  # noqa: F401

BACKENDS = ind.BACKENDS if sys.platform == 'win32' else ('hacl', 'reference')
BOUNDARIES = (0, 1, 55, 56, 57, 63, 64, 65, 119, 120, 121, 127, 128, 129, 191, 192, 1000)


def hasher(backend):
    return ind.CandidateHasher(backend)


def native(backend):
    return ind._FACTORIES[backend]()


# ------------------------------------------------------------ known answers

@pytest.mark.parametrize('backend', BACKENDS)
def test_published_known_answers(backend):
    digest = native(backend)
    for message, expected in ind.KNOWN_ANSWERS:
        if backend == 'reference' and len(message) > 1000:
            continue
        assert digest(message).hex() == expected
    assert hasher(backend).identity()['known_answers'] == 'passed'


def test_reference_oracle_matches_the_million_a_vector():
    assert reference.sha256(b'a' * 1_000_000).hex() == 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0'


def test_known_answer_table_is_the_published_fips_set_and_agrees_with_the_accepted_repository_tests():
    assert len(ind.KNOWN_ANSWERS) == 5
    assert dict(ind.KNOWN_ANSWERS)[b'abc'] == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    assert dict(ind.KNOWN_ANSWERS)[b''] == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    for message, expected in ind.KNOWN_ANSWERS:                                  # producer and OpenSSL agree too
        assert SHA256Engine().digest(message).hex() == expected


# ------------------------------------------------------ differential agreement

@pytest.mark.parametrize('backend', BACKENDS)
def test_padding_boundaries_and_binary_inputs_agree_with_reference_and_producer(backend):
    digest, rnd = native(backend), random.Random(20261015)
    messages = [bytes(n) for n in BOUNDARIES] + [b'\xff' * n for n in BOUNDARIES] + [b'\x00\x80\xff\x7f' * (n // 4) for n in BOUNDARIES]
    messages += [bytes(rnd.getrandbits(8) for _ in range(n)) for n in BOUNDARIES]
    messages += [bytes([i]) for i in range(0, 256, 17)]
    for message in messages:
        expected = reference.sha256(message)
        assert digest(message) == expected == SHA256Engine().digest(message) == openssl_sha256(message).digest()


@pytest.mark.parametrize('backend', BACKENDS)
def test_candidate_encodings_from_the_bounded_stream_agree_exactly_with_the_producer(backend):
    candidates = [row[3] for row in v.attempts(v.BOUNDED, 0, frozenset(), ())]
    assert {len(c) for c in candidates} == {8, 80} and len(candidates) >= 78
    h, engine = hasher(backend), SHA256Engine()
    for candidate in candidates:
        raw = h.digest(candidate)
        assert raw == engine.digest(candidate) and len(raw) == 32
        assert int.from_bytes(raw, 'big') == int(openssl_sha256(candidate).hexdigest(), 16)    # big-endian order


def test_digest_byte_order_is_big_endian_with_the_first_byte_most_significant():
    digest = native('hacl')(b'abc')
    assert digest[:4].hex() == 'ba7816bf' and digest[-4:].hex() == 'f20015ad'
    assert int.from_bytes(digest, 'big') == 0xba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    assert int.from_bytes(digest, 'little') != int.from_bytes(digest, 'big')


@pytest.mark.parametrize('backend', BACKENDS)
def test_repeated_calls_and_interleaving_have_no_shared_state(backend):
    h = hasher(backend)
    a, b = bytes(range(8)), bytes(range(80))
    first = (h.digest(a), h.digest(b))
    for _ in range(5):
        assert (h.digest(b), h.digest(a), h.digest(b), h.digest(a)) == (first[1], first[0], first[1], first[0])
    other = hasher(backend)
    assert other.digest(a) == first[0] and h.digest(a) == first[0]


# -------------------------------------------------- strict input / fail-closed

@pytest.mark.parametrize('backend', BACKENDS)
def test_candidate_interface_accepts_only_8_and_80_raw_bytes(backend):
    h = hasher(backend)
    for bad in ('abcdefgh', bytearray(8), memoryview(bytes(8)), None, 8, [0] * 8, b'', bytes(7), bytes(9), bytes(79), bytes(81), bytes(64)):
        with pytest.raises(ValueError):
            h.digest(bad)
    assert len(h.digest(bytes(8))) == len(h.digest(bytes(80))) == 32


@pytest.mark.parametrize('name', ['hashlib', 'openssl', 'sha256', '', None, 'HACL', 'cng ', 'hmac'])
def test_non_independent_or_unknown_backends_are_refused(name):
    with pytest.raises(ind.BackendUnavailable):
        ind.CandidateHasher(name)


def test_unavailable_backend_fails_closed(monkeypatch):
    monkeypatch.setitem(sys.modules, '_sha2', None)
    with pytest.raises(ind.BackendUnavailable):
        ind.CandidateHasher('hacl')
    monkeypatch.undo()
    monkeypatch.setattr(sys, 'platform', 'linux')
    with pytest.raises(ind.BackendUnavailable):
        ind.CandidateHasher('cng')


def test_a_backend_that_fails_known_answers_is_refused(monkeypatch):
    monkeypatch.setitem(ind._FACTORIES, 'hacl', lambda: (lambda data: bytes(32)))
    with pytest.raises(ind.BackendUnavailable):
        ind.CandidateHasher('hacl')
    monkeypatch.setitem(ind._FACTORIES, 'hacl', lambda: (lambda data: openssl_sha256(data + b'x').digest()))
    with pytest.raises(ind.BackendUnavailable):
        ind.CandidateHasher('hacl')


def test_verifier_refuses_to_start_without_an_independent_backend(evidence):
    root, pin = evidence
    with pytest.raises(ind.BackendUnavailable):
        verify(root, pin, candidate_backend='hashlib')
    with pytest.raises(ind.BackendUnavailable):
        ev.verify_evidence(Path('does-not-exist'), completion_sha256='0' * 64, geometry_name='bounded-fixture', seed_record=SEED,
                           audit_root=AUDIT, repository_root=REPO, candidate_backend='openssl')


# -------------------------------------------------------- independence evidence

def test_hacl_backend_is_a_different_implementation_object_than_the_producer_backend():
    import _sha2
    import hashlib
    assert type(_sha2.sha256(b'')).__module__ == '_sha2'
    assert type(hashlib.sha256()).__module__ == '_hashlib'            # producer: OpenSSL in this runtime
    assert _sha2.sha256 is not hashlib.sha256
    identity = hasher('hacl').identity()
    assert identity['independent_of_producer'] is True and identity['shared_with_producer'] is False
    assert 'HACL' in identity['lineage'] and len(identity['interpreter_sha256']) == 64
    assert ind.file_integrity_backend()['used_for_candidate_evaluation'] is False


def test_hacl_backend_works_with_openssl_modules_blocked():
    script = (
        "import sys\nsys.modules['_hashlib'] = None\nsys.modules['_ssl'] = None\nsys.modules['ssl'] = None\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from e002_verify import sha256_independent as s\n"
        "h = s.CandidateHasher('hacl')\n"
        "assert h.digest(bytes(8)).hex() == 'af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc'\n"
        "assert '_hashlib' not in [k for k, v in sys.modules.items() if v is not None]\n"
        "print('ok')\n")
    result = subprocess.run([sys.executable, '-B', '-c', script, str(REPO / 'src')], capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip() == 'ok', result.stderr


def test_candidate_loop_never_uses_hashlib(evidence, monkeypatch):
    root, pin = evidence
    real = ev.sha256

    def guarded(data=b'', *a, **k):
        assert len(data) not in (8, 80), 'candidate bytes reached the file-integrity hash'
        return real(data, *a, **k)
    monkeypatch.setattr(ev, 'sha256', guarded)
    assert verify(root, pin)['coverage']['candidates_rehashed'] == 78


def test_independent_module_does_not_import_the_producer():
    script = ("import sys;sys.path.insert(0,sys.argv[1]);import e002_verify.sha256_independent,e002_verify.production_evidence;"
              "assert not any(n=='hashlab' or n.startswith('hashlab.') for n in sys.modules)")
    result = subprocess.run([sys.executable, '-B', '-c', script, str(REPO / 'src')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# ------------------------------------------- bounded replay through each backend

@pytest.mark.parametrize('backend', BACKENDS)
def test_bounded_replay_is_exact_for_every_independent_backend(evidence, backend):
    root, pin = evidence
    report = verify(root, pin, candidate_backend=backend)
    assert report['coverage']['candidates_rehashed'] == 78 and report['coverage']['compression_blocks'] == 106
    identity = report['independence']['candidate_sha256']
    assert identity['backend'] == backend and identity['independent_of_producer'] is True
    assert report['independence']['file_integrity_sha256']['used_for_candidate_evaluation'] is False
    baseline = verify(root, pin)
    assert {k: v for k, v in report.items() if k != 'independence'} == {k: v for k, v in baseline.items() if k != 'independence'}


@pytest.mark.parametrize('manipulation', ['raw-bit', 'zero', 'short', 'long', 'openssl-of-other'])
def test_manipulated_digests_from_the_backend_are_rejected(evidence, monkeypatch, manipulation):
    root, pin = evidence
    real = ind.CandidateHasher.evaluator
    state = {'n': 0}

    def evaluator(self):
        inner = real(self)

        def digest(candidate):
            state['n'] += 1
            raw = inner(candidate)
            if state['n'] != 5:
                return raw
            return {'raw-bit': bytes([raw[0] ^ 1]) + raw[1:], 'zero': bytes(32), 'short': raw[:31], 'long': raw + b'\0',
                    'openssl-of-other': openssl_sha256(candidate + b'x').digest()}[manipulation]
        return digest
    monkeypatch.setattr(ind.CandidateHasher, 'evaluator', evaluator)
    with pytest.raises(ValueError):
        verify(root, pin)


def test_success_rule_target_boundaries_with_injected_digests():
    target = 2**248
    assert v.TARGET == target
    cases = {target - 1: True, target: False, target + 1: False, 0: True, 2**256 - 1: False, 2**247: True}
    accounting = empty_accounting()
    row = next(r for r in accounting['streams'] if (r['arm'], r['stage']) == ('A1', 'D'))
    expected_successes = 0
    for value, success in cases.items():
        digest = value.to_bytes(32, 'big')
        assert ev.tally(row, digest, bytes(8), 'A1', None) is success
        expected_successes += success
    assert row['trials'] == len(cases) and row['successes'] == expected_successes == 3
    assert row['first_byte'][0] == 3 and row['first_byte'][1] == 2 and row['first_byte'][255] == 1
    assert row['leading_zero_bits'][8] == 2 and row['leading_zero_bits'][7] == 2
    assert row['leading_zero_bits'][0] == 1 and row['leading_zero_bits'][256] == 1
    assert sum(row['leading_zero_bits']) == len(cases) == sum(row['first_byte'])


def test_tally_updates_cluster_and_weight_counters_without_changing_success_rule():
    accounting = empty_accounting()
    rows = {(r['arm'], r['stage']): r for r in accounting['streams']}
    ev.tally(rows['A2', 'V'], (2**248 - 1).to_bytes(32, 'big'), bytes(80), 'A2', 1501)
    ev.tally(rows['A3', 'D'], (2**248).to_bytes(32, 'big'), (2**33 + 1).to_bytes(8, 'big'), 'A3', None)
    assert rows['A2', 'V']['cluster_trials'][1] == 1 and rows['A2', 'V']['cluster_successes'][1] == 1
    assert rows['A3', 'D']['weight_trials'][1] == 1 and rows['A3', 'D']['weight_successes'][1] == 0


@pytest.mark.parametrize('mode', ['P1', 'P2+', 'P2-'])
def test_control_transformations_unchanged_at_target_boundaries(mode):
    t = 2**248
    for value in (t - 1, t, t + 1):
        for u in (0, v.THRESHOLDS[mode] - 1, v.THRESHOLDS[mode], 2**32 - 1):
            raw = ((value & ~(2**32 - 1)) | u).to_bytes(32, 'big')
            effective = int.from_bytes(v.transform(mode, raw), 'big')
            if mode == 'P2-':
                lifted = int.from_bytes(raw, 'big') < t and u < v.THRESHOLDS[mode]
                assert effective == int.from_bytes(raw, 'big') + (t if lifted else 0)
            else:
                lifted = int.from_bytes(raw, 'big') >= t and u < v.THRESHOLDS[mode]
                assert effective == (int.from_bytes(raw, 'big') % t if lifted else int.from_bytes(raw, 'big'))


def test_candidate_widths_in_the_verifier_stream_are_only_8_and_80():
    widths = {len(row[3]) for row in v.attempts(v.BOUNDED, 0, frozenset(), ())}
    assert widths == {8, 80}


def test_identity_pins_the_binary_that_actually_contains_the_builtin_sha2():
    identity = hasher('hacl').identity()
    container = identity['sha2_container']
    assert container['builtin_module'] is True and Path(container['path']).is_file()
    assert container['sha256'] == openssl_sha256(Path(container['path']).read_bytes()).hexdigest()
    assert container['hacl_source_tree_marker_present'] is True
    assert identity['interpreter_sha256'] == openssl_sha256(Path(sys.executable).read_bytes()).hexdigest()
    if sys.platform == 'win32':       # the small launcher does not contain _sha2; the loaded python3XY.dll does
        assert Path(container['path']).name.lower() == 'python%d%d.dll' % sys.version_info[:2]
        assert container['sha256'] != identity['interpreter_sha256']


def test_the_actual_verifier_report_carries_the_container_identity(evidence):
    root, pin = evidence
    candidate = verify(root, pin)['independence']['candidate_sha256']
    assert candidate['backend'] == 'hacl' and candidate['sha2_container']['sha256'] == hasher('hacl').identity()['sha2_container']['sha256']
