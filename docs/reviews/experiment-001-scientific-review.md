# Experiment 001: scientific review and closeout

- **Assignment:** Engineering Assignment 004, Part A
- **Run reviewed:** `20261011T205056Z-exp001-fc1d75fc`
- **Evidence:** `results/20261011T205056Z-exp001-fc1d75fc/` (local only; `results/` is git-ignored)
- **Frozen release:** `v0.2.0` = commit `ef595f5c2f2166923fd277def39708409f564419`
- **Review basis:** the sealed evidence files, read without modification, plus the independent checks in
  section 2. No new hashing was performed for this review.
- **Status:** accepted by the Architect (Architecture Review 002), subject to wording cleanup, which is
  applied in this revision. Experiment 001 was accepted as completed by the Director. This document records
  the scientific reading of that result. It changes no decision rule and no evidence.
- **Revision 2 (Architecture Review 002, finding 1):** wording only. A null-consistent result is now
  consistently distinguished from proof of the null hypothesis. Every recorded observation, statistic,
  p-value, interval and count is unchanged. See
  [architecture-review-002-remediation.md](architecture-review-002-remediation.md).

Throughout, statements are tagged:

- **[Observation]**: a value read directly from the sealed evidence.
- **[Statistical conclusion]**: the outcome of a pre-registered test or interval, under its stated
  assumptions.
- **[Hypothesis]**: an interpretation or post hoc pattern that the evidence does not test. It needs a new,
  predeclared experiment before it can be believed.

**Terminology.** This review uses the terms below in a fixed sense:

| Term | Meaning | Does **not** mean |
|---|---|---|
| **Null-consistent** | No pre-registered test rejected the null hypothesis at its stated alpha. The data are compatible with `p = p0` | That `p = p0` is true, proven or demonstrated |
| **Not detected** | No effect cleared the decision threshold at this sample size | That no effect exists, or that any effect is below a particular size |
| **Equivalence** | An effect bounded inside a predeclared margin by a predeclared procedure | Experiment 001 has **no** equivalence procedure, so it makes **no** equivalence statement |

A failure to reject the null hypothesis is **not** proof of the null hypothesis. Nothing in this review
proves that SHA-256 success probability is independent of input structure.

## 1. Summary

| Item | Result |
|---|---|
| Run status | `complete` |
| Evidence integrity | **Passed.** No discrepancy found; no blocker |
| Harness integrity (blocking checks in `analysis.json`) | Passed, no problems, no diagnostics |
| Positive control (+25% planted lift) | Detected, one-sided p = 1.46 × 10⁻¹⁴ |
| Null control (`random-bytes-w8`) | No signal (Holm-adjusted p = 0.671) |
| Primary family (10 generators, Holm, alpha = 0.01) | 0 discovery flags. All 10 `consistent-with-null` |
| Validation phase | No generator was eligible (none flagged). Reported descriptively only |
| Secondary family (60 distribution tests, Holm) | 0 flagged |
| Exploratory economic screen | Not reached by any generator. `confirmatory_economic_claim: false` |
| **Scientific disposition** | **Null-consistent: no deviation from `p0` detected at the planned sensitivity. The null hypothesis is not proven, and equivalence is not established** (section 13) |

## 2. Evidence verification (non-mutating)

All checks were run against the sealed directory with read-only operations. File modification times and
sizes were captured before and after the checks and are unchanged. `hashlab analyze` was **not** used,
because it writes a new `analyses/<stamp>/` subdirectory into the evidence directory. Its verification and
analysis functions were called in memory instead.

