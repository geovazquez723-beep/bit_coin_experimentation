"""G1-D / Q-2: the second-host replay tool refuses mislabelled or altered replays (no verification is run here)."""
from pathlib import Path
import json

import pytest

import second_host_replay as q2

REPO = Path(__file__).resolve().parents[1]


def make_package(tmp_path, commit):
    pkg = tmp_path / 'pkg'
    (pkg / 'evidence').mkdir(parents=True)
    (pkg / 'evidence' / 'x.bin').write_bytes(b'evidence')
    manifest = {'schema': q2.SCHEMA, 'required_commit': commit, 'completion_sha256': '0' * 64, 'producer_runtime': {},
                'producer_host': q2.host_fingerprint(), 'files': q2.inventory(pkg), 'audit_inputs': {}}
    (pkg / 'MANIFEST.json').write_text(json.dumps(manifest))
    return pkg


def run(pkg, tmp_path, name='report.json'):
    audit = tmp_path / 'audit'
    audit.mkdir(exist_ok=True)
    out = tmp_path / name
    args = type('A', (), dict(package=pkg, repository=REPO, audit=audit, out=out, observe_hashing=False))
    return q2.replay(args), json.loads(out.read_text())


def test_same_host_fingerprint_is_detected_and_distinct_hosts_are_not():
    here = q2.host_fingerprint()
    assert q2.same_host(here, dict(here))
    other = dict(node_sha256='0' * 64, machine_guid_sha256='1' * 64)
    assert not q2.same_host(here, other)
    assert q2.same_host(dict(node_sha256='a', machine_guid_sha256=None), dict(node_sha256='a', machine_guid_sha256=None))


def test_replay_never_runs_when_the_package_audit_inputs_or_checkout_differ_and_flags_same_host(tmp_path):
    pkg = make_package(tmp_path, '0' * 40)
    code, report = run(pkg, tmp_path)
    assert code == 1 and report['result'] is None and report['matches_expected'] is False
    problems = ' '.join(report['package_problems'])
    assert 'audit inputs' in problems and 'manifest requires' in problems
    assert report['q2_qualifying'] is False                       # this machine produced the manifest fingerprint


def test_altered_package_file_is_reported(tmp_path):
    pkg = make_package(tmp_path, '0' * 40)
    (pkg / 'evidence' / 'x.bin').write_bytes(b'tampered')
    _code, report = run(pkg, tmp_path)
    assert 'package inventory differs from the manifest' in report['package_problems']


def test_existing_report_is_never_overwritten(tmp_path):
    pkg = make_package(tmp_path, '0' * 40)
    run(pkg, tmp_path)
    with pytest.raises(SystemExit):
        run(pkg, tmp_path)
