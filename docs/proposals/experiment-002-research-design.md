# Experiment 002: research design proposal

- **Assignment:** Engineering Assignment 004, Part B; revised under Architecture Review 002
- **Revision:** 2. It supersedes revision 1. The changes are mapped finding by finding in
  [architecture-review-002-remediation.md](../reviews/architecture-review-002-remediation.md).
- **Status:** **PROPOSAL, conditional.** The Architect requires revisions before implementation is
  authorized. Not approved, not implemented, not executed. No executable configuration exists. Nothing in
  this document changes the frozen `v0.2.0` release or the Experiment 001 evidence.
- **Builds on:** [Experiment 001 scientific review](../reviews/experiment-001-scientific-review.md)
  (run `20261011T205056Z-exp001-fc1d75fc`).
- **Governance:** the Architect approves the design. The Director approves and runs every execution. The
  Engineer implements only after approval (research charter, Governance).

## 1. What Experiment 001 leaves open

Experiment 001 is a valid **null-consistent** result: no deviation was detected. It does not prove the null
hypothesis, and it is a weak result for structural reasons that more hashing alone would not fix:

| Gap in Experiment 001 | Consequence | Review section |
|---|---|---|
| No equivalence procedure | A null-consistent result cannot bound an effect | 6, 12 |
| Power 14% at ±5%, under 1% at ±2% | Economically relevant effect sizes went untested | 6 |
| 10 unfocused hypotheses across heterogeneous domains | Alpha budget spread thin; no shared motivation | 12 |
| `seq-be-w8` and `struct-gray-w8` share 95% of candidates | About 9 effective tests, not 10; agreement is not corroboration | 9 |
| Deterministic enumeration from index 0 | Inference limited to small corners such as integers below 2^20 | 9 |
| Validation used only if discovery flagged | Half the data had no inferential role in the most likely outcome | 12 |
| Positive control at +25%, far above the 9.4% MDE | Sensitivity near the MDE was never calibrated | 7 |
| Successes not recorded; single implementation and machine | No digest-level audit; no independent recomputation | 12 |
| Post hoc hints (low-integer inputs slightly high; discovery-phase dispersion) | Must be tested on fresh data or dropped, never pooled | 11 |

## 2. Options considered

The numbers below use the revised design: a combined alpha of 0.01 and 15 million candidates per arm per
stage (section 3.6).

### Option 0 (baseline comparison): rerun Experiment 001 with more hashes