| # | Check | Result |
|---|---|---|
| 1 | `sha256sum` of every evidence file equals the hash and size listed in `manifest.json` (9 files) | Pass |
| 2 | SHA-256 of `manifest.json` equals `manifest.sha256` (`546d83a2…a967b`) | Pass |
| 3 | `hashlab.evidence.manifest.verify_manifest()` returns no problems (hashes, sizes, schema, no unlisted files) | Pass |
| 4 | Plan fingerprint recomputed from `plan.json` (canonical JSON without the fingerprint key) equals `d0808d45…2dc9` | Pass |
| 5 | The same fingerprint appears in `plan.json`, `results.json` and `manifest.json` | Pass |
| 6 | `configs/baseline.yaml` at `v0.2.0` is byte-identical to the sealed `config.source.yaml` and re-resolves to `config.resolved.json` | Pass |
| 7 | `build_plan(config.resolved.json)` at `v0.2.0` reproduces `plan.json` exactly | Pass |
| 8 | `seed_table()` reproduces `seeds.json` | Pass |
| 9 | Per-batch counts in `batches.jsonl` sum exactly to the per-phase counters in `results.json` (attempted, unique, successes, within- and cross-phase duplicates) | Pass |
| 10 | `analyze_results(results.json, config.resolved.json)` in memory reproduces `analysis.json`, except `analyzed_at_utc` and the **order** of `secondary_tests` (section 12, item R4) | Pass (content identical) |
| 11 | Independent exact two-sided binomial p-values (log-space, no HASHLAB code) and an independent Holm adjustment match `analysis.json` | Pass (max abs. difference 7.4 × 10⁻¹⁰) |
| 12 | `environment.json` records commit `ef595f5…` on `main`, `dirty: false`, 0 changed paths, and `v0.2.0` resolves to the same commit | Pass |
| 13 | Evidence files are read-only on disk (`-r--r--r--`) and unchanged by this review | Pass |
| 14 | Existing test suite at the review branch (`pytest -p no:cacheprovider`) | 240 passed |

**No integrity discrepancy was found.** The only difference between the sealed analysis and a fresh
in-memory re-analysis is the list order of the 60 secondary tests. Every statistic, p-value, adjusted
p-value and flag is identical once the lists are compared as sets. This is a reproducibility nuisance, not
a blocker, because the Holm adjustment is order-invariant (section 12).

Sealed file hashes (verified):

| File | Bytes | SHA-256 |
|---|---:|---|
| `analysis.json` | 81,503 | `5e22b2fc5d0ce4ed9dca71f0499c7b1b35f0f40a43d34228d8daad455d38b252` |
| `batches.jsonl` | 254,047 | `65ecf72decf20c9e9a8db29b1526c5dd39eeb2ecfc3d29166100d92e339fbad8` |
| `config.resolved.json` | 2,875 | `d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b` |
| `config.source.yaml` | 4,268 | `f2c0de21f3eba4b6a5fff41c8729b10d5c389e09334bd218f133d55a0140f225` |
| `environment.json` | 843 | `34e5e3c11015405dd540b2541f54086824b066aa83ed94c5fb80e2c13aa467f3` |
| `plan.json` | 37,502 | `ea38ed0150fae79d140b44691ad64dbda223163296b98671966d1b07456f3f36` |
| `report.md` | 11,305 | `e253f9ab9c40410e8f601a107716fbabd090782c75efa4dd47afb17cd64fb428` |
| `results.json` | 242,708 | `1ff1e2a3dc51c2860d7e5e5d69b8941c62e000c2e06f0f03b3d39331ee15818c` |
| `seeds.json` | 1,158 | `b04fa14409ff07606e81757908109427e4309615afd702a564f346b19b32d931` |
| `manifest.json` | 1,482 | `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b` |

## 3. Frozen protocol and execution environment

**[Observation]**

| Item | Value |
|---|---|
| Release / commit | `v0.2.0` / `ef595f5c2f2166923fd277def39708409f564419` (clean tree, branch `main`) |
| Package version | `hashlab` 0.2.0 (`analysis.json`, `plan.json`, `environment.json` agree) |
| Plan fingerprint | `d0808d4537db0c4eae8385740ae1663ff04c7ab6c4dc236fed22d8a4dffa2dc9` (matches the amended fingerprint recorded in `architecture-review-001-remediation.md`) |
| Config | `configs/baseline.yaml`, SHA-256 `f2c0de21…0140f225` (unchanged since Amendment 1) |
| Engine | `sha256` (`hashlib.sha256(candidate).digest()`, digest read big-endian) |
| Target | `T = 2^248` (8 leading zero bits); `p0 = 1/256 = 0.00390625` |
| Master seed | `20261011`; sub-seeds derived by SHA-256 (`seeds.json`) |
| Allocation | 10 generators × (500,000 discovery + 500,000 validation) = 10,000,000 candidates; positive control 200,000 candidates; **10,200,000 SHA-256 evaluations** |
| Run window | started `2026-10-11T20:50:57.04Z`, finished `20:51:09.43Z`; total wall time 12.39 s |
| Sealed | `2026-10-11T20:51:09.55Z`, manifest schema `hashlab-manifest-v1` |
| Machine | Windows 10.0.26200, AMD64, AMD Family 25 Model 97 (16 logical CPUs) |
| Software | CPython 3.11.0 (MSC v.1933, 64-bit), OpenSSL 1.1.1q (5 Jul 2022), PyYAML 6.0.3, pytest 9.1.1 |

