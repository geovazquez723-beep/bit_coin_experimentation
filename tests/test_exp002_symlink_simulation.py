"""G1-C: SIMULATED symlink rejection for hosts without SeCreateSymbolicLinkPrivilege.

These tests do NOT replace ``test_symbolic_links_block_inventory_and_disclosure`` (skipped with
WinError 1314 on unprivileged Windows).  They make a regular file named ``link`` *appear* to be a
symbolic link / reparse point to ``pathlib`` and confirm that the production code's rejection
branches (reparse-point attribute, ``is_symlink``) fire.  The real junction test remains the
unprivileged evidence that an actual reparse point is refused.
"""
from pathlib import Path
from types import SimpleNamespace
import stat

import pytest

from hashlab.experiments import exp002_journal as j
from hashlab.experiments import exp002_provenance as p

REPARSE = 0x400


def fake_symlink(monkeypatch, name='link', *, attributes=REPARSE, mode=stat.S_IFLNK | 0o777, is_symlink=True):
    real_lstat, real_is_symlink = Path.lstat, Path.is_symlink

    def lstat(self, *a, **k):
        if self.name != name:
            return real_lstat(self, *a, **k)
        info = real_lstat(self, *a, **k)
        return SimpleNamespace(st_mode=mode, st_file_attributes=attributes, st_size=info.st_size)

    monkeypatch.setattr(Path, 'lstat', lstat)
    monkeypatch.setattr(Path, 'is_symlink', lambda self: True if (self.name == name and is_symlink) else real_is_symlink(self))


@pytest.mark.parametrize('attributes,mode', [(REPARSE, stat.S_IFLNK | 0o777), (REPARSE, stat.S_IFREG | 0o644), (0, stat.S_IFLNK | 0o777)])
def test_require_plain_refuses_link_shaped_entries(tmp_path, monkeypatch, attributes, mode):
    (tmp_path / 'link').write_bytes(b'x')
    fake_symlink(monkeypatch, attributes=attributes, mode=mode)
    with pytest.raises(ValueError):
        j.require_plain(tmp_path / 'link')


def test_plain_file_is_still_accepted(tmp_path):
    (tmp_path / 'plain').write_bytes(b'x')
    j.require_plain(tmp_path / 'plain')


@pytest.mark.parametrize('operation', [p.inventory, j.inspect_partial])
def test_inventory_and_partial_inspection_refuse_a_link_shaped_entry(tmp_path, monkeypatch, operation):
    root = tmp_path / 'journal'
    root.mkdir()
    (root / 'link').write_bytes(b'synthetic')
    fake_symlink(monkeypatch)
    with pytest.raises(ValueError):
        operation(root)
    assert (root / 'link').read_bytes() == b'synthetic'
