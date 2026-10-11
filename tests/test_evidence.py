from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from hashlab.evidence import RunDirectory, collect_environment, new_run_id, validate_run_id, verify_manifest
from hashlab.evidence.manifest import MANIFEST_NAME, file_sha256


def make_sealed(tmp_path: Path) -> RunDirectory:
    run = RunDirectory.create(tmp_path, new_run_id("001"))
    run.write_json("results.json", {"successes": 3})
    run.write_text("report.md", "# report\n")
    with run.open_stream("batches.jsonl") as stream:
        stream.write('{"batch": 1}\n')
    run.seal({"run_id": run.path.name, "status": "complete"})
    return run


def make_writable(path: Path) -> None:
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def test_run_id_format_and_uniqueness() -> None:
    a, b = new_run_id("001"), new_run_id("001")
    assert a != b
    assert validate_run_id(a) == a
    with pytest.raises(ValueError):
        validate_run_id("../escape")


def test_sealed_run_verifies(tmp_path: Path) -> None:
    run = make_sealed(tmp_path)
    assert verify_manifest(run.path) == []


def test_sealed_files_are_read_only(tmp_path: Path) -> None:
    run = make_sealed(tmp_path)
    for name in ("results.json", "report.md", "batches.jsonl", MANIFEST_NAME):
        assert not os.access(run.path / name, os.W_OK)


def test_tampering_is_detected(tmp_path: Path) -> None:
    run = make_sealed(tmp_path)
    target = run.path / "results.json"
    make_writable(target)
    target.write_text('{"successes": 4}\n', encoding="utf-8")
    problems = verify_manifest(run.path)
    assert any("results.json" in p for p in problems)


def test_missing_and_unlisted_files_are_detected(tmp_path: Path) -> None:
    run = make_sealed(tmp_path)
    (run.path / "extra.txt").write_text("x", encoding="utf-8")
    report = run.path / "report.md"
    make_writable(report)
    report.unlink()
    problems = verify_manifest(run.path)
    assert any("unlisted" in p and "extra.txt" in p for p in problems)
    assert any("missing evidence file report.md" in p for p in problems)


def test_manifest_edit_is_detected(tmp_path: Path) -> None:
    run = make_sealed(tmp_path)
    manifest = run.path / MANIFEST_NAME
    make_writable(manifest)
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("complete", "edited"), encoding="utf-8")
    assert any("does not match" in p for p in verify_manifest(run.path))


def test_analyses_subdirectory_is_allowed(tmp_path: Path) -> None:
    run = make_sealed(tmp_path)
    (run.path / "analyses").mkdir()
    assert verify_manifest(run.path) == []


def test_run_directory_is_never_reused(tmp_path: Path) -> None:
    run_id = new_run_id("001")
    RunDirectory.create(tmp_path, run_id)
    with pytest.raises(FileExistsError):
        RunDirectory.create(tmp_path, run_id)


def test_no_writes_after_seal_or_duplicate_names(tmp_path: Path) -> None:
    run = RunDirectory.create(tmp_path, new_run_id("001"))
    run.write_text("a.txt", "a")
    with pytest.raises(ValueError):
        run.write_text("a.txt", "b")
    with pytest.raises(ValueError):
        run.write_text("../b.txt", "b")
    run.seal({})
    with pytest.raises(RuntimeError):
        run.write_text("c.txt", "c")


def test_manifest_hashes_match_files(tmp_path: Path) -> None:
    import json

    run = make_sealed(tmp_path)
    manifest = json.loads((run.path / MANIFEST_NAME).read_text(encoding="utf-8"))
    for name, entry in manifest["files"].items():
        assert entry["sha256"] == file_sha256(run.path / name)


def test_environment_capture_has_required_fields() -> None:
    env = collect_environment()
    assert {"python", "packages", "machine", "git", "openssl"} <= set(env)
    assert "version" in env["python"] and "cpu_count" in env["machine"]
    assert "available" in env["git"]
