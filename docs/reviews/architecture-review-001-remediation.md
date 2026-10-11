# Architecture Review 001: remediation record

- **Assignments:** Engineering Assignment 002 (sections 1-9), scientific methodology hardening before
  Experiment 001, and Engineering Assignment 003 (section 10), final pre-experiment hardening
- **Baseline commit:** `50e6a9b` (working tree clean before the changes)
- **Status:** the Director reported 235 passing tests after Assignment 002. The Assignment 003 changes have
  not been tested yet.
- **Experiment 001:** not executed. No results exist (`results/` holds only `.gitkeep`). Nothing here is an
  experimental result, and no hypothesis has been validated.

## 1. Provenance

### Original configuration (verified independently, not copied from the report)

Recomputed from the files at `50e6a9b` before any change, with the dry-run plan (no hashing):

| Fingerprint | Value |
|---|---|
| SHA-256 of `configs/baseline.yaml` bytes | `2ec327e6277fd909a09bc7d938d01ed242f2bfffcaedd333d0eb4919b2709a1e` |
| SHA-256 of the resolved config (canonical JSON) | `f46e729e27f387542ff8c806bf951bf6ac017c437f7fa49d7d166d2fd97d90ee` |
| Plan fingerprint (`plan_fingerprint`) | `c8dd07b28eb478da4e22e928e822760c45f35c610636440d138f565b6f36ca46` |

The recomputed plan fingerprint matches the value in the review. "Canonical JSON" means
`json.dumps(resolved, sort_keys=True, ensure_ascii=True)`, the same serialization the plan fingerprint uses.

### Amended configuration

| Fingerprint | After Assignment 002 (0.1.0) | After Assignment 003 (0.2.0, current) |
|---|---|---|
| SHA-256 of `configs/baseline.yaml` bytes | `f2c0de21f3eba4b6a5fff41c8729b10d5c389e09334bd218f133d55a0140f225` | unchanged |
| SHA-256 of the resolved config | `3f17e1c04dbf6b645b70a24d363b2f3bc69357363035cf21f83c70320dcef47c` | unchanged |
| Plan fingerprint | `0c5c1613e3330be888d3d7b972f6d6da9ea6e0ed65ac86c2384db1ff0d4df9d2` | `d0808d4537db0c4eae8385740ae1663ff04c7ab6c4dc236fed22d8a4dffa2dc9` |

The plan fingerprint hashes the whole plan, including text the code generates. After Assignment 002 it
changed because the config gained an `economics` section and the plan carried the amended decision rules,
the comparability table and the sensitivity block. After Assignment 003 it changed again only because of
the version string (0.2.0), the classification legend, a reworded rule and a new overlap warning. The
config itself did not change.

### Fields changed in `configs/baseline.yaml`

| Field | Change | Reason |
|---|---|---|
| `economics.reference_generator` | **added**: `seq-be-w8` | Remediation B: predeclare the economic reference before execution, instead of picking the fastest observed generator |
| `statistics.confidence_level` comment | reworded (value `0.99` unchanged) | Remediation C: says the intervals are marginal |
| `statistics.power` comment | reworded (value `0.80` unchanged) | Remediation D: the MDE is not an exclusion bound |
| `statistics.min_actionable_relative_effect` comment | reworded (value `0.01` unchanged) | Remediation C: the threshold drives an exploratory screen only |
| comment block above `economics` | added | records Amendment 1 |

**Primary hypotheses changed: no.** **Sample allocations changed: no.** Engine, target, seed, phases,
generators, alpha, confidence level, correction, power and both controls are unchanged.
`tests/test_config.py::test_baseline_primary_design_is_unchanged_by_remediation` pins these values.

## 2. Remediation A: null-control interpretation

**Finding.** `analysis._verdict` (at `50e6a9b`) returned `HARNESS ALARM` whenever the null-control
generator was flagged in discovery (`null_control.passed = not flagged`). A correctly working null
control is flagged with probability up to alpha, so statistical chance was being treated as a harness
failure. Real integrity problems (missing evidence, inconsistent counts) were not checked at all.

