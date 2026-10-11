"""Analysis of Experiment 001 results under the pre-registered decision rules.

Decision chain per generator (see docs/methodology.md):

1. Discovery: an exact two-sided binomial test of H0: p = p0 on unique
   candidates, corrected across all generators (the primary family).
2. Replication: generators flagged in discovery are tested again on the
   disjoint validation phase with a one-sided test in the same direction,
   corrected across the flagged generators.
3. Exploratory economic screen: a replicated effect passes only if it means
   MORE successes, the generator's domain is identical to the PREDECLARED
   economic reference (``economics.reference_generator``; never the fastest
   observed generator), and the validation lower confidence bound of the
   success-rate ratio, scaled by end-to-end throughput relative to that
   reference, reaches 1 + min_actionable_relative_effect. The bound used is the
   Bonferroni-SIMULTANEOUS bound across the primary family; a marginal bound
   alone never passes the screen. The screen is exploratory: this analysis
   never declares a confirmatory economic advantage (``actionable`` is always
   False).

Run-level gates: an incomplete run, or a harness INTEGRITY failure (missing
control evidence, invalid or internally inconsistent counts), blocks
interpretation. A statistically significant null control is a DIAGNOSTIC
WARNING, not an integrity failure: a correctly working null control is still
flagged with probability up to alpha.

Even the strongest label is "candidate anomaly: needs independent
replication". This analysis never concludes that SHA-256 is weak.
"""

from __future__ import annotations

import math

from hashlab import DIGEST_BITS, __version__
from hashlab.candidates import build_generator, expected_duplicates
from hashlab.evidence.manifest import utc_now_iso
from hashlab.experiments.config import PHASES, target_from_resolved
from hashlab.experiments.economics import (
    EVIDENCE_LEVEL,
    STATUS_NO_REFERENCE,
    STATUS_NOT_COMPARABLE,
    comparability_table,
    is_comparable,
    reference_generator,
)
from hashlab.statistics.distribution import DigestAccumulator, leading_zero_gof, uniform_byte_gof
from hashlab.statistics.inference import adjust, binom_test, clopper_pearson

CLASS_NULL = "consistent-with-null"
CLASS_UNREPLICATED = "unreplicated-discovery-signal"
CLASS_NON_ACTIONABLE = "replicated-anomaly-non-actionable"
CLASS_CANDIDATE = "candidate-anomaly-requires-independent-replication"

INTERVAL_MARGINAL = "marginal"
INTERVAL_SIMULTANEOUS = "simultaneous-bonferroni"

NULL_OK = "no-signal"
NULL_FLAGGED = "statistical-anomaly"
NULL_REPLICATED = "statistical-anomaly-replicated"
NULL_MISSING = "missing-evidence"

VERDICT_INCOMPLETE = "incomplete"
VERDICT_INTEGRITY = "integrity-failure"
VERDICT_UNINFORMATIVE = "uninformative"
VERDICT_CANDIDATE = "candidate-anomaly"
VERDICT_REPLICATED = "replicated-non-actionable"
VERDICT_NULL = "consistent-with-null"
BLOCKING_VERDICTS = (VERDICT_INCOMPLETE, VERDICT_INTEGRITY)

POSITIVE_CONTROL_LABEL = "positive-control"

NULL_RULE = (
    "statistical significance of the null control is a non-blocking diagnostic; missing or invalid "
    "null-control evidence is a blocking integrity failure"
)
NULL_INTERPRETATION = {
    NULL_OK: "The null control was not flagged in discovery.",
    NULL_FLAGGED: (
        "The null control was flagged in discovery but did not replicate. A correctly working null control "
        "is flagged with probability up to alpha, so this alone is not a harness failure. Confidence in "
        "every positive label of this run is reduced until the cause is investigated."
    ),
    NULL_REPLICATED: (
        "The null control was flagged in discovery AND replicated on disjoint validation candidates. Under a "
        "correct harness this has probability of order alpha squared. It is still reported as a diagnostic, not "
        "an integrity failure, but no positive label of this run should be acted on until it is explained."
    ),
    NULL_MISSING: "No usable null-control evidence was recorded. This is a blocking integrity failure.",
}
CONFIRMATORY_NOTE = (
    "not established: no predeclared confirmatory economic procedure exists; throughput is a single "
    "uncalibrated measurement and the screen is exploratory"
)

#: What each classification does and does not mean. Written into analysis.json and report.md.
#: The class strings are kept for compatibility; none of them is a confirmatory mining advantage.
CLASSIFICATION_LEGEND = {
    CLASS_NULL: "Not flagged in discovery after Holm correction. Not evidence of equivalence with the null.",
    CLASS_UNREPLICATED: "Flagged in discovery but not replicated on the disjoint validation phase.",
    CLASS_NON_ACTIONABLE: (
        "Statistically replicated deviation that did NOT pass the exploratory economic screen (fewer successes, "
        "a domain not comparable with the reference, no usable reference, or below the threshold). A lead for "
        "artifact investigation, not a search advantage."
    ),
    CLASS_CANDIDATE: (
        "Statistically replicated deviation that ALSO passed the EXPLORATORY economic screen. Exploratory only: "
        "it is not a confirmed mining advantage, not evidence of a SHA-256 weakness, and requires independent "
        "replication (fresh seeds, another machine, code review) before any further claim."
    ),
}
LABEL_NOTE = (
    "No label in this analysis is a confirmatory mining advantage: 'actionable' is always false and every "
    "economic figure is exploratory. The word 'non-actionable' in a class name means the exploratory screen "
    "was not passed; there is no 'actionable' class."
)