The run executed exactly the pre-registered protocol in `docs/experiment-001.md` with Amendments 1 and 2.
Both amendments were recorded before execution (no data existed). No deviation from the protocol was found.

## 4. Primary hypothesis and decision criteria

Pre-registered (methodology sections 2–3):

- **Null model.** For distinct candidates, digests are independent and uniform on `[0, 2^256)`, so successes
  over `n` unique candidates follow `Binomial(n, p0)`. The independence is an assumption under test, not a
  theorem.
- **Primary family H1 (10 tests).** For each generator `g`: `H0_g: p_g = p0` vs `H1_g: p_g ≠ p0`, exact
  two-sided binomial test (doubled smaller tail) on the discovery phase, Holm-corrected at family-wise
  alpha = 0.01.
- **Replication.** Only discovery-flagged generators are tested on their disjoint validation phase, with a
  one-sided exact test in the discovery direction, Holm-corrected across the flagged generators.
- **Classification.** `consistent-with-null` → `unreplicated-discovery-signal` →
  `replicated-anomaly-non-actionable` → `candidate-anomaly-requires-independent-replication`. No label is
  confirmatory. `actionable` is always `false`.
- **Run gates.** The run must be complete, pass harness integrity, and detect the positive control. A flagged
  null control is a non-blocking diagnostic.
- **Planning sensitivity.** 80%-power MDE ≈ 9.3% relative (pooled normal approximation; +9.42% / −9.24%
  unpooled), per generator, discovery test alone, alpha' = 0.001 two-sided. Declared a planning quantity,
  not an exclusion bound.

## 5. Discovery and validation outcomes

**[Observation]** `p0 = 0.00390625`; expected successes per 500,000 unique candidates = 1,953.1
(SD 44.1). There were no duplicates in any generator or phase (0 observed, 0.00 expected).

| Generator | Discovery k | Discovery ratio [99% marginal CI] | p (two-sided) | Holm p | Validation k | Validation ratio [99.9% simultaneous CI] | Class |
|---|---:|---|---:|---:|---:|---|---|
| seq-be-w8 | 2,053 | 1.0511 [0.9925, 1.1122] | 0.0252 | 0.2269 | 1,977 | 1.0122 [0.9391, 1.0892] | consistent-with-null |
| seq-dec-w16 | 1,948 | 0.9974 [0.9402, 1.0569] | 0.9194 | 1.0000 | 2,000 | 1.0240 [0.9505, 1.1014] | consistent-with-null |
| uniform-be-w8 | 1,935 | 0.9907 [0.9338, 1.0501] | 0.6918 | 1.0000 | 1,989 | 1.0184 [0.9450, 1.0956] | consistent-with-null |
| uniform-dec-w16 | 1,947 | 0.9969 [0.9397, 1.0564] | 0.9014 | 1.0000 | 1,898 | 0.9718 [0.9002, 1.0472] | consistent-with-null |
| pattern-bytes-w8 | 1,969 | 1.0081 [0.9507, 1.0680] | 0.7249 | 1.0000 | 2,036 | 1.0424 [0.9682, 1.1205] | consistent-with-null |
| pattern-chars-w16 | 1,909 | 0.9774 [0.9208, 1.0364] | 0.3227 | 1.0000 | 1,913 | 0.9795 [0.9076, 1.0552] | consistent-with-null |
| struct-gray-w8 | 2,043 | 1.0460 [0.9875, 1.1070] | 0.0439 | 0.3513 | 2,039 | 1.0440 [0.9697, 1.1221] | consistent-with-null |
| struct-stride-w8 | 2,061 | 1.0552 [0.9964, 1.1165] | 0.0157 | 0.1568 | 1,906 | 0.9759 [0.9041, 1.0515] | consistent-with-null |
| struct-bitrev-w8 | 1,876 | 0.9605 [0.9045, 1.0190] | 0.0810 | 0.5670 | 1,955 | 1.0010 [0.9283, 1.0775] | consistent-with-null |
| random-bytes-w8 (null control) | 2,024 | 1.0363 [0.9780, 1.0970] | 0.1119 | 0.6712 | 1,938 | 0.9923 [0.9199, 1.0685] | consistent-with-null |

