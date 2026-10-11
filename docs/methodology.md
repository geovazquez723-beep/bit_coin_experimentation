# Scientific Methodology

## 1. Definitions

- **Candidate**: a byte string. It is the exact input to the hash engine.
- **Domain**: the set a generator draws candidates from. It is defined by
  `kind` (`bytes`, meaning any byte values, or `ascii-chars`, meaning ASCII
  text encoded one byte per character), `width_bytes`, the alphabet and its
  exact `cardinality`. A 16-character decimal string and an 8-byte integer are
  different inputs from different domains.
- **Engine**: `sha256` gives `H(x)` and `sha256d` gives `H(H(x))`, using
  `hashlib` with no other transformation.
- **Hash integer**: the 32-byte digest read as a **big-endian** unsigned
  integer `h` in `[0, 2^256)`. Leading zero bytes are kept.
- **Success**: `h < T` for the target `T` (an exact integer comparison).
  Requiring `k` leading zero bits is the same as `T = 2^(256-k)`.
- **Theoretical success probability**: `p0 = T / 2^256`, stored as an exact
  fraction.

## 2. Null model and hypotheses

Null model: for distinct candidates, digests are independent and uniform on
`[0, 2^256)`. So the success count `X` over `n` distinct candidates is
distributed as `Binomial(n, p0)`.

The independence in that model is an *assumption under test*. HASHLAB does not
claim that SHA-256 outputs for different inputs are proven to be independent.

**Primary family (H1).** For each generator `g`:
- `H0_g: p_g = p0`
- `H1_g: p_g != p0` (two-sided)

It is tested on the discovery phase with an exact binomial test (doubled
smaller tail) and corrected across all generators with Holm–Bonferroni (or
Bonferroni) at family-wise level `alpha`.

**Secondary family (H2, exploratory).** For each generator and phase:
- leading-zero-bit counts against the geometric(1/2) null (Pearson
  chi-square, with the tail pooled so every expected count is at least 5);
- first digest byte uniform on 0..255 (chi-square, 255 df);
- last digest byte uniform on 0..255 (chi-square, 255 df).

These are corrected within their own family. They never change the verdict.
They share data with the primary test (the same digests), so they are **not
independent** of it.

## 3. Decision rules (pre-registered)

1. **Discovery flag**: adjusted two-sided p < alpha.
2. **Replication**: flagged generators are tested on the validation phase with
   a *one-sided* exact test in the direction seen in discovery. The test is
   corrected across the flagged generators, and replication requires adjusted
   p < alpha.
3. **Exploratory economic screen** (amended by Architecture Review 001, see
   [the remediation record](reviews/architecture-review-001-remediation.md)).
   A replicated effect passes the screen only if:
   - it means *more* successes (direction `greater`);
   - the generator's domain is **identical** to the predeclared economic
     reference (section 5a); and
   - `L_sim × R ≥ 1 + min_actionable_relative_effect`, where `L_sim` is the
     validation-phase **Bonferroni-simultaneous** Clopper–Pearson lower bound
     of `rate / p0` (confidence `1 − (1 − confidence_level) / m` over the `m`
     primary generators) and `R` is the generator's end-to-end
     unique-candidates-per-second divided by that of the **predeclared
     reference** (never the fastest observed generator).

   The marginal bound `L` is still reported, with whether `L × R` alone would
   have passed, but a marginal bound alone never passes the screen. Passing the
   screen is **exploratory** evidence only: the analysis never declares a
   confirmatory economic advantage (`actionable` is always `false`), because
   throughput is one uncalibrated measurement and no confirmatory economic
   procedure is predeclared.
4. **Classification** (strongest label last):
   `consistent-with-null`, `unreplicated-discovery-signal`,
   `replicated-anomaly-non-actionable` (replicated, but fewer successes, a
   domain not comparable with the reference, no reference, or the screen not
   passed), `candidate-anomaly-requires-independent-replication` (replicated
   and passed the exploratory screen).
5. **Run-level gates**, checked in this order before any per-generator reading:
   - status not `complete` → **INCOMPLETE**, no conclusions;
   - harness integrity failure (section 4a) → **HARNESS INTEGRITY FAILURE**,
     no result may be interpreted;
   - positive control not detected (one-sided p ≥ alpha / family size) →
     **UNINFORMATIVE**.

   A statistically flagged null control is **not** a gate. It is a
   non-blocking diagnostic (section 4a) that is appended to the verdict.

A conventional significance threshold on its own is never treated as
evidence of cryptographic weakness.