def _safe_div(a: float, b: float) -> float | None:
    return a / b if b else None


def phase_summary(counters: dict, p0: float, confidence: float, family_size: int = 1) -> dict:
    """Theoretical, empirical and throughput summary of one generator phase.

    ``rate_ci``/``rate_ratio_ci`` are MARGINAL intervals (this generator and
    phase alone). ``empirical.simultaneous`` holds Bonferroni-simultaneous
    intervals across ``family_size`` generators (confidence 1 - (1 - c) / m).
    """
    n = counters["unique"]
    k = counters["successes"]
    wall = counters["wall_seconds"]
    end_to_end = _safe_div(n, wall)
    overhead = counters["generation_seconds"] + counters["dedup_seconds"]
    summary: dict = {
        "theoretical": {
            "success_probability": p0,
            "expected_successes": n * p0,
            "standard_deviation": math.sqrt(n * p0 * (1.0 - p0)),
        },
        "empirical": {
            "attempted": counters["attempted"],
            "unique": n,
            "duplicates_within_phase": counters["duplicates_within_phase"],
            "duplicates_cross_phase": counters["duplicates_cross_phase"],
            "successes": k,
            "success_rate": _safe_div(k, n),
            "exhausted": counters["exhausted"],
        },
        "throughput": {
            "generation_per_second": _safe_div(counters["attempted"], counters["generation_seconds"]),
            "hashing_per_second": _safe_div(n, counters["hashing_seconds"]),
            "end_to_end_unique_per_second": end_to_end,
            "generation_seconds": counters["generation_seconds"],
            "dedup_seconds": counters["dedup_seconds"],
            "hashing_seconds": counters["hashing_seconds"],
            "wall_seconds": wall,
            "candidate_overhead_seconds": overhead,
            "candidate_overhead_fraction_of_wall": _safe_div(overhead, wall),
            "expected_valid_per_second": None if end_to_end is None else end_to_end * p0,
            "observed_valid_per_second": _safe_div(k, wall),
        },
    }
    if n > 0:
        lower, upper = clopper_pearson(k, n, confidence)
        family = max(1, int(family_size))
        sim_confidence = 1.0 - (1.0 - confidence) / family
        sim_lower, sim_upper = (lower, upper) if family == 1 else clopper_pearson(k, n, sim_confidence)
        summary["empirical"].update(
            {
                "confidence_level": confidence,
                "interval_type": INTERVAL_MARGINAL,
                "rate_ci": [lower, upper],
                "rate_ratio": (k / n) / p0,
                "rate_ratio_ci": [lower / p0, upper / p0],
                "p_value_two_sided": binom_test(k, n, p0, "two-sided"),
                "simultaneous": {
                    "interval_type": INTERVAL_SIMULTANEOUS,
                    "family_size": family,
                    "confidence_level": sim_confidence,
                    "rate_ci": [sim_lower, sim_upper],
                    "rate_ratio_ci": [sim_lower / p0, sim_upper / p0],
                },
            }
        )
    return summary