**[Statistical conclusion]**

- No generator was flagged in discovery. The smallest Holm-adjusted p-value is 0.157 (`struct-stride-w8`),
  far above alpha = 0.01. The smallest unadjusted p-value (0.0157) is also above the first Holm threshold
  (0.001). The null hypothesis was therefore not rejected for any generator. Non-rejection is not
  acceptance of the null.
- The replication family was therefore empty. Validation p-values are descriptive only and carry no
  inferential weight under the pre-registered rules.
- Every 99% marginal discovery interval for the rate ratio contains 1, and so does every 99.9% simultaneous
  validation interval.

**[Observation]** The three smallest discovery p-values (`struct-stride-w8`, `seq-be-w8`, `struct-gray-w8`)
are all positive deviations. Of these, `struct-stride-w8` reversed sign in validation (ratio 0.976), and
`seq-be-w8` fell to 1.012. Across all 10 generators the discovery and validation deviations have the same
sign in 5 of 10 cases, which is exactly the chance expectation.

## 6. Effect sizes, confidence intervals and power limitations

**[Statistical conclusion]** Observed discovery rate ratios range from 0.9605 to 1.0552, and validation
ratios from 0.9718 to 1.0440. All point estimates are within about ±5.5% of 1, and every interval in
section 5 contains 1. An interval containing 1 means the data are compatible with no effect. It does not
show that there is no effect.

**Power actually available.** Exact power of the discovery test (n = 500,000, alpha' = 0.001 two-sided,
the first Holm step), computed with `statistics.inference.exact_binomial_power`:

| True relative effect | Power (increase) | Power (decrease) |
|---|---:|---:|
| ±2% | 0.008 | 0.008 |
| ±5% | 0.136 | 0.142 |
| ±9.42% (planning MDE) | 0.786 | 0.832 |
| ±15% | 0.999 | 1.000 |

Consequences:

1. Experiment 001 had essentially **no ability to detect effects of 2%** and only about a **14% chance at
   5%**. The observed deviations of +4.6% to +5.5% in three generators are exactly the size that this design
   could not resolve. A null-consistent verdict says nothing about whether effects in that range exist.
2. The simultaneous validation intervals are the tightest pre-registered statement available. Read
   descriptively, they are compatible with true ratios from about 0.90 to about 1.12, depending on the
   generator. That is a description of the intervals, **not** an equivalence finding: no equivalence margin
   or equivalence test was pre-registered, and the planning MDE is explicitly not an exclusion bound.
3. **Not demonstrated:** that structured candidates behave like random ones, that SHA-256 success
   probability is independent of input structure, or that any effect is below any particular size.

## 7. Positive and null control performance

**Positive control [Observation, Statistical conclusion].** 200,000 candidates hashed through
`BiasedControlEngine` with a planted relative lift of 0.25 (implemented success probability
0.0048828124, i.e. 1.25 × p0 to 10 significant figures).

- 1,003 successes, rate ratio vs p0 = 1.2838 (99% marginal CI 1.1821–1.3917), one-sided p = 1.46 × 10⁻¹⁴,
  far below the detection threshold of 0.001. **Detected.** The run-level gate passed.
- Ratio of observed to planted probability = 1.027 (99% CI 0.946–1.113): the control recovered its planted
  effect without visible bias.
