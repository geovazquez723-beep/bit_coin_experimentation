"""G1-D: real-output blinding qualification of the production-disabled output boundary.

Scope: ordinary program interfaces only (stdout/stderr at file-descriptor level, logging, warnings, exception
text/tracebacks/chains, return values, repr/str/format, standard serialization).  Out of scope, by design: a
hostile operator with filesystem, debugger or deliberate-introspection access (the private files remain complete).

Sentinels are taken from the real bounded fixture: every raw and effective digest of every attempt, and the
numeric leaves of the private statistics payload computed from artificial counts.  Injected "PRIVATE_*" markers
are emitted from inside the failing code paths (print, logging, warnings, exception messages).
"""
from contextlib import contextmanager
from pathlib import Path
import copy
import errno
import json
import logging
import pickle
import sys
import traceback
import warnings

import pytest

from hashlab.experiments import exp002_finalization as fin  # noqa: F401
from hashlab.experiments import exp002_kernel as kernel
from hashlab.experiments import exp002_kernel_bounded as bounded
from hashlab.experiments import exp002_kernel_disclosure as disclosure
from hashlab.experiments import exp002_kernel_evidence as binary
from hashlab.experiments import exp002_kernel_inference as inference
from hashlab.experiments import exp002_kernel_statistics as statistics
from hashlab.experiments.exp002_controls import Feistel64
from hashlab.experiments.exp002_kernel_disclosure import KernelFailure
from test_exp002_finalization import COUNTS, PLAN, unit_capture
from test_exp002_production_verification import (AUDIT, REPO, evidence, inputs, original, read_rows,  # noqa: F401
                                                 rewrite, verify)

MARK = 'PRIVATE_V_SUCCESS_5521'


class Observation:
    def __init__(self):
        self.records, self.warns, self.pieces = [], [], []

    def note(self, *values):
        self.pieces.extend(values)

    def exception(self, exc):
        seen = set()
        while exc is not None and id(exc) not in seen:
            seen.add(id(exc))
            self.pieces.append(''.join(traceback.format_exception(exc)))
            self.pieces.append(repr(exc) + str(exc) + repr(exc.args))
            exc = exc.__cause__ or exc.__context__

    def text(self, capfd):
        out, err = capfd.readouterr()
        logs = ' '.join(r.getMessage() + ' ' + str(r.args) for r in self.records)
        return ' '.join([out, err, logs] + [str(w.message) for w in self.warns] + [str(p) for p in self.pieces])


@contextmanager
def observed(capfd):
    obs = Observation()

    class Collect(logging.Handler):
        def emit(self, record):
            obs.records.append(record)

    handler, root = Collect(level=0), logging.getLogger()
    previous_level, previous_disable = root.level, logging.root.manager.disable
    root.addHandler(handler)
    root.setLevel(0)
    logging.disable(logging.NOTSET)
    capfd.readouterr()
    try:
        with warnings.catch_warnings():              # default delivery: warnings go to sys.stderr
            warnings.simplefilter('always')
            yield obs
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        logging.disable(previous_disable)


def noisy(secret=MARK):
    """Emit a secret through every ordinary side channel."""
    print(secret)
    print(secret, file=sys.stderr)
    logging.getLogger('g1d').critical(secret)
    warnings.warn(secret)


def sentinels(root):
    values = set()
    for _attempt, raw, effective in read_rows(root):
        values.update(bytes(x).hex() for x in (raw, effective) if x is not None)
    from hashlab.experiments import exp002_kernel_inference as k
    flat = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, float):
            flat.append(repr(x))
    walk(k._calculate(COUNTS))
    values.update(v for v in flat if len(v) >= 8)
    assert len(values) > 50
    return values


def assert_clean(text, secrets, extra=()):
    leaked = [s for s in list(secrets) + list(extra) if s in text]
    assert not leaked, leaked[:3]


# ------------------------------------------------------------------ failure paths of the producer

