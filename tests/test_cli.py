"""CLI behavior: validate/plan are dry, run seals evidence, analyze verifies integrity."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from hashlab.cli import main
from hashlab.evidence import verify_manifest

EXPECTED_FILES = {
    "config.source.yaml",
    "config.resolved.json",
    "plan.json",
    "environment.json",
    "seeds.json",
    "batches.jsonl",
    "results.json",
    "analysis.json",
    "report.md",
    "manifest.json",
    "manifest.sha256",
}


def test_validate_runs_self_checks_and_writes_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["validate"]) == 0
    assert "no experiment was run" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_validate_with_config(tmp_path: Path, monkeypatch, tiny_config_file: Path) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["validate", "--config", str(tiny_config_file)]) == 0
    assert not (tmp_path / "results").exists()


def test_plan_is_a_dry_run(tmp_path: Path, monkeypatch, tiny_config_file: Path, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "--config", str(tiny_config_file)]) == 0
    out = capsys.readouterr().out
    assert "dry run only" in out and "Plan fingerprint" in out
    assert not (tmp_path / "results").exists()


def test_plan_json_output(tmp_path: Path, monkeypatch, tiny_config_file: Path, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "--config", str(tiny_config_file), "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["primary_family_size"] == 5 and plan["errors"] == []


def test_invalid_config_is_rejected(tmp_path: Path, tiny_config: dict) -> None:
    tiny_config["engine"] = "md5"
    tiny_config["mystery"] = 1
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(tiny_config), encoding="utf-8")
    assert main(["plan", "--config", str(path)]) == 2
    assert main(["validate", "--config", str(path)]) == 2
    assert main(["run", "--config", str(path), "--results-dir", str(tmp_path / "r")]) == 2
    assert not (tmp_path / "r").exists()


def test_infeasible_plan_blocks_run(tmp_path: Path, tiny_config: dict) -> None:
    tiny_config["generators"].append({"id": "tiny", "type": "sequential", "width": 1})
    path = tmp_path / "infeasible.json"
    path.write_text(json.dumps(tiny_config), encoding="utf-8")
    assert main(["plan", "--config", str(path)]) == 2
    assert main(["run", "--config", str(path), "--results-dir", str(tmp_path / "r")]) == 2
    assert not (tmp_path / "r").exists()


def _single_run(results: Path) -> Path:
    runs = [p for p in results.iterdir() if p.is_dir()]
    assert len(runs) == 1
    return runs[0]


def test_tiny_run_seals_evidence_and_analyze_verifies(tmp_path: Path, tiny_config_file: Path, capsys) -> None:
    results = tmp_path / "results"
    assert main(["run", "--config", str(tiny_config_file), "--results-dir", str(results)]) == 0
    run_dir = _single_run(results)
    assert {p.name for p in run_dir.iterdir()} == EXPECTED_FILES
    assert verify_manifest(run_dir) == []
    assert (run_dir / "config.source.yaml").read_bytes() == tiny_config_file.read_bytes()

    data = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert data["status"] == "complete"
    for gid, entry in data["generators"].items():
        for phase in ("discovery", "validation"):
            c = entry["phases"][phase]
            assert c["attempted"] == 300
            assert c["unique"] + c["duplicates_within_phase"] + c["duplicates_cross_phase"] == c["attempted"]
    analysis = json.loads((run_dir / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["positive_control"]["detected"] is True
    assert analysis["null_control"]["generator"] == "rand"

    capsys.readouterr()
    assert main(["analyze", "--run-id", run_dir.name, "--results-dir", str(results)]) == 0
    assert "integrity verified" in capsys.readouterr().out
    assert len(list((run_dir / "analyses").iterdir())) == 1
    assert verify_manifest(run_dir) == []


def test_analyze_refuses_tampered_evidence(tmp_path: Path, tiny_config_file: Path) -> None:
    results = tmp_path / "results"
    assert main(["run", "--config", str(tiny_config_file), "--results-dir", str(results)]) == 0
    run_dir = _single_run(results)
    target = run_dir / "results.json"
    os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
    target.write_text(target.read_text(encoding="utf-8").replace('"complete"', '"completE"'), encoding="utf-8")
    assert main(["analyze", "--run-id", run_dir.name, "--results-dir", str(results)]) == 3


def test_analyze_unknown_run(tmp_path: Path) -> None:
    assert main(["analyze", "--run-id", "20260101T000000Z-exp001-deadbeef", "--results-dir", str(tmp_path)]) == 2


def test_same_seed_reproduces_counts(tmp_path: Path, tiny_config_file: Path) -> None:
    results = tmp_path / "results"
    assert main(["run", "--config", str(tiny_config_file), "--results-dir", str(results)]) == 0
    assert main(["run", "--config", str(tiny_config_file), "--results-dir", str(results)]) == 0
    runs = sorted(p for p in results.iterdir() if p.is_dir())
    assert len(runs) == 2

    def counts(run: Path) -> dict:
        data = json.loads((run / "results.json").read_text(encoding="utf-8"))
        return {
            gid: {
                phase: {k: v for k, v in c.items() if not k.endswith("_seconds")}
                for phase, c in entry["phases"].items()
            }
            for gid, entry in data["generators"].items()
        }

    assert counts(runs[0]) == counts(runs[1])


@pytest.mark.parametrize("argv", [[], ["bogus"], ["plan"], ["analyze"]])
def test_bad_arguments_exit(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        main(argv)
