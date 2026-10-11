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
from hashlab.statistics.inference import clopper_pearson, holm

N = 100_000  # expected successes at p0 = 1/256: 390.6
SUCCESS_BITS = 8  # target 2**248: a success is a digest with >= 8 leading zero bits


def histogram(unique: int, successes: int) -> dict:
    """Digest histograms consistent with the counts (the analysis checks this as harness integrity)."""
    acc = DigestAccumulator()
    acc.leading_zero_bits[0] = unique - successes
    acc.leading_zero_bits[SUCCESS_BITS] = successes
    base, extra = divmod(unique, 256)
    acc.first_byte = [base + (1 if i < extra else 0) for i in range(256)]
    acc.last_byte = list(acc.first_byte)
    return acc.to_dict()


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
        "digest_distribution": histogram(unique, successes),
    }


SCENARIOS = {
    # id: (discovery successes, validation successes, wall seconds)
    "null": (391, 389, 1.0),
    "strong": (600, 610, 1.0),
    "strong-but-slow": (600, 610, 20.0),
    "fewer": (250, 240, 1.0),
    "fluke": (600, 392, 1.0),
}

FIRST = "first scenario"  # default economic reference: the first scenario id


def build(
    tiny_config: dict,
    scenarios=SCENARIOS,
    status="complete",
    positive=None,
    null_control=None,
    reference: str | None = FIRST,
    specs: dict | None = None,
    positive_enabled: bool = False,
) -> tuple[dict, dict]:
    tiny_config["target"] = {"leading_zero_bits": SUCCESS_BITS}
    tiny_config["phases"] = {phase: {"candidates_per_generator": N} for phase in ("discovery", "validation")}
    tiny_config["generators"] = [
        {"id": gid, "type": "sequential", "width": 8, **(specs or {}).get(gid, {})} for gid in scenarios
    ]
    tiny_config["controls"] = {
        "null_control_generator": null_control,
        "positive_control": {"enabled": positive_enabled, "candidates": N},
    }
    tiny_config["economics"] = {"reference_generator": next(iter(scenarios)) if reference == FIRST else reference}
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
    return results, resolved


def make(tiny_config: dict, scenarios=SCENARIOS, **kwargs) -> dict:
    return analyze_results(*build(tiny_config, scenarios, **kwargs))


def diagnostic_codes(analysis: dict) -> dict:
    return {d["code"]: d for d in analysis["diagnostics"]}


# ---- decision chain


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
    assert analysis["integrity"]["passed"] is True  # the synthetic fixture itself is consistent


def test_null_only_run_is_consistent_with_null(tiny_config) -> None:
    analysis = make(tiny_config, {"a": (391, 389, 1.0), "b": (400, 380, 1.0)})
    summary = analysis["verdict"]["summary"]
    assert "consistent with the cryptographic null" in summary
    assert "does not establish equivalence" in summary


def test_correction_is_applied(tiny_config) -> None:
    analysis = make(tiny_config)
    g = analysis["generators"]["strong"]["primary"]
    assert g["p_value_adjusted"] >= g["p_value"]


def test_holm_correction_and_separate_replication_family(tiny_config) -> None:
    analysis = make(tiny_config)
    gens = analysis["generators"]
    ids = list(gens)
    assert [gens[g]["primary"]["p_value_adjusted"] for g in ids] == pytest.approx(
        holm([gens[g]["primary"]["p_value"] for g in ids])
    )
    flagged = [g for g in ids if gens[g]["primary"]["flagged"]]
    assert flagged == ["strong", "strong-but-slow", "fewer", "fluke"]
    assert [gens[g]["replication"]["p_value_adjusted"] for g in flagged] == pytest.approx(
        holm([gens[g]["replication"]["p_value_one_sided"] for g in flagged])
    )
    assert "replication" not in gens["null"]  # only discovery-flagged generators are replicated


def test_theoretical_and_empirical_are_separate(tiny_config) -> None:
    phase = make(tiny_config)["generators"]["null"]["phases"]["discovery"]
    assert phase["theoretical"]["expected_successes"] == pytest.approx(N / 256)
    assert phase["empirical"]["successes"] == 391
    lower, upper = phase["empirical"]["rate_ci"]
    assert lower < 1 / 256 < upper


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
    assert analysis["verdict"]["blocking"] is True


# ---- Remediation A: null-control statistics vs harness integrity