- **Compute is not the obstacle.** Experiment 001 took 12.4 s of wall time for 10.2 million hashes.
- Reaching a 1% relative MDE with the Experiment 001 test (alpha' = 0.001 two-sided, 80% power) needs about
  **43.5 million unique candidates per generator per phase**, about 870 million hashes in total.

Why it is not recommended:

1. **Some generators cannot scale.** `pattern-bytes-w8` has only 16,842,496 candidates and
   `pattern-chars-w16` has 82,307,905. Both would run out before reaching 2 × 43.5 million.
2. **Scaling changes what is measured.** Deterministic generators would enumerate further from index 0, so a
   larger n samples a different population.
3. **Dependence does not shrink with n.** `seq-be-w8` and `struct-gray-w8` stay almost the same measurement.
4. **Exact deduplication stops being practical.** At 43.5 million per phase, the Python sets exceed
   `max_tracked_candidates` (2 million) and need several GB.
5. **A bigger null-consistent result is still not an equivalence result.**
6. **Optional stopping.** Enlarging n after seeing p = 0.016 and 0.025 in discovery is the pattern
   pre-registration exists to prevent.
7. **Systematic error does not average out.** A harness artifact grows more significant with n.

### Option 1: independent candidate-set replication with reduced overlap

| Criterion | Assessment |
|---|---|
| Scientific value | **Low to moderate.** Re-confirms Experiment 001 at the same sensitivity. Its main value is ruling out a harness artifact |
| Feasibility | High. Small generator changes |
| Statistical requirements | Unchanged: 10 tests, Holm, MDE about 9.4% at 500,000 per phase |
| Computational cost | About 10 million hashes |
| Limitations | Still unfocused, no equivalence, deterministic corners, no calibration near the MDE. Power for the +4–5% post hoc hints is about 14% |
| Meaningful result | A replicated deviation in a disjoint generator (unlikely). A second null-consistent result adds little |

### Option 2: targeted structure-class hypothesis with equivalence bounds (recommended)

Three predeclared input populations, each:

- defined exactly;
- sampled without replacement (or, for A2, by clustered prefix-and-nonce sampling);
- kept apart from every other arm, control and Experiment 001 candidate, with each guarantee stated as one
  of the guarantee classes in section 3.3;
- tested for **difference** (discovery, then validation) and against a **±2% margin**.

| Criterion | Assessment |
|---|---|
| Scientific value | **High.** Can give a bounded statement, or find a replicated deviation. Tests the post hoc low-integer hint on fresh data only. Inference applies to defined populations, not corners |
| Feasibility | Medium. Needs reviewed new code: exact samplers, an A2 cluster-level analysis, the margin rule and labels, a negative-lift control, success recording, a read-only verifier and a run registry |
| Statistical requirements | 3 primary arms. Combined alpha 0.01, split 0.005 difference + 0.005 margin. 15 million per arm per stage |
| Computational cost | **180.2 million SHA-256 evaluations** (240.2 million compression blocks). Estimated 15–45 minutes single-process, dominated by candidate generation (section 3.12) |
| Limitations | Bounds hold only for the defined populations, `T = 2^248`, engine `sha256` and these input lengths. Effects inside ±2% stay undetermined unless a deviation is detected. Arm A1 was motivated post hoc (disclosed) |
| Meaningful result | Either an equivalence outcome (falsifies a ≥2% effect for that population), or a replicated deviation with clean controls that goes forward to independent replication |

### Option 3: candidate-generation efficiency and throughput benchmarking

| Criterion | Assessment |
|---|---|
| Scientific value | **Low for HASHLAB's research question.** Engineering value only |
| Feasibility | High. A timing harness, run by the Director |
| Statistical requirements | Repeated randomized blocks, interval estimates of throughput ratios, a variance model |
| Computational cost | Low |
| Limitations | Machine- and implementation-specific. Must never be combined with success-rate data without a separately predeclared confirmatory economic procedure |
| Meaningful result | Calibrated throughput ratios with intervals. Cannot show a mining advantage |

### Comparison

| | Option 0: more hashes | Option 1: replication | **Option 2: targeted** | Option 3: throughput |
|---|---|---|---|---|
| Answers a new scientific question | No | Weakly | **Yes** | No (engineering) |
| Can bound an effect | No | No | **Yes, ±2%** | n/a |
| Defined, independent populations | No | Partly | **Yes** | n/a |
| Calibrated sensitivity | No | No | **Yes, planted ±2%** | n/a |
| Discovery-and-replication power at ±2% | n/a | about 0.01 | **0.926–0.948** | n/a |
| SHA-256 evaluations | about 870 million | about 10 million | **180.2 million** | small |

## 3. Recommended design: Experiment 002

**Recommendation: Option 2.** It includes Option 1's independence requirements. Option 3 is deferred as a
separate, non-confirmatory benchmark.

It is preferable to simply increasing the hash count because it changes **what can be concluded**:

- a bounded margin statement becomes possible;
- populations are defined and sampled representatively;
- sensitivity is calibrated at the margin;
- alpha is spent on 3 motivated hypotheses;
- it uses about 21% of the hashes Option 0 needs, without that option's exhaustion, dependence and
  optional-stopping problems.

### 3.1 Hypotheses and estimands

Engine `sha256`, target `T = 2^248`, `p0 = 1/256`. For each primary arm `a ∈ {A1, A2, A3}`, the estimand is
the **population-average success-rate ratio** `ρ_a = p̄_a / p0` over the population `U_a` defined in
section 3.2:

- For A1 and A3, `p̄_a` is the success fraction over the finite population `U_a`.
- For A2, `p̄_a` is the expected success fraction over a uniformly random prefix, with the nonce block fixed
  as defined in 3.2.

**Research hypothesis under test (falsifiable).** *H_S: for at least one of A1–A3, `|ρ_a − 1| ≥ 0.02`.*

Each arm has two predeclared analyses:

| Analysis | Hypotheses | Data | Procedure |
|---|---|---|---|
| **Difference** (discovery) | `H0_a`: every input in `U_a` has success probability `p0` (the strict input-level null); `H1_a`: not so | Stage D | exact two-sided binomial; Holm across A1–A3 at **alpha_diff = 0.005** |
| **Difference** (validation) | same null; one-sided in the discovery direction | Stage V, only for arms flagged in D | exact one-sided binomial; Holm across the flagged arms at **0.005** |
| **Margin** | interval for `ρ_a`, compared with `(1 − δ, 1 + δ)`, `δ = 0.02` | Stages D + V pooled | two-sided interval at level `1 − 2·(0.005/3)` = **99.667%**: Clopper–Pearson for A1 and A3; for A2 the hull of Clopper–Pearson and a cluster-level t interval (3.2). Bonferroni across A1–A3 at **alpha_margin = 0.005** |

How H_S is decided for each arm (section 3.4 has the full matrix):

- **Falsified** if the margin outcome is `WITHIN`: the interval lies inside `(0.98, 1.02)`.
- **Corroborated, as a candidate only**, if the difference outcome is `REPLICATED` **and** the margin outcome
  is `BEYOND`: the interval lies entirely outside `[0.98, 1.02]`, on one side. This only triggers artifact
  investigation and independent replication (3.9). It never supports a claim of SHA-256 weakness.
- **Not decided** otherwise.

A class-average bound does **not** bound sub-populations. For example, A3's weight-≤3 inputs are 0.045% of
A3 (3.2), so an effect confined to them would barely move `ρ_A3`.

**Disclosure.** Arm A1 was motivated by a post hoc pattern in Experiment 001 (review section 11). It is now
declared in advance and is tested only on fresh, disjoint data. Experiment 001 data are never pooled with
Experiment 002 data.

### 3.2 Populations and sampling

The **unit** is one distinct input. All random choices come from sub-seeds derived from the committed master
seed. **No sampler uses SHA-256 per candidate**, so the sampler cannot be entangled with the function under
test. Seed derivation reuses the existing domain-separated `derive_seed`, a one-off key derivation.

#### A1: low integers

- **Population:** `U1 = { x : 2^20 ≤ x < 2^32 }`, encoded as 8-byte big-endian.
  `|U1| = 4,294,967,296 − 1,048,576 = 4,293,918,720`.
- **Overlap with Experiment 001:** none. `U1 ∩ E001 = ∅` by exact enumeration (3.3), so no exclusion is
  needed.
- **Sampling:** a simple random sample (SRS) without replacement of size 30,000,000 from `U1`, then an exact
  random split into Stage D and Stage V, 15,000,000 each.
  - The SRS uses sequential random sampling, Vitter's Algorithm D (skip-based, O(n)).
  - Knuth's Algorithm S would need 4.29 × 10⁹ iterations, about 24 minutes at the prototype rate.
  - The split is a sequential hypergeometric assignment (3.2.4).

#### A2: clustered prefix-and-nonce design

A2 is **not** a uniform sample of 80-byte inputs. It is a **two-stage cluster design**.

- **Population:** `U2 = { prefix ‖ LE32(nonce) : prefix ∈ {0..255}^76, 0 ≤ nonce < 1,000,000 }`.
  - Inputs are 80 bytes, which is two SHA-256 compression blocks. The nonce is in the second block.
  - Estimand: the success fraction over the fixed nonce block, averaged over a **uniformly random 76-byte
    prefix**.
- **Prefix sampling (stage 1):** 30 prefixes drawn independently and uniformly from `{0..255}^76`.
  - Prefix `j` (`j = 0..29`) is the first 76 bytes of
    `BLAKE2b-512(key = K_A2, "hashlab-exp002-prefix" ‖ j ‖ 0) ‖ BLAKE2b-512(key = K_A2, … ‖ j ‖ 1)`.
  - All 30 prefixes are stored in the evidence.
  - Distinctness is **verified deterministically** at plan time. A collision blocks execution; its
    probability is about 2^-600.
- **Nonce block assignment (stage 2):** every prefix gets the **same** block `[0, 1,000,000)`, enumerated in
  ascending order. Within a cluster, nonces are **enumerated completely, not sampled**. This mirrors
  counter-based proof-of-work practice.
- **Clusters to stages:** clusters `j = 0..14` form Stage D and `j = 15..29` form Stage V, 15,000,000 inputs
  each. Prefixes are i.i.d., so this fixed assignment is exchangeable with a random one.
- **Conclusions apply to** the average over uniformly random 76-byte prefixes, nonces `0..999,999`, engine
  `sha256`, 80-byte inputs.
- **Conclusions do not apply to:**
  - other nonce ranges or encodings;
  - structured prefixes such as real block headers (version, previous hash, Merkle root, time and bits are
    not uniform);
  - `sha256d`;
  - 80-byte inputs in general.
- **Analysis consequences:**
  - The **difference test** uses exact binomial stage totals. It is valid under the strict input-level null,
    whatever the clustering. If success probability varies between prefixes (heterogeneity), the strict null
    is false and the test may reject even when `ρ̄ = 1`. For A2, a difference flag means "the input-level null
    is rejected", not "the average differs".
  - The **margin interval** for `ρ̄_A2` is the **hull** (union) of two intervals, each at 99.667%:
    - the pooled exact Clopper–Pearson interval;
    - a cluster-level Student t interval on the 30 per-cluster ratios `r_j = k_j / (10^6 · p0)`
      (29 df, `t = 3.1982`). Cluster sizes are equal, so the mean of the `r_j` equals the pooled ratio.

    The hull covers whenever either interval covers, so it is valid both conditionally on the sampled
    prefixes and for the prefix population.
  - **Secondary:** a between-cluster χ² heterogeneity test per stage (14 df). Exploratory. **No prefix-level
    claims.**

#### A3: low Hamming weight

- **Class:** `C3 = { x ∈ [0, 2^64) : HW(x) ≤ 6 and ⌊x / 2^32⌋ ≠ 0 }`, encoded as 8-byte big-endian. It is
  disjoint from A1 because A1 requires the top 32 bits to be zero.
- **Exclusion:** `X3 = C3 ∩ E001`, the Experiment 001 8-byte candidates inside the class.
- **Sampling population:** `U3 = C3 \ X3`.

Cardinality, verified three independent ways:

| Quantity | Value | Method |
|---|---:|---|
| `|{HW ≤ 6}|` over 64 bits | 83,278,001 | `Σ_{w≤6} C(64, w)` |
| of which top 32 bits zero | 1,149,017 | `Σ_{w≤6} C(32, w)` |
| **`|C3|`** | **82,128,984** | complement formula = split identity `Σ_{a=1..6} C(32,a) Σ_{b≤6−a} C(32,b)` = bit-by-bit dynamic programme; all three agree. Brute force on three small analogs (16/20/12-bit) agrees with the formula and the DP |
| **`|X3|`** | **60,721** | exact enumeration of all 7,000,000 Experiment 001 8-byte candidates from the sealed seeds: `struct-bitrev-w8` 60,439, `pattern-bytes-w8` 282, all others 0 (including `random-bytes-w8`). Exclusion-set digest `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c` (SHA-256 of the sorted 8-byte big-endian values) |
| **`|U3|`** | **82,068,263** | `|C3| − |X3|` |

Composition of `U3` by Hamming weight:

| Weight | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|
| In `C3` | 32 | 1,520 | 36,704 | 599,416 | 7,423,136 | 74,068,176 |
| Excluded (`X3`) | 20 | 198 | 1,152 | 4,889 | 15,599 | 38,863 |
| **In `U3`** | 12 | 1,322 | 35,552 | 594,527 | 7,407,537 | 74,029,313 |
| Share of `U3` | < 0.0001% | 0.0016% | 0.043% | 0.72% | 9.03% | 90.20% |

- `ρ_A3` is therefore dominated by weight-6 inputs.
- The exclusion removes 0.074% of `C3`. Conclusions apply to `U3`, not to `C3`. Effects confined to the
  excluded inputs are outside Experiment 002's population; Experiment 001 already measured those inputs,
  null-consistently and at low power.

**Indexing.** Ranks enumerate `C3` by weight, then by colex order of the set-bit positions, skipping the
subsets that lie entirely in the low 32 bits. Unranking is a bijection:

- verified exhaustively onto the class for two small analogs;
- verified by 200,009 rank/unrank round trips on the full `C3`, with 0 failures.

**Sampling:**

1. Knuth's Algorithm S over the ranks of `C3`, in ascending order, skipping the 60,721 excluded ranks. It
   draws an SRS of 30,000,000 from `U3` (sampling fraction 36.6%).
2. A sequential hypergeometric split into D and V (15,000,000 each).
3. Unranking to 8-byte values.

#### 3.2.4 Why the A1 and A3 samplers are unbiased

- **Algorithm S (integer form).** Element `t` of `N_u` remaining is selected iff
  `randrange(N_u − t) < need`. This selects every size-`n` subset of `U` with probability `1 / C(|U|, n)`,
  exactly, given an ideal uniform RNG (Knuth, TAOCP vol. 2, 3.4.2). Skipping a fixed excluded set before
  selection makes the subset uniform over `U3` itself.
- **Hypergeometric split.** Each selected element goes to D with probability `remaining_D / remaining_total`.
  This gives a uniformly random partition into sizes 15M / 15M, so D and V are each an SRS from `U`, and they
  are disjoint.
- **Vitter's Algorithm D** produces the same distribution as Algorithm S, via skip lengths (Vitter, ACM TOMS
  1987).