**Change** (`src/hashlab/experiments/analysis.py`):
- New `check_integrity(results, resolved)` returns blocking problems: missing generator, phase or
  null-control evidence (complete runs only), an enabled positive control with no evidence or zero
  candidates, invalid or negative counts, missing, negative or non-finite timings,
  `successes > unique`, `unique + duplicates != attempted`, more candidates than planned or fewer
  without exhaustion, histogram totals that differ from `unique`, success counts that disagree with
  the leading-zero histogram (power-of-two targets), and generators that are not in the configuration.
  Any problem gives the verdict `HARNESS INTEGRITY FAILURE` (`verdict.status = integrity-failure`,
  `blocking = true`). Counters too broken to analyze are left out of the statistics instead of crashing.
- The null control is reported with `status` (`no-signal`, `statistical-anomaly`,
  `statistical-anomaly-replicated`, `missing-evidence`), `statistically_flagged`, `p_value`,
  `p_value_adjusted`, `replicated` and `blocking`. Only `missing-evidence` is blocking, and it is also
  an integrity problem.
- A flagged null control adds a `null-control-statistically-significant` diagnostic (`warning`, or
  `serious` when it also replicated) and a warning sentence to the verdict. Classifications and every
  p-value are unchanged.
- Manifest verification (`hashlab analyze`, exit code 3) is unchanged and still runs first.

**Effect on confidence** (methodology section 4a): every positive label of a run with a flagged null
control is reported with reduced confidence and should not go to independent replication until the
diagnostic is explained. A replicated null-control deviation (probability of order alpha² under a
correct harness) is a strong sign of a pipeline artifact.

**Tests:** `tests/test_analysis.py` (diagnostic, unchanged statistics, replicated diagnostic, missing
null-control evidence, five invalid-count cases, histogram mismatch, missing positive control, missing
phase), and `tests/test_cli.py` now requires a genuine tiny run to pass every integrity check.

## 3. Remediation B: economic baseline selection

**Finding.** `analyze_results` computed `fastest = max(end_to_end_unique_per_second)` over all
generators and scaled every replicated effect by `throughput / fastest`. The reference was therefore
chosen after seeing the data, and could come from a different domain (for example a 16-character ASCII
generator compared with an 8-byte one).

**Change:**
- Config: `economics.reference_generator` (strictly validated; must name a configured generator;
  default `None`). Baseline: `seq-be-w8`.
- New `src/hashlab/experiments/economics.py`: `comparability_table` compares configured domains only.
  Comparable means identical `kind`, `width_bytes`, `alphabet`, `alphabet_size` and `cardinality`.
  The plan records the reference, the selection rule and the table, so they are fixed before execution
  and covered by the plan fingerprint.
- Analysis: the throughput ratio is `end-to-end / reference end-to-end` (validation phase), only for
  the reference and comparable generators. Non-comparable generators, a missing reference or a reference
  without throughput give descriptive metrics only, `throughput_ratio_vs_reference = null`, and the
  screen cannot be passed (`screen_status` says why).
- New per-phase metrics: `candidate_overhead_seconds`, `candidate_overhead_fraction_of_wall`,
  `expected_valid_per_second`, `observed_valid_per_second`. The existing raw metrics
  (`generation_per_second`, `hashing_per_second`, `end_to_end_unique_per_second`, timings) are unchanged.
- The primary SHA-256 success-probability hypotheses are untouched.

**Baseline comparability:** reference `seq-be-w8`; comparable `uniform-be-w8`, `struct-gray-w8`,
`struct-stride-w8`, `struct-bitrev-w8`, `random-bytes-w8`; not comparable `seq-dec-w16`,
`uniform-dec-w16`, `pattern-chars-w16` (kind, width, alphabet) and `pattern-bytes-w8` (cardinality: a
16.8-million-element subset of the 8-byte space).

**Tests:** reference fixed by config, not the fastest (adding a 100× faster generator does not change
the comparison); reference chosen only through configuration; no reference; reference without
throughput; incompatible domain; reported metrics; config validation; baseline comparability table.

## 4. Remediation C: confidence intervals and actionability

**Finding.** `rate_ratio_ci` was a marginal 99% Clopper-Pearson interval with no label. Its lower bound
alone (times the throughput ratio) could produce `actionable: true` and the strongest classification,
with an "above the economic threshold" verdict, although no multiplicity adjustment or confirmatory
economic procedure was involved.