- **Limitation.** The planted lift (+25%) is about 2.7 times the planning MDE (9.4%). The control therefore
  shows that the pipeline can see a large effect at this target and sample size. It does **not** calibrate
  sensitivity near the MDE or near the small deviations seen in discovery. It also exercises the analysis
  pipeline through an engine substitution, so it does not test generator, deduplication or overlap
  artifacts.

**Null control [Statistical conclusion].** `random-bytes-w8` (keyed BLAKE2b counter stream): discovery ratio
1.0363, p = 0.112, Holm p = 0.671, `status: no-signal`, `statistically_flagged: false`, `blocking: false`.
Validation ratio 0.9923. No diagnostic was raised. The null-control result is consistent with a correctly
functioning harness, but it does not prove correctness. One unflagged null control is weak evidence about
harness correctness, since a correct harness and many subtly incorrect ones would both pass it.

## 8. Secondary distribution diagnostics

**[Observation]** 60 exploratory tests (10 generators × 2 phases × {leading-zero-bit count vs geometric(1/2),
first digest byte uniform, last digest byte uniform}), Holm-corrected within the family:

- **0 flagged** after correction. All adjusted p-values are 1.0.
- 3 of 60 raw p-values are below 0.05 (expected under the null: 3.0). None is below 0.01 (expected: 0.6).
- Smallest raw p-values: `pattern-chars-w16` validation, last byte (χ² = 297.5, 255 df, p = 0.035);
  `struct-gray-w8` validation, leading-zero bits (χ² = 27.4, 16 df, p = 0.037); `uniform-dec-w16`
  validation, last byte (χ² = 295.3, 255 df, p = 0.042).

**[Statistical conclusion]** The raw p-values are consistent with their distribution under the null.
This does not show that the digest distributions are exactly uniform or geometric. These tests share
digests with the primary test (the leading-zero histogram and the first-byte histogram both contain the
success count) and with each other, so they are not independent corroboration of the primary result.

## 9. Cross-generator candidate overlap

**[Observation]** Recomputed for this review by enumerating the candidates of every seedless and MT19937
generator from the sealed seeds, with no hashing. `random-bytes-w8` was not enumerated for this pairwise
table, because its stream is a keyed BLAKE2b. Its overlap with the other 8-byte generators is therefore
**not verified**. It is a probabilistic expectation of about 5 × 10⁻⁸ shared candidates, not an exact zero.

| Pair | Shared candidates (of 1,000,000 each) | Of which discovery ∩ discovery |
|---|---:|---:|
| `seq-be-w8` × `struct-gray-w8` | **951,424** | 475,712 |
| every other pair among `seq-be-w8`, `pattern-bytes-w8`, `struct-gray-w8`, `struct-stride-w8`, `struct-bitrev-w8` | 1 (the all-zero candidate) | 1 |
| `seq-dec-w16` × `pattern-chars-w16` | 1 (`"0000000000000000"`) | 1 |
| any pair involving `uniform-be-w8` or `uniform-dec-w16` | 0 | 0 |

This exactly matches the overlap documented in methodology section 5b.

Implications:

- **[Statistical conclusion]** Holm controls the family-wise error rate under arbitrary dependence, so the
  primary verdict is valid despite the overlap.
- **[Observation]** `seq-be-w8` and `struct-gray-w8` are close to a single measurement. Their similar
  discovery deviations (+5.1%, +4.6%) are **one** observation, not two. The effective number of independent
  primary tests is about 9, not 10.
- **[Observation]** The deterministic generators (`seq`, `gray`, `stride`, `bitrev`, `pattern`) cover small,
  structured corners of their domains, for example integers below 2^20. Their results describe the
  candidates actually hashed. They do not generalize to the structural class the generator is named after.
- **Design implication for Experiment 002:** experimental units must be disjoint by construction, and
  structured classes should be sampled at random rather than enumerated from index 0. See the Experiment 002
  proposal.

## 10. Exploratory economic and throughput observations

Everything in this section is **exploratory**. Throughput is a single measurement of about 0.3–1.5 s per
phase, from one Python process on one machine, with no uncertainty model. No confirmatory economic
procedure was predeclared, and none is claimed.

**[Observation]**

- Raw hashing throughput was nearly constant across generators: 1.50–1.53 million hashes/s (about 2%
  spread). Every candidate was 8 or 16 bytes, which is a single SHA-256 compression block.