- The integer comparison avoids floating-point bias. The only remaining assumption is the **RNG model**:
  MT19937, seeded from a derived sub-seed, treated as an ideal uniform source (section 3.3, class C).
- **Demonstration** (scratch prototype, small analog: 2,354-element class, 100 excluded, 300 + 300 drawn,
  6,000 seeds):
  - stage-D inclusion frequencies are uniform (χ² scaled for sampling without replacement 2171.2 on 2253 df,
    p = 0.89);
  - stage-V inclusion frequencies are uniform (2233.6, p = 0.61);
  - pairwise inclusion is 0.01517 against the SRS value 0.01766 (SE 0.0017, 1.5 SE);
  - 0 violations: exact sizes, D ∩ V = ∅, no excluded element drawn.

  The production implementation must repeat these checks as unit tests (gate G1).
- **Alternative considered.** A keyed Feistel permutation with cycle-walking also passed the analog
  uniformity checks (p = 0.26 and 0.84). It is **not** recommended for the inferential arms, for two
  reasons:
  - Its uniformity rests on a pseudorandom-permutation assumption with no meaningful proven bound on small
    domains (2^28 for A3) when about 2^25 points are drawn.
  - It was 20 times slower in the prototype.

#### Null and positive controls

- **N1, 8-byte null control:**
  - Inputs come from a keyed 64-bit Feistel permutation `π_N` (6 rounds, BLAKE2b round function) applied to
    indices `0, 1, 2, …`.
  - Values in `C1 ∪ C3` (by predicate) or in `E001` are rejected. `E001` rejection works by index: every
    Experiment 001 8-byte candidate is mapped through `π_N⁻¹` at plan time, and the resulting indices are
    skipped.
  - First 15M accepted values go to D, next 15M to V. Uniqueness follows from the bijection.
  - Because N1 is a control, not an inferential arm, its uniformity rests on the PRP heuristic (class C).
