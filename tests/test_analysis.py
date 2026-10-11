"""Decision rules on synthetic counters (no hashing)."""

from __future__ import annotations

import pytest

from hashlab.experiments.analysis import (
    CLASS_CANDIDATE,
    CLASS_NON_ACTIONABLE,
    CLASS_NULL,
    CLASS_UNREPLICATED,
    analyze_results,
    render_report,
)
from hashlab.experiments.config import resolve_config
from hashlab.statistics.distribution import DigestAccumulator

N = 100_000  # expected successes at p0 = 1/256: 390.6


def counters(successes: int, wall: float = 1.0, unique: int = N) -> dict:
    return {
        "attempted": unique,
        "unique": unique,
        "duplicates_within_phase": 0,
        "duplicates_cross_phase": 0,
        "successes": successes,
        "batches": 10,
        "generation_seconds": wall / 4,
        "dedup_seconds": 0.0,
        "hashing_seconds": wall / 2,
        "wall_seconds": wall,
        "exhausted": False,
        "seed": None,
        "start_index": 0,
        "digest_distribution": DigestAccumulator().to_dict(),
    }


SCENARIOS = {
    # id: (discovery successes, validation successes, wall seconds)
    "null": (391, 389, 1.0),
    "strong": (600, 610, 1.0),
    "strong-but-slow": (600, 610, 20.0),
    "fewer": (250, 240, 1.0),
    "fluke": (600, 392, 1.0),
}


def make(tiny_config: dict, scenarios=SCENARIOS, status="complete", positive=None, null_control=None):
    tiny_config["target"] = {"leading_zero_bits": 8}
    tiny_config["generators"] = [
        {"id": gid, "type": "sequential", "width": 8} for gid in scenarios
    ]
    tiny_config["controls"] = {"null_control_generator": null_control, "positive_control": {"enabled": False}}
    resolved = resolve_config(tiny_config)
    results = {
        "run_id": "synthetic",
        "status": status,
        "engine": {"name": "sha256"},
        "target": resolved["target"],
        "generators": {
            gid: {
                "description": {"type": "sequential", "parameters": {}, "domain": {"kind": "bytes", "width_bytes": 8}},
                "dedup_method": "unique by construction",
                "phases": {"discovery": counters(d, wall), "validation": counters(v, wall)},
            }
            for gid, (d, v, wall) in scenarios.items()
        },
        "positive_control": positive,
    }
    return analyze_results(results, resolved)


def test_classifications(tiny_config) -> None:
    analysis = make(tiny_config)
    classes = analysis["verdict"]["classifications"]
    assert classes["null"] == CLASS_NULL
    assert classes["strong"] == CLASS_CANDIDATE
    assert classes["strong-but-slow"] == CLASS_NON_ACTIONABLE
    assert classes["fewer"] == CLASS_NON_ACTIONABLE  # fewer successes is never a search advantage
    assert classes["fluke"] == CLASS_UNREPLICATED
    assert "CANDIDATE ANOMALY" in analysis["verdict"]["summary"]
    assert "not evidence of a SHA-256 weakness" in analysis["verdict"]["summary"]


def test_null_only_run_is_consistent_with_null(tiny_config) -> None:
    analysis = make(tiny_config, {"a": (391, 389, 1.0), "b": (400, 380, 1.0)})
    assert "consistent with the cryptographic null" in analysis["verdict"]["summary"]


def test_correction_is_applied(tiny_config) -> None:
    analysis = make(tiny_config)
    g = analysis["generators"]["strong"]["primary"]
    assert g["p_value_adjusted"] >= g["p_value"]


def test_theoretical_and_empirical_are_separate(tiny_config) -> None:
    phase = make(tiny_config)["generators"]["null"]["phases"]["discovery"]
    assert phase["theoretical"]["expected_successes"] == pytest.approx(N / 256)
    assert phase["empirical"]["successes"] == 391
    lower, upper = phase["empirical"]["rate_ci"]
    assert lower < 1 / 256 < upper


def test_null_control_failure_raises_alarm(tiny_config) -> None:
    analysis = make(tiny_config, null_control="strong")
    assert analysis["null_control"]["passed"] is False
    assert analysis["verdict"]["summary"].startswith("HARNESS ALARM")


def test_undetected_positive_control_makes_run_uninformative(tiny_config) -> None:
    positive = {
        "engine": {"expected_success_probability": 1.25 / 256, "relative_lift_requested": 0.25},
        "counters": counters(392),
    }
    analysis = make(tiny_config, {"a": (391, 389, 1.0)}, positive=positive)
    assert analysis["positive_control"]["detected"] is False
    assert analysis["verdict"]["summary"].startswith("UNINFORMATIVE")


def test_aborted_run_draws_no_conclusions(tiny_config) -> None:
    analysis = make(tiny_config, status="aborted")
    assert analysis["verdict"]["summary"].startswith("INCOMPLETE")


def test_report_renders_required_sections(tiny_config) -> None:
    report = render_report(make(tiny_config))
    for heading in ("## Verdict", "## Theoretical expectation", "## Empirical measurements", "## Validation phase",
                    "## Duplicates", "## Throughput", "## Controls", "## Limitations"):
        assert heading in report