def failing_hash(monkeypatch, exception):
    real, state = bounded.SHA256Engine.digest, {'n': 0}

    def digest(self, raw):
        state['n'] += 1
        if state['n'] == 30:
            noisy()
            raise exception
        return real(self, raw)
    monkeypatch.setattr(bounded.SHA256Engine, 'digest', digest)


@pytest.mark.parametrize('name', ['hash-runtime', 'hash-interrupt', 'hash-memory', 'generation', 'serialization-memory',
                                  'write-enospc', 'finalization-enospc'])
def test_producer_failure_paths_emit_nothing_sensitive_and_retain_evidence(tmp_path, inputs, monkeypatch, capfd, name):
    if name == 'hash-runtime':
        failing_hash(monkeypatch, RuntimeError(MARK))
    elif name == 'hash-interrupt':
        failing_hash(monkeypatch, KeyboardInterrupt(MARK))
    elif name == 'hash-memory':
        failing_hash(monkeypatch, MemoryError(MARK))
    elif name == 'generation':
        real, state = Feistel64.forward, {'n': 0}

        def forward(self, value):
            state['n'] += 1
            if state['n'] == 5:
                noisy()
                raise RuntimeError(MARK)
            return real(self, value)
        monkeypatch.setattr(Feistel64, 'forward', forward)
    elif name == 'serialization-memory':
        real, state = binary.encode_row, {'n': 0}

        def encode(*a, **k):
            state['n'] += 1
            if state['n'] == 20:
                noisy()
                raise MemoryError(MARK)
            return real(*a, **k)
        monkeypatch.setattr(binary, 'encode_row', encode)
    elif name == 'write-enospc':
        def fsync(fd):
            noisy()
            raise OSError(errno.ENOSPC, MARK)
        monkeypatch.setattr(binary.os, 'fsync', fsync)
    else:
        real_create = bounded.durable_create

        def create(path, raw):
            if Path(path).name == 'complete.json':
                noisy()
                raise OSError(errno.ENOSPC, MARK)
            return real_create(path, raw)
        monkeypatch.setattr(bounded, 'durable_create', create)
    root = tmp_path / 'run'
    with observed(capfd) as obs:
        with pytest.raises(KernelFailure) as failure:
            bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
        obs.exception(failure.value)
    assert_clean(obs.text(capfd), [MARK])
    assert failure.value.__context__ is None and failure.value.__cause__ is None
    assert not (root / 'complete.json').exists()
    if root.exists() and (root / 'failure.json').exists():
        assert MARK.encode() not in (root / 'failure.json').read_bytes()
        assert json.loads((root / 'failure.json').read_bytes()).get('primary') == 'withheld'


def test_normal_run_progress_status_inspection_and_verifier_report_are_clean(tmp_path, inputs, capfd):
    root = tmp_path / 'run'
    with observed(capfd) as obs:
        outcome = bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
        obs.note(repr(outcome), str(outcome), json.dumps(outcome.to_dict()), disclosure.progress('processing', 7))
        report = verify(root, outcome.completion_sha256)
        obs.note(json.dumps(report, sort_keys=True), repr(report))
    secrets = sentinels(root)
    assert_clean(obs.text(capfd), secrets)
    assert set(outcome.to_dict()) == {'status', 'scope', 'completion_sha256'}
    assert report['claims']['disclosure_authorized'] is False and report['claims']['execution_authorized'] is False


# ------------------------------------------------------------------ verifier rejection

@pytest.mark.parametrize('mutation', ['transport', 'semantic-raw', 'semantic-effective'])
def test_verifier_rejection_text_contains_no_digest_or_outcome(evidence, capfd, mutation):
    root, pin = evidence
    secrets = sentinels(root)
    if mutation == 'transport':
        chunk = root / 'chunk-00000000.bin'
        data = bytearray(chunk.read_bytes())
        data[-5] ^= 1
        chunk.write_bytes(bytes(data))
    else:
        rows = read_rows(root)
        column = 1 if mutation == 'semantic-raw' else 2
        forged = bytes([rows[4][column][0] ^ 1]) + rows[4][column][1:]
        rows[4][column] = forged
        pin = rewrite(root, rows)
        secrets |= {forged.hex()}
    with observed(capfd) as obs:
        with pytest.raises(ValueError) as failure:
            verify(root, pin)
        obs.exception(failure.value)
    assert_clean(obs.text(capfd), secrets)
    assert len(str(failure.value)) < 200


