"""Analysis of Experiment 001 results under the pre-registered decision rules.

Decision chain per generator (see docs/methodology.md):

1. Discovery: an exact two-sided binomial test of H0: p = p0 on unique
   candidates, corrected across all generators (the primary family).
2. Replication: generators flagged in discovery are tested again on the
   disjoint validation phase with a one-sided test in the same direction,
   corrected across the flagged generators.
3. Actionability: a replicated effect counts only if it means MORE successes,
   and if the validation lower confidence bound of the success-rate ratio,
   scaled by the generator's end-to-end throughput relative to the fastest
   generator, reaches 1 + min_actionable_relative_effect.

Even the strongest label is "candidate anomaly: needs independent
replication". This analysis never concludes that SHA-256 is weak.
"""

from __future__ import annotations

import math

from hashlab import __version__
from hashlab.candidates import build_generator, expected_duplicates
from hashlab.evidence.manifest import utc_now_iso
from hashlab.experiments.config import PHASES, target_from_resolved
from hashlab.statistics.distribution import DigestAccumulator, leading_zero_gof, uniform_byte_gof
from hashlab.statistics.inference import adjust, binom_test, clopper_pearson

CLASS_NULL = "consistent-with-null"
CLASS_UNREPLICATED = "unreplicated-discovery-signal"
CLASS_NON_ACTIONABLE = "replicated-anomaly-non-actionable"
CLASS_CANDIDATE = "candidate-anomaly-requires-independent-replication"


def _safe_div(a: float, b: float) -> float | None:
    return a / b if b else None


def phase_summary(counters: dict, p0: float, confidence: float) -> dict:
    n = counters["unique"]
    k = counters["successes"]
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
            "end_to_end_unique_per_second": _safe_div(n, counters["wall_seconds"]),
            "generation_seconds": counters["generation_seconds"],
            "dedup_seconds": counters["dedup_seconds"],
            "hashing_seconds": counters["hashing_seconds"],
            "wall_seconds": counters["wall_seconds"],
        },
    }
    if n > 0:
        lower, upper = clopper_pearson(k, n, confidence)
        summary["empirical"].update(
            {
                "confidence_level": confidence,
                "rate_ci": [lower, upper],
                "rate_ratio": (k / n) / p0,
                "rate_ratio_ci": [lower / p0, upper / p0],
                "p_value_two_sided": binom_test(k, n, p0, "two-sided"),
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

    generators: dict = {}
    for gid, entry in results["generators"].items():
        phases = {phase: phase_summary(entry["phases"][phase], p0, confidence) for phase in entry["phases"]}
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

    # ---- actionability (economic relevance)
    throughputs = {
        gid: g["phases"].get("validation", {}).get("throughput", {}).get("end_to_end_unique_per_second")
        for gid, g in generators.items()
    }
    fastest = max((t for t in throughputs.values() if t), default=None)
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
        throughput_ratio = (throughputs[gid] / fastest) if (throughputs[gid] and fastest) else 0.0
        lower_ratio = val["rate_ratio_ci"][0]
        adjusted_lift = lower_ratio * throughput_ratio
        actionable = primary["direction"] == "greater" and adjusted_lift >= 1.0 + min_effect
        g["actionability"] = {
            "validation_rate_ratio_lower_bound": lower_ratio,
            "throughput_ratio_vs_fastest": throughput_ratio,
            "throughput_adjusted_lift_lower_bound": adjusted_lift,
            "required": 1.0 + min_effect,
            "actionable": actionable,
        }
        g["classification"] = CLASS_CANDIDATE if actionable else CLASS_NON_ACTIONABLE

    # ---- secondary (exploratory) family
    secondary = []
    for gid, entry in results["generators"].items():
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
    null_id = resolved["controls"]["null_control_generator"]
    null_control = None
    if null_id is not None and null_id in generators and "primary" in generators[null_id]:
        null_control = {
            "generator": null_id,
            "passed": not generators[null_id]["primary"]["flagged"],
            "rule": "the null-control generator must not be flagged in discovery",
        }
    positive = _positive_control(results.get("positive_control"), p0, alpha, max(1, len(primary_ids)), confidence)

    verdict = _verdict(results.get("status"), generators, null_control, positive)
    return {
        "hashlab_version": __version__,
        "analyzed_at_utc": utc_now_iso(),
        "run_id": results.get("run_id"),
        "run_status": results.get("status"),
        "engine": results.get("engine"),
        "target": results.get("target"),
        "decision_parameters": {
            "alpha": alpha,
            "confidence_level": confidence,
            "correction": correction,
            "min_actionable_relative_effect": min_effect,
        },
        "generators": generators,
        "secondary_tests": secondary,
        "null_control": null_control,
        "positive_control": positive,
        "verdict": verdict,
        "limitations": LIMITATIONS,
    }


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
        "p_value_one_sided": p_value,
        "threshold": alpha / family,
        "detected": p_value < alpha / family,
        "rule": "one-sided exact test against p0 at alpha / primary_family_size",
    }


def _verdict(status: str | None, generators: dict, null_control: dict | None, positive: dict | None) -> dict:
    classes = {gid: g.get("classification", CLASS_NULL) for gid, g in generators.items()}
    candidates = [gid for gid, c in classes.items() if c == CLASS_CANDIDATE]
    replicated = [gid for gid, c in classes.items() if c == CLASS_NON_ACTIONABLE]
    unreplicated = [gid for gid, c in classes.items() if c == CLASS_UNREPLICATED]
    if status != "complete":
        summary = "INCOMPLETE RUN: no scientific conclusions may be drawn."
    elif null_control is not None and not null_control["passed"]:
        summary = (
            "HARNESS ALARM: the null-control generator was flagged. Investigate the pipeline "
            "before interpreting any other result."
        )
    elif positive is not None and not positive.get("detected"):
        summary = (
            "UNINFORMATIVE: the positive control was not detected, so this run could not detect the "
            "planted effect. Null results here carry little weight."
        )
    elif candidates:
        summary = (
            "CANDIDATE ANOMALY (not evidence of a SHA-256 weakness): replicated, positive and above the "
            "economic threshold for " + ", ".join(candidates) + ". Needs independent replication with "
            "fresh seeds, a separate machine and code review before any further claim."
        )
    elif replicated:
        summary = (
            "Replicated statistical deviation(s) that are NOT actionable (" + ", ".join(replicated) + "). "
            "Treat as a lead for investigating artifacts, not as a search advantage."
        )
    else:
        summary = "All primary results are consistent with the cryptographic null hypothesis at the planned sensitivity."
    return {
        "summary": summary,
        "classifications": classes,
        "unreplicated_discovery_signals": unreplicated,
    }


LIMITATIONS = [
    "Generators with different widths, alphabets or encodings draw from different sample spaces; "
    "each is compared with the theoretical p0, not with each other.",
    "Candidates are deduplicated within a generator (both phases), not across generators. Different "
    "generators may share inputs (for example the all-zero candidate).",
    "Successes at the primary target and the leading-zero-bit histogram describe the same digests; the "
    "secondary tests are not independent of the primary test.",
    "Measurements across distinct SHA-256 inputs are modeled as independent Bernoulli trials. That is the "
    "null model under test, not a proven mathematical fact.",
    "Throughput reflects this Python implementation on this machine and is not representative of "
    "optimized or hardware mining.",
    "A p-value below alpha is never, by itself, evidence of cryptographic weakness.",
]


# --------------------------------------------------------------------------- report


def _fmt_p(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3e}" if value < 1e-3 else f"{value:.4f}"


def _fmt_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6e}"


