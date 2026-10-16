"""G1-B: synthetic resource-failure qualification. Engineering fixtures only; no production activation.

Each failure must (1) raise a sanitized failure, (2) never leave a completion marker or a passing reader,
(3) retain evidence, (4) not retry, replace a seed or re-run a stream, and (5) disclose no results.
"""
import errno
import hashlib
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from hashlab.experiments import exp002_kernel as k
from hashlab.experiments import exp002_kernel_evidence as binary
from hashlab.experiments import exp002_kernel_disclosure as disclosure
from hashlab.experiments import exp002_kernel_plan as plans
from hashlab.experiments import exp002_resource_preflight as preflight
from hashlab.experiments.exp002_foundation import canonical
from hashing_fixture import synthetic_hashing_identity
from test_exp002_kernel import AUDIT, REPO, reseal_transport, unit_inputs, verify as reference_verify

ENOSPC = OSError(errno.ENOSPC, 'No space left on device')


@pytest.fixture
def inputs(monkeypatch):
    return unit_inputs(monkeypatch)


@pytest.fixture
def spies(monkeypatch):
    """Count scheduling passes and base evaluations: a silent retry would raise either counter."""
    calls = dict(schedule=0, digest=0)
    original_schedule, original_digest = k._scheduled_attempts, k.SHA256Engine.digest

    def schedule(*args):
        calls['schedule'] += 1
        yield from original_schedule(*args)

    def digest(self, data):
        calls['digest'] += 1
        return original_digest(self, data)

    monkeypatch.setattr(k, '_scheduled_attempts', schedule)
    monkeypatch.setattr(k.SHA256Engine, 'digest', digest)
    return calls


def assert_retained_failure(root, calls=None):
    assert (root / 'INCOMPLETE').exists() or not (root / 'complete.json').exists()
    assert not (root / 'complete.json').exists()
    failure = root / 'failure.json'
    if failure.exists():                                  # may legitimately be absent when the volume is full
        assert failure.read_bytes() == canonical(disclosure.failure_report('F1'))
    if calls is not None:
        assert calls['schedule'] <= 1 and calls['digest'] <= 206           # no retry, no second pass
    with pytest.raises(Exception):                         # neither reader accepts it, whatever pin is offered
        k.authenticate_capture(root, plan=plans.EngineeringPlan(), completion_sha256='0' * 64)
    with pytest.raises(disclosure.KernelFailure):          # no resume/repair into the same directory
        k.run_engineering(root, audit_root=AUDIT, repository_root=REPO)


def run_failing(tmp_path, spies):
    root = tmp_path / 'run'
    with pytest.raises(disclosure.KernelFailure) as exc:
        k.run_engineering(root, audit_root=AUDIT, repository_root=REPO)
    assert exc.value.__context__ is None and 'No space' not in str(exc.value)
    return root


class FullDisk:
    """File wrapper that raises ENOSPC after ``allowed`` bytes."""
    def __init__(self, handle, allowed):
        self.handle, self.allowed, self.written = handle, allowed, 0

    def write(self, data):
        if self.written + len(data) > self.allowed:
            raise ENOSPC
        self.written += len(data)
        return self.handle.write(data)

    def __getattr__(self, name):
        return getattr(self.handle, name)


@pytest.mark.parametrize('stage', ['chunk-create', 'chunk-write-early', 'chunk-write-late', 'fsync', 'index-write',
                                   'accounting', 'complete'])
def test_disk_full_never_completes_and_never_retries(tmp_path, inputs, monkeypatch, spies, stage):
    if stage == 'chunk-create':
        monkeypatch.setattr(binary.ChunkWriter, '_start', lambda self: (_ for _ in ()).throw(ENOSPC))
    elif stage in ('chunk-write-early', 'chunk-write-late'):
        original = binary.ChunkWriter._start
        allowed = 40 if stage == 'chunk-write-early' else 20_000

        def start(self):
            original(self)
            self.handle = FullDisk(self.handle, allowed)
        monkeypatch.setattr(binary.ChunkWriter, '_start', start)
    elif stage == 'fsync':
        monkeypatch.setattr(binary.os, 'fsync', lambda fd: (_ for _ in ()).throw(ENOSPC))
    elif stage == 'index-write':
        original_init = binary.ChunkWriter.__init__

        def init(self, root):
            original_init(self, root)
            self.index = FullDisk(self.index, 10)
        monkeypatch.setattr(binary.ChunkWriter, '__init__', init)
    else:
        name = dict(accounting='accounting.json', complete='complete.json')[stage]
        original_create = k.durable_create

        def create(path, raw):
            if Path(path).name == name:
                raise ENOSPC
            return original_create(path, raw)
        monkeypatch.setattr(k, 'durable_create', create)
    root = run_failing(tmp_path, spies)
    assert_retained_failure(root, spies)


