"""G1-D / Q-1: real reparse-point and symlink qualification of the evidence readers.

Real filesystem objects only.  Junctions (``mklink /J``) need no privilege and always run on Windows.
File and directory SYMLINKS need ``SeCreateSymbolicLinkPrivilege`` (or Developer Mode); where the host cannot
create one the test is SKIPPED with a Q-1 message, never passed.  Run the same file on a symlink-capable host:

    python -B -m pytest tests/test_exp002_g1d_reparse_security.py tests/test_exp002_e4.py -q -rs

Covered readers: the independent production verifier (``e002_verify.production_evidence``), the producer
chunk reader and root creation, and the finalization helpers.  Containment tests assert that a rejected
substitution leaves the original evidence byte-identical.
"""
from pathlib import Path
import os
import shutil
import subprocess

import pytest

from hashlab.experiments import exp002_finalization as fin
from hashlab.experiments import exp002_journal as journal
from hashlab.experiments import exp002_kernel_evidence as binary
from test_exp002_production_verification import AUDIT, REPO, evidence, inputs, original, verify  # noqa: F401

windows_only = pytest.mark.skipif(os.name != 'nt', reason='Windows reparse-point qualification')


def snapshot(root):
    return {p.name: p.read_bytes() for p in sorted(Path(root).iterdir())}


def junction(link, target):
    done = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
    assert done.returncode == 0, done.stderr


def symlink_or_skip(link, target, *, directory):
    try:
        Path(link).symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f'Q-1 open: symlink creation unavailable on this host ({exc})')


def directory_link(kind, link, target):
    if kind == 'junction':
        if os.name != 'nt':
            pytest.skip('junctions are Windows-only')
        junction(link, target)
    else:
        symlink_or_skip(link, target, directory=True)


KINDS = ['junction', 'dir-symlink']


# ------------------------------------------------------------ evidence root is a link

@pytest.mark.parametrize('kind', KINDS)
def test_linked_evidence_root_is_refused_by_every_reader(tmp_path, evidence, kind):
    root, pin = evidence
    alias = tmp_path / 'alias'
    directory_link(kind, alias, root)
    before = snapshot(root)
    with pytest.raises(ValueError):
        verify(alias, pin)                                           # independent production verifier
    with pytest.raises(ValueError):
        list(binary.iter_chunks(alias, expected_chunks=1, expected_attempts=78))     # producer reader
    with pytest.raises(ValueError):
        fin.classify_attempt_evidence(alias)                          # finalization
    with pytest.raises(ValueError):
        fin.verify_restored_copy({'complete.json': {'size': 1, 'sha256': '0' * 64}}, alias)
    assert snapshot(root) == before and verify(root, pin)             # original untouched and still verifies


@pytest.mark.parametrize('kind', KINDS)
def test_output_beneath_a_linked_parent_is_refused_before_anything_is_created(tmp_path, kind):
    real = tmp_path / 'real'
    real.mkdir()
    parent = tmp_path / 'linked-parent'
    directory_link(kind, parent, real)
    with pytest.raises(ValueError):
        binary.create_root(parent / 'run', repository=REPO, audit_root=AUDIT)
    assert list(real.iterdir()) == []


# ------------------------------------------------- an evidence ENTRY is a link or reparse point

@pytest.mark.parametrize('name', ['chunk-00000000.bin', 'unexpected-entry'])
@pytest.mark.parametrize('kind', KINDS)
def test_linked_directory_entry_in_the_evidence_inventory_fails_closed(tmp_path, evidence, kind, name):
    root, pin = evidence
    target = tmp_path / 'elsewhere'
    target.mkdir()
    saved = None
    if name in {p.name for p in root.iterdir()}:
        saved = (root / name).read_bytes()
        (root / name).unlink()
    directory_link(kind, root / name, target)
    with pytest.raises(ValueError):
        verify(root, pin)
    with pytest.raises(ValueError):
        journal.inspect_partial(root)
    with pytest.raises(ValueError):
        fin.classify_attempt_evidence(root)
    assert (root / name).exists() and target.is_dir()                 # nothing followed, deleted or repaired
    os.rmdir(root / name)                                             # removes the link only
    if saved is not None:
        (root / name).write_bytes(saved)
    assert verify(root, pin)


@pytest.mark.parametrize('name', ['chunk-00000000.bin', 'complete.json', 'plan.json', 'chunks.jsonl', 'environment.json'])
def test_file_symlink_substituted_for_a_regular_evidence_file_is_refused_even_when_bytes_match(tmp_path, evidence, name):
    root, pin = evidence
    outside = tmp_path / 'outside-copy'
    shutil.copyfile(root / name, outside)                             # byte-identical substitute target
    original_bytes = (root / name).read_bytes()
    (root / name).unlink()
    symlink_or_skip(root / name, outside, directory=False)
    try:
        with pytest.raises(ValueError):
            verify(root, pin)
        with pytest.raises(ValueError):
            journal.inspect_partial(root)
        assert outside.read_bytes() == original_bytes
    finally:
        os.unlink(root / name)
        (root / name).write_bytes(original_bytes)
    assert verify(root, pin)


# ---------------------------------------------------------------- characterisation (not a claim)

@windows_only
def test_content_pinning_not_path_pinning_for_a_linked_ancestor(tmp_path, evidence):
    """The verifier checks the evidence directory and its entries, not every ancestor of the path.

    Evidence reached through a junctioned *ancestor* is therefore verified by content pins only: the
    bytes must equal the retained completion pin, so a substituted directory fails and the genuine one
    passes.  Recorded as an observation for the Director; no code was changed.
    """
    root, pin = evidence
    parent = tmp_path / 'p'
    parent.mkdir()
    shutil.copytree(root, parent / 'run')
    link = tmp_path / 'via-link'
    junction(link, parent)
    assert verify(link / 'run', pin)                                  # genuine bytes: accepted by content
    chunk = parent / 'run' / 'chunk-00000000.bin'
    raw = bytearray(chunk.read_bytes())
    raw[-1] ^= 1
    chunk.write_bytes(bytes(raw))
    with pytest.raises(ValueError):
        verify(link / 'run', pin)                                     # substituted bytes: refused by pin