- Candidate-generation overhead varied widely: 15.3% of wall time for `seq-be-w8` up to 78.5% for
  `pattern-chars-w16` (validation phase).
- End-to-end throughput relative to the predeclared reference `seq-be-w8`, for generators with an identical
  domain: `struct-gray-w8` 0.943, `struct-stride-w8` 0.883, `uniform-be-w8` 0.879, `random-bytes-w8` 0.798,
  `struct-bitrev-w8` 0.614.
- Patterned generators were about 2× slower in validation than in discovery. Validation continues the
  enumeration into longer motifs, so this is a structural change in workload, not timing noise.
- Observed valid hashes/s differs from expected valid hashes/s in proportion to success-count noise. It adds
  no information beyond the success counts.
- No generator reached the economic screen. It is only evaluated for replicated `greater` deviations.

**[Hypothesis]** In this harness, relative search efficiency is set by candidate-generation cost, not by
success probability, and the simplest counter (`seq-be-w8`) is the most efficient. This is consistent with
the null model and with ordinary engineering intuition. It is not established: no repeated timings, no
variance estimate, and no optimized or hardware implementation. It says nothing about production mining.

## 11. Post hoc exploratory observations (not pre-registered)

These summaries were computed for this review **after** seeing the data. They are not part of the
pre-registered analysis and **cannot change the verdict**. They are recorded so that any follow-up is
predeclared rather than chosen silently.

| Post hoc summary | Value | Comment |
|---|---|---|
| Sum of squared z-scores, all 20 generator-phases | 35.29 on 20 df, p = 0.019 | **Invalid as stated:** it double-counts `seq-be-w8` and `struct-gray-w8` |
| Same, excluding `struct-gray-w8` | 27.34 on 18 df, p = 0.073 | |
| Discovery phase only, excluding `struct-gray-w8` | 18.08 on 9 df, p = 0.034; Stouffer Z = 1.09 | |
| Validation phase only, excluding `struct-gray-w8` | 9.26 on 9 df, p = 0.41; Stouffer Z = 0.26 | The discovery-phase excess dispersion does **not** recur on disjoint data |
| Pooled discovery + validation, `struct-gray-w8` | ratio 1.0450, 99% CI [1.0034, 1.0878] | One of 10 post hoc pooled intervals excludes 1. With 10 such intervals, at least one exclusion has about a 10% chance under the null. Its candidates are 95% shared with `seq-be-w8` (pooled 1.0317, CI [0.9904, 1.0742]) |
| Pooled, all generators except `struct-gray-w8` (9 million candidates) | ratio 1.0051, 99% CI [0.9914, 1.0189] | Compatible with 1. Mixes different domains, so descriptive only |

**[Hypothesis]** The slight excess of positive deviations among low-integer 8-byte inputs (`seq-be-w8` and
`struct-gray-w8`, which are essentially one sample of integers below 2^20) and the extra dispersion in the
discovery phase are consistent with chance variation. This is a judgement, not a test result:

- the dispersion did not recur in validation;
- the pre-registered analysis found nothing;
- the patterns were selected after looking at the data.

The only legitimate use of these patterns is to **name a hypothesis in advance** and test it on fresh,
independent data. They must never be pooled with Experiment 002 confirmatory data, and they must never be
cited as preliminary evidence of an effect.

## 12. Reproducibility limitations and unresolved methodological risks

### Reproducibility

| # | Limitation | Severity | Note |
|---|---|---|---|
| R1 | One run, one machine, one hashing implementation (CPython 3.11.0 `hashlib` on OpenSSL 1.1.1q, which is past end of support) | Medium | No independent implementation has recomputed any digest of this run |
| R2 | `record_successes: false`. Only counts and histograms are sealed, not the individual successful candidates | Medium | A digest-level audit needs deterministic re-execution from the sealed seeds (about 12 s of hashing). That needs Director approval and was not done |
| R3 | `results/` is git-ignored. The sealed evidence exists only on the Director's disk | Medium | The tag pins the code, not the evidence. The manifest hashes in section 2 should be archived off-machine |
| R4 | Re-analysis lists `secondary_tests` in a different order from the sealed analysis, because generator order follows the key order of the sorted `results.json` | Low | Statistics are identical, and Holm is order-invariant. A byte-level comparison of `analysis.json` would wrongly look like a discrepancy |
| R5 | `hashlab analyze` writes `analyses/<stamp>/` inside the sealed directory (the manifest verifier allows this by design) | Low | No command verifies evidence without writing. This review used the library functions instead |
| R6 | Throughput cannot be reproduced by design: one timing per phase, with OS and CPU-state noise | Low (exploratory only) | |
| R7 | `docs/experiment-001.md` still says "Not executed" | Low (documentation) | Out of scope here. Should be updated in a recorded change |