@pytest.mark.parametrize('error', [MemoryError(), KeyboardInterrupt(), OSError(errno.EIO, 'I/O error')])
@pytest.mark.parametrize('where', ['accumulate', 'encode', 'hash'])
def test_allocation_failure_interruption_and_io_error(tmp_path, inputs, monkeypatch, spies, where, error):
    def fail(*args, **kwargs):
        raise error
    if where == 'accumulate':
        monkeypatch.setattr(k.Accumulator, 'add', fail)
    elif where == 'encode':
        monkeypatch.setattr(binary, 'encode_row', fail)
    else:
        monkeypatch.setattr(k.SHA256Engine, 'digest', fail)
    root = run_failing(tmp_path, spies)
    assert_retained_failure(root)


def test_insufficient_free_space_fails_before_anything_is_created(tmp_path, monkeypatch):
    destination = tmp_path / 'run'
    required = preflight.required_free_bytes()
    free = type('U', (), {'free': required - 1})
    monkeypatch.setattr(preflight.shutil, 'disk_usage', lambda path: free)
    with pytest.raises(ValueError, match='insufficient free space'):
        binary.create_root(destination, repository=REPO, audit_root=AUDIT, minimum_free_bytes=required)
    assert not destination.exists() and list(tmp_path.iterdir()) == []
    monkeypatch.setattr(preflight.shutil, 'disk_usage', lambda path: type('U', (), {'free': required})())
    root = binary.create_root(destination, repository=REPO, audit_root=AUDIT, minimum_free_bytes=required)
    assert (root / 'INCOMPLETE').exists()


def test_preflight_byte_model_matches_the_frozen_row_layout():
    from hashlab.experiments.exp002_kernel_evidence import Attempt, encode_row
    a8 = Attempt('A1', 'D', (2**20).to_bytes(8, 'big'), 0, population_rank=0)
    a80 = Attempt('A2', 'D', bytes(76) + bytes(4), 0, source_index=0, cluster=0)
    assert len(encode_row(0, a8, bytes(32), bytes(32))) == binary.ROW.size + 8 + preflight.DIGESTS == 120
    assert len(encode_row(0, a80, bytes(32), bytes(32))) == binary.ROW.size + 80 + preflight.DIGESTS == 192
    assert preflight.accepted_rows()['P1'] == 200_000 and sum(preflight.accepted_rows().values()) == 180_200_000
    exact = 120_200_000 * 120 + 60_000_000 * 192
    assert exact == 25_944_000_000
    assert exact < preflight.evidence_bytes(0) < exact * 1.01 and preflight.required_free_bytes() > preflight.evidence_bytes()
    for bad in (0, -1, 1.5, None):
        with pytest.raises(ValueError):
            preflight.check_free_space('.', bad)


@pytest.fixture
def complete_run(tmp_path, inputs):
    root = tmp_path / 'good'
    outcome = k.run_engineering(root, audit_root=AUDIT, repository_root=REPO)
    return root, outcome.completion_sha256


@pytest.mark.parametrize('cut', ['header', 'mid-row', 'before-trailer', 'trailer-tail'])
def test_interrupted_chunk_writes_are_rejected_by_both_readers(complete_run, tmp_path, cut):
    root = tmp_path / 'torn'
    shutil.copytree(complete_run[0], root)
    chunk = root / 'chunk-00000000.bin'
    raw = chunk.read_bytes()
    chunk.write_bytes(raw[:{'header': 10, 'mid-row': binary.HEADER.size + 70, 'before-trailer': len(raw) - binary.TRAILER.size,
                            'trailer-tail': len(raw) - 5}[cut]])
    with pytest.raises(Exception):
        list(binary.iter_chunks(root, expected_chunks=1, expected_attempts=206))
    for pin in (complete_run[1], reseal_transport(root)):
        with pytest.raises(Exception):
            reference_verify(root, pin)


def multi_chunk_run(root, monkeypatch, rows=13, chunk_rows=4):
    """Real ChunkWriter output with several tiny chunks (inventory damage needs more than one line)."""
    monkeypatch.setattr(binary, 'CHUNK_ROWS', chunk_rows)
    root.mkdir()
    writer = binary.ChunkWriter(root)
    for i in range(rows):
        writer.add(binary.Attempt('A1', 'D', (2**20 + i).to_bytes(8, 'big'), i, population_rank=i), bytes([i]) * 32, bytes([i]) * 32)
    return writer.finish()


@pytest.mark.parametrize('damage', ['truncate-line', 'drop-line', 'duplicate-line', 'swap-lines', 'alter-hash', 'alter-size',
                                    'garbage-tail', 'empty', 'missing-chunk-file'])