# ------------------------------------------------------------------ numerical-inference failure and F1-F4

def test_numerical_inference_failure_is_sanitized(tmp_path, monkeypatch, capfd):
    secrets = {MARK, '0.0123456789', '9.87654321e-05'}

    def ambiguous(*a):
        noisy()
        raise ArithmeticError(MARK + ' ' + ' '.join(secrets))
    monkeypatch.setattr(inference.secondary, 'analyze_secondary', ambiguous)
    destination = tmp_path / 'statistics.json'
    with observed(capfd) as obs:
        with pytest.raises(KernelFailure) as one:
            inference.infer_measured(unit_capture(), plan=PLAN)
        with pytest.raises(KernelFailure) as two:
            statistics.commit_statistics(unit_capture(), plan=PLAN, destination=destination)
        obs.exception(one.value)
        obs.exception(two.value)
    assert_clean(obs.text(capfd), secrets)
    assert not destination.exists()
    assert one.value.__context__ is None and two.value.__context__ is None


def test_failure_reports_and_f4_disclosure_restrictions():
    for code in ('F1', 'F2', 'F3'):
        report = disclosure.failure_report(code)
        assert report['primary'] == 'withheld' and report['validation'] == 'withheld' and set(report) == {
            'status', 'failure', 'primary', 'validation'}
    with pytest.raises(ValueError):
        disclosure.failure_report('F4')                           # requires authenticated control inference
    with pytest.raises(ValueError):
        disclosure.progress('PRIVATE_COUNTER', 1)
    with pytest.raises(ValueError):
        disclosure.progress('processing', -1)
    counts = __import__('hashlab.experiments.exp002_integration', fromlist=['x']).count_fixtures(REPO)['cases']
    passing = disclosure.RestrictedInference(inference._calculate(counts[0]['accounting']), _token=disclosure._INFERENCE)
    failed = disclosure.RestrictedInference(inference._calculate(counts[2]['accounting']), _token=disclosure._INFERENCE)
    with pytest.raises(PermissionError):
        passing.disclose_f4()                                      # gate passed: nothing may be disclosed
    with pytest.raises(PermissionError):
        failed.disclose_final()                                    # no final-disclosure adapter exists
    assert failed.disclose_f4()['failure'] == 'F4'


# ------------------------------------------------------------------ ordinary serialization interfaces

@pytest.fixture
def restricted(tmp_path):
    result, _pin = statistics.commit_statistics(unit_capture(), plan=PLAN, destination=tmp_path / 's.json')
    return result


@pytest.mark.parametrize('operation', ['pickle', 'pickle-protocol-0', 'copy', 'deepcopy', 'reduce-ex'])
@pytest.mark.parametrize('subject', ['restricted', 'capture'])
def test_private_wrappers_cannot_be_serialized_or_copied_through_standard_interfaces(restricted, subject, operation):
    value = restricted if subject == 'restricted' else unit_capture()
    actions = {'pickle': lambda: pickle.dumps(value), 'pickle-protocol-0': lambda: pickle.dumps(value, protocol=0),
               'copy': lambda: copy.copy(value), 'deepcopy': lambda: copy.deepcopy(value),
               'reduce-ex': lambda: value.__reduce_ex__(2)}
    with pytest.raises(TypeError):
        actions[operation]()


def test_private_wrapper_text_forms_withhold(restricted):
    for form in (repr(restricted), str(restricted), format(restricted, ''), f'{restricted}', '%s' % restricted):
        assert 'withheld' in form and 'p_value' not in form and 'discovery' not in form
    form = repr(unit_capture()) + str(unit_capture())
    assert 'withheld' in form and 'streams' not in form
    assert restricted.inspect() == dict(primary='withheld', validation='withheld', final_disclosure='authorization-unavailable')