def analyze_results(results: dict, resolved: dict) -> dict:
    target = target_from_resolved(resolved)
    p0 = float(target.probability)
    stats = resolved["statistics"]
    alpha = stats["alpha"]
    confidence = stats["confidence_level"]
    correction = stats["correction"]
    min_effect = stats["min_actionable_relative_effect"]
    family_size = max(1, len(resolved["generators"]))

    integrity, broken = check_integrity(results, resolved)
    configured = {spec["id"] for spec in resolved["generators"]}
    recorded = results.get("generators") if isinstance(results.get("generators"), dict) else {}

    # Only configured generators and structurally valid counters are analyzed. Everything else
    # is listed under integrity problems, which block the verdict.
    analyzable: dict = {}
    for gid, entry in recorded.items():
        if gid not in configured or not isinstance(entry, dict) or not isinstance(entry.get("phases"), dict):
            continue
        phases = {p: c for p, c in entry["phases"].items() if p in PHASES and (gid, p) not in broken}
        analyzable[gid] = {**entry, "phases": phases}

    generators: dict = {}
    for gid, entry in analyzable.items():
        phases = {
            phase: phase_summary(entry["phases"][phase], p0, confidence, family_size) for phase in entry["phases"]
        }
        generators[gid] = {
            "domain": entry["description"]["domain"],
            "type": entry["description"]["type"],
            "parameters": entry["description"]["parameters"],
            "dedup_method": entry["dedup_method"],
            "phases": phases,
            "duplicates": _duplicate_summary(gid, entry, resolved),
        }

    # ---- primary family: discovery
    primary_ids = [
        gid for gid, g in generators.items()
        if "discovery" in g["phases"] and g["phases"]["discovery"]["empirical"]["unique"] > 0
    ]
    raw_p = [generators[gid]["phases"]["discovery"]["empirical"]["p_value_two_sided"] for gid in primary_ids]
    adj_p = adjust(raw_p, correction) if raw_p else []
    flagged = []
    for gid, p_raw, p_adj in zip(primary_ids, raw_p, adj_p):
        disc = generators[gid]["phases"]["discovery"]["empirical"]
        direction = "greater" if disc["success_rate"] > p0 else "less"
        generators[gid]["primary"] = {
            "p_value": p_raw,
            "p_value_adjusted": p_adj,
            "flagged": p_adj < alpha,
            "direction": direction,
        }
        if p_adj < alpha:
            flagged.append(gid)

    # ---- replication on the validation phase
    replication_ids = [
        gid for gid in flagged
        if "validation" in generators[gid]["phases"]
        and generators[gid]["phases"]["validation"]["empirical"]["unique"] > 0
    ]
    rep_raw = []
    for gid in replication_ids:
        val = generators[gid]["phases"]["validation"]["empirical"]
        rep_raw.append(binom_test(val["successes"], val["unique"], p0, generators[gid]["primary"]["direction"]))
    rep_adj = adjust(rep_raw, correction) if rep_raw else []
    for gid, p_raw, p_adj in zip(replication_ids, rep_raw, rep_adj):
        generators[gid]["replication"] = {"p_value_one_sided": p_raw, "p_value_adjusted": p_adj, "replicated": p_adj < alpha}

    # ---- economics (exploratory; predeclared reference, identical domains only)
    reference = reference_generator(resolved)
    comparability = comparability_table(resolved)
    reference_throughput = _validation_throughput(generators.get(reference)) if reference else None
    for gid, g in generators.items():
        comp = comparability.get(gid, {"status": STATUS_NO_REFERENCE, "reference": reference, "domain_differences": []})
        throughput = _validation_throughput(g)
        ratio = (
            throughput / reference_throughput
            if is_comparable(comp["status"]) and throughput and reference_throughput
            else None
        )
        g["economics"] = {
            "evidence_level": EVIDENCE_LEVEL,
            "phase": "validation",
            "reference_generator": reference,
            "comparability": comp["status"],
            "domain_differences": comp["domain_differences"],
            "end_to_end_unique_per_second": throughput,
            "throughput_ratio_vs_reference": ratio,
            "note": _economics_note(comp["status"], ratio),
        }

    # ---- classification and the exploratory economic screen
    required = 1.0 + min_effect
    for gid, g in generators.items():
        primary = g.get("primary")
        replication = g.get("replication")
        if primary is None or not primary["flagged"]:
            g["classification"] = CLASS_NULL
            continue
        if replication is None or not replication["replicated"]:
            g["classification"] = CLASS_UNREPLICATED
            continue
        val = g["phases"]["validation"]["empirical"]
        ratio = g["economics"]["throughput_ratio_vs_reference"]
        lower_marginal = val["rate_ratio_ci"][0]
        lower_simultaneous = val["simultaneous"]["rate_ratio_ci"][0]
        greater = primary["direction"] == "greater"
        if ratio is None:
            status = g["economics"]["comparability"]
            screen_status = status if not is_comparable(status) else "reference-unavailable"
            lift_marginal = lift_simultaneous = None
            marginal_pass = simultaneous_pass = False
        else:
            screen_status = "screened"
            lift_marginal = lower_marginal * ratio
            lift_simultaneous = lower_simultaneous * ratio
            marginal_pass = greater and lift_marginal >= required
            simultaneous_pass = greater and lift_simultaneous >= required
        g["actionability"] = {
            "evidence_level": EVIDENCE_LEVEL,
            "screen_status": screen_status,
            "reference_generator": reference,
            "validation_rate_ratio_lower_bound": lower_marginal,
            "validation_rate_ratio_lower_bound_interval": INTERVAL_MARGINAL,
            "validation_rate_ratio_lower_bound_simultaneous": lower_simultaneous,
            "throughput_ratio_vs_reference": ratio,
            "throughput_adjusted_lift_lower_bound": lift_marginal,
            "throughput_adjusted_lift_lower_bound_simultaneous": lift_simultaneous,
            "required": required,
            "marginal_bound_alone_would_pass": marginal_pass,
            "exploratory_screen_passed": simultaneous_pass,
            "actionable": False,
            "confirmatory_status": CONFIRMATORY_NOTE,
        }
        g["classification"] = CLASS_CANDIDATE if simultaneous_pass else CLASS_NON_ACTIONABLE

    # ---- secondary (exploratory) family
    secondary = []
    for gid, entry in analyzable.items():
        for phase, counters in entry["phases"].items():
            acc = DigestAccumulator.from_dict(counters["digest_distribution"])
            for gof in (
                leading_zero_gof(acc.leading_zero_bits),
                uniform_byte_gof(acc.first_byte, "first_byte_uniform"),
                uniform_byte_gof(acc.last_byte, "last_byte_uniform"),
            ):
                secondary.append({"generator": gid, "phase": phase, **gof.to_dict()})
    tested = [row for row in secondary if row["p_value"] is not None]
    for row, p_adj in zip(tested, adjust([row["p_value"] for row in tested], correction) if tested else []):
        row["p_value_adjusted"] = p_adj
        row["flagged"] = p_adj < alpha

    # ---- controls
    null_control = _null_control(resolved["controls"]["null_control_generator"], generators)
    if (POSITIVE_CONTROL_LABEL, "control") in broken:
        positive: dict | None = {"detected": False, "note": "invalid positive-control counters (integrity failure)"}
    else:
        positive = _positive_control(results.get("positive_control"), p0, alpha, max(1, len(primary_ids)), confidence)

    diagnostics = _diagnostics(null_control, reference, reference_throughput, generators)
    verdict = _verdict(results.get("status"), generators, null_control, positive, integrity, diagnostics)
    for g in generators.values():
        g["classification_meaning"] = CLASSIFICATION_LEGEND[g.get("classification", CLASS_NULL)]
    return {
        "hashlab_version": __version__,
        "analyzed_at_utc": utc_now_iso(),
        "experiment": resolved["experiment"],
        "run_id": results.get("run_id"),
        "run_status": results.get("status"),
        "engine": results.get("engine"),
        "target": results.get("target"),
        "decision_parameters": {
            "alpha": alpha,
            "confidence_level": confidence,
            "correction": correction,
            "min_actionable_relative_effect": min_effect,
            "interval_type": INTERVAL_MARGINAL,
            "simultaneous_interval": {
                "interval_type": INTERVAL_SIMULTANEOUS,
                "family_size": family_size,
                "confidence_level": 1.0 - (1.0 - confidence) / family_size,
            },
            "economic_reference_generator": reference,
            "economic_evidence_level": EVIDENCE_LEVEL,
        },
        "integrity": {"passed": not integrity, "blocking": bool(integrity), "problems": integrity},
        "diagnostics": diagnostics,
        "economics": {
            "reference_generator": reference,
            "evidence_level": EVIDENCE_LEVEL,
            "reference_end_to_end_unique_per_second": reference_throughput,
            "comparability": comparability,
        },
        "generators": generators,
        "secondary_tests": secondary,
        "null_control": null_control,
        "positive_control": positive,
        "verdict": verdict,
        "classification_legend": CLASSIFICATION_LEGEND,
        "label_note": LABEL_NOTE,
        "limitations": LIMITATIONS,
    }