def test_significant_null_control_is_a_diagnostic_not_a_harness_failure(tiny_config) -> None:
    analysis = make(tiny_config, null_control="fluke")  # flagged in discovery, not replicated
    nc = analysis["null_control"]
    assert nc["statistically_flagged"] is True and nc["passed"] is False
    assert nc["status"] == "statistical-anomaly" and nc["blocking"] is False
    verdict = analysis["verdict"]
    assert not verdict["summary"].startswith(("HARNESS", "INCOMPLETE"))
    assert verdict["status"] == "candidate-anomaly" and verdict["blocking"] is False
    assert "WARNING: the null control fluke was statistically flagged" in verdict["summary"]
    assert analysis["integrity"]["passed"] is True
    diagnostic = diagnostic_codes(analysis)["null-control-statistically-significant"]
    assert diagnostic["severity"] == "warning" and diagnostic["blocking"] is False
    assert diagnostic["message"] in verdict["warnings"]
    assert "NULL-CONTROL DIAGNOSTIC" in render_report(analysis)


def test_null_control_designation_does_not_change_statistics(tiny_config) -> None:
    plain = make(tiny_config)
    designated = make(tiny_config, null_control="fluke")
    for gid in SCENARIOS:
        assert designated["generators"][gid]["primary"] == plain["generators"][gid]["primary"]
        assert designated["generators"][gid]["classification"] == plain["generators"][gid]["classification"]
    assert designated["null_control"]["p_value"] == plain["generators"]["fluke"]["primary"]["p_value"]
    assert designated["null_control"]["p_value_adjusted"] == plain["generators"]["fluke"]["primary"]["p_value_adjusted"]


def test_replicated_null_control_is_serious_but_not_blocking(tiny_config) -> None:
    analysis = make(tiny_config, null_control="strong")
    nc = analysis["null_control"]
    assert nc["status"] == "statistical-anomaly-replicated" and nc["replicated"] is True
    assert nc["blocking"] is False
    assert diagnostic_codes(analysis)["null-control-statistically-significant"]["severity"] == "serious"
    assert analysis["verdict"]["blocking"] is False
    assert "and replicated" in analysis["verdict"]["summary"]


def test_missing_null_control_evidence_is_blocking(tiny_config) -> None:
    results, resolved = build(tiny_config, null_control="fluke")
    del results["generators"]["fluke"]
    analysis = analyze_results(results, resolved)
    assert analysis["integrity"]["blocking"] is True
    assert any("null control fluke" in p for p in analysis["integrity"]["problems"])
    assert analysis["null_control"]["status"] == "missing-evidence"
    assert analysis["null_control"]["blocking"] is True
    assert analysis["verdict"]["summary"].startswith("HARNESS INTEGRITY FAILURE")
    assert analysis["verdict"]["status"] == "integrity-failure" and analysis["verdict"]["blocking"] is True


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("successes", N + 1, "exceed unique"),
        ("successes", -1, "missing or invalid"),
        ("successes", 601, "disagree with the leading-zero histogram"),
        ("unique", N - 5, "!= attempted"),
        ("wall_seconds", None, "missing or invalid"),
    ],
)
def test_invalid_counts_are_blocking(tiny_config, field, value, message) -> None:
    results, resolved = build(tiny_config)
    results["generators"]["strong"]["phases"]["discovery"][field] = value
    analysis = analyze_results(results, resolved)
    assert analysis["verdict"]["status"] == "integrity-failure"
    assert any(message in p for p in analysis["integrity"]["problems"])


def test_inconsistent_histogram_is_blocking(tiny_config) -> None:
    results, resolved = build(tiny_config)
    results["generators"]["null"]["phases"]["validation"]["digest_distribution"]["first_byte"][0] += 1
    analysis = analyze_results(results, resolved)
    assert analysis["verdict"]["status"] == "integrity-failure"
    assert any("first_byte histogram total" in p for p in analysis["integrity"]["problems"])


def test_enabled_positive_control_without_evidence_is_blocking(tiny_config) -> None:
    analysis = make(tiny_config, positive_enabled=True, positive=None)
    assert analysis["verdict"]["status"] == "integrity-failure"
    assert any("positive control is enabled" in p for p in analysis["integrity"]["problems"])


def test_missing_phase_of_configured_generator_is_blocking(tiny_config) -> None:
    results, resolved = build(tiny_config)
    del results["generators"]["fewer"]["phases"]["validation"]
    analysis = analyze_results(results, resolved)
    assert analysis["verdict"]["status"] == "integrity-failure"
    assert "fewer/validation: phase results are missing" in analysis["integrity"]["problems"]