- **N2, 80-byte null control:**
  - i.i.d. uniform 80-byte strings from a keyed BLAKE2b stream, 15M per stage.
  - Any string equal to an A2 input is rejected. The check is deterministic: does the first 76 bytes match
    one of the 30 prefixes, with a nonce below 10^6.
- **P1, P2+ and P2− positive controls:**
  - Inputs come from the same permutation `π_N`, on indices starting at 2^63. N1 uses fewer than 31 × 10^6
    indices, so these index ranges are disjoint from N1's and the values are distinct.
  - The same rejection rules as N1 apply.
  - Each control is hashed through the biased control engine.

### 3.3 Overlap and exclusion guarantees

Every claim of "no shared candidates" belongs to exactly one guarantee class. Probabilistic statements are
**never** reported as zero.

| Class | Meaning | What the evidence records |
|---|---|---|
| **M**: mathematical | Disjointness follows from the construction (length, a defining predicate, a bijection on disjoint index ranges) and is proven in the design. Unit tests on small analogs check the implementation | The proof reference and the unit-test result (G1) |
| **E**: exact enumeration | The relevant sets were enumerated completely and intersected exactly (done for this revision from the sealed Experiment 001 seeds) | Counts and set digest; rerun at plan time |
| **D**: deterministic verification | An algorithm checks every relevant element at plan or run time and rejects or blocks on a hit. Disjointness then holds exactly **given** the check, which is recorded | Number of elements checked, hits, rejections |
| **P**: probabilistic, negligible | Not checked. A bound on the probability of any overlap is reported instead | The bound, labelled "not verified" |
| **C**: computational assumption | Not an overlap claim. Sampling uniformity relies on the RNG model (MT19937) or on the PRP heuristic (Feistel, controls only) | Stated as an assumption |

Pairwise guarantees (E001 means the Experiment 001 candidates: 7,000,000 of 8 bytes and 3,000,000 of 16
bytes):

| Pair | Guarantee | Basis |
|---|---|---|
| A1 vs A3 | **M** | top 32 bits zero vs non-zero |
| any 8-byte set (A1, A3, N1, P) vs any 80-byte set (A2, N2) | **M** | input length |
| any Experiment 002 set vs the 16-byte E001 candidates | **M** | input length |
| A2, N2 vs E001 | **M** | input length |
| A1 vs E001 (8-byte) | **E**, plus **M** for `seq-be-w8` and `struct-gray-w8` | 0 of 7,000,000 enumerated candidates lie in `U1` (`random-bytes-w8` included). Sequential and Gray candidates are below 2^20 by construction |
| A3 vs E001 (8-byte) | **E**, then **M** | the 60,721 shared candidates are enumerated exactly (E). Sampling from `U3 = C3 \ X3` then makes disjointness hold by construction (M) |
| N1, P vs A1 ∪ A3 | **M** | predicate rejection |
| N1, P vs E001 (8-byte) | **D** | inverse-permutation index check of all 7,000,000 candidates; hits skipped and counted |
| N1 vs P | **M** | same bijection, disjoint index ranges |
| Stage D vs Stage V in A1 and A3 | **M** | partition of one SRS drawn without replacement |
| Stage D vs Stage V in N1 | **M** | bijection, disjoint index ranges |
| Within A1, A3, N1, P (uniqueness) | **M** | SRS without replacement; bijection |
| A2 clusters and stages | **D**, then **M** | 30 prefixes verified distinct (D); distinct prefixes, or the same prefix with distinct nonces, give distinct inputs (M) |
| N2 vs A2 | **D** | membership check of every N2 input; hits rejected and counted |
| Uniqueness within N2 | **P** | not checked. P(any duplicate) ≤ `C(3×10^7, 2) / 2^640` ≈ 2^-591 |
| Sampling uniformity (A1, A3) | **C** | MT19937 treated as an ideal RNG |
| Sampling uniformity (N1, P, prefixes, N2) | **C** | Feistel / BLAKE2b treated as pseudorandom; controls only |

**Gate rule.** Execution is blocked unless, at plan time:

- every **D** check has run, with its hits rejected and recorded;
- the re-enumerated **E** counts equal the values above (0 for A1; 60,721 with the stated digest for A3);
- every **M** property passed its G1 unit tests.

**P** items are reported with their bounds and never as zero.

### 3.4 Discovery, validation and margin procedure; classification

- **Stage D:** 15,000,000 inputs per arm. Exact two-sided tests; Holm across A1–A3 at 0.005.
  - First Holm threshold 0.005/3 = 0.001667.
  - Rejection region at n = 15M: `k ≤ 57,835` or `k ≥ 59,356`; expected 58,593.75.
- **Stage V:** 15,000,000 fresh inputs per arm, **always collected**.
  - Arms flagged in D get a one-sided same-direction test, Holm across the flagged arms at 0.005.
- **Margin:** the pooled interval (30M) for every arm, whatever the D outcome.
- **No interim analyses, no top-ups, no early stopping.**

**Outcomes.**

Difference outcome:

- `NONE`: not flagged in D.
- `UNREP`: flagged in D, not replicated in V.
- `REP`: flagged in D and replicated in V.

Margin outcome:

- `WITHIN`: the interval lies inside `(0.98, 1.02)`.
- `BEYOND`: the interval lies entirely outside `[0.98, 1.02]`.
- `UNDET`: anything else.

**Classification of simultaneous difference and margin findings** (predeclared, exhaustive):

| Difference \ margin | `WITHIN` | `UNDET` | `BEYOND` |
|---|---|---|---|
| `NONE` | `equivalent-within-margin` | `inconclusive-at-margin` | `discordant-requires-investigation` |
| `UNREP` | `equivalent-within-margin` (with an `unreplicated-discovery-signal` note) | `unreplicated-discovery-signal` | `discordant-requires-investigation` |
| `REP` | `replicated-deviation-within-margin` | `replicated-deviation-margin-undetermined` | `replicated-deviation-beyond-margin` |

How to read the table:

- **`REP` with `WITHIN` is not a contradiction.** It means the strict null `ρ = 1` was rejected **and**
  `|ρ − 1| < 0.02`: a detectable deviation smaller than the margin. Both findings are reported. H_S is
  falsified for that arm, yet the deviation still goes to artifact investigation and 002-R. If genuine, any
  replicated deviation would be of scientific interest.
- **Discordant cells** (`BEYOND` without replication) are nearly impossible under any true `ρ`. At
  `|ρ − 1| ≥ 2.5%`, discovery power is at least 0.998, while `BEYOND` needs `|ρ̂ − 1| ≥ 2.87%`. These cells
  therefore indicate an artifact, such as inconsistency between stages. They support no H_S statement and
  trigger investigation.
