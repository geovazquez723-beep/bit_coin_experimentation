"""G1-D / D-3: a producer/verifier stream mismatch is a disclosed failure, never a waiver, retry or seed replacement.

The independent verifier is made to consume one extra 64-bit block in its A1 sampler (the observable effect of
the rare enclosure-width refinement difference).  Producer refinement logging is NOT implemented or commissioned.
"""
import inspect
import json

import pytest

from e002_verify import production as prod
from e002_verify import production_evidence as ev
from test_exp002_production_verification import SEED, evidence, inputs, original, verify  # noqa: F401


def snapshot(root):
    return {p.name: p.read_bytes() for p in sorted(root.iterdir())}


def test_verifier_has_no_waiver_retry_tolerance_or_seed_parameters():
    parameters = set(inspect.signature(ev.verify_evidence).parameters)
    assert not {p for p in parameters if any(w in p for w in ('waive', 'retry', 'tolerance', 'ignore', 'resume', 'repair'))}
    with pytest.raises(ValueError):
        ev.verify_evidence('x', completion_sha256='0' * 64, geometry_name='bounded-fixture', seed_record=SEED,
                           audit_root='x', repository_root='x', mode='sampled')


def test_extra_consumed_block_is_a_failure_with_one_pass_no_report_and_unchanged_evidence(evidence, monkeypatch):
    root, pin = evidence
    before = snapshot(root)
    real, calls = prod._skip, {'n': 0}

    def skipping(N, n, rng):
        calls['n'] += 1
        if calls['n'] == 3:
            rng.getrandbits(64)                       # one refinement block the producer did not consume
        return real(N, n, rng)
    monkeypatch.setattr(prod, '_skip', skipping)
    with pytest.raises(ValueError) as failure:
        verify(root, pin)
    first_pass_calls = calls['n']
    assert first_pass_calls >= 3 and len(str(failure.value)) < 200
    assert snapshot(root) == before                   # evidence retained, nothing repaired or rewritten
    calls['n'] = 0
    with pytest.raises(ValueError):                   # deterministic: the same failure, not a different outcome on retry
        verify(root, pin)
    assert calls['n'] == first_pass_calls             # exactly one pass per call: no hidden retry loop
    monkeypatch.setattr(prod, '_skip', real)
    assert verify(root, pin)['claims']['independent_regeneration_and_rehash'] is True   # genuine evidence still verifies


def test_a_mismatch_cannot_be_overridden_by_a_replacement_seed(evidence, monkeypatch):
    root, pin = evidence
    real = prod._skip
    monkeypatch.setattr(prod, '_skip', lambda N, n, rng: (rng.getrandbits(64), real(N, n, rng))[1])
    other = json.dumps(dict(schema=ev.SEED_RECORD_SCHEMA, kind='public-engineering', master='1', domain='experiment-002-kat'),
                       sort_keys=True, separators=(',', ':')).encode()
    for seed in (SEED, other):
        with pytest.raises(ValueError):
            verify(root, pin, seed_record=seed)