def _validation_throughput(generator: dict | None) -> float | None:
    if generator is None:
        return None
    return generator["phases"].get("validation", {}).get("throughput", {}).get("end_to_end_unique_per_second")


def _economics_note(status: str, ratio: float | None) -> str:
    if status == STATUS_NO_REFERENCE:
        return "no predeclared economic reference: descriptive throughput only"
    if status == STATUS_NOT_COMPARABLE:
        return "domain differs from the predeclared reference: descriptive throughput only, no relative-efficiency claim"
    if ratio is None:
        return "throughput of this generator or of the reference is unavailable: no relative-efficiency figure"
    return (
        "identical domain to the predeclared reference (not necessarily independent samples); the ratio is one "
        "uncalibrated measurement (exploratory)"
    )


# --------------------------------------------------------------------------- integrity

_COUNT_FIELDS = ("attempted", "unique", "duplicates_within_phase", "duplicates_cross_phase", "successes")
_TIME_FIELDS = ("generation_seconds", "dedup_seconds", "hashing_seconds", "wall_seconds")
_HISTOGRAMS = {"leading_zero_bits": DIGEST_BITS + 1, "first_byte": 256, "last_byte": 256}


def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_duration(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _counter_problems(label: str, counters: object, planned: int | None, success_bits: int | None) -> tuple[list[str], bool]:
    """Problems with one set of phase counters, and whether they are too broken to analyze."""
    if not isinstance(counters, dict):
        return [f"{label}: counters are missing"], True
    bad = [f for f in _COUNT_FIELDS if not _is_count(counters.get(f))]
    bad += [f for f in _TIME_FIELDS if not _is_duration(counters.get(f))]
    if bad:
        return [f"{label}: {', '.join(bad)} missing or invalid"], True
    problems: list[str] = []
    fatal = False
    attempted, unique, dup_within, dup_cross, successes = (counters[f] for f in _COUNT_FIELDS)
    if successes > unique:
        problems.append(f"{label}: successes ({successes}) exceed unique candidates ({unique})")
        fatal = True
    if unique + dup_within + dup_cross != attempted:
        problems.append(f"{label}: unique + duplicates ({unique + dup_within + dup_cross}) != attempted ({attempted})")
    if planned is not None:
        if attempted > planned:
            problems.append(f"{label}: attempted ({attempted}) exceeds the planned {planned}")
        elif attempted < planned and counters.get("exhausted") is not True:
            problems.append(f"{label}: attempted ({attempted}) is below the planned {planned} without exhaustion")
    dist = counters.get("digest_distribution")
    if not isinstance(dist, dict):
        return problems + [f"{label}: digest distribution is missing"], True
    histograms_valid = True
    for name, max_bins in _HISTOGRAMS.items():
        values = dist.get(name)
        if not isinstance(values, list) or len(values) > max_bins or not all(_is_count(v) for v in values):
            problems.append(f"{label}: {name} histogram is missing or invalid")
            histograms_valid = False
        elif name != "leading_zero_bits" and len(values) != max_bins:
            problems.append(f"{label}: {name} histogram must have {max_bins} bins")
            histograms_valid = False
        elif sum(values) != unique:
            problems.append(f"{label}: {name} histogram total ({sum(values)}) != unique ({unique})")
    if not histograms_valid:
        return problems, True
    if success_bits is not None:
        tail = sum(dist["leading_zero_bits"][success_bits:])
        if tail != successes:
            problems.append(
                f"{label}: successes ({successes}) disagree with the leading-zero histogram "
                f"({tail} digests with >= {success_bits} leading zero bits)"
            )
    return problems, fatal


def check_integrity(results: dict, resolved: dict) -> tuple[list[str], set[tuple[str, str]]]:
    """Blocking harness-integrity problems, plus the (generator, phase) counters too broken to analyze.

    Covers missing control or generator evidence (complete runs only), counts
    that are invalid or internally inconsistent, histograms that disagree with
    the counts, and (for power-of-two targets) success counts that disagree
    with the leading-zero histogram. Evidence-file integrity (manifest hashes)
    is verified separately by ``hashlab analyze`` before this function runs.
    Statistical results, including a significant null control, are never
    integrity problems.
    """
    problems: list[str] = []
    broken: set[tuple[str, str]] = set()
    complete = results.get("status") == "complete"
    success_bits = target_from_resolved(resolved).equivalent_leading_zero_bits
    planned = {phase: resolved["phases"][phase]["candidates_per_generator"] for phase in PHASES}
    configured = [spec["id"] for spec in resolved["generators"]]
    recorded = results.get("generators")
    if not isinstance(recorded, dict):
        problems.append("results contain no generator section")
        recorded = {}

    def phases_of(gid: str) -> dict | None:
        entry = recorded.get(gid)
        phases = entry.get("phases") if isinstance(entry, dict) else None
        return phases if isinstance(phases, dict) else None

    for gid in recorded:
        if gid not in configured:
            problems.append(f"{gid}: results include a generator that is not in the configuration")
    for gid in configured:
        phases = phases_of(gid)
        if phases is None:
            if complete or gid in recorded:
                problems.append(f"{gid}: no generator results recorded")
            continue
        for phase in phases:
            if phase not in PHASES:
                problems.append(f"{gid}: unknown phase {phase!r}")
        for phase in PHASES:
            if phase not in phases:
                if complete:
                    problems.append(f"{gid}/{phase}: phase results are missing")
                continue
            found, fatal = _counter_problems(f"{gid}/{phase}", phases[phase], planned[phase], success_bits)
            problems += found
            if fatal:
                broken.add((gid, phase))

    null_id = resolved["controls"]["null_control_generator"]
    if complete and null_id is not None:
        discovery = (phases_of(null_id) or {}).get("discovery")
        if not isinstance(discovery, dict) or (null_id, "discovery") in broken or discovery.get("unique") == 0:
            problems.append(f"null control {null_id}: no usable discovery-phase evidence")

    positive_cfg = resolved["controls"]["positive_control"]
    positive = results.get("positive_control")
    if positive is None:
        if complete and positive_cfg["enabled"]:
            problems.append("positive control is enabled but no evidence was recorded")
    else:
        counters = positive.get("counters") if isinstance(positive, dict) else None
        found, fatal = _counter_problems(
            POSITIVE_CONTROL_LABEL, counters, positive_cfg["candidates"] if positive_cfg["enabled"] else None, success_bits
        )
        problems += found
        if fatal:
            broken.add((POSITIVE_CONTROL_LABEL, "control"))
        elif complete and positive_cfg["enabled"] and counters["unique"] == 0:
            problems.append("positive control: no candidates were hashed")
    return problems, broken


# --------------------------------------------------------------------------- per-generator helpers


def _duplicate_summary(gid: str, entry: dict, resolved: dict) -> dict:
    spec = next(s for s in resolved["generators"] if s["id"] == gid)
    gen = build_generator(spec)
    attempted = sum(entry["phases"][p]["attempted"] for p in entry["phases"])
    observed = sum(
        entry["phases"][p]["duplicates_within_phase"] + entry["phases"][p]["duplicates_cross_phase"]
        for p in entry["phases"]
    )
    return {
        "attempted_total": attempted,
        "observed_duplicates": observed,
        "theoretical_expected_duplicates": (
            expected_duplicates(attempted, gen.domain().cardinality) if gen.uses_seed else 0.0
        ),
        "note": (
            "Seeded phases use different sub-seeds; candidates repeated across phases are removed from validation."
            if gen.uses_seed
            else "Unique by construction; validation continues the enumeration after discovery."
        ),
    }


def _null_control(null_id: str | None, generators: dict) -> dict | None:
    if null_id is None:
        return None
    generator = generators.get(null_id)
    primary = generator.get("primary") if generator else None
    if primary is None:
        return {
            "generator": null_id,
            "status": NULL_MISSING,
            "passed": False,
            "statistically_flagged": None,
            "blocking": True,
            "rule": NULL_RULE,
            "interpretation": NULL_INTERPRETATION[NULL_MISSING],
        }
    flagged = primary["flagged"]
    replicated = (generator.get("replication") or {}).get("replicated", False) if flagged else None
    status = NULL_OK if not flagged else (NULL_REPLICATED if replicated else NULL_FLAGGED)
    return {
        "generator": null_id,
        "status": status,
        "passed": not flagged,  # unchanged meaning: the discovery test did not flag the null control
        "statistically_flagged": flagged,
        "p_value": primary["p_value"],
        "p_value_adjusted": primary["p_value_adjusted"],
        "replicated": replicated,
        "blocking": False,
        "rule": NULL_RULE,
        "interpretation": NULL_INTERPRETATION[status],
    }


def _positive_control(entry: dict | None, p0: float, alpha: float, family: int, confidence: float) -> dict | None:
    if entry is None:
        return None
    counters = entry["counters"]
    n, k = counters["unique"], counters["successes"]
    if n == 0:
        return {"detected": False, "note": "no candidates were hashed"}
    p_value = binom_test(k, n, p0, "greater")
    lower, upper = clopper_pearson(k, n, confidence)
    return {
        "expected_success_probability": entry["engine"]["expected_success_probability"],
        "relative_lift_requested": entry["engine"]["relative_lift_requested"],
        "unique": n,
        "successes": k,
        "rate_ratio": (k / n) / p0,
        "rate_ratio_ci": [lower / p0, upper / p0],
        "interval_type": INTERVAL_MARGINAL,
        "p_value_one_sided": p_value,
        "threshold": alpha / family,
        "detected": p_value < alpha / family,
        "rule": "one-sided exact test against p0 at alpha / primary_family_size",
    }


def _diagnostics(
    null_control: dict | None, reference: str | None, reference_throughput: float | None, generators: dict
) -> list[dict]:
    diagnostics: list[dict] = []
    if null_control is not None and null_control["status"] in (NULL_FLAGGED, NULL_REPLICATED):
        diagnostics.append(
            {
                "code": "null-control-statistically-significant",
                "severity": "serious" if null_control["status"] == NULL_REPLICATED else "warning",
                "blocking": False,
                "generator": null_control["generator"],
                "message": (
                    f"NULL-CONTROL DIAGNOSTIC: {null_control['generator']} was flagged in discovery "
                    f"(adjusted p = {null_control['p_value_adjusted']:.3g})"
                    + (" and replicated in validation. " if null_control["replicated"] else ". ")
                    + null_control["interpretation"]
                ),
            }
        )
    if reference is None:
        diagnostics.append(
            {
                "code": "no-economic-reference",
                "severity": "info",
                "blocking": False,
                "message": "No predeclared economic reference: the economic screen is disabled and throughput is "
                "descriptive only.",
            }
        )
    elif reference_throughput is None:
        diagnostics.append(
            {
                "code": "economic-reference-unavailable",
                "severity": "warning",
                "blocking": False,
                "generator": reference,
                "message": f"The predeclared economic reference {reference} has no validation-phase throughput; "
                "no generator can pass the economic screen.",
            }
        )
    for gid, g in generators.items():
        if g.get("replication", {}).get("replicated") and g["economics"]["comparability"] == STATUS_NOT_COMPARABLE:
            diagnostics.append(
                {
                    "code": "economic-domain-not-comparable",
                    "severity": "info",
                    "blocking": False,
                    "generator": gid,
                    "message": (
                        f"{gid} replicated but its domain differs from the reference "
                        f"({', '.join(g['economics']['domain_differences'])}); no relative-efficiency claim is made."
                    ),
                }
            )
    return diagnostics


def _verdict(
    status: str | None,
    generators: dict,
    null_control: dict | None,
    positive: dict | None,
    integrity: list[str],
    diagnostics: list[dict],
) -> dict:
    classes = {gid: g.get("classification", CLASS_NULL) for gid, g in generators.items()}
    candidates = [gid for gid, c in classes.items() if c == CLASS_CANDIDATE]
    replicated = [gid for gid, c in classes.items() if c == CLASS_NON_ACTIONABLE]
    unreplicated = [gid for gid, c in classes.items() if c == CLASS_UNREPLICATED]
    if status != "complete":
        code = VERDICT_INCOMPLETE
        summary = "INCOMPLETE RUN: no scientific conclusions may be drawn."
    elif integrity:
        code = VERDICT_INTEGRITY
        summary = (
            f"HARNESS INTEGRITY FAILURE: {len(integrity)} problem(s) with the recorded evidence (see "
            "integrity.problems). No result of this run may be interpreted until they are resolved."
        )
    elif positive is not None and not positive.get("detected"):
        code = VERDICT_UNINFORMATIVE
        summary = (
            "UNINFORMATIVE: the positive control was not detected, so this run could not detect the "
            "planted effect. Null results here carry little weight."
        )
    elif candidates:
        code = VERDICT_CANDIDATE
        summary = (
            "CANDIDATE ANOMALY (not evidence of a SHA-256 weakness, and not a confirmed mining advantage): "
            "replicated on independent validation candidates, more successes than p0, and passed the EXPLORATORY "
            "economic screen against the predeclared reference using simultaneous bounds, for "
            + ", ".join(candidates) + ". Needs independent replication with fresh seeds, a separate machine and "
            "code review before any further claim."
        )
    elif replicated:
        code = VERDICT_REPLICATED
        summary = (
            "Replicated statistical deviation(s) that did not pass the exploratory economic screen ("
            + ", ".join(replicated) + "). Treat as a lead for investigating artifacts, not as a search advantage."
        )
    else:
        code = VERDICT_NULL
        summary = (
            "All primary results are consistent with the cryptographic null hypothesis (no corrected discovery "
            "signal). This does not establish equivalence and does not rule out effects near or below the "
            "planning minimum detectable effect."
        )
    null_flagged = null_control is not None and null_control["status"] in (NULL_FLAGGED, NULL_REPLICATED)
    if code not in BLOCKING_VERDICTS and null_flagged:
        summary += (
            f" WARNING: the null control {null_control['generator']} was statistically flagged"
            + (" and replicated" if null_control["replicated"] else "")
            + "; this is a non-blocking diagnostic that reduces confidence in every positive label of this run."
        )
    return {
        "status": code,
        "blocking": code in BLOCKING_VERDICTS,
        "summary": summary,
        "classifications": classes,
        "unreplicated_discovery_signals": unreplicated,
        "warnings": [d["message"] for d in diagnostics if d["severity"] in ("warning", "serious")],
        "exploratory_screen_passed": candidates,
        "confirmatory_economic_claim": False,
        "economic_evidence_level": EVIDENCE_LEVEL,
    }


LIMITATIONS = [
    "Generators with different widths, alphabets or encodings draw from different sample spaces; "
    "each is compared with the theoretical p0, not with each other.",
    "Candidates are deduplicated within a generator (both phases), not across generators. Different "
    "generators may share inputs (for example the all-zero candidate).",
    "An identical domain does not mean independent samples. In the baseline, seq-be-w8 and struct-gray-w8 "
    "share 951,424 of their 1,000,000 candidates (both enumerate integers below 2^20), so their results are "
    "nearly the same measurement and agreement between them is not corroboration. Validation is disjoint "
    "within a generator, not across generators. Deterministic generators cover a structured corner of the "
    "domain, not a random sample of it.",
    "Successes at the primary target and the leading-zero-bit histogram describe the same digests; the "
    "secondary tests are not independent of the primary test.",
    "Measurements across distinct SHA-256 inputs are modeled as independent Bernoulli trials. That is the "
    "null model under test, not a proven mathematical fact.",
    "Throughput reflects this Python implementation on this machine and is not representative of "
    "optimized or hardware mining. It is one measurement with no uncertainty model, so every economic "
    "comparison is exploratory, and only generators whose domain is identical to the predeclared reference "
    "are compared with it.",
    "Intervals labelled 'marginal' cover one generator and phase at the stated confidence; they are not "
    "simultaneous across generators. 'Simultaneous' intervals use Bonferroni across the primary family.",
    "A non-significant result is not evidence of equivalence. The planning minimum detectable effect is not "
    "an exclusion bound.",
    "A statistically significant null control is reported as a diagnostic: a correct harness flags it with "
    "probability up to alpha.",
    "A p-value below alpha is never, by itself, evidence of cryptographic weakness.",
]


# --------------------------------------------------------------------------- report


def _fmt_p(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3e}" if value < 1e-3 else f"{value:.4f}"


def _fmt_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6e}"