- **Every `REP` label** goes to artifact investigation and then Experiment 002-R before any statement
  stronger than "candidate deviation, unconfirmed".
- **No label** implies a cryptographic weakness or an economic advantage.

### 3.5 Error budget and multiple testing

| Family | Size | Method | Budget |
|---|---:|---|---|
| Difference (discovery, then validation) | 3 | Holm two-sided in D; Holm one-sided in V among flagged | **0.005**. A false `REP` claim needs a false discovery, so P(any false `REP`) ≤ 0.005 under strong FWER control |
| Margin (`WITHIN` / `BEYOND`) | 3 | Bonferroni: one two-sided 99.667% interval per arm | **0.005**. For any true `ρ_a`, at most one of a false `WITHIN` (`|ρ_a − 1| ≥ δ`) or a false `BEYOND` (`|ρ_a − 1| < δ`) is possible, each requiring a one-sided miss of probability ≤ 0.005/3. Total ≤ 0.005 |
| **Combined primary claims** | | Bonferroni over the two families | **≤ 0.01** |
| Secondary (leading-zero bits, first byte, last byte per arm and stage; A2 heterogeneity; A3 weight strata) | | Holm within the family | exploratory; never changes a label |
| Controls | | individual thresholds (3.7) | gates or diagnostics, outside the primary budget |

The 0.005 / 0.005 split is the Architect's provisional allocation (decision D4).

### 3.6 Sample size and power

**Assumptions.**

- Under the null, distinct inputs are independent Bernoulli(`p0`) trials.
- A1 and A3 are finite-population SRS designs (sampling fractions 0.7% and 36.6%). The binomial model is
  then **conservative** for the finite-population estimand, because hypergeometric variance is smaller by
  `1 − f`. Size is preserved and power is understated.
- A2 uses the cluster design of 3.2.
- No duplicates.
- Every power figure below is a planning quantity. The analysis never reads it.

**Formulas** (planning; normal approximation, `SE(ρ̂) = sqrt((1 − p0) / (n·p0))`):

- Difference: `n = (z_{1−α_d/(2m)} + z_{1−β})² · (1 − p0) / (p0 · e²)`.
  - With `α_d = 0.005`, `m = 3`, `e = 0.02`, power 0.95: `(3.144 + 1.645)² · 255 / 0.0004 ≈ 14.6 × 10^6`.
- Margin, at true `ρ = 1`: `n = (z_{1−α_m/m} + z_{1−β/2})² · (1 − p0) / (p0 · δ²)`.
  - Power 0.9: `(2.935 + 1.645)² · 637,500 ≈ 13.4 × 10^6` pooled.
- **The difference and replication requirement binds.** n = **15,000,000 per arm per stage** (30M pooled),
  up from 13M in revision 1 because of the smaller alpha.

**Exact power.** Two independent implementations were used:

- (A) `hashlab.statistics.inference` (`exact_binomial_power`, `clopper_pearson`, `binom_cdf`);
- (B) a self-contained check with log-space binomial sums and Clopper–Pearson by bisection.

A and B agree to every printed digit. The normal approximation agrees to within 0.011.

Difference, n = 15M per stage:

| True effect | Discovery power (two-sided 0.001667) | Validation power, 1 arm flagged (0.005) | Validation power, 3 flagged (0.001667) | **Joint discovery and replication** |
|---|---:|---:|---:|---:|
| +1.0% / −1.0% | 0.234 / 0.237 | 0.438 / 0.440 | 0.303 / 0.306 | 0.071–0.103 / 0.072–0.104 |
| +1.5% / −1.5% | 0.685 / 0.693 | 0.853 / 0.858 | 0.755 / 0.762 | 0.517–0.584 / 0.528–0.594 |
| **+2.0% / −2.0%** | **0.954 / 0.958** | 0.988 / 0.989 | 0.971 / 0.974 | **0.926–0.942 / 0.933–0.948** |
| +2.5% / −2.5% | 0.998 / 0.998 | 1.000 / 1.000 | 0.999 / 0.999 | 0.997–0.998 / 0.998 |

For comparison, revision 1's n = 13M under the new alpha gives a joint power at ±2% of only 0.857–0.895,
which is why n was increased.

Margin, A1 and A3, exact Clopper–Pearson at 99.667%, pooled n = 30M:

- `WITHIN` acceptance region: `115,839 ≤ k ≤ 118,519`, i.e. `ρ̂ ∈ [0.98849, 1.01136]`.
- `BEYOND` region: `k ≥ 120,546` (`ρ̂ ≥ 1.02866`) or `k ≤ 113,851` (`ρ̂ ≤ 0.97153`).

| True `ρ` | 0.980 | 0.985 | 0.990 | 0.995 | 1.000 | 1.005 | 1.010 | 1.015 | 1.020 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P(`WITHIN`), exact | **0.00166** | 0.114 | 0.699 | 0.987 | 0.99991 | 0.985 | 0.680 | 0.108 | **0.00166** |
| Normal approximation | 0.00167 | 0.111 | 0.690 | 0.986 | 0.99991 | 0.986 | 0.690 | 0.111 | 0.00167 |

| True `ρ` | 0.960 | 0.965 | 0.970 | 0.975 | 1.025 | 1.030 | 1.035 | 1.040 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P(`BEYOND`), exact | 0.99997 | 0.989 | 0.703 | 0.114 | 0.108 | 0.675 | 0.984 | 0.99993 |

At the boundary `ρ = 1 ± 0.02`, P(`WITHIN`) = 0.00166 ≤ 0.005/3 = 0.001667. The exact size of the
equivalence decision is therefore controlled, as required.

Margin, A2: Monte Carlo of the hull rule, 30 clusters of 10^6, 40,000 replicates (Monte Carlo SE ≤ 0.0025).
`τ` is the between-prefix standard deviation of the relative effect.

| True `ρ̄` | `τ = 0` | `τ = 0.005` | `τ = 0.010` |
|---|---:|---:|---:|
| 1.000 | 0.9994 | 0.9983 | 0.9846 |
| 1.005 | 0.963 | 0.945 | 0.860 |
| 1.010 | 0.568 | 0.517 | 0.395 |
| 1.015 | 0.070 | 0.067 | 0.054 |
| 1.020 (boundary) | 0.0010 | 0.0011 | 0.0014 |

The hull rule stays within the nominal 0.00167 at the boundary under heterogeneity.

Positive controls (exact, one-sided alpha 0.001):

| Control | Power |
|---|---:|
| P1, +25%, 200,000 inputs | 0.99976 |
| P2+, +2%, 15M inputs | 0.959 |
| P2−, −2%, 15M inputs | 0.963 |
| At least one of P2± detected | 0.9985 |