# ---- Remediation B: predeclared economic reference


def test_economic_reference_is_predeclared_not_the_fastest(tiny_config) -> None:
    scenarios = dict(SCENARIOS, speedy=(391, 389, 0.01))  # a much faster comparable generator
    analysis = make(tiny_config, scenarios)
    assert analysis["economics"]["reference_generator"] == "null"
    strong = analysis["generators"]["strong"]
    assert strong["economics"]["throughput_ratio_vs_reference"] == pytest.approx(1.0)
    assert strong["classification"] == CLASS_CANDIDATE  # not penalized against the fastest observed generator
    assert analysis["generators"]["speedy"]["economics"]["throughput_ratio_vs_reference"] == pytest.approx(100.0)


def test_reference_comes_only_from_configuration(tiny_config) -> None:
    analysis = make(tiny_config, reference="strong-but-slow")
    slow = analysis["generators"]["strong-but-slow"]
    assert slow["economics"]["comparability"] == "reference"
    assert slow["actionability"]["throughput_ratio_vs_reference"] == pytest.approx(1.0)
    assert slow["classification"] == CLASS_CANDIDATE
    assert analysis["generators"]["strong"]["economics"]["throughput_ratio_vs_reference"] == pytest.approx(20.0)


def test_without_a_reference_no_generator_passes_the_economic_screen(tiny_config) -> None:
    analysis = make(tiny_config, reference=None)
    strong = analysis["generators"]["strong"]
    assert strong["classification"] == CLASS_NON_ACTIONABLE
    assert strong["actionability"]["screen_status"] == "no-reference"
    assert strong["actionability"]["throughput_ratio_vs_reference"] is None
    assert "no-economic-reference" in diagnostic_codes(analysis)
    # raw throughput metrics stay available
    assert strong["phases"]["validation"]["throughput"]["end_to_end_unique_per_second"] == pytest.approx(N)
    assert strong["phases"]["validation"]["throughput"]["hashing_per_second"] == pytest.approx(2 * N)


def test_reference_without_throughput_disables_the_screen(tiny_config) -> None:
    scenarios = dict(SCENARIOS, null=(391, 389, 0.0))  # zero wall time: no throughput figure
    analysis = make(tiny_config, scenarios)
    strong = analysis["generators"]["strong"]
    assert strong["actionability"]["screen_status"] == "reference-unavailable"
    assert strong["classification"] == CLASS_NON_ACTIONABLE
    assert "economic-reference-unavailable" in diagnostic_codes(analysis)


def test_incomparable_domain_gets_no_relative_efficiency_claim(tiny_config) -> None:
    analysis = make(tiny_config, specs={"strong": {"encoding": "ascii-decimal", "width": 16}})
    strong = analysis["generators"]["strong"]
    assert strong["economics"]["comparability"] == "not-comparable"
    assert {"kind", "width_bytes"} <= set(strong["economics"]["domain_differences"])
    assert strong["economics"]["throughput_ratio_vs_reference"] is None
    assert strong["actionability"]["screen_status"] == "not-comparable"
    assert strong["classification"] == CLASS_NON_ACTIONABLE
    assert strong["phases"]["validation"]["throughput"]["end_to_end_unique_per_second"] == pytest.approx(N)
    assert "economic-domain-not-comparable" in diagnostic_codes(analysis)


def test_economic_metrics_are_reported(tiny_config) -> None:
    t = make(tiny_config)["generators"]["strong"]["phases"]["validation"]["throughput"]
    assert t["expected_valid_per_second"] == pytest.approx(N / 256)
    assert t["observed_valid_per_second"] == pytest.approx(610)
    assert t["candidate_overhead_fraction_of_wall"] == pytest.approx(0.25)


# ---- Remediation C: interval types and actionability


def test_intervals_are_labelled_and_marginal_values_unchanged(tiny_config) -> None:
    analysis = make(tiny_config)
    emp = analysis["generators"]["strong"]["phases"]["validation"]["empirical"]
    assert emp["interval_type"] == "marginal"
    assert emp["rate_ci"] == list(clopper_pearson(610, N, 0.99))
    sim = emp["simultaneous"]
    assert sim["interval_type"] == "simultaneous-bonferroni" and sim["family_size"] == len(SCENARIOS)
    assert sim["confidence_level"] == pytest.approx(1 - 0.01 / len(SCENARIOS))
    assert sim["rate_ci"][0] < emp["rate_ci"][0] and sim["rate_ci"][1] > emp["rate_ci"][1]
    report = render_report(analysis)
    assert "marginal CI" in report and "simultaneous CI" in report