### Unresolved methodological risks

1. **No equivalence analysis.** The design can only reject the null. It cannot bound an effect, so a
   null-consistent outcome cannot be turned into "no effect larger than X", and it never proves the null.
2. **Low power for small effects.** Power is 14% at ±5% and under 1% at ±2%. These are the effect sizes
   that would matter economically and that the discovery data hinted at.
3. **Dependent and non-representative units.** Overlapping generators (section 9) and deterministically
   enumerated corners limit inference to the realized candidates.
4. **The validation phase was conditional.** With no discovery flags, 5 million validation candidates had no
   pre-registered inferential role. The design gives no confirmatory use for half its data in the most
   likely outcome.
5. **The positive control is miscalibrated for sensitivity claims.** +25% planted vs a 9.4% MDE (section 7).
   No planted negative effect, and no generator-level planted artifact.
6. **Secondary tests are dependent** on the primary test and on each other.
7. **Null-model independence** across inputs is assumed, not tested, beyond what the success counts can
   show.
8. **Multiplicity of unfocused hypotheses.** Ten generators with heterogeneous domains, each against p0,
   spreads the alpha budget across hypotheses that have no shared prior motivation.
9. **Throughput lacks an uncertainty model**, so economic statements stay exploratory.

## 13. Final scientific disposition

**[Statistical conclusion]** Experiment 001 is a **valid, complete, integrity-verified and null-consistent
result**. The pre-registered procedure:

- detected no deviation from `p0 = 1/256` in SHA-256 success probability for any of the 10 candidate
  generators, at family-wise alpha = 0.01 with Holm correction;
- flagged no secondary distribution test after correction;
- detected the planted +25% positive control;
- did not flag the null control.

What the result means, and what it does not:

- It is **consistent with** the cryptographic null hypothesis at the sensitivity of the design (80% power
  at about ±9.4% per generator; low power below about ±7%). It is **not proof** of the null hypothesis.
- It does **not** establish that structured and random candidates are equivalent. It does not exclude
  effects below about 10%, and it makes no claim about other targets, engines, input lengths or
  implementations.
- No economic advantage was detected for any candidate-generation strategy. None was tested
  confirmatorily. Throughput differences are a property of this Python harness.
- No post hoc pattern (section 11) is evidence of an effect, and none is evidence of its absence.

**Recommended disposition:** close Experiment 001 as *null-consistent (no deviation detected) at the planned
sensitivity*. Keep the sealed
evidence unchanged and archive its manifest hashes. Carry the limitations in section 12 forward as design
requirements for Experiment 002 (`docs/proposals/experiment-002-research-design.md`).

## Appendix A: review method

- Hash and manifest checks: `sha256sum` and `hashlab.evidence.manifest.verify_manifest`, both read-only.
- Plan fingerprint: `sha256(json.dumps(plan_without_fingerprint, sort_keys=True, ensure_ascii=True))`, the
  serialization used by `build_plan`.
- Re-analysis: `hashlab.experiments.analysis.analyze_results` in memory. No files were written.
- Independent statistics: exact binomial tails computed in log space with `math.lgamma`, and Holm step-down
  written from scratch. Power figures use `statistics.inference.exact_binomial_power`.
- Overlap: candidate sets enumerated with `hashlab.candidates.build_generator` from the sealed configuration
  and seeds (enumeration only, no SHA-256).
- The verification script was kept outside the repository (session scratch space). It was run with
  `python -I -B` so that no bytecode was written into the source tree.