Expected successes: 58,594 per arm-stage, 117,188 per arm pooled, about 703,900 in total.

### 3.7 Positive and negative controls

| Control | Purpose | Rule |
|---|---|---|
| **P1** (+25%, 200k) | The pipeline sees a gross effect | **Gate:** detected at one-sided p < 0.001 |
| **P2+ / P2−** (±2%, 15M each) | Calibrate sensitivity at the margin, both directions | **Gate:** at least one detected at one-sided p < 0.001 (expected failure about 0.15%). Both detections, and whether the interval covers the planted value, are reported |
| **P2± not `WITHIN`** | The margin rule does not accept an effect at the margin | **Gate:** the margin rule (99.667% Clopper–Pearson, n = 15M) must not return `WITHIN` for P2+ or P2− (probability ≤ 0.00167 each under correct code) |
| **N1, N2** | Detect artifacts specific to input length or sampler | Tested exactly like arms (D: two-sided 0.001667; V: one-sided 0.005). Flagged in D: non-blocking diagnostic. **Flagged in D and replicated in V: gate failure F4** (3.8). Margin not `WITHIN`: diagnostic (expected about 10⁻⁴) |
| **Overlap and exclusion audit** | Unit independence | **Gate** per section 3.3 |

P2− requires a new negative-lift mode in the control engine. The current control supports positive lifts
only.

### 3.8 Seeds, run attempts and retry policy (pre-registered)

**Seeds.**

- A single master seed is committed in the configuration, and therefore in the plan fingerprint, and in the
  pre-registration record **before any attempt**.
- Every sub-seed, permutation key and the A2 prefix key derive from it.
- The confirmatory seed must never be used by a smoke run. Smoke runs use their own experiment id, their own
  seed, at most 1% of the sample size, and `results-smoke/`.
- How the seed is chosen is decision D5.

**Run registry.**

- A committed, append-only record, for example `docs/experiments/002-run-registry.md`.
- Before every invocation of `hashlab run` with the Experiment 002 configuration, the Director adds an entry:
  attempt number, UTC time, commit, configuration SHA-256, plan fingerprint.
- After the attempt, the Director appends the run id, the failure class or `valid`, and the manifest hash.
- No attempt is ever deleted, and no sealed evidence directory is ever deleted.

**Determinism.**

- Given the seed and the code, every candidate set is fixed, so a rerun with the same seed and code
  reproduces the same data.
- Selective reruns therefore cannot pick a different sample. Results can change only through a code change,
  and every code change is a recorded amendment.

**Blinding.**

- For a failed attempt, only the failure class and the diagnostic messages are read.
- The harness must emit **no primary-arm success counts** in progress output, and none in `INCOMPLETE` or
  `HARNESS INTEGRITY FAILURE` reports. This is an implementation item to verify at G1.
- Where a deterministic consistency check against an earlier attempt is needed, it compares digests of
  per-component counter blocks automatically, without displaying the counts.

**Failure classes**, determined by the harness and the gates, never by the primary statistics:

| Class | Definition | Verdict | Permitted retry |
|---|---|---|---|
| **F1 implementation failure** | Plan errors, an exception, or a crash before sealing; or a defect found in pre-execution testing | none (unsealed) or `INCOMPLETE` | Same seed. With no code change, rerun directly. With a code change: a recorded amendment, Architect review of the diff, the new fingerprint committed before the rerun |
| **F2 incomplete execution** | Sealed with status ≠ `complete` (interruption, resource exhaustion) | `INCOMPLETE` | Same seed and the same fingerprint, unless F1 applies. Counts for unaffected components must reproduce (digest check) |
| **F3 integrity failure** | Manifest verification fails, or a blocking harness-integrity problem appears | `HARNESS INTEGRITY FAILURE` | A root cause is required first. Storage or environment cause: rerun with the same seed. Code defect: the F1 amendment path. The digest check against the earlier attempt applies where meaningful |
| **F4 statistical control failure** | P1 not detected; no P2 detected; a P2 returns `WITHIN`; a null control replicated a deviation; an overlap or exclusion audit hit not handled as specified | `UNINFORMATIVE` (`BLOCKED` for a replicated null control) | **No rerun with the same code** (it would reproduce the same result). Investigate. If a defect is found, the amendment must be approved **before** the rerun is executed; same seed; both attempts reported in full, **including the failed attempt's primary statistics**; labels of the rerun carry a `post-amendment` qualifier. If no defect is found, Experiment 002 closes as `UNINFORMATIVE` |
| **Valid** | Complete, integrity passed, every G3 gate passed | labels per 3.4 | **None. The attempt is final and confirmatory.** No further attempts under Experiment 002 for any reason |

**Limits and prohibitions.**

- More than 3 attempts of classes F1–F3 requires Architect escalation.
- **A new seed means a new experiment.** It needs a new id, a new pre-registration, and disclosure of every
  Experiment 002 attempt in all later reports.
- Rerunning a **valid** attempt, choosing among attempts, or pooling attempts is prohibited.
- A confirmatory claim requires:
  - a complete registry;
  - retained evidence for every attempt;
  - a final report that lists every attempt and its class.

### 3.9 Independent replication

1. **Computational reproducibility (always).** After sealing, an independent verifier recomputes:
   - every recorded success (candidate bytes are stored);
   - a seeded 1% audit sample of the other inputs.

   It uses a different SHA-256 implementation (for example another OpenSSL major version or a reference
   implementation) and an independent reimplementation of the samplers for the audit sample. On the
   Director's decision, a full deterministic rerun on a second machine must reproduce every count exactly.
2. **Statistical replication (built in).** Stage V.
3. **Independent scientific replication (conditional).** Every `REP` label triggers a separately approved
   Experiment 002-R:
   - new master seed;
   - different machine;
   - independent hashing implementation;
   - code review of the samplers;
   - the same predeclared rules, applied to that arm and to the controls.

### 3.10 Evidence provenance and integrity

The `hashlab-manifest-v1` sealing scheme is kept. The following are added, each requiring approval:

- **Pre-registration record**, committed before any attempt. It holds:
  - the configuration SHA-256, the resolved-configuration hash and the plan fingerprint;
  - the master-seed commitment;
  - the E counts and digest (3.3);
  - the release tag.
- **Run registry** (3.8).
- **Success recording.** Candidate bytes and the stage for every success; about 704,000 records, roughly
  75 MB.
- **Audit sample.** Defined by a seed. The audit seed is recorded; the indices are not stored.
- **Overlap audit results** (3.3) and the 30 A2 prefixes, stored in the evidence.
- **Read-only verification command**, with no writes into the evidence directory (review R5).
- **Deterministic ordering** of every list in `analysis.json` (review R4).
- **Off-machine archive** of the sealed evidence, with its manifest hash list committed to the repository in
  the results document (review R3).