## 3a. Evidence levels and interval types

| Item | Meaning | Can it support a confirmatory claim? |
|---|---|---|
| Marginal interval (`interval_type: marginal`) | `confidence_level` Clopper–Pearson for one generator and one phase, not adjusted for the number of generators | No. Descriptive only |
| Simultaneous interval (`simultaneous-bonferroni`) | Clopper–Pearson at `1 − (1 − confidence_level) / m`; all `m` primary generators are covered jointly with probability ≥ `confidence_level` | Used by the exploratory screen; still not confirmatory for economics |
| Discovery evidence | Holm-corrected two-sided exact tests on the discovery phase | Flags candidates for replication only |
| Validation evidence | Holm-corrected one-sided exact tests on disjoint validation candidates, only for discovery-flagged generators | Statistical replication within this run (not independent replication) |
| Exploratory economic screen | Section 3, rule 3 | No |
| Confirmatory economic conclusion | Not available in Experiment 001 | Would need a predeclared procedure that models throughput uncertainty, on fresh data |

Discovery and validation never share candidates within a generator, and the
validation family contains only discovery-flagged generators.

**Reading the labels (version 0.2.0).** No classification is a confirmatory
mining advantage, and there is no "actionable" class. The word
`non-actionable` in `replicated-anomaly-non-actionable` only means the
exploratory screen was not passed.
`candidate-anomaly-requires-independent-replication` means "replicated, and
passed the exploratory screen". In machine-readable output:
`actionability.actionable` is always `false`;
`actionability.exploratory_screen_passed` and
`verdict.exploratory_screen_passed` list exploratory results only;
`verdict.confirmatory_economic_claim` is always `false`. Every generator
carries `classification_meaning`, and `analysis.json` and `report.md` include
the full `classification_legend`. (The `actionability` key and the
`min_actionable_relative_effect` config key keep their names for
compatibility.)

## 4. Controls and independent validation

- **Validation set**: every generator has a validation phase disjoint from
  discovery:
  - Seedless generators continue their enumeration where discovery stopped.
  - Seeded generators use a separately derived sub-seed, and any candidate
    already seen in discovery is removed (counted as a cross-phase duplicate).
- **Null control**: a designated generator (baseline: `random-bytes-w8`,
  keyed BLAKE2b counter stream) that should behave like the null. It is
  tested exactly like every other generator; see section 4a for how its
  result is read.
- **Positive control**: a separate stream hashed by a deliberately biased
  engine (`experiments/controls.py`) that plants a known success lift. It
  checks that this run's sample size and analysis can detect an effect of that
  size. It never enters the primary family.

## 4a. Harness integrity vs null-control diagnostics

Two different things used to share one "harness alarm". They are now separate.

**Integrity failures (blocking).** `analysis.check_integrity` reports, and the
verdict becomes **HARNESS INTEGRITY FAILURE**, when a complete run has:
- a configured generator, phase or the null control with no usable evidence,
  or an enabled positive control with no evidence or zero hashed candidates;
- counts that are not non-negative integers, timings that are missing,
  negative or not finite, `successes > unique`, or
  `unique + duplicates ≠ attempted`;
- more candidates than planned, or fewer without the generator being
  exhausted;
- digest histograms whose totals differ from `unique`, or (for power-of-two
  targets) a success count that differs from the number of digests with at
  least `k` leading zero bits;
- generator results that are not in the configuration.

Evidence-file integrity (manifest hashes) stays a separate, earlier gate:
`hashlab analyze` refuses tampered evidence with exit code 3 before any
analysis runs.