def render_report(analysis: dict) -> str:
    dp = analysis["decision_parameters"]
    target = analysis["target"] or {}
    lines = [
        f"# HASHLAB report: run {analysis['run_id']}",
        "",
        f"- Run status: **{analysis['run_status']}**",
        f"- Engine: `{(analysis['engine'] or {}).get('name')}`",
        f"- Target: `{target.get('target_hex')}` (leading zero bits: {target.get('equivalent_leading_zero_bits')})",
        f"- alpha = {dp['alpha']}, confidence = {dp['confidence_level']}, correction = {dp['correction']}, "
        f"min actionable relative effect = {dp['min_actionable_relative_effect']}",
        f"- Analyzed at {analysis['analyzed_at_utc']} with hashlab {analysis['hashlab_version']}",
        "",
        "## Verdict",
        "",
        analysis["verdict"]["summary"],
        "",
        "## Theoretical expectation (null hypothesis)",
        "",
        f"p0 = target / 2^256 = {target.get('success_probability_exact')} "
        f"= {target.get('success_probability_float')}",
        "",
        "## Empirical measurements: primary family (discovery phase)",
        "",
        "| generator | domain | unique | successes | expected | rate | rate ratio [CI] | p | p adj | class |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for gid, g in analysis["generators"].items():
        phase = g["phases"].get("discovery")
        if phase is None:
            continue
        emp, theo = phase["empirical"], phase["theoretical"]
        primary = g.get("primary", {})
        ratio_ci = emp.get("rate_ratio_ci")
        ratio = (
            f"{emp['rate_ratio']:.4f} [{ratio_ci[0]:.4f}, {ratio_ci[1]:.4f}]" if ratio_ci else "n/a"
        )
        domain = g["domain"]
        lines.append(
            f"| {gid} | {domain['kind']} w={domain['width_bytes']} | {emp['unique']:,} | {emp['successes']:,} | "
            f"{theo['expected_successes']:.1f} | {_fmt_rate(emp['success_rate'])} | {ratio} | "
            f"{_fmt_p(primary.get('p_value'))} | {_fmt_p(primary.get('p_value_adjusted'))} | "
            f"{g.get('classification')} |"
        )

    lines += [
        "",
        "## Validation phase (independent, disjoint candidates)",
        "",
        "| generator | unique | successes | expected | rate ratio [CI] | two-sided p (unadjusted, descriptive) | replication p adj |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for gid, g in analysis["generators"].items():
        phase = g["phases"].get("validation")
        if phase is None:
            continue
        emp, theo = phase["empirical"], phase["theoretical"]
        ratio_ci = emp.get("rate_ratio_ci")
        ratio = f"{emp['rate_ratio']:.4f} [{ratio_ci[0]:.4f}, {ratio_ci[1]:.4f}]" if ratio_ci else "n/a"
        rep = g.get("replication", {})
        lines.append(
            f"| {gid} | {emp['unique']:,} | {emp['successes']:,} | {theo['expected_successes']:.1f} | {ratio} | "
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

    lines += ["", "## Controls", ""]
    nc = analysis["null_control"]
    lines.append(
        f"- Null control: {nc['generator']}: {'PASSED' if nc['passed'] else 'FAILED'}" if nc else "- Null control: none designated"
    )
    pc = analysis["positive_control"]
    if pc and "p_value_one_sided" in pc:
        lines.append(
            f"- Positive control (planted lift {pc['relative_lift_requested']}): ratio {pc['rate_ratio']:.4f} "
            f"[{pc['rate_ratio_ci'][0]:.4f}, {pc['rate_ratio_ci'][1]:.4f}], one-sided p = {_fmt_p(pc['p_value_one_sided'])}, "
            f"{'DETECTED' if pc['detected'] else 'NOT DETECTED'} (threshold {pc['threshold']:.3g})"
        )
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
