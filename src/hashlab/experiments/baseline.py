"""Experiment 001: candidate structure vs hash success.

``build_plan`` is pure: it does no hashing and writes nothing. ``run_experiment``
executes the plan in bounded batches and streams per-batch counters to disk.
It keeps only fixed-size counters per generator and phase, plus (for
generators that aren't unique by construction) the exact set of seen
candidates needed to remove duplicates.

Timing is split into three parts per batch:
    generation_ns  producing candidates from the generator
    dedup_ns       duplicate removal (zero for unique-by-construction generators)
    hashing_ns     hashing, the integer target comparison and histogram updates
End-to-end wall time per phase is recorded separately.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, TextIO

from hashlab import __version__
from hashlab.candidates import CandidateGenerator, build_generator, derive_seed, expected_duplicates
from hashlab.candidates.random import RandomBytesGenerator
from hashlab.evidence.manifest import collect_environment, utc_now_iso
from hashlab.evidence.storage import RunDirectory, new_run_id
from hashlab.experiments.analysis import CLASSIFICATION_LEGEND
from hashlab.experiments.config import PHASES, target_from_resolved
from hashlab.experiments.controls import BiasedControlEngine
from hashlab.experiments.economics import (
    EVIDENCE_LEVEL,
    STATUS_COMPARABLE,
    STATUS_NOT_COMPARABLE,
    comparability_table,
    reference_generator,
)
from hashlab.hashing import get_engine
from hashlab.statistics.distribution import DigestAccumulator
from hashlab.statistics.inference import minimum_detectable_effect, minimum_detectable_effect_unpooled, normal_power

POSITIVE_CONTROL_ID = "positive-control"
#: Rough per-entry memory of a Python set holding bytes objects (object header + slot), for planning only.
SET_ENTRY_OVERHEAD_BYTES = 33 + 40

Progress = Callable[[str], None]


def _stderr(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- planning


def needs_dedup_set(generator: CandidateGenerator, dedup_mode: str) -> bool:
    return dedup_mode == "always" or not generator.unique_by_construction


def build_plan(resolved: dict) -> dict:
    """Return the pre-registered plan for a resolved config. Performs no hashing."""
    target = target_from_resolved(resolved)
    p0 = float(target.probability)
    stats = resolved["statistics"]
    execution = resolved["execution"]
    generators = [build_generator(spec) for spec in resolved["generators"]]
    tests = len(generators)
    errors: list[str] = []
    warnings: list[str] = []
    entries = []
    total_hashes = 0

    for gen in generators:
        requested = {phase: resolved["phases"][phase]["candidates_per_generator"] for phase in PHASES}
        total_requested = sum(requested.values())
        available = gen.available(0)
        dedup_set = needs_dedup_set(gen, execution["dedup"])
        if total_requested > available:
            errors.append(
                f"{gen.generator_id}: requests {total_requested} candidates but its domain has only {available}"
            )
        if dedup_set and total_requested > execution["max_tracked_candidates"]:
            errors.append(
                f"{gen.generator_id}: exact duplicate tracking for {total_requested} candidates exceeds "
                f"execution.max_tracked_candidates ({execution['max_tracked_candidates']})"
            )
        exp_dups = expected_duplicates(total_requested, gen.domain().cardinality) if gen.uses_seed else 0.0
        if exp_dups >= 1.0:
            warnings.append(
                f"{gen.generator_id}: about {exp_dups:.1f} duplicate draws expected; they are removed and counted"
            )
        power = {phase: _power_dict(n, p0, stats, tests) for phase, n in requested.items()}
        total_hashes += total_requested
        entries.append(
            {
                **gen.describe(),
                "requested": requested,
                "dedup_method": "exact set of seen candidates" if dedup_set else "unique by construction",
                "dedup_memory_estimate_bytes": (
                    total_requested * (gen.width + SET_ENTRY_OVERHEAD_BYTES) if dedup_set else 0
                ),
                "expected_duplicate_draws": exp_dups,
                "power": power,
            }
        )

    widths = {gen.domain().width_bytes for gen in generators}
    kinds = {gen.domain().kind for gen in generators}
    if len(widths) > 1 or len(kinds) > 1:
        warnings.append(
            "generators span different domains (widths/kinds); comparisons between them compare "
            "different sample spaces. Primary tests compare each generator only to the theoretical p0."
        )

    positive = resolved["controls"]["positive_control"]
    if positive["enabled"]:
        total_hashes += positive["candidates"]

    null_control = resolved["controls"]["null_control_generator"]
    if null_control is None:
        warnings.append("no null-control generator is designated")

    reference = reference_generator(resolved)
    comparability = comparability_table(resolved)
    if reference is None:
        warnings.append(
            "no economic reference is predeclared (economics.reference_generator): the exploratory economic screen "
            "is disabled, so a replicated positive effect is classified at most replicated-anomaly-non-actionable"
        )
    not_comparable = sorted(gid for gid, row in comparability.items() if row["status"] == STATUS_NOT_COMPARABLE)
    if not_comparable:
        warnings.append(
            f"domains differ from the economic reference {reference} for: {', '.join(not_comparable)}; "
            "their throughput is reported descriptively, without a relative-efficiency comparison"
        )
    if any(row["status"] == STATUS_COMPARABLE for row in comparability.values()):
        warnings.append(
            "an identical domain does not mean independent samples: generators are not deduplicated against "
            "each other, and deterministic generators can share most of their candidates (seq-be-w8 and "
            "struct-gray-w8 at baseline settings share 951,424 of 1,000,000). Agreement between such generators "
            "is not independent corroboration (methodology section 5b)"
        )

    hypotheses = [
        {
            "id": f"H1.{gen.generator_id}",
            "family": "primary",
            "null": f"P(success | {gen.generator_id}) = p0 = target/2**256",
            "alternative": "two-sided: P(success) != p0",
            "test": "exact binomial test on unique candidates (discovery phase)",
            "correction": stats["correction"],
        }
        for gen in generators
    ]
    hypotheses.append(
        {
            "id": "H2.*",
            "family": "secondary (exploratory)",
            "null": "leading-zero-bit counts are geometric(1/2); first/last digest bytes are uniform",
            "test": "Pearson chi-square goodness of fit per generator and phase",
            "correction": f"{stats['correction']} within the secondary family",
        }
    )

    plan = {
        "hashlab_version": __version__,
        "experiment": resolved["experiment"],
        "engine": get_engine(resolved["engine"]).describe(),
        "target": resolved["target"],
        "theoretical_success_probability": p0,
        "primary_family_size": tests,
        "hypotheses": hypotheses,
        "decision_rules": {
            "alpha": stats["alpha"],
            "confidence_level": stats["confidence_level"],
            "correction": stats["correction"],
            "discovery_flag": "adjusted two-sided p < alpha in the discovery phase",
            "replication": "same-direction one-sided exact test p < alpha in the validation phase, "
            "corrected across flagged generators",
            "actionable": (
                "never declared by this analysis: economic evidence is exploratory and no confirmatory economic "
                "procedure is predeclared"
            ),
            "exploratory_economic_screen": (
                "replicated AND more successes than p0 AND the generator's domain is identical to the predeclared "
                "economic reference AND the Bonferroni-simultaneous (across the primary family) validation lower "
                "bound of the success-rate ratio, times the generator's end-to-end throughput relative to the "
                f"predeclared reference, is at least 1 + {stats['min_actionable_relative_effect']}. A marginal bound "
                "alone never passes. Passing gives the label candidate-anomaly-requires-independent-replication, "
                "which is exploratory and never a confirmatory mining advantage"
            ),
            "classification_legend": CLASSIFICATION_LEGEND,
            "economic_reference": reference,
            "intervals": (
                f"marginal: {stats['confidence_level']} Clopper-Pearson per generator and phase (descriptive); "
                f"simultaneous: Bonferroni across the {tests} primary generators"
            ),
            "integrity": (
                "missing generator or control evidence and invalid or inconsistent counts are blocking "
                "integrity failures"
            ),
            "null_control": null_control,
            "null_control_rule": (
                "a statistically flagged null control is a non-blocking diagnostic that is reported in the verdict; "
                "missing null-control evidence is a blocking integrity failure"
            ),
            "positive_control": positive,
        },
        "economics": {
            "reference_generator": reference,
            "selection": "predeclared in the configuration before execution; never chosen from observed throughput",
            "evidence_level": EVIDENCE_LEVEL,
            "comparability_rule": "identical domain: kind, width_bytes, alphabet, alphabet_size and cardinality",
            "comparability": comparability,
        },
        "sensitivity": _sensitivity(resolved, p0, tests),
        "generators": entries,
        "total_hashes_planned": total_hashes,
        "batch_size": execution["batch_size"],
        "errors": errors,
        "warnings": warnings,
    }
    plan["plan_fingerprint"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return plan


MDE_INTERPRETATION = (
    "planning quantity, not an exclusion bound: an effect of this size would be flagged in discovery with "
    "probability about equal to the power target (not guaranteed); a non-significant result does not show "
    "that effects of this size or smaller are absent"
)


def _unpooled_mde(n: int, p0: float, stats: dict, tests: int, direction: str) -> float | None:
    try:
        return minimum_detectable_effect_unpooled(n, p0, stats["alpha"], stats["power"], tests, direction)
    except ValueError:  # no detectable effect inside the valid probability range (extreme targets)
        return None


def _power_dict(n: int, p0: float, stats: dict, tests: int) -> dict:
    pooled = minimum_detectable_effect(n, p0, stats["alpha"], stats["power"], tests)
    return {
        "expected_successes": pooled.expected_successes,
        "min_detectable_relative_effect": pooled.min_detectable_relative_effect,
        "min_detectable_relative_increase_unpooled": _unpooled_mde(n, p0, stats, tests, "increase"),
        "min_detectable_relative_decrease_unpooled": _unpooled_mde(n, p0, stats, tests, "decrease"),
        "alpha_per_test": pooled.alpha_per_test,
        "power_target": stats["power"],
        "method": (
            "normal approximation, two-sided, Bonferroni alpha/tests (conservative for Holm), discovery test only; "
            "'min_detectable_relative_effect' uses the null variance in both terms, the 'unpooled' values use the "
            "alternative variance (planning only)"
        ),
        "interpretation": MDE_INTERPRETATION,
    }


def _sensitivity(resolved: dict, p0: float, tests: int) -> dict:
    """Planning sensitivity of the whole decision chain (normal approximations; no data involved)."""
    stats = resolved["statistics"]
    n_discovery = resolved["phases"]["discovery"]["candidates_per_generator"]
    n_validation = resolved["phases"]["validation"]["candidates_per_generator"]
    increase = _unpooled_mde(n_discovery, p0, stats, tests, "increase")
    replication: dict = {"one_generator_flagged": None, "all_generators_flagged": None}
    if increase is not None and p0 * (1.0 + increase) <= 1.0:
        # Replication is one-sided, Holm-corrected across the flagged generators: alpha (1 flagged) .. alpha/tests.
        replication = {
            "one_generator_flagged": normal_power(n_validation, p0, increase, stats["alpha"], "greater"),
            "all_generators_flagged": normal_power(n_validation, p0, increase, stats["alpha"] / tests, "greater"),
        }
    return {
        "purpose": "planning only; the analysis uses exact tests and never reads these numbers",
        "assumptions": {
            "n_discovery": n_discovery,
            "n_validation": n_validation,
            "n_basis": "planned attempted candidates per phase, assuming all are unique (removed duplicates lower n)",
            "p0": p0,
            "alpha_family": stats["alpha"],
            "tests": tests,
            "alpha_per_test": stats["alpha"] / tests,
            "discovery_test": "two-sided; Bonferroni alpha/tests, which equals Holm's first step (conservative)",
            "power_target": stats["power"],
            "approximation": "normal approximation to Binomial(n, p0); one rejection tail",
        },
        "discovery_mde_pooled": minimum_detectable_effect(
            n_discovery, p0, stats["alpha"], stats["power"], tests
        ).min_detectable_relative_effect,
        "discovery_mde_increase_unpooled": increase,
        "discovery_mde_decrease_unpooled": _unpooled_mde(n_discovery, p0, stats, tests, "decrease"),
        "replication_power_at_discovery_increase_mde": replication,
        "interpretation": [
            MDE_INTERPRETATION,
            "the power target applies to the discovery test alone; flagging AND replicating an effect at the MDE "
            "has probability of about power_target x replication power",
            "excluding effects of a given size needs a predeclared confidence-bound or equivalence analysis, "
            "which this experiment does not include",
            "the exact doubled-tail binomial test is discrete and slightly conservative; "
            "statistics.inference.exact_binomial_power gives its exact power",
        ],
    }


def seed_table(resolved: dict) -> dict:
    master = resolved["seeds"]["master"]
    table: dict = {
        "master": master,
        "derivation": "first 8 bytes (big-endian) of SHA-256('hashlab-seed-v1|<master>|<generator_id>|<phase>')",
        "generators": {},
    }
    for spec in resolved["generators"]:
        gen = build_generator(spec)
        if gen.uses_seed:
            table["generators"][gen.generator_id] = {
                phase: derive_seed(master, gen.generator_id, phase) for phase in PHASES
            }
        else:
            table["generators"][gen.generator_id] = "seedless (validation continues the enumeration after discovery)"
    table["positive_control"] = derive_seed(master, POSITIVE_CONTROL_ID, "control")
    return table


# --------------------------------------------------------------------------- execution


@dataclass
class PhaseCounters:
    attempted: int = 0
    unique: int = 0
    duplicates_within_phase: int = 0
    duplicates_cross_phase: int = 0
    successes: int = 0
    batches: int = 0
    generation_ns: int = 0
    dedup_ns: int = 0
    hashing_ns: int = 0
    wall_ns: int = 0
    exhausted: bool = False
    seed: int | None = None
    start_index: int = 0
    digest: DigestAccumulator = field(default_factory=DigestAccumulator)

    def to_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "unique": self.unique,
            "duplicates_within_phase": self.duplicates_within_phase,
            "duplicates_cross_phase": self.duplicates_cross_phase,
            "successes": self.successes,
            "batches": self.batches,
            "generation_seconds": self.generation_ns / 1e9,
            "dedup_seconds": self.dedup_ns / 1e9,
            "hashing_seconds": self.hashing_ns / 1e9,
            "wall_seconds": self.wall_ns / 1e9,
            "exhausted": self.exhausted,
            "seed": self.seed,
            "start_index": self.start_index,
            "digest_distribution": self.digest.to_dict(),
        }


class SuccessRecorder:
    def __init__(self, stream: TextIO | None, limit: int) -> None:
        self.stream = stream
        self.limit = limit
        self.recorded = 0
        self.dropped = 0

    def record(self, generator_id: str, phase: str, candidate: bytes, digest: bytes) -> None:
        if self.stream is None:
            return
        if self.recorded >= self.limit:
            self.dropped += 1
            return
        self.stream.write(
            json.dumps(
                {"generator": generator_id, "phase": phase, "candidate_hex": candidate.hex(), "digest_hex": digest.hex()}
            )
            + "\n"
        )
        self.recorded += 1


def run_phase(
    generator: CandidateGenerator,
    engine,
    target_value: int,
    phase: str,
    requested: int,
    seed: int | None,
    start_index: int,
    batch_size: int,
    seen_previous: set[bytes] | None,
    seen_current: set[bytes] | None,
    batch_stream: TextIO | None,
    recorder: SuccessRecorder,
    progress: Progress | None = None,
    progress_every: int = 50,
) -> PhaseCounters:
    """Hash `requested` attempted candidates from one generator phase in bounded batches."""
    counters = PhaseCounters(seed=seed, start_index=start_index)
    stream = generator.stream(seed, start_index)
    digest_fn = engine.digest
    lzb = counters.digest.leading_zero_bits
    first = counters.digest.first_byte
    last = counters.digest.last_byte
    remaining = requested
    phase_start = time.perf_counter_ns()

    while remaining > 0:
        t0 = time.perf_counter_ns()
        batch = list(itertools.islice(stream, min(batch_size, remaining)))
        t1 = time.perf_counter_ns()
        if not batch:
            counters.exhausted = True
            break

        dup_within = dup_cross = 0
        if seen_current is None:
            unique = batch
        else:
            unique = []
            for candidate in batch:
                if seen_previous is not None and candidate in seen_previous:
                    dup_cross += 1
                elif candidate in seen_current:
                    dup_within += 1
                else:
                    seen_current.add(candidate)
                    unique.append(candidate)
        t2 = time.perf_counter_ns()

        successes = 0
        for candidate in unique:
            digest = digest_fn(candidate)
            value = int.from_bytes(digest, "big")
            lzb[256 - value.bit_length()] += 1
            first[digest[0]] += 1
            last[digest[31]] += 1
            if value < target_value:
                successes += 1
                recorder.record(generator.generator_id, phase, candidate, digest)
        t3 = time.perf_counter_ns()

        counters.attempted += len(batch)
        counters.unique += len(unique)
        counters.duplicates_within_phase += dup_within
        counters.duplicates_cross_phase += dup_cross
        counters.successes += successes
        counters.batches += 1
        counters.generation_ns += t1 - t0
        counters.dedup_ns += t2 - t1
        counters.hashing_ns += t3 - t2
        remaining -= len(batch)

        if batch_stream is not None:
            batch_stream.write(
                json.dumps(
                    {
                        "generator": generator.generator_id,
                        "phase": phase,
                        "batch": counters.batches,
                        "attempted": len(batch),
                        "unique": len(unique),
                        "duplicates_within_phase": dup_within,
                        "duplicates_cross_phase": dup_cross,
                        "successes": successes,
                        "generation_ns": t1 - t0,
                        "dedup_ns": t2 - t1,
                        "hashing_ns": t3 - t2,
                    }
                )
                + "\n"
            )
        if progress is not None and counters.batches % progress_every == 0:
            progress(f"  {generator.generator_id}/{phase}: {counters.attempted:,}/{requested:,} attempted")

    counters.wall_ns = time.perf_counter_ns() - phase_start
    return counters


def run_experiment(
    resolved: dict,
    config_source: bytes,
    results_root: Path,
    progress: Progress | None = _stderr,
) -> tuple[str, Path]:
    """Execute Experiment 001 and seal an evidence directory. Returns (run_id, path)."""
    from hashlab.experiments.analysis import analyze_results, render_report

    plan = build_plan(resolved)
    if plan["errors"]:
        raise ValueError("plan has errors:\n" + "\n".join(plan["errors"]))

    run_id = new_run_id(resolved["experiment"]["id"])
    run_dir = RunDirectory.create(results_root, run_id)
    run_dir.write_bytes("config.source.yaml", config_source)
    run_dir.write_json("config.resolved.json", resolved)
    run_dir.write_json("plan.json", plan)
    run_dir.write_json("environment.json", collect_environment())
    seeds = seed_table(resolved)
    run_dir.write_json("seeds.json", seeds)

    execution = resolved["execution"]
    target = target_from_resolved(resolved)
    engine = get_engine(resolved["engine"])
    batch_stream = run_dir.open_stream("batches.jsonl")
    success_stream = run_dir.open_stream("successes.jsonl") if execution["record_successes"] else None
    recorder = SuccessRecorder(success_stream, execution["max_recorded_successes"])

    results: dict = {
        "run_id": run_id,
        "status": "running",
        "started_at_utc": utc_now_iso(),
        "plan_fingerprint": plan["plan_fingerprint"],
        "engine": engine.describe(),
        "target": resolved["target"],
        "generators": {},
        "positive_control": None,
    }
    say = progress or (lambda _msg: None)
    say(f"[hashlab] run {run_id}: {plan['total_hashes_planned']:,} hashes planned")
    run_start = time.perf_counter_ns()
    status = "complete"
    try:
        for spec in resolved["generators"]:
            gen = build_generator(spec)
            use_set = needs_dedup_set(gen, execution["dedup"])
            seen_previous: set[bytes] | None = set() if use_set else None
            phases_out: dict = {}
            consumed = 0
            for phase in PHASES:
                seed = seeds["generators"][gen.generator_id][phase] if gen.uses_seed else None
                seen_current: set[bytes] | None = set() if use_set else None
                counters = run_phase(
                    gen,
                    engine,
                    target.value,
                    phase,
                    resolved["phases"][phase]["candidates_per_generator"],
                    seed,
                    0 if gen.uses_seed else consumed,
                    execution["batch_size"],
                    seen_previous,
                    seen_current,
                    batch_stream,
                    recorder,
                    progress,
                    execution["progress_every_batches"],
                )
                consumed += counters.attempted
                if use_set and phase != PHASES[-1]:
                    assert seen_previous is not None and seen_current is not None
                    seen_previous |= seen_current
                seen_current = None
                phases_out[phase] = counters.to_dict()
                say(
                    f"[hashlab] {gen.generator_id}/{phase}: {counters.unique:,} unique, "
                    f"{counters.successes:,} successes, {counters.wall_ns / 1e9:.1f}s"
                )
            results["generators"][gen.generator_id] = {
                "description": gen.describe(),
                "dedup_method": "exact set" if use_set else "unique by construction",
                "phases": phases_out,
            }
            del seen_previous

        positive = resolved["controls"]["positive_control"]
        if positive["enabled"]:
            control_gen = RandomBytesGenerator(POSITIVE_CONTROL_ID, positive["width"])
            control_engine = BiasedControlEngine(engine, target, positive["relative_lift"])
            seen: set[bytes] = set()
            counters = run_phase(
                control_gen,
                control_engine,
                target.value,
                "control",
                positive["candidates"],
                seeds["positive_control"],
                0,
                execution["batch_size"],
                None,
                seen,
                batch_stream,
                SuccessRecorder(None, 0),
            )
            results["positive_control"] = {
                "description": control_gen.describe(),
                "engine": control_engine.describe(),
                "counters": counters.to_dict(),
            }
            say(f"[hashlab] positive control: {counters.unique:,} unique, {counters.successes:,} successes")
    except KeyboardInterrupt:
        status = "aborted"
        say("[hashlab] interrupted: sealing partial evidence (status=aborted)")
    finally:
        batch_stream.close()
        if success_stream is not None:
            success_stream.close()

    results["status"] = status
    results["finished_at_utc"] = utc_now_iso()
    results["wall_seconds_total"] = (time.perf_counter_ns() - run_start) / 1e9
    results["successes_recorded"] = recorder.recorded
    results["successes_not_recorded_cap"] = recorder.dropped
    run_dir.write_json("results.json", results)

    analysis = analyze_results(results, resolved)
    run_dir.write_json("analysis.json", analysis)
    run_dir.write_text("report.md", render_report(analysis))
    run_dir.seal({"run_id": run_id, "status": status, "plan_fingerprint": plan["plan_fingerprint"]})
    say(f"[hashlab] sealed evidence: {run_dir.path}")
    if status == "aborted":
        raise KeyboardInterrupt
    return run_id, run_dir.path


def describe_plan(plan: dict) -> str:
    """Human-readable plan summary for the CLI."""
    lines = [
        f"Experiment {plan['experiment']['id']}: {plan['experiment']['name']}",
        f"Engine: {plan['engine']['name']}   Target: {plan['target']['target_hex']}",
        f"Theoretical success probability p0 = {plan['target']['success_probability_exact']}"
        f" ({plan['theoretical_success_probability']:.6g})",
        f"Primary family size: {plan['primary_family_size']}   Total hashes planned: {plan['total_hashes_planned']:,}",
        f"Economic reference (predeclared, exploratory screen only): {plan['economics']['reference_generator']}",
        "",
        "Generators:",
    ]
    comparability = plan["economics"]["comparability"]
    for g in plan["generators"]:
        disc = g["power"]["discovery"]
        lines.append(
            f"  - {g['id']} [{g['type']}] {g['domain']['kind']} width={g['domain']['width_bytes']} "
            f"domain={_short_int(g['domain']['cardinality'])}; requested {g['requested']}; {g['dedup_method']}; "
            f"E[successes/discovery]={disc['expected_successes']:.1f}; "
            f"planning MDE ({disc['power_target']:.0%}-power target, discovery only)"
            f"~{disc['min_detectable_relative_effect']:.1%}; "
            f"economics: {comparability[g['id']]['status']}"
        )
    sens = plan["sensitivity"]
    increase, decrease = sens["discovery_mde_increase_unpooled"], sens["discovery_mde_decrease_unpooled"]
    lines += [
        "",
        f"Sensitivity (planning only, normal approximation, alpha/test = {sens['assumptions']['alpha_per_test']:.3g}, "
        f"power target {sens['assumptions']['power_target']}): MDE ~{sens['discovery_mde_pooled']:.2%} pooled"
        + (f", ~{increase:.2%} for an increase" if increase is not None else "")
        + (f", ~{decrease:.2%} for a decrease" if decrease is not None else "")
        + ".",
        "  The MDE is not an exclusion bound: a non-significant result does not rule out effects of this size.",
    ]
    for warning in plan["warnings"]:
        lines.append(f"WARNING: {warning}")
    for error in plan["errors"]:
        lines.append(f"ERROR: {error}")
    lines.append(f"Plan fingerprint: {plan['plan_fingerprint']}")
    return "\n".join(lines)


def _short_int(text: str) -> str:
    value = int(text)
    if value < 10**12:
        return f"{value:,}"
    if value & (value - 1) == 0:
        return f"2^{value.bit_length() - 1}"
    return f"~{value:.3e}"


__all__ = ["build_plan", "describe_plan", "run_experiment", "run_phase", "seed_table"]
