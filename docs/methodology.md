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
3. **Actionability**: a replicated effect is actionable only if:
   - it means *more* successes (direction `greater`), and
   - `L × R ≥ 1 + min_actionable_relative_effect`, where `L` is the
     validation-phase Clopper–Pearson lower bound of `rate / p0` and `R` is the
     generator's end-to-end unique-candidates-per-second relative to the
     fastest generator in the run.
4. **Classification** (strongest label last):
   `consistent-with-null`, `unreplicated-discovery-signal`,
   `replicated-anomaly-non-actionable`,
   `candidate-anomaly-requires-independent-replication`.
5. **Run-level gates**, checked in this order before any per-generator reading:
   - status not `complete` → **INCOMPLETE**, no conclusions;
   - null-control generator flagged → **HARNESS ALARM**, investigate the
     pipeline first;
   - positive control not detected (one-sided p ≥ alpha / family size) →
     **UNINFORMATIVE**.

A conventional significance threshold on its own is never treated as
evidence of cryptographic weakness.

## 4. Controls and independent validation

- **Validation set**: every generator has a validation phase disjoint from
  discovery:
  - Seedless generators continue their enumeration where discovery stopped.
  - Seeded generators use a separately derived sub-seed, and any candidate
    already seen in discovery is removed (counted as a cross-phase duplicate).
- **Null control**: a designated generator (baseline: `random-bytes-w8`,
  keyed BLAKE2b counter stream) that should behave like the null.
- **Positive control**: a separate stream hashed by a deliberately biased
  engine (`experiments/controls.py`) that plants a known success lift. It
  checks that this run's sample size and analysis can detect an effect of that
  size. It never enters the primary family.

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
- a normal-approximation minimum detectable effect, for **planning only**.

## 8. Sensitivity statement

With baseline settings (`k = 8`, so `p0 = 1/256`; 500,000 candidates per phase;
alpha 0.01 across 10 tests; power 0.8), the minimum detectable relative change
in success rate is about **9.3%**. A null result rules out effects of roughly
that size or larger for the tested generators. It says nothing about smaller
effects. To tighten it, increase `candidates_per_generator`: the minimum
detectable effect scales as `1/sqrt(n·p0)`.