def test_corrupted_chunk_inventory_is_rejected(tmp_path, monkeypatch, damage):
    root = tmp_path / 'multi'
    info = multi_chunk_run(root, monkeypatch)
    assert info['chunks'] == 4
    pristine = list(binary.iter_chunks(root, expected_chunks=4, expected_attempts=13))
    assert len(pristine) == 13
    index = root / 'chunks.jsonl'
    raw = index.read_bytes()
    lines = raw.splitlines(keepends=True)
    if damage == 'truncate-line':
        index.write_bytes(raw[:-20])
    elif damage == 'drop-line':
        index.write_bytes(b''.join(lines[:-1]))
    elif damage == 'duplicate-line':
        index.write_bytes(b''.join(lines + [lines[-1]]))
    elif damage == 'swap-lines':
        index.write_bytes(b''.join([lines[1], lines[0]] + lines[2:]))
    elif damage == 'alter-hash':
        index.write_bytes(raw.replace(b'"sha256":"', b'"sha256":"0', 1))
    elif damage == 'alter-size':
        index.write_bytes(raw.replace(b'"size":', b'"size":9', 1))
    elif damage == 'garbage-tail':
        index.write_bytes(raw + b'{not json')
    elif damage == 'empty':
        index.write_bytes(b'')
    else:
        (root / 'chunk-00000002.bin').unlink()
    with pytest.raises(Exception):
        list(binary.iter_chunks(root, expected_chunks=4, expected_attempts=13))


@pytest.mark.parametrize('damage', ['truncate-line', 'garbage-tail', 'empty', 'alter-size'])
def test_corrupted_inventory_of_a_complete_run_fails_the_pin_and_reference_verifier(complete_run, tmp_path, damage):
    root = tmp_path / 'inv'
    shutil.copytree(complete_run[0], root)
    index = root / 'chunks.jsonl'
    raw = index.read_bytes()
    index.write_bytes({'truncate-line': raw[:-20], 'garbage-tail': raw + b'{not json', 'empty': b'',
                       'alter-size': raw.replace(b'"size":', b'"size":9', 1)}[damage])
    with pytest.raises(Exception):
        list(binary.iter_chunks(root, expected_chunks=1, expected_attempts=206))
    with pytest.raises(Exception):
        reference_verify(root, complete_run[1])                         # the completion pin binds the inventory


def test_runtime_artifact_mismatch_blocks_before_any_output(tmp_path, monkeypatch):
    h = synthetic_hashing_identity()
    runtime = plans.RuntimeBinding('CPython 3.13.0 x', 'p', '1' * 64, (('PyYAML', '6', '2' * 64),), hashing=h)
    plan = plans.ProductionPlan('16f8b30ae30a9ef3ffc0f2868e9508e70c8007cd',
                                tuple(plans.Artifact(p, 1, '3' * 64) for p in sorted(plans.REQUIRED_SOURCES)), runtime)
    altered = synthetic_hashing_identity()
    next(a for a in altered['artifacts'] if a['role'] == 'libcrypto')['sha256'] = 'f' * 64
    monkeypatch.setattr(plans, 'observe_runtime', lambda: replace(runtime, hashing=altered))
    with pytest.raises(ValueError, match='runtime'):
        plan.validate_local_inputs(REPO, AUDIT)
    assert list(tmp_path.iterdir()) == []


def test_incomplete_or_unmarked_evidence_never_authenticates(complete_run, tmp_path):
    root = tmp_path / 'fin'
    shutil.copytree(complete_run[0], root)
    (root / 'INCOMPLETE').write_bytes(b'incomplete\n')                      # marker present beside complete.json
    with pytest.raises(ValueError):
        k.authenticate_capture(root, plan=plans.EngineeringPlan(), completion_sha256=complete_run[1])
    (root / 'INCOMPLETE').unlink()
    (root / 'complete.json').rename(root / 'complete.json.hidden')           # neither marker (crash between steps)
    with pytest.raises(Exception):
        k.authenticate_capture(root, plan=plans.EngineeringPlan(), completion_sha256=complete_run[1])
    assert disclosure.inspect_evidence(root, plans.ProductionPlan.__new__(plans.ProductionPlan), complete_run[1]) \
        == dict(scope='production-disabled', primary='withheld', validation='withheld')


def test_reference_verifier_interruption_leaves_evidence_untouched_and_rerun_works(complete_run, monkeypatch):
    root, pin = complete_run
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
    from e002_verify import kernel as reference
    calls = []

    def interrupted(*args, **kwargs):
        calls.append(1)
        raise KeyboardInterrupt
    with monkeypatch.context() as local:
        local.setattr(reference, 'decode_chunks', interrupted)
        with pytest.raises(KeyboardInterrupt):
            reference_verify(root, pin)
    assert {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()} == before
    assert calls and reference_verify(root, pin)                             # a fresh verification still passes, nothing latched
