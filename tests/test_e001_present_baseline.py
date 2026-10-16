"""G1-C: present-baseline preservation check for the local E001 qualification snapshots."""
from hashlib import sha256
from pathlib import Path
import json

import pytest

from e001_snapshot import BASELINE, check_snapshot_file, compare_snapshot

SNAPSHOTS = [Path('results-smoke/e001-s12-qualification/before.json'),
             Path('results-smoke/e001-s13-qualification/before.json')]


def entry(path: Path, data: bytes):
    return {'size': len(data), 'mtime_ns': path.stat().st_mtime_ns, 'sha256': sha256(data).hexdigest()}


@pytest.mark.parametrize('snapshot', SNAPSHOTS)
def test_local_snapshots_match_present_baseline(snapshot):
    if not snapshot.exists():
        pytest.skip('local qualification snapshot not present')
    assert check_snapshot_file(snapshot) == []


def test_baseline_pins_only_lf_normalised_hashes():
    baseline = json.loads(BASELINE.read_text())
    assert baseline['schema'] == 'hashlab-e001-present-baseline-v1'
    for name, pin in baseline['superseded_since_snapshot'].items():
        assert chr(92) not in name and len(pin['current_lf_sha256']) == 64
        raw = Path(name).read_bytes()
        assert sha256(raw.replace(b'\r\n', b'\n')).hexdigest() == pin['current_lf_sha256']


def make(tmp_path, content=b'a\nb\n'):
    sealed, prot = tmp_path / 'sealed.txt', tmp_path / 'prot.txt'
    sealed.write_bytes(b'sealed')
    prot.write_bytes(content)
    before = {'sealed': {'sealed.txt': entry(sealed, b'sealed')}, 'protected': {'prot.txt': entry(prot, content)}}
    return before, sealed, prot


def test_unchanged_and_crlf_only_pass_but_sealed_change_and_other_edit_fail(tmp_path):
    empty = {'superseded_since_snapshot': {}}
    before, sealed, prot = make(tmp_path)
    assert compare_snapshot(before, empty, tmp_path) == []
    prot.write_bytes(b'a\r\nb\r\n')
    assert compare_snapshot(before, empty, tmp_path) == []          # checkout line-ending conversion only
    prot.write_bytes(b'a\nB\n')
    assert compare_snapshot(before, empty, tmp_path) == ['protected changed outside present baseline: prot.txt']
    prot.unlink()
    assert compare_snapshot(before, empty, tmp_path) == ['protected missing: prot.txt']
    before, sealed, prot = make(tmp_path)
    sealed.write_bytes(b'sealeD')
    assert compare_snapshot(before, empty, tmp_path) == ['sealed changed: sealed.txt']


def test_pinned_supersession_accepts_only_the_exact_current_content(tmp_path):
    before, sealed, prot = make(tmp_path)
    prot.write_bytes(b'new\n')
    pin = {'superseded_since_snapshot': {'prot.txt': {'current_lf_sha256': sha256(b'new\n').hexdigest()}}}
    assert compare_snapshot(before, pin, tmp_path) == []
    prot.write_bytes(b'newer\n')
    assert compare_snapshot(before, pin, tmp_path) == ['protected changed outside present baseline: prot.txt']