def test_marginal_bound_alone_cannot_pass_the_screen(tiny_config) -> None:
    probe = make(tiny_config)["generators"]["strong"]["actionability"]
    marginal = probe["validation_rate_ratio_lower_bound"]
    simultaneous = probe["validation_rate_ratio_lower_bound_simultaneous"]
    assert simultaneous < marginal
    ratio = probe["required"] / ((marginal + simultaneous) / 2)  # marginal * ratio > required > simultaneous * ratio
    action = make(tiny_config, dict(SCENARIOS, strong=(600, 610, 1.0 / ratio)))["generators"]["strong"]
    assert action["actionability"]["throughput_ratio_vs_reference"] == pytest.approx(ratio)
    assert action["actionability"]["marginal_bound_alone_would_pass"] is True
    assert action["actionability"]["exploratory_screen_passed"] is False
    assert action["classification"] == CLASS_NON_ACTIONABLE


def test_no_confirmatory_economic_label_is_emitted(tiny_config) -> None:
    analysis = make(tiny_config, reference="strong-but-slow")  # several generators pass the screen
    screened = [g for g in analysis["generators"].values() if "actionability" in g]
    assert screened
    for g in screened:
        assert g["actionability"]["actionable"] is False
        assert g["actionability"]["evidence_level"] == "exploratory"
        assert g["economics"]["evidence_level"] == "exploratory"
    assert "not a confirmed mining advantage" in analysis["verdict"]["summary"]
    assert "EXPLORATORY" in analysis["verdict"]["summary"]


def test_report_renders_required_sections(tiny_config) -> None:
    report = render_report(make(tiny_config))
    for heading in ("## Verdict", "## Harness integrity", "## Diagnostics", "## Theoretical expectation",
                    "## Empirical measurements", "## Validation phase", "## Duplicates", "## Throughput",
                    "## Economics", "## Controls", "## Limitations"):
        assert heading in report


# ---- Assignment 003: exploratory labels are never confirmatory


def test_labels_are_explained_and_never_confirmatory(tiny_config) -> None:
    import json

    from hashlab.experiments.analysis import CLASSIFICATION_LEGEND

    analysis = make(tiny_config, reference="strong-but-slow")  # several generators pass the screen
    assert analysis["classification_legend"] == CLASSIFICATION_LEGEND
    assert set(CLASSIFICATION_LEGEND) == {CLASS_NULL, CLASS_UNREPLICATED, CLASS_NON_ACTIONABLE, CLASS_CANDIDATE}
    assert "not a confirmed mining advantage" in CLASSIFICATION_LEGEND[CLASS_CANDIDATE]
    assert "EXPLORATORY" in CLASSIFICATION_LEGEND[CLASS_CANDIDATE]
    for g in analysis["generators"].values():
        assert g["classification_meaning"] == CLASSIFICATION_LEGEND[g["classification"]]
    verdict = analysis["verdict"]
    assert verdict["confirmatory_economic_claim"] is False
    assert verdict["economic_evidence_level"] == "exploratory"
    assert verdict["exploratory_screen_passed"] == [
        gid for gid, c in verdict["classifications"].items() if c == CLASS_CANDIDATE
    ]
    assert '"actionable": true' not in json.dumps(analysis)
    report = render_report(analysis)
    assert "## How to read the labels" in report and analysis["label_note"] in report
    assert "passed (exploratory)" in report


def test_replicated_but_unscreened_summary_does_not_use_actionable(tiny_config) -> None:
    analysis = make(tiny_config, {"null": (391, 389, 1.0), "fewer": (250, 240, 1.0)})
    summary = analysis["verdict"]["summary"]
    assert analysis["verdict"]["status"] == "replicated-non-actionable"
    assert "did not pass the exploratory economic screen" in summary
    assert "actionable" not in summary


def test_report_names_the_experiment(tiny_config) -> None:
    analysis = make(tiny_config)
    assert analysis["experiment"]["id"] == "test"
    assert "- Experiment: **test** (tiny-fixture)" in render_report(analysis)