**Null-control diagnostic (non-blocking).** Even a perfect null control is
flagged in discovery with probability up to `alpha` (Holm keeps the
family-wise rate at or below `alpha`). A flagged null control therefore does
not invalidate the run. The analysis:
- keeps every statistical result unchanged and visible (`null_control.p_value`,
  `p_value_adjusted`, the generator's own primary and replication results);
- records `status` = `statistical-anomaly` (flagged, not replicated) or
  `statistical-anomaly-replicated` (flagged and replicated on disjoint
  validation candidates, which has probability of order `alpha²` under a
  correct harness), with `blocking: false`;
- adds a `null-control-statistically-significant` entry to `diagnostics`
  (`warning`, or `serious` when replicated) and appends a warning to the
  verdict summary.

How it affects confidence: classifications are not changed, but every
positive label of that run is reported with reduced confidence and must not
go forward to independent replication until the diagnostic is explained. A
replicated null-control deviation should be treated as a strong sign of a
pipeline artifact. Missing null-control evidence is an integrity failure, not
a diagnostic.

## 5. Duplicates and overlap

- Generators marked *unique by construction* (sequential, patterned,
  structured) are proved injective in code comments and checked against small
  domains in the unit tests.
- Seeded generators (uniform, random_bytes) are deduplicated **exactly** with
  a set of seen candidates. The memory needed is checked against
  `execution.max_tracked_candidates` at plan time (no probabilistic filters).
- Statistics use **unique** candidates only. Attempted, unique, within-phase
  duplicate and cross-phase duplicate counts are all reported, together with
  the theoretical expected number of duplicates.
- Candidates are **not** deduplicated *across* generators. Generators may
  share inputs, and their results are not presented as independent of each
  other.

## 5a. Economic reference and comparability

- The reference is **predeclared** in the configuration
  (`economics.reference_generator`; baseline: `seq-be-w8`) before execution.
  It is copied into `plan.json` and so into the plan fingerprint. It is never
  chosen from observed throughput.
- Two generators are **comparable** only if their domains are identical:
  same `kind`, `width_bytes`, `alphabet`, `alphabet_size` and `cardinality`
  (so the same hash input length and the same sample space). The comparability
  table is computed from the configuration and printed in the plan. In the
  baseline, `uniform-be-w8`, `struct-*-w8` and `random-bytes-w8` are comparable
  with `seq-be-w8`. The `*-w16` generators (different kind or width) and
  `pattern-bytes-w8` (a subset of the 8-byte space) are not.
- Reported per generator and phase: raw hashing throughput
  (`hashing_per_second`), candidate-generation overhead
  (`candidate_overhead_seconds` = generation + dedup time, and its share of
  wall time), end-to-end evaluation throughput
  (`end_to_end_unique_per_second`), expected valid hashes per second
  (`p0 × end-to-end`) and observed valid hashes per second
  (`successes / wall_seconds`).
- For comparable generators the analysis reports the throughput ratio against
  the reference. For non-comparable generators, or when there is no reference
  or the reference has no throughput, only descriptive metrics are reported
  and the economic screen cannot be passed.
- Every economic figure is exploratory: throughput is one measurement of this
  Python implementation on one machine, with no uncertainty model.
- "Comparable" means the same sample space. It does **not** mean independent
  samples (section 5b).

## 5b. Sample overlap: identical domains are not independent samples

Candidates are deduplicated within a generator, never across generators, and
the validation phase is disjoint from discovery only *within* a generator. So
two generators with the same domain can hash many of the same inputs. Overlap
at baseline settings (500,000 + 500,000 candidates each), computed exactly
from the generator definitions with integer arithmetic (no hashing):

| Pair (8-byte domain) | Shared candidates | Why |
|---|---:|---|
| `seq-be-w8` / `struct-gray-w8` | **951,424 of 1,000,000** | Gray code maps indices below 2^20 onto integers below 2^20, so both enumerate almost the same low integers. 475,712 shared within discovery, 427,136 within validation, and 24,288 + 24,288 across phases |
| any two of `seq-be-w8`, `struct-gray-w8`, `struct-stride-w8`, `struct-bitrev-w8`, `pattern-bytes-w8` | at least the all-zero candidate | all start at index 0 with offset 0 |
| `uniform-be-w8` or `random-bytes-w8` with any other | expected about 5 × 10^-8 | independent draws from 2^64 values; possible but not checked |

The 16-character generators share at most the all-zero string
(`"0000000000000000"`).

Implications:
- **Dependent primary tests.** The success counts of `seq-be-w8` and
  `struct-gray-w8` are nearly the same measurement (identical digests for 95%
  of inputs). Holm controls the family-wise error rate under any dependence,
  so the primary tests stay valid. But two such generators being flagged
  together, or both replicating, is **not** two independent pieces of
  evidence.
- **Cross-generator "replication" is not replication.** Validation for one
  generator can reuse candidates another generator saw in discovery (24,288
  for `seq` vs `gray`). Only the within-generator validation phase counts as
  replication.
- **Direct comparisons.** Comparing sequential, structured and random
  generators is not a comparison of independent samples: deterministic
  generators that overlap share most of their randomness (any difference
  comes from the non-shared candidates), and deterministic generators cover a
  structured corner of the domain (for example, integers below 2^20 with
  their top five bytes zero) rather than a random sample of it. Random
  generators sample the whole domain. Results for a deterministic generator
  describe the candidates it actually produced, not its whole domain.
- **Economic ratios.** Throughput ratios between comparable generators
  compare candidate-generation costs. They say nothing about independent
  success rates.
- Experiment 001 adds no between-generator test. Any later direct comparison
  must account for shared candidates (for example by removing or pairing
  them) in a design predeclared for that purpose.

## 6. Measurement

Each bounded batch records generation time, dedup time and hashing time
(hash, integer compare and histogram updates) separately. Each phase records
its end-to-end wall time. Throughput figures describe this Python
implementation on the Director's machine. They are not general claims about
hashing speed.

Memory is bounded: one batch of candidates, fixed-size histograms and (only
for seeded generators) the dedup set. Full digests are never retained.
Per-batch counters stream to `batches.jsonl`. Successful candidates can
optionally be streamed to `successes.jsonl`, with a cap.

## 7. Statistical computation

All statistics are implemented in pure Python (`statistics/inference.py`) and
unit-tested against closed forms and reference values:
- binomial tails via the regularized incomplete beta function (continued
  fraction), with the small tail computed directly to keep relative accuracy;
- Clopper–Pearson intervals by bisection on the incomplete beta;
- chi-square survival via the regularized upper incomplete gamma function;
- Holm and Bonferroni adjustments;
- normal-approximation minimum detectable effects and power
  (`minimum_detectable_effect`, `minimum_detectable_effect_unpooled`,
  `normal_power`), for **planning only**;
- exact power of the doubled-tail binomial test (`exact_binomial_power`), to
  reproduce planning figures. The plan does not call it.

`tests/test_statistics_reference.py` checks these against references that
share no code with the implementation: exact rational (`Fraction`) binomial
sums, closed-form Clopper–Pearson bounds for `k ∈ {0, 1, n−1, n}`, a published
R interval, hand-computed Holm adjustments and an independent step-down
procedure, and tabulated normal quantiles.

**Numerical tolerances and limits.** Relative tolerance `1e-9` for
`n ≤ 10,000`. At `n ≈ 10^6` it is `1e-7`, because log-gamma differences such
as `lgamma(n + 1) − lgamma(n)` keep only about `1e-9` absolute precision
there (`lgamma(10^6) ≈ 1.3 × 10^7`). Tails below about `1e-300` underflow to 0
(absolute floor `1e-300`). Results are deterministic (no random numbers).

## 8. Sensitivity statement

The minimum detectable effect (MDE) is a **planning quantity**. It is the
relative change in success rate that the discovery test would flag with
probability equal to the power target, under stated approximations. It
depends on the sample size `n`, the target probability `p0`, the significance
level, the multiplicity assumption and the desired power.

Baseline assumptions: `n = 500,000` planned candidates per phase (all assumed
unique), `p0 = 1/256` (`k = 8`), family `alpha = 0.01` split Bonferroni-style
over 10 tests (`alpha' = 0.001` two-sided, which equals Holm's first step and
is conservative for Holm), power `0.8`, normal approximation with one
rejection tail. Then

`MDE = (z_{1−alpha'/2} + z_{0.8}) × sqrt(p0 (1 − p0) / n) / p0`
`    = (3.29053 + 0.84162) × 0.022583 = 0.09332`, about **9.3%**.

This figure was re-derived independently during Architecture Review 001 and is
correct for those assumptions. Refinements (see the remediation record):
- with the alternative-hypothesis variance, the MDE is about 9.42% for an
  increase and 9.24% for a decrease;
- the analysis actually uses the exact doubled-tail test, whose power at
  +9.33% is about 0.775 (it reaches 0.80 near +9.5%);
- 0.8 is the power of the **discovery** step alone. An effect at the MDE must
  also replicate (one-sided, Holm across the flagged generators): about 0.96
  power if only it is flagged, about 0.85 if all 10 are. The chance of
  flagging AND replicating it is therefore roughly 0.68 to 0.77 under the
  normal approximation, and a little lower with the exact test.

What it does **not** mean:
- An 80%-power MDE does not guarantee detection of an effect of that size.
- A non-significant result does not establish equivalence with the null and
  does not rule out effects at, above or below the MDE.
- Excluding effects of a given size would need a predeclared confidence-bound
  or equivalence analysis, which Experiment 001 does not include. (The
  reported intervals describe the data; they were not designed as an
  equivalence test.)

`python -m hashlab.cli plan` prints the MDE in each direction and the
replication power. The MDE scales as `1/sqrt(n·p0)`; increasing
`candidates_per_generator` tightens it.