**Change (conservative, smallest defensible):**
- Every interval is labelled: `interval_type: marginal` (unchanged values), plus a new
  `empirical.simultaneous` block: Bonferroni-simultaneous Clopper-Pearson at
  `1 − (1 − confidence_level) / m`, with `m` = the number of configured generators (10 in the baseline,
  so 99.9% per interval). `decision_parameters` and the report header state both types.
- The economic screen uses the **simultaneous** lower bound. `marginal_bound_alone_would_pass` is
  reported for transparency but cannot promote a generator.
- `actionability.actionable` is always `false`; `evidence_level: exploratory` and `confirmatory_status`
  explain why. The classification string `candidate-anomaly-requires-independent-replication` is kept
  for compatibility; it now means "replicated and passed the exploratory screen". The verdict says
  "not a confirmed mining advantage" and "EXPLORATORY".
- Holm discovery tests, the separate replication family on disjoint validation data, and the
  replication requirement are unchanged. No new testing framework was introduced.

**Reasoning note for the Architect.** Selection in discovery does not bias validation-phase intervals,
because the phases share no candidates. The multiplicity that matters is across the generators that are
screened together. Bonferroni over all `m` generators covers every possible selected subset, so it is
valid but conservative. The economic ratio itself still has no uncertainty model, which is why the
screen remains exploratory even with simultaneous bounds.

**Tests:** interval labels and unchanged marginal values; a case where the marginal bound would pass
but the simultaneous bound does not (classified non-actionable); no `actionable: true` anywhere; Holm and
the replication family checked against an independent computation.

## 5. Remediation D: statistical sensitivity