- **Environment capture**, with the Python and OpenSSL versions (decision D7).
- **Experiment 001 compatibility.** The new release must verify and re-analyse Experiment 001 evidence with
  identical results. Experiment 001 files are never rewritten.

### 3.11 Economic claims

No economic hypothesis and no economic screen. Throughput may be recorded as descriptive metadata labelled
exploratory. A confirmatory economic claim needs its own predeclared procedure, approved separately.

### 3.12 Workload and resources

| Component | Inputs | SHA-256 compression blocks |
|---|---:|---:|
| A1, A3, N1 (8 B): 3 × 30M | 90.0M | 90.0M |
| A2, N2 (80 B): 2 × 30M | 60.0M | 120.0M |
| P1 (8 B) | 0.2M | 0.2M |
| P2+, P2− (8 B): 2 × 15M | 30.0M | 30.0M |
| **Total** | **180.2M** | **240.2M** |

Time estimates. Assumptions are stated for each line. **Prototype rates come from scratch code**, not
production code, and must be re-measured in the G2 smoke run.

| Step | Basis | Estimate |
|---|---|---|
| SHA-256, 120.2M one-block inputs | Experiment 001 measured 1.50–1.53M hashes/s | about 80 s |
| SHA-256, 60M two-block inputs | not measured; assumed 0.75–1.2M/s | 50–80 s |
| A3 Algorithm S pass (82.1M ranks) | prototype: 10^6 selections in 0.9 s | about 0.5 min |
| A3 unranking, 30M | prototype: about 99,000 per s | about 5 min (optimizable) |
| A1 Vitter's Algorithm D, 30M | not prototyped | 1–5 min. Algorithm S fallback: about 24 min |
| N1 + P, about 60.2M Feistel evaluations | prototype: about 57,000 per s **including** cycle-walking of about 3.3 evaluations each, so about 190,000 per s per evaluation; no cycle-walking on 2^64 | about 5–6 min |
| E001 inverse index check (7M) and re-enumeration | prototype enumeration rates | 1–3 min |
| N2 generation (30M × 80 B) and A2 membership check | BLAKE2b stream | about 1–2 min |
| **Total, single process** | | **about 15–45 min**. Uncertainty about 2×, until measured at G2 |

- **Memory:** under 1 GB. There are no deduplication sets; the exclusion set has 60,721 entries; E001 is
  streamed.
- **Storage:** about 100 MB per attempt (successes about 75 MB, batch log about 5 MB, the rest small).
- **Verifier:** about 0.7M success re-hashes plus about 1.8M audit inputs, which is minutes.
- **The dominant cost is engineering and review** (D8), not compute.

### 3.13 Go / no-go criteria

| Gate | Who | Go when | Otherwise |
|---|---|---|---|
| **G0** Design approval | Architect, then Director | Decisions in section 5 resolved; this document amended | No implementation |
| **G1** Implementation acceptance | Architect review; Director runs tests | See the list below this table | Fix and re-review |
| **G2** Pre-execution | Director | Smoke run passes and its throughput is reported. Dry-run plan shows m = 3, n = 15M per stage, the alpha allocation, the power tables, and the E and D audit results of 3.3. Pre-registration record and empty run registry committed. Clean tree; release tagged; written approval | No attempt |
| **G3** Run validity | Analysis (automatic) | Status complete; integrity passes; P1 detected; at least one P2 detected; neither P2 `WITHIN`; no replicated null-control deviation; audit results recorded and consistent with 3.3 | F2, F3 or F4, per section 3.8 |
| **G4** Post-run decision | Architect and Director | See the outcomes below this table | |

G1 requires all of the following:

- the samplers pass the exactness checks of 3.2.4 on small analogs;
- unranking is a bijection;
- every **M** property is tested;
- the margin rule and the A2 hull rule match reference values;
- the negative-lift control is tested;
- blinding of progress and failure output is verified;
- all existing tests pass;
- Experiment 001 evidence verifies and re-analyses identically.

G4 outcomes:

- **All arms `equivalent-within-margin`.** H_S is falsified for all three populations at ±2%. No-go for any
  scale-up on these populations.
- **Any `REP` label.** Go for artifact investigation and then 002-R. No external claim.
- **Any `inconclusive-at-margin`.** Report the interval. No-go for topping up. A tighter study must be a new
  pre-registered experiment.
- **Any `discordant-requires-investigation`.** Artifact investigation; no scientific reading of that arm.
- **G3 failed.** Section 3.8 applies.

### 3.14 Risks of post hoc selection and misleading claims

| Risk | Mitigation |
|---|---|
| A1 chosen after seeing Experiment 001 | Disclosed; fresh disjoint data; Experiment 001 data never pooled or cited as support |
| Optional stopping, top-ups | Fixed n; no interim looks; registry |
| Seed shopping, selective reruns | Seed committed before any attempt; deterministic reruns; failure classes defined without primary statistics; blinding; a new seed means a new experiment; every attempt disclosed (3.8) |
| Margin or outcome switching | δ, the arms, the tests, the alpha split and the labels are fixed in the plan fingerprint. All arms are reported |
| Sub-population mining (A2 prefixes, A3 weights, bytes) | Secondary family only; Holm; no sub-population claims. Class averages do not bound sub-populations (3.1) |
| Over-claiming equivalence | The wording is fixed: "`ρ` for population U lies within ±2% at `T = 2^248`, `sha256`, this implementation". Never "SHA-256 has no structural bias" |
| Over-claiming deviation | At 30M per arm, tiny artifacts become significant. Every `REP` is a candidate until 002-R |
| Over-generalizing A2 | Clustered design with a stated population (3.2); no claim about real block headers, `sha256d` or other nonce ranges |
| Treating a probabilistic guarantee as exact | Guarantee classes M / E / D / P / C (3.3) |
| Economic misreading | No economic labels |

## 4. Proposed configuration outline (non-executable)

> **Outline only.** This is not a valid HASHLAB configuration. It uses keys the `v0.2.0` schema does not
> support and contains placeholders. Do not copy it into `configs/`.