def _fmt_ratio(value: float | None, ci: list[float] | None) -> str:
    if value is None or ci is None:
        return "n/a"
    return f"{value:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]"


def render_report(analysis: dict) -> str:
    dp = analysis["decision_parameters"]
    target = analysis["target"] or {}
    sim = dp["simultaneous_interval"]
    experiment = analysis.get("experiment") or {}
    lines = [
        f"# HASHLAB report: run {analysis['run_id']}",
        "",
        f"- Experiment: **{experiment.get('id')}** ({experiment.get('name')})",
        f"- Run status: **{analysis['run_status']}**",
        f"- Engine: `{(analysis['engine'] or {}).get('name')}`",
        f"- Target: `{target.get('target_hex')}` (leading zero bits: {target.get('equivalent_leading_zero_bits')})",
        f"- alpha = {dp['alpha']}, confidence = {dp['confidence_level']}, correction = {dp['correction']}, "
        f"min actionable relative effect = {dp['min_actionable_relative_effect']} (exploratory economic screen only)",
        f"- Intervals: **marginal** = {dp['confidence_level']} Clopper-Pearson per generator and phase, not "
        f"multiplicity-adjusted; **simultaneous** = Bonferroni across {sim['family_size']} generators "
        f"(per-interval confidence {sim['confidence_level']:.6g})",
        f"- Economic reference (predeclared): `{dp['economic_reference_generator']}`; economic evidence is "
        f"{dp['economic_evidence_level']}",
        f"- Analyzed at {analysis['analyzed_at_utc']} with hashlab {analysis['hashlab_version']}",
        "",
        "## Verdict",
        "",
        analysis["verdict"]["summary"],
        "",
        "## How to read the labels",
        "",
        analysis["label_note"],
        "",
    ]
    lines += [f"- `{label}`: {meaning}" for label, meaning in analysis["classification_legend"].items()]
    lines += [
        "",
        "## Harness integrity",
        "",
    ]
    integrity = analysis["integrity"]
    if integrity["passed"]:
        lines.append("No integrity problems in the recorded counts and control evidence (blocking checks).")
    else:
        lines.append("BLOCKING problems:")
        lines += [f"- {problem}" for problem in integrity["problems"]]

    lines += ["", "## Diagnostics (non-blocking)", ""]
    if analysis["diagnostics"]:
        lines += [f"- [{d['severity']}] {d['message']}" for d in analysis["diagnostics"]]
    else:
        lines.append("None.")

    lines += [
        "",
        "## Theoretical expectation (null hypothesis)",
        "",
        f"p0 = target / 2^256 = {target.get('success_probability_exact')} "
        f"= {target.get('success_probability_float')}",
        "",
        "## Empirical measurements: primary family (discovery phase)",
        "",
        "| generator | domain | unique | successes | expected | rate | rate ratio [marginal CI] | p | p adj | class (see legend) |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for gid, g in analysis["generators"].items():
        phase = g["phases"].get("discovery")
        if phase is None:
            continue
        emp, theo = phase["empirical"], phase["theoretical"]
        primary = g.get("primary", {})
        domain = g["domain"]
        lines.append(
            f"| {gid} | {domain['kind']} w={domain['width_bytes']} | {emp['unique']:,} | {emp['successes']:,} | "
            f"{theo['expected_successes']:.1f} | {_fmt_rate(emp['success_rate'])} | "
            f"{_fmt_ratio(emp.get('rate_ratio'), emp.get('rate_ratio_ci'))} | "
            f"{_fmt_p(primary.get('p_value'))} | {_fmt_p(primary.get('p_value_adjusted'))} | "
            f"{g.get('classification')} |"
        )

    lines += [
        "",
        "## Validation phase (independent, disjoint candidates)",
        "",
        "| generator | unique | successes | expected | rate ratio [marginal CI] | rate ratio [simultaneous CI] | "
        "two-sided p (unadjusted, descriptive) | replication p adj |",
        "|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for gid, g in analysis["generators"].items():
        phase = g["phases"].get("validation")
        if phase is None:
            continue
        emp, theo = phase["empirical"], phase["theoretical"]
        rep = g.get("replication", {})
        lines.append(
            f"| {gid} | {emp['unique']:,} | {emp['successes']:,} | {theo['expected_successes']:.1f} | "
            f"{_fmt_ratio(emp.get('rate_ratio'), emp.get('rate_ratio_ci'))} | "
            f"{_fmt_ratio(emp.get('rate_ratio'), (emp.get('simultaneous') or {}).get('rate_ratio_ci'))} | "
            f"{_fmt_p(emp.get('p_value_two_sided'))} | {_fmt_p(rep.get('p_value_adjusted'))} |"
        )

    lines += [
        "",
        "## Duplicates",
        "",
        "| generator | dedup method | attempted | observed duplicates | theoretical expected |",
        "|---|---|---:|---:|---:|",
    ]
    for gid, g in analysis["generators"].items():
        d = g["duplicates"]
        lines.append(
            f"| {gid} | {g['dedup_method']} | {d['attempted_total']:,} | {d['observed_duplicates']:,} | "
            f"{d['theoretical_expected_duplicates']:.2f} |"
        )

    lines += [
        "",
        "## Throughput (measured, this machine, Python implementation)",
        "",
        "| generator | phase | generation/s | hashing/s | end-to-end unique/s |",
        "|---|---|---:|---:|---:|",
    ]
    for gid, g in analysis["generators"].items():
        for phase_name in PHASES:
            phase = g["phases"].get(phase_name)
            if phase is None:
                continue
            t = phase["throughput"]
            lines.append(
                f"| {gid} | {phase_name} | {_fmt_num(t['generation_per_second'])} | "
                f"{_fmt_num(t['hashing_per_second'])} | {_fmt_num(t['end_to_end_unique_per_second'])} |"
            )

    lines += [
        "",
        "## Economics (EXPLORATORY, validation phase)",
        "",
        f"Predeclared reference: `{analysis['economics']['reference_generator']}`. Relative figures are given only "
        "for generators whose domain is identical to the reference. No row is a confirmatory economic claim.",
        "",
        "| generator | comparability | candidate overhead (share of wall) | expected valid/s | observed valid/s | "
        "throughput vs reference | exploratory screen |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for gid, g in analysis["generators"].items():
        econ = g["economics"]
        t = g["phases"].get("validation", {}).get("throughput", {})
        share = t.get("candidate_overhead_fraction_of_wall")
        ratio = econ["throughput_ratio_vs_reference"]
        action = g.get("actionability")
        if action is None:
            screen = "n/a"
        else:
            screen = ("passed (exploratory)" if action["exploratory_screen_passed"] else "not passed") + f" ({action['screen_status']})"
        differences = f" ({', '.join(econ['domain_differences'])})" if econ["domain_differences"] else ""
        lines.append(
            f"| {gid} | {econ['comparability']}{differences} | {'n/a' if share is None else f'{share:.1%}'} | "
            f"{_fmt_float(t.get('expected_valid_per_second'))} | {_fmt_float(t.get('observed_valid_per_second'))} | "
            f"{'n/a' if ratio is None else f'{ratio:.4f}'} | {screen} |"
        )

    lines += ["", "## Controls", ""]
    nc = analysis["null_control"]
    if nc is None:
        lines.append("- Null control: none designated")
    elif nc["status"] == NULL_MISSING:
        lines.append(f"- Null control: {nc['generator']}: MISSING EVIDENCE (blocking integrity failure)")
    else:
        lines.append(
            f"- Null control: {nc['generator']}: {nc['status']} (adjusted p = {_fmt_p(nc['p_value_adjusted'])}; "
            f"{'not flagged' if nc['passed'] else 'flagged: non-blocking diagnostic'})"
        )
    pc = analysis["positive_control"]
    if pc and "p_value_one_sided" in pc:
        lines.append(
            f"- Positive control (planted lift {pc['relative_lift_requested']}): ratio {pc['rate_ratio']:.4f} "
            f"[{pc['rate_ratio_ci'][0]:.4f}, {pc['rate_ratio_ci'][1]:.4f}] (marginal), "
            f"one-sided p = {_fmt_p(pc['p_value_one_sided'])}, "
            f"{'DETECTED' if pc['detected'] else 'NOT DETECTED'} (threshold {pc['threshold']:.3g})"
        )
    elif pc:
        lines.append(f"- Positive control: NOT DETECTED ({pc.get('note', 'no data')})")
    else:
        lines.append("- Positive control: disabled or empty")

    flagged_secondary = [row for row in analysis["secondary_tests"] if row.get("flagged")]
    lines += [
        "",
        "## Secondary (exploratory) distribution tests",
        "",
        f"{len(analysis['secondary_tests'])} tests; {len(flagged_secondary)} flagged after {dp['correction']} correction. "
        "Exploratory only: they do not change the verdict.",
    ]
    for row in flagged_secondary:
        lines.append(f"- {row['generator']}/{row['phase']}: {row['test']} adjusted p = {_fmt_p(row['p_value_adjusted'])}")

    lines += ["", "## Limitations", ""] + [f"- {item}" for item in analysis["limitations"]]
    return "\n".join(lines) + "\n"


def _fmt_num(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.0f}"


def _fmt_float(value: float | None) -> str:
    return "n/a" if value is None else f"{value:,.2f}"