**Derivation review.** The 9.3% figure comes from `minimum_detectable_effect` (unchanged):
`(z_{1−alpha'/2} + z_power) · sqrt(p0 (1 − p0) / n) / p0` with `n = 500,000`, `p0 = 1/256`,
`alpha' = 0.01 / 10 = 0.001` (two-sided Bonferroni, equal to Holm's first step), power 0.8:
`(3.290527 + 0.841621) × 0.0225832 = 0.093317`. Re-derived independently; **the arithmetic is correct**
for its assumptions. Assumptions that were implicit and are now documented:

1. normal approximation with the null variance in both terms (direction-symmetric);
2. one rejection tail;
3. `n` = planned attempted candidates, assuming all unique (seeded generators lose a negligible number);
4. power refers to the discovery test only.

**Refinements, computed independently** (standalone scripts using only `math`, not project code):

| Quantity | Value |
|---|---|
| Normal-approximation MDE, alternative variance, increase / decrease | 9.419% / 9.242% |
| Exact doubled-tail test, rejection region at alpha' = 0.001 | k ≤ 1809 or k ≥ 2101 (null tails 4.948e-4 and 4.760e-4) |
| Exact power at +9.332% / −9.332% | 0.7749 / 0.8213 |
| Exact 80%-power MDE, increase / decrease (bisection) | about 9.54% / 9.16% |
| Replication power at the increase MDE (one-sided, normal approximation), 1 flagged / all 10 flagged | 0.961 / 0.849 |

So "about 9.3%" stays as the documented planning figure, which is accurate for the stated
approximation, but it slightly overstates sensitivity to increases under the exact test, and the
probability of flagging *and* replicating an effect at that size is roughly 0.68 to 0.77, not 0.80.
No sample size was changed.

**Corrected wording** (README, methodology section 8, experiment spec, plan output): the MDE is a
planning quantity; it depends on `n`, `p0`, alpha, power and the multiplicity assumption; 80% power
does not guarantee detection; a non-significant result does not establish equivalence or rule out
effects of that size; excluding effects needs a predeclared confidence-bound or equivalence analysis.
The old sentence "A null result rules out effects of roughly that size or larger" was removed.

**Code:** `normal_power`, `minimum_detectable_effect_unpooled` and `exact_binomial_power` in
`statistics/inference.py`. The plan now reports, per phase, the pooled and directional MDEs with the
power target, method and interpretation, and a plan-level `sensitivity` block with all assumptions and
the replication power. `describe_plan` prints the MDE in each direction and the not-an-exclusion-bound
note. To reproduce the exact-test figure:
`python -c "from hashlab.statistics.inference import exact_binomial_power as e; print(e(500000, 1/256, (1/256)*1.0933170395514487, 0.001))"`.

## 6. Remediation E: statistical reference tests

New `tests/test_statistics_reference.py`. All expected values come from methods that share no code with
the implementation:

- binomial CDF, survival function and two-sided/one-sided p-values against exact `Fraction` sums
  evaluated at the exact binary value of the float `p`, for `n` from 1 to 60 and `p` from `2^-40` to
  `1 − 2^-40`;
- zero and all successes against closed forms (`(1 − p)^n`, `p^n`, `1 − p^n`, `1 − (1 − p)^n`);
- boundary counts and probabilities (`k < 0`, `k > n`, `p = 0`, `p = 1`, `n = 0`, invalid input);
- an extreme valid target (`p = 2^-64`, `n = 10^6`) against `log1p`/`expm1` closed forms and the
  leading Poisson term;
- Clopper-Pearson closed forms for `k ∈ {0, 1, n−1, n}`, `n` from 1 to 10^6, at 95% and 99%; a published
  R interval; the defining tail equations re-checked in exact arithmetic;
- Holm: eight hand-computed vectors (ties, capping, unsorted input, boundary p-values, empty input) and
  agreement with an independent step-down rejection procedure;
- planning: tabulated normal quantiles, the textbook MDE case, the baseline 9.3% figure, `1/sqrt(n)`
  scaling, the directional MDE's defining equation, `normal_power` size and consistency, exact power
  against an exact-arithmetic rejection region, and the baseline exact power (0.77488) from the
  standalone computation;
- decision-chain behavior with a false-positive null control is in `tests/test_analysis.py`.

**Tolerances and limits.** Relative `1e-9` for `n ≤ 10,000`; relative `1e-7` at `n ≈ 10^6`, because
differences of `lgamma` values near `1.3 × 10^7` keep only about `1e-9` absolute precision; absolute
floor `1e-300` for underflowing tails. All tests are deterministic.

## 7. Compatibility implications

`analysis.json` and `plan.json` gained fields; consumers that only read the old fields keep working,
with these exceptions:

| Change | Impact |
|---|---|
| `actionability.throughput_ratio_vs_fastest` **removed**, replaced by `throughput_ratio_vs_reference` | readers of the old key get a missing key |
| `actionability.actionable` is now always `false` | it used to be `true` for the strongest label |
| `actionability.throughput_adjusted_lift_lower_bound` may be `null` (no reference or not comparable) | it used to always be a number |
| verdict text: `HARNESS ALARM` no longer exists; `HARNESS INTEGRITY FAILURE` is new; the null-run and candidate texts changed | tools matching verdict strings should use the new `verdict.status` code |
| `null_control` is a dict with `status` and `blocking` even when the null control has no evidence (it used to be `None`) | `passed` keeps its old meaning (not flagged in discovery) |
| analysis now reads `resolved["economics"]` with a default | old resolved configs (no `economics`) analyze with no reference: no generator can pass the economic screen |
| config: new optional top-level key `economics` | old configs stay valid (reference `None`, plus a plan warning) |
| `phase_summary` has an optional `family_size` argument | the existing call signature still works |
| plan: new `economics`, `sensitivity` and decision-rule keys; changed `actionable` text; richer `power` entries | the plan fingerprint changes for any config |

No evidence directories exist, so no stored result is affected.

## 8. Remaining scientific limitations and open decisions

1. **No confirmatory economic procedure.** A confirmatory claim would need a predeclared model of
   throughput variability (for example repeated timing blocks), a predeclared threshold and fresh data.
2. **No exclusion or equivalence analysis.** If the Director or Architect wants to report that effects
   above some size are absent, an equivalence design (for example a TOST on the rate ratio with a
   predeclared margin, and a sample size to match) must be added before execution.
3. **The planning MDE stays a normal approximation.** It is documented next to the exact-test figures
   but not replaced. Whether the plan should report exact power is an Architect decision (it costs
   several betainc evaluations per generator).
4. **Bonferroni simultaneous intervals are conservative.** A tighter choice (for example over the
   replicated subset only) would need its own justification.
5. **Throughput** is one measurement per phase in pure Python, and phases run sequentially, so drift in
   machine load can bias ratios between generators.
6. **Version number.** Resolved in Assignment 003: now 0.2.0 (section 10).
7. **`docs/research-charter.md`** was not edited. Its principle 6 ("economic relevance") is consistent
   with the exploratory screen but does not mention the predeclared reference.
8. Earlier open questions in the README (evidence commitment, two-sample comparisons within a domain,
   doubled-tail vs minimum-likelihood p-values, secondary metrics, patterned sampling, sha256d) remain
   open.

## 9. What was and was not executed

- **Executed by the Engineer:** reading the code; `git status` / `git diff`; SHA-256 of the config bytes;
  the dry-run plan in-process (`build_plan`, no hashing, nothing written) to compute the original and
  amended fingerprints; in-memory syntax compilation of the changed Python files; standalone arithmetic
  scripts (only `math` and `fractions`) for the reference values in sections 5 and 6.
- **Not executed:** pytest or any test file, `hashlab validate`, Experiment 001, benchmarks, installs.
  The new and changed tests have **not been run** and may need fixes after the Director runs them.
- `results/` was not touched.

## 10. Assignment 003: final pre-experiment hardening

**1. Exploratory classifications.** The decision logic is unchanged (discovery, replication, the screen and
the class strings). Clarified:
- `analysis.json`: `classification_legend` and `label_note` (top level), `classification_meaning` per
  generator, and `verdict.exploratory_screen_passed`, `verdict.confirmatory_economic_claim` (always
  `false`), `verdict.economic_evidence_level`. `actionability.actionable` stays `false`.
- `report.md`: an experiment header line, a "How to read the labels" section right after the verdict,
  the class column marked "(see legend)", and the screen column reading "passed (exploratory)".
- Verdict wording: "NOT actionable" became "did not pass the exploratory economic screen". Nothing implies
  there is an actionable class.
- Plan: `decision_rules.classification_legend`, and the screen rule says the label is never a confirmatory
  mining advantage.

**2. Sample overlap** (methodology section 5b). Identical domains are not independent samples. Exact overlap
was computed with standalone integer arithmetic from the generator definitions (no hashing, no project code):
`seq-be-w8` and `struct-gray-w8` share 951,424 of 1,000,000 candidates (475,712 within discovery, 427,136
within validation, 24,288 in each cross-phase direction). The other deterministic 8-byte pairs share only
the all-zero candidate. Documented implications: dependent primary tests (Holm stays valid under
dependence, but joint flags are not independent evidence), no cross-generator replication, and direct
comparisons between sequential, structured and random generators are not comparisons of independent
samples. A plan warning and an analysis limitation say the same. No comparison procedure was added.

**3. Version 0.2.0** in `pyproject.toml` and `hashlab.__version__`. The contract changes are in
[`docs/CHANGELOG.md`](../CHANGELOG.md). Hypotheses, sample allocations, seeds, thresholds and target are
unchanged, and `configs/baseline.yaml` is byte-identical to the Assignment 002 version. The installed
editable package must be reinstalled so `environment.json` records 0.2.0; a new test checks this.

**4. Smoke test.** `configs/smoke-evidence.yaml` (id `smoke-evidence`, name
`SMOKE-TEST-evidence-pipeline-NOT-experiment-001`, seed 424242, 4 generators × 600 candidates, a 3,000-candidate
positive control, about 5,400 hashes, output `results-smoke/`, git-ignored). Instructions and expected output
are in [`docs/smoke-test.md`](../smoke-test.md). It was **not executed**. Only its dry-run plan was computed
(no errors; plan fingerprint `5a80d10d57539c6e4209c8dbdde89db815fb104950b32a167bd7c2b22fba8204`).

**Executed for Assignment 003:** reading code, git inspection, the in-memory dry-run plan for both configs,
in-memory syntax compilation, and the standalone overlap arithmetic. **Not executed:** pytest, `validate`,
the smoke test, Experiment 001, installs.