```text
# OUTLINE ONLY -- NOT A VALID HASHLAB CONFIG -- DO NOT EXECUTE
schema_version: <TBD: 2>
experiment: {id: "002", name: structure-class-margin, specification: docs/experiment-002.md}
engine: sha256                                       # decision D3
target: {equivalent_leading_zero_bits: 8}            # T = 2^248, p0 = 1/256
seeds: {master: <TBD: committed before attempt 1, decision D5>, rng: mt19937, prf: blake2b-keyed}

arms:                                               # primary family, m = 3
  - id: A1-lowint-w8
    population: {encoding: be-bytes, width: 8, range: [2^20, 2^32)}       # |U1| = 4,293,918,720
    sampling: {method: srs-without-replacement, algorithm: vitter-D, split: hypergeometric}
  - id: A2-prefix-nonce-w80
    population: {prefix_bytes: 76, prefix_distribution: uniform, nonce: {bytes: 4, order: little, block: [0, 1000000)}}
    sampling: {method: two-stage-cluster, clusters: 30, prefix_source: blake2b-keyed,
               nonce_assignment: same-block-all-clusters, enumeration: complete-ascending,
               stage_assignment: {discovery: clusters 0-14, validation: clusters 15-29}}
    analysis: {margin_interval: hull(clopper-pearson, cluster-t-29df)}
  - id: A3-lowhw-w8
    population: {width: 8, max_hamming_weight: 6, require_top32_nonzero: true,
                 exclude: experiment-001-candidates}                         # |U3| = 82,068,263
    sampling: {method: srs-without-replacement, algorithm: knuth-S-over-ranks, ranking: weight-then-colex,
               split: hypergeometric}

stages: {discovery: {per_arm: 15000000}, validation: {per_arm: 15000000}}

exclusions:
  experiment_001: {run_id: 20261011T205056Z-exp001-fc1d75fc, method: enumerate-from-sealed-seeds,
                   expected: {A1: 0, A3: 60721, A3_digest: 7c946a93...585c}}
  audits: {mathematical: unit-tested, exact: re-enumerated, deterministic: [n1-p-vs-e001, n2-vs-a2, a2-prefix-distinct],
           probabilistic_reported: [n2-internal-uniqueness]}

controls:
  null:
    - {id: N1-w8, source: feistel64-blake2b, indices: from 0, reject: [A1, A3, E001], per_stage: 15000000}
    - {id: N2-w80, source: blake2b-stream, reject: [A2], per_stage: 15000000}
  positive:                                         # inputs from the N1 permutation, indices >= 2^63
    - {id: P1,       relative_lift: +0.25, inputs: 200000,   detect_alpha_one_sided: 0.001, gate: must-detect}
    - {id: P2-plus,  relative_lift: +0.02, inputs: 15000000, detect_alpha_one_sided: 0.001}
    - {id: P2-minus, relative_lift: -0.02, inputs: 15000000, detect_alpha_one_sided: 0.001}   # new code
  gates: {at_least_one_P2_detected: true, P2_never_WITHIN: true, null_control_replicated: blocking}

statistics:
  alpha_total: 0.01                                 # decision D4 (provisional split below)
  difference: {alpha: 0.005, discovery: holm-two-sided-exact, validation: holm-one-sided-exact}
  margin: {alpha: 0.005, correction: bonferroni, delta_relative: 0.02,          # decision D2
           interval: clopper-pearson, level: 0.996667, data: pooled-discovery-validation}
  classification: difference{NONE,UNREP,REP} x margin{WITHIN,UNDET,BEYOND}   # section 3.4
  secondary: {tests: [leading_zero_bits, first_byte, last_byte, a2_heterogeneity, a3_weight_strata],
              correction: holm, role: exploratory}

execution:
  record_successes: candidate-bytes
  audit: {fraction: 0.01, selection: seeded}
  progress_output: no-primary-counts                # blinding, section 3.8
  run_registry: docs/experiments/002-run-registry.md
economics: {screen: disabled, throughput: descriptive-only}
```

## 5. Decisions required from the Director or Architect

| # | Decision | Engineer's recommendation |
|---|---|---|
| D1 | Primary direction: Option 2, with Option 3 deferred | Approve |
| D2 | Margin `δ` | ±2%. At 30M pooled: P(`WITHIN`) 0.99991 at `ρ = 1`, 0.68 at `ρ = 1.01` |
| D3 | Engine for A2 (`sha256` or `sha256d`) | `sha256` for continuity; `sha256d` as a later experiment |
| D4 | Confirm the provisional alpha split, 0.005 difference + 0.005 margin (total 0.01) | Confirm |
| D5 | How the master seed is chosen and committed (Director-chosen and committed, or a public randomness-beacon value published after the pre-registration commit) | Director-chosen and committed, plus the registry rules of 3.8 |
| D6 | Population definitions: A1 range; A2 prefix length, nonce block `[0, 10^6)` shared by all clusters, 30 clusters; A3 weight cap 6 and exclusion of Experiment 001 candidates | As proposed |
| D7 | Execution environment (keep CPython 3.11.0 / OpenSSL 1.1.1q, or upgrade); the independent SHA-256 implementation for the verifier; whether to do a second-machine full rerun | Keep for the main run; use an independent implementation for the verifier; the second-machine rerun is optional |
| D8 | Implementation scope: exact samplers (Algorithm S; Vitter's Algorithm D); ranking; N1 permutation and inverse index check; A2 cluster design and hull interval; margin rule and the 9-cell classification; negative-lift control; success recording and audit; blinding; read-only verifier; deterministic ordering; run-registry template; schema version 2; release `v0.3.0` | Approve as one reviewed change set |
| D9 | Experiment 001 follow-ups: off-machine archive; update `docs/experiment-001.md` status; optional deterministic re-execution audit | Archive and update the docs |
| D10 | Retry ceiling before escalation (3.8) | 3 attempts of classes F1–F3 |
| D11 | n = 15M per arm per stage (raised from 13M to restore joint power under the 0.005 split) | Approve |

Until these decisions are made, nothing in this proposal is implemented or executed.

## Appendix: reproducing the calculations

All calculations are offline, used no SHA-256 success evaluation, and were run with `python -I -B` from the
session scratch space, outside the repository:

- **Power and margin tables:** implementation A, `hashlab.statistics.inference` at `v0.2.0`; implementation
  B, independent log-space binomial sums and bisection Clopper–Pearson; plus a normal-approximation
  cross-check. A2 uses a Monte Carlo of the hull rule (normal approximation to the per-cluster binomial
  counts; seed 20261011; 40,000 replicates per cell).
- **A3:**
  - cardinality by three methods plus brute-force analogs;
  - exact re-enumeration of the Experiment 001 8-byte candidates from the sealed configuration and seeds
    (generation only; the `random-bytes-w8` stream's keyed BLAKE2b was evaluated to generate candidates,
    with nothing tested against a target);
  - rank/unrank checks;
  - Monte Carlo of the Algorithm S + hypergeometric prototype and of the Feistel alternative.
- **Throughput:** prototype figures come from scratch code on the Director's machine. They are estimates,
  not measurements of production code.
