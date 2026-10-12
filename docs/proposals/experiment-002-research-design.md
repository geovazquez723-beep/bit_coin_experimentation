# Experiment 002: research design proposal

- **Assignment:** Engineering Assignment 004, Part B; revised under Architecture Reviews 002–008
- **Revision:** 7 (Architecture Review 008; workload erratum and verifier accounting). It supersedes revision 6.
  - Removes the obsolete QA2 workload row and separates statistical checks, candidate reconstruction
    and sampled hashing costs (3.9, 3.12). Scientific design remains the accepted `a28c563` baseline.
    Recovery instructions and pending audit-format decisions are in the Review 008 operational note.
  - The Architect provisionally accepts Review 005 and approves the reduced QA2 design. This pass
    confirms thresholds/FWER, execution-path coverage and operational blockers (addendum section 8).
    Documentation finalization and a scoped commit are authorized; implementation and execution are not.
  - Revision 5 independently verifies the fixed A2 decision tails, corrects universal CP-coverage wording
    and outward FWER rounding, replaces 90M-hash QA2 with deterministic fixtures plus <=4,200 small-test
    hashes, and specifies drand pinning, non-discretionary outage handling, independent verification and
    Experiment 001 archival. See addendum section 7 and remediation section 10.
  - Revision 3 adopted **Option B for A2** (3,000 prefixes × nonces `0..9,999`, 1,500 per stage, `sha256`).
  - Revision 4 (Architecture Review 004):
    - distinguishes the observed fraction, the model mean probability and the structural population
      fraction throughout (3.1.1–3.1.2);
    - makes A1 and A3's margin claims **design-based** (3.2.5);
    - corrects and verifies the Hoeffding (1956) citation (3.2, A2);
    - makes the difference claim non-directional;
    - historically reported a combined bound of 0.0083867; revision 5 corrects outward rounding (3.5);
    - specifies the A2 qualification test QA2 (3.7.1);
    - defines the exact seed-commitment and registry procedure (3.8).
  - Changes are mapped in
    [architecture-review-002-remediation.md](../reviews/architecture-review-002-remediation.md) (sections 8–11).
    The statistical basis is in
    [experiment-002-protocol-readiness-addendum.md](../reviews/experiment-002-protocol-readiness-addendum.md).
- **Status:** **PROPOSAL.** Research direction approved in principle. **Protocol freeze, implementation and
  execution are not authorized.** No executable configuration exists, and no execution seed has been
  selected. Nothing in this document changes the frozen `v0.2.0` release or the Experiment 001 evidence.
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

Engine `sha256`, target `T = 2^248`, `p0 = 1/256`.

#### 3.1.1 Three distinct quantities (Architecture Review 004)

The protocol distinguishes three quantities and never substitutes one for another. Write `E_a` for the set
of evaluated inputs of arm `a` (30,000,000 per arm) and `Y_x ∈ {0, 1}` for the SHA-256 success indicator of
input `x`.

| Symbol | Quantity | Nature | Role |
|---|---|---|---|
| **`f_a`** | **Observed success fraction** of the evaluated inputs: `f_a = Σ_{x∈E_a} Y_x / |E_a|`; ratio `f_a / p0` | Known exactly once hashing is done. Deterministic given `E_a` and SHA-256 | The **test statistic**. Always reported. **Never the object of an inferential claim**: there is nothing to infer about a number that has been observed |
| **`μ_a`** | **Model mean probability:** `μ_a = Σ_{x∈E_a} p_x / |E_a|`, where the statistical model treats `Y_x` as independent Bernoulli(`p_x`) with unknown, arbitrary `p_x ∈ [0, 1]`; ratio `ρ_a^mod = μ_a / p0` | A parameter of a **hypothetical** model. SHA-256 is deterministic; the model is HASHLAB's null model with heterogeneity allowed | Object of all **difference** claims (through the strict null `p_x = p0`) and of **A2's confirmatory margin** claim |
| **`θ_a`** | **Structural population fraction:** `θ_a = Σ_{x∈U_a} Y_x / |U_a|` over the whole population `U_a`, most of which is never evaluated; ratio `θ_a / p0` | Deterministic, fixed, unknown | Object of **A1 and A3's confirmatory margin** claims (design-based, 3.2.4). For A2 (`θ_A2 = ρ̄_A2 · p0`) **non-confirmatory** only (3.2, A2) |

#### 3.1.2 Which quantity each element addresses

| Element | A1 | A2 | A3 |
|---|---|---|---|
| Difference null `H0_a` (D and V tests) | model, strict: `p_x = p0` for all `x ∈ U_a` | same | same |
| `REP` / `UNREP` claim | "the strict model null is false for `U_a`"; **direction is a description of `f_a`**, not a claim | same | same |
| Margin decision interval (nominal 99.667%) | for `θ_A1 / p0`, **design-based** (randomness = SRS sampler only; valid for the fixed, deterministic SHA-256) | for `ρ_A2^mod = μ_A2 / p0`, **model-based** (requires independence; any heterogeneity) | for `θ_A3 / p0`, **design-based** |
| `WITHIN` / `BEYOND` claim | `|θ_A1/p0 − 1| < δ` / `≥ δ` | `|ρ_A2^mod − 1| < δ` / `≥ δ` | `|θ_A3/p0 − 1| < δ` / `≥ δ` |
| H_S decision | about `θ_A1` | about `μ_A2` (evaluated inputs, under the model) | about `θ_A3` |
| Population sentence | the claim **is** about the population `U_A1` | "under H-A2, `θ_A2` is also …": non-confirmatory | the claim **is** about `U_A3` |
| `f_a` | reported | reported | reported |

Two consequences:

- A1 and A3 margin claims need **no model of SHA-256**. Their only assumption is that the sampler draws a
  uniform SRS (ideal RNG).
- A2's margin claim, and every difference claim, are statements **within the independent-Bernoulli model**.
  They are only as good as that model's independence assumption, which is HASHLAB's null model and is never
  claimed to be a theorem.

**Research hypothesis under test (falsifiable).** *H_S: for at least one arm, the arm's confirmatory margin
quantity differs from `p0` by at least 2% relative: `|θ_A1/p0 − 1| ≥ 0.02`, `|ρ_A2^mod − 1| ≥ 0.02` or
`|θ_A3/p0 − 1| ≥ 0.02`.*

Each arm has two predeclared analyses:

| Analysis | Hypotheses | Data | Procedure |
|---|---|---|---|
| **Difference** (discovery) | `H0_a`: in the model, `p_x = p0` for every `x ∈ U_a` (strict); `H1_a`: not so | Stage D | exact two-sided binomial; Holm across A1–A3 at **alpha_diff = 0.005** |
| **Difference** (validation) | same null; one-sided, in the direction observed in D | Stage V, only for arms flagged in D | exact one-sided binomial; Holm across the flagged arms at **0.005** |
| **Margin** | interval for the arm's quantity (`θ_a / p0` for A1 and A3; `ρ_A2^mod` for A2), compared with `(1 − δ, 1 + δ)`, `δ = 0.02` | Stages D + V pooled | the decision regions of the two-sided 99.667% (`1 − 2·0.005/3`) Clopper–Pearson interval for A1 and A3; for A2, the hull of Clopper–Pearson and a cluster-level t interval (2,999 df; 3.2). Bonferroni across arms at **alpha_margin = 0.005** |

**Difference vs margin.**

- The difference analysis tests the **strict** model null: every input has probability exactly `p0`.
- The margin analysis bounds an **average** (`θ_a` or `μ_a`).
- If success probability varies between inputs while the average equals `p0`, the strict null is false.
  The difference test may then correctly flag the arm even though the average is null.
- A difference flag therefore means "not every input behaves like Bernoulli(`p0`)". It does **not** mean
  "the average differs from `p0`".
- **Revision 4 change.** The difference claim is non-directional. Its direction only describes `f_a`. A
  directional claim about `μ_a` is not covered by the error budget under heterogeneity (addendum 2.3).

How H_S is decided for each arm (section 3.4 has the full matrix):

- **Falsified** if the margin outcome is `WITHIN`: the interval lies inside `(0.98, 1.02)`.
- **Corroborated, as a candidate only**, if the difference outcome is `REPLICATED` **and** the margin outcome
  is `BEYOND`: the interval lies entirely outside `[0.98, 1.02]`, on one side. This only triggers artifact
  investigation and independent replication (3.9). It never supports a claim of SHA-256 weakness.
- **Not decided** otherwise.

For A2, H_S is decided confirmatorily for `ρ_A2^mod`, the model mean over the evaluated inputs, not for the
observed `f_A2`. A statement about the prefix population `ρ̄_A2 = θ_A2 / p0` is never confirmatory (3.2).

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

#### A2: clustered prefix-and-nonce design (Option B, Architecture Review 003)

A2 is **not** a uniform sample of 80-byte inputs. It is a **two-stage cluster design**: many independently
sampled prefixes, each with a short, completely enumerated nonce block. It supersedes the 30-prefix design
of revision 2.

- **Population:** `U2 = { prefix ‖ LE32(nonce) : prefix ∈ {0..255}^76, 0 ≤ nonce < 10,000 }`.
  - Inputs are 80 bytes, which is two SHA-256 compression blocks. Bytes 64–75 of the prefix and the 4-byte
    nonce lie in the second block.
  - Engine `sha256`, as decided in Architecture Review 003.
- **Prefix sampling (stage 1):** **3,000 prefixes**, drawn independently and uniformly from `{0..255}^76`.
  - Prefix `j` (`j = 0..2,999`) is the first 76 bytes of
    `BLAKE2b-512(key = K_A2, "hashlab-exp002-prefix" ‖ j ‖ 0) ‖ BLAKE2b-512(key = K_A2, … ‖ j ‖ 1)`.
  - `K_A2` derives from the master seed. No seed has been selected.
  - All 3,000 prefixes are stored in the evidence.
  - Pairwise distinctness is **verified deterministically** at plan time. A collision blocks execution; its
    probability is about `C(3000, 2) / 2^608 ≈ 2^-586`.
- **Nonce block assignment (stage 2):** every prefix gets the **same** block `[0, 10,000)`, enumerated
  completely in ascending order. Nonces are not sampled.
- **Clusters to stages:** clusters `j = 0..1,499` form Stage D and `j = 1,500..2,999` form Stage V. Each
  stage has 1,500 × 10,000 = 15,000,000 inputs; the arm has 30,000,000. Prefixes are i.i.d., so this fixed
  assignment is exchangeable with a random one.
- **Applicability of conclusions:**

  | Level | Statement | Status |
  |---|---|---|
  | Observed fraction of the evaluated inputs (`f_A2`) | reported descriptively | **No inferential claim** |
  | Model mean probability of the evaluated inputs (`ρ_A2^mod = μ_A2 / p0`) | A2 margin labels; A2 difference labels (strict model null) | **Confirmatory.** Error bound proven within the independent-Bernoulli model, for any heterogeneity (below) |
  | Prefix population (`ρ̄_A2`), uniformly random 76-byte prefixes, nonces `0..9,999`, `sha256`, 80 bytes | Generalization of a `WITHIN` or `BEYOND` result | **Model-conditional, not confirmatory.** Holds approximately only under assumption H-A2 (below), supported by simulation, not proof |
  | Other nonce ranges or encodings; structured prefixes such as real block headers; `sha256d`; 80-byte inputs in general | none | **Out of scope** |

- **Difference analysis (strict input-level null).**
  - Exact binomial test on each stage total (15M inputs), with the same thresholds as A1 and A3.
  - **Valid under the strict null** whatever the clustering: every input is then Bernoulli(`p0`), so the
    stage total is exactly Binomial(15M, `p0`).
  - Under prefix heterogeneity with average 1, the strict null is false and flags are **correct rejections of
    the strict null**. They are not evidence that the average differs (3.1).
- **Margin analysis.**
  - The decision interval is the **hull** (smallest containing interval) of two intervals:
    - the pooled nominal 99.667% Clopper–Pearson component (fixed classification guarantees below;
      universal heterogeneous confidence-set coverage is not claimed);
    - a cluster-level Student t interval on the 3,000 per-cluster ratios `r_j = k_j / (10^4 · p0)`, with
      **2,999 df** and `t_{0.998333, 2999} = 2.9376`. Cluster sizes are equal, so `mean(r_j)` equals the
      pooled ratio.
  - `WITHIN` requires **both** intervals inside `(0.98, 1.02)`. `BEYOND` requires **both** to lie entirely
    outside `[0.98, 1.02]`, on the same side.
  - Stages are pooled for the margin analysis. A per-stage analysis (1,499 df) is not used.
- **Guarantee for the confirmatory classifications about rho_A2^mod** (addendum 7.1).
  - Conditional on evaluated inputs, S is a sum of 30M independent Bernoulli(p_x) variables, with arbitrary
    fixed probabilities. The CP/t hull classification events are subsets of the CP count events.
  - The verified Hoeffding extremal theorem gives P(S<=d)<=P(B<=d) for d<=n mu-1 and
    P(S>=d)<=P(B>=d) for d>=n mu+1, where B has the same mean. These are pointwise tail results under
    specified conditions, not consequences of convex order. A readable primary source is
    [Bancal and Sekatski, section II, equations (7)-(8)](https://arxiv.org/html/2212.12558).
  - W_HI=118,519 <=119,530.25; W_LO=115,839 >=114,844.75;
    B_HI=120,546 >=119,532.25; B_LO=113,851 <=114,842.75. All four conditions hold and remain valid
    across the relevant false-decision parameter regions. Binomial monotonicity bounds the boundary tails.
  - False WITHIN <=0.0016629396; false BEYOND <=0.0016632432 plus an opposite-side term below 1e-22.
    Use the outward per-arm bound **0.001664**. The t hull cannot enlarge these events.
  - **Coverage wording correction:** CP is a decision component. Its nominal one-sided endpoint
    control can fail for heterogeneous Bernoulli means (addendum 7.1). The n=2 example does not disprove
    full two-sided 1-2alpha coverage; that universal assertion is not established here. The guarantee
    used here is for fixed WITHIN/BEYOND labels, not every reported CP endpoint.
  - This review verifies a cited theorem and derives its application; it does not furnish a self-contained
    proof of the extremal theorem. An elementary Chernoff alternative and its power are in addendum 7.3.
    D15 proposes keeping the rule on this basis; final acceptance is the Architect's decision.
- **No uniform guarantee for the population estimand** (proof by two-point argument; addendum 1.2(4)).
  - A prefix population in which a fraction `π = 0.02/255 ≈ 7.8 × 10⁻⁵` of prefixes succeed on every nonce,
    and all others are exactly null, has `ρ̄_A2 = 1.02`.
  - With probability `(1 − π)^3000 = 0.790`, none of these prefixes is sampled. The data are then distributed
    exactly as under the null.
  - Hence **any** decision rule with P(`WITHIN` | null population) = `w` has P(`WITHIN`) ≥ `w − 0.210` under
    this population. For the proposed rule, `w = 0.9999`, so false `WITHIN` is at least 0.790.
  - Simulation confirms this and shows the failure begins at moderate rarity (addendum 1.3):
    - false `WITHIN` 0.0041 at `π = 0.01` (independent cross-check 0.0038);
    - 0.050 at `π = 0.001`.
- **Assumption H-A2 for population-level statements.** The deviation of per-prefix success rates from the
  population average is **not concentrated in prefixes of prevalence below about 5%**. Under the families
  simulated, the hull's population-level false-`WITHIN` rate is 0.0012–0.0020 (at most about 1.2× the
  nominal 0.00167) and its false-`BEYOND` rate is ≤ 0.0019:
  - homogeneous;
  - normal, heavy-tailed (Student t₃) and lognormal variation up to a relative SD of 0.3;
  - mixtures with prevalence ≥ 5%.

  These are simulation results, not a proof. The population statement is therefore **approximately**, not
  exactly, at the nominal level even when H-A2 holds.

  H-A2 is an assumption about SHA-256's behaviour across prefixes. It **cannot be verified** from 3,000
  clusters. The between-cluster heterogeneity test (secondary) can only reveal gross violations.
- **Secondary (exploratory):** a between-cluster χ² heterogeneity test per stage (1,499 df). **No
  prefix-level claims.**

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

#### 3.2.5 Design-based margin guarantee for A1 and A3 (revision 4)

- **Setting.** For the fixed, deterministic SHA-256, let `K_a = Σ_{x∈U_a} Y_x`, so `θ_a = K_a / N_a`. The
  pooled sample is an SRS of `n = 3 × 10^7` from `U_a`. The pooled count is therefore exactly
  **Hypergeometric(`N_a`, `K_a`, `n`)**, whatever SHA-256 does. No model of the hash function is involved.
- **Monotonicity** (elementary proof).
  `P_{K+1}(X = k) / P_K(X = k) = (K + 1)(N − K − n + k) / ((K + 1 − k)(N − K))` increases in `k`. So the family
  has a monotone likelihood ratio in `K`, and `P_K(X ≤ c)` decreases as `K` grows.
- **Worst cases.**
  - For `θ ≥ 1.02·p0`, every false claim (`WITHIN`, or `BEYOND` on the wrong side) lies inside
    `{X ≤ W_HI}`, and is largest at `K*_hi = ⌈1.02·p0·N⌉`.
  - For interior `θ`, a false `BEYOND`-high lies inside `{X ≥ B_HI}`, largest at `K*_hi − 1`.
  - The low side is symmetric.
  - Evaluated exactly (log-space sums):

  | Arm | `N` | `K*_hi` (`θ/p0`) | sup P(false claim \| θ ≥ 1.02 p0) | sup P(false `BEYOND`-high \| interior θ) | low side | opposite-side term |
  |---|---:|---:|---:|---:|---:|---:|
  | A1 | 4,293,918,720 | 17,108,583 (1.02000004) | 0.0016085 | 0.0016086 | 0.0016012 / 0.0016011 | ≈ 10⁻²² |
  | A3 | 82,068,263 | 326,991 (1.02000083) | 0.0001149 | 0.0001124 | 0.0001117 / 0.0001141 | ≈ 10⁻³⁴ |

- **Result.** Per arm, P(false margin claim about `θ_a`) ≤ 0.0016086 (A1) and ≤ 0.0001149 (A3), for every
  possible SHA-256 behaviour. The only assumption is that the sampler draws an exact SRS (ideal RNG; 3.2.4).
  A3's much smaller value reflects the finite-population correction (sampling fraction 36.6%).

#### Null and positive controls

- **N1, 8-byte null control:**
  - Inputs come from a keyed 64-bit Feistel permutation `π_N` (6 rounds, BLAKE2b round function) applied to
    indices `0, 1, 2, …`.
  - Values in `C1 ∪ C3` (by predicate) or in `E001` are rejected. `E001` rejection works by index: every
    Experiment 001 8-byte candidate is mapped through `π_N⁻¹` at plan time, and the resulting indices are
    skipped.
  - First 15M accepted values go to D, next 15M to V. Uniqueness follows from the bijection.
  - Because N1 is a control, not an inferential arm, its uniformity rests on the PRP heuristic (class C).
- **N2, 80-byte null control, matched to A2's analysis path:**
  - i.i.d. uniform 80-byte strings from a keyed BLAKE2b stream, 15M per stage.
  - The strings are grouped, in stream order, into **pseudo-clusters of 10,000** (1,500 per stage).
  - N2 is analysed with **exactly A2's procedures**: the stage-total difference tests and the hull margin rule
    with the cluster t interval on 2,999 df. N2 therefore exercises the A2 analysis code on null data.
  - Any string equal to an A2 input is rejected. The check is deterministic: do the first 76 bytes match one
    of the 3,000 prefixes, with a little-endian nonce below 10,000.
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
| A2 clusters and stages | **D**, then **M** | 3,000 prefixes verified pairwise distinct (D); distinct prefixes, or the same prefix with distinct nonces, give distinct inputs (M) |
| N2 vs A2 | **D** | membership check of every N2 input against the 3,000 prefixes and nonces `0..9,999`; hits rejected and counted |
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

- **Quantities.** `REP` and `UNREP` refer to the strict model null (all arms). `WITHIN` and `BEYOND` refer to
  `θ_a` for A1 and A3 and to `ρ_A2^mod` for A2 (3.1.2). Every label is reported together with the observed
  ratio `f_a / p0`, as a description.
- **`REP` with `WITHIN` is not a contradiction.** It means the strict null (every `p_x = p0`) was rejected
  **and** the arm's average quantity is within 2% of `p0`: a detectable deviation smaller than the margin. Both findings are reported. H_S is
  falsified for that arm, yet the deviation still goes to artifact investigation and 002-R. If genuine, any
  replicated deviation would be of scientific interest.
- **Discordant cells** (`BEYOND` without replication) are nearly impossible under any true `ρ`. At
  `|ρ − 1| ≥ 2.5%`, discovery power is at least 0.998, while `BEYOND` needs `|ρ̂ − 1| ≥ 2.87%`. These cells
  therefore indicate an artifact, such as inconsistency between stages. They support no H_S statement and
  trigger investigation.
- **Every `REP` label** goes to artifact investigation and then Experiment 002-R before any statement
  stronger than "candidate deviation, unconfirmed".
- **No label** implies a cryptographic weakness or an economic advantage.
- **A2 reading.** The same 9 cells apply, with two differences:
  - The difference outcome refers to the **strict input-level null**. `REP` means "not every evaluated input
    behaves like Bernoulli(`p0`)".
  - The margin outcome refers to **`ρ_A2^mod`**: the model mean probability of the evaluated inputs, not their
    observed fraction `f_A2`.

  Every A2 label is reported with the qualifier `estimand: model-mean-of-evaluated-inputs`. A population-level sentence may
  be added only in the form "under assumption H-A2, the prefix population average `ρ̄_A2` is also within ±2%"
  (or beyond it), and it is never part of the confirmatory result. A2 `REP` with `WITHIN` is consistent with
  between-prefix heterogeneity around an average near 1. It is reported as such and still goes to artifact
  investigation.

### 3.5 Error budget and multiple testing

| Family | Size | Method | Budget |
|---|---:|---|---|
| Difference (discovery, then validation) | 3 | Holm two-sided in D; Holm one-sided in V among flagged | **0.005**. A false `REP` claim needs a false discovery, so P(any false `REP`) ≤ 0.005 under strong FWER control |
| Margin (`WITHIN` / `BEYOND`) | 3 | Bonferroni: one two-sided 99.667% interval per arm | **0.005** budgeted. Outward per-arm bounds including opposite-side tails: A1 <0.001609 (design-based), A2 <0.001664 (model-based), A3 <0.000115 (design-based). Sum <0.003388; reported as **<=0.003389** |
| **Combined primary claims** | | union bound over the two families | **≤ 0.005 + 0.003389 = 0.008389 ≤ 0.01**, under the conditions below |
| Secondary (leading-zero bits, first byte, last byte per arm and stage; A2 heterogeneity; A3 weight strata) | | Holm within the family | exploratory; never changes a label |
| Controls | | individual thresholds (3.7) | gates or diagnostics, outside the primary budget |

For A2, the guarantee is for the specified classification events, not universal CP confidence-set
coverage. The 0.005 / 0.005 split is the Architect's provisional allocation (decision D4).

**Conditions of the 0.01 guarantee** (formal argument: addendum section 2). The bound is a union bound in
one joint probability space: the sampler's randomness, plus outcomes `Y_x` that are independent
Bernoulli(`p_x`) with arbitrary `p_x`.

- **Difference claims, all arms (model-based).** Under the strict null `H0_a`, each stage total is exactly
  Binomial(15M, `p0`), so every test has its exact size, and Holm gives FWER ≤ 0.005 (0.0049599 at the
  global null).
- **A1 and A3 margin claims about `θ_a` (design-based).** Hold conditionally on every realization of the
  `Y_x`, hence also in the joint space, and also **without any model** (3.2.5).
- **A2 margin claims about `ρ_A2^mod` (model-based).** Bounded by the binomial values via Hoeffding (1956)
  for any heterogeneity, given independence (3.2, A2).
- **Model-free reading.** If SHA-256 is treated as a fixed function with no probability model, only the A1
  and A3 margin claims keep a frequentist guarantee (outward bound <0.001724 combined). Difference claims
  and A2 margin claims are then model statements and have no frequentist meaning.
- **Excluded from the guarantee:**
  - A2 statements about the prefix population `θ_A2` (no uniform bound exists; H-A2, simulation only);
  - directional readings of `REP` (the direction describes `f_a` only);
  - secondary tests and controls, including the A2 qualification test (3.7.1);
  - Experiment 002-R;
  - any attempt beyond a single confirmatory attempt (3.8).

### 3.6 Sample size and power

**Assumptions.**

- Under the null, distinct inputs are independent Bernoulli(`p0`) trials.
- A1 and A3 are finite-population SRS designs (sampling fractions 0.7% and 36.6%). The finite-population
  variance has factor 1-f; variance reduction alone does not prove tail domination or uniform power
  ordering. Fixed decision size is checked directly by hypergeometric tails (addendum 7.2). Binomial
  power tables below are model planning calculations, not exact design-based population power.
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

**A2 (Option B), recalculated.** Simulation evidence, not proof. Direct simulation with exact per-cluster
Binomial(10⁴, `p_j`) counts and the full procedure. Full tables are in addendum 1.3.

- **Homogeneous prefixes** (no between-prefix variation).
  - The stage totals are exactly Binomial(15M), so difference power equals A1 and A3 exactly: discovery
    0.954 / 0.958 at ±2%.
  - Simulated discovery and replication with a single arm flagged: 0.941 / 0.947.
  - `WITHIN` power at `ρ` = 1 / 1.005 / 1.01 / 1.015: 0.99993 / 0.986 / 0.673 / 0.108. That is slightly
    below A1 and A3, because the t interval must also lie inside.
  - `BEYOND` power at 1.025 / 1.03 / 1.035: 0.102 / 0.665 / 0.984.
- **Heterogeneous prefixes:** **power is not unchanged.**

  | Model (relative between-prefix SD) | P(`WITHIN`) at `ρ̄` = 1.000 / 1.005 / 1.010 | P(`REP`), single arm, at `ρ̄` = 1.02 |
  |---|---|---:|
  | normal, τ = 0.05 | 0.9998 / 0.974 / 0.624 | 0.930 |
  | normal, τ = 0.10 | 0.995 / 0.918 / 0.483 | 0.895 |
  | lognormal, τ = 0.30 | **0.223** / 0.170 / 0.066 | 0.670 |
  | mixture, 1% of prefixes carry the effect | 0.9999 / 0.972 / 0.486 | 0.791 |

  Strong heterogeneity widens the cluster t interval, so `WITHIN` becomes hard to reach. Such an outcome is
  reported as `inconclusive-at-margin`, not as a failure.
- **Operating characteristics at the margin** (population level; 120,000 replicates; SE ≈ 0.00012):
  - false `WITHIN` at `ρ̄ = 1.02 / 0.98` is **0.0012–0.0020** for homogeneous, normal, t₃ and lognormal
    variation, and for mixtures with prevalence ≥ 5%;
  - it is **0.0041** at 1% prevalence, **0.050** at 0.1%, and **0.74–0.79** at 0.01% and below;
  - false `BEYOND` at `ρ̄ = 1.0199 / 0.9801` is ≤ 0.0019 in every model.
- **Errors about the confirmatory estimand `ρ_A2^mod`** stay at or below the proven bound in every model.

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
| **N1, N2** | Detect artifacts specific to input length, sampler or (N2) the A2 cluster analysis path | Tested exactly like arms; N2 with A2's procedures on 3,000 pseudo-clusters (D: two-sided 0.001667; V: one-sided 0.005). Flagged in D: non-blocking diagnostic. **Flagged in D and replicated in V: gate failure F4** (3.8). Margin not `WITHIN`: diagnostic (expected about 10⁻⁴) |
| **Overlap and exclusion audit** | Unit independence | **Gate** per section 3.3 |

P2− requires a new negative-lift mode in the control engine. The current control supports positive lifts
only.

#### 3.7.1 A2 engineering qualification QA2 (design approved in Review 006; D13)

This specification replaces the 90M-hash QA2 proposal. **Do not implement or run it under this review.**
QA2 is deterministic engineering qualification, completed after G1 and before C_pre. It makes no
confirmatory claim and does not estimate power. There is no probabilistic pass criterion or seed search.
The production geometry remains 3,000 clusters, 10,000 trials per cluster, 1,500 clusters per stage.

**Statistical fixtures (zero candidate hashes).** Commit explicit arrays of 3,000 integer cluster counts,
stage assignments, geometry, alpha, expected intermediate statistics and expected final labels. Expected
answers must come from an independent reference calculation, not snapshots of the implementation under
qualification. Fixtures are synthetic counts, never represented as actual SHA-256 observations.

| Fixture family | Required cases and assertions |
|---|---|
| Null | Balanced counts 39/40, pooled total 117,188, balanced D/V; no discovery, WITHIN, hence no REP |
| Positive and negative | Balanced counts 42/43 (mean ratio about 1.08) and 35/36 (about 0.91); REP with descriptive high/low direction, BEYOND on the corresponding side |
| Heterogeneous | Same pooled total and D/V totals as null, but 2,250 zero counts and 750 counts 156/157, distributed in both stages; CP WITHIN, t not WITHIN, hull inconclusive. Equal totals must not erase cluster variance. Also concentrated positive/negative fixtures |
| Boundary | Each CP total 113,851; 115,839; 118,519; 120,546, and each adjacent integer. Distribute evenly to isolate CP; separately vary cluster dispersion at fixed totals to cross the t boundary. Exact endpoint equality is inconclusive for strict WITHIN/BEYOND interval comparisons |
| Difference boundaries | Discovery two-sided p-value and each validation Holm level (1, 2, 3 flagged arms): critical count and adjacent integers, both directions; Holm ordering and tied p-values across three arms |
| Contradictory | Significant D-high / V-low, D-low / V-high, D-only, V-only, REP with WITHIN, and CP/t disagreement. Cover all nine difference-by-margin cells with independently derived labels; contradictory directions cannot produce REP |
| Degenerate / invalid | All-zero and all-10,000 counts; zero cluster variance (t interval collapses to the mean); missing/duplicate cluster ids, wrong stages, unequal geometry, fractional/negative/out-of-range counts and total mismatches must fail validation |

Fixture generation may solve for suitable integer arrays offline before qualification; commit the final
arrays and reference results before testing production code. Include t-boundary bracketing fixtures with
reference endpoints on either side; do not silently round endpoints into equality. Ties use the exact
protocol comparison. Test byte-order and stage-boundary errors explicitly. Include null and concentrated-cluster cases
for the secondary dispersion path; independently verify its predeclared statistic, df and p-value.

**Independent recomputation.** A separately authored verifier must read the fixture/evidence counts,
without importing HASHLAB inference, aggregation or classification code. Recompute stage sums, pooled
sum, sum of squares, cluster mean/variance, t interval (2,999 df), CP endpoints, exact binomial tests,
Holm decisions, hull endpoints, per-stage secondary dispersion statistics/df/p-values, and all nine labels. Counts, ordering, directions and labels must match
exactly. Numerical agreement: absolute error <= 1e-10 for p-values and ratio endpoints; additionally
compare discrete critical counts against high-precision references. If numerical uncertainty straddles a
cutoff, qualification fails pending a higher-precision calculation; tolerance cannot excuse a label error.

**Small hashing integration test.** Fixed, visibly non-confirmatory fixture key; 8 distinct 76-byte
prefixes, nonces 0..255, 4 prefixes per stage: **2,048 candidate SHA-256 evaluations**. Use actual candidate
generation, 80-byte encoding, SHA-256, strict digest < 2^248, cluster/stage aggregation, success recording,
serialization, sealing and read-only verification. A separate implementation checks every candidate and
digest (another 2,048 evaluations). Include known-answer SHA-256 vectors, nonce endian checks at
0, 1, 255, 256, 9,999 and 2^32-1, and reject nonce 2^32. Do not enlarge this test to obtain a statistical
outcome; it has no margin or power acceptance criterion. Full geometry is exercised by synthetic fixtures.
Budget <= 4,200 candidate/known-answer SHA-256 evaluations plus small file-integrity hashes.

**Complete-path requirement (Review 006).** Use the same production orchestration/entry point and
plan/configuration validation, generator, engine, accounting, evidence serializer/sealer and read-only
verifier paths. Only geometry and non-confirmatory fixture identity differ. Bind the resolved
configuration, plan, environment and qualification Q-entry to the evidence. A separate miniature harness
that bypasses those production paths cannot pass QA2. Synthetic fixtures enter the statistical path via
a documented test adapter and cover all nine cells at full geometry; they cannot replace the hashing
integration test. Include strict target-comparison probes at digest integers 0, T-1, T, T+1 and 2^256-1
without searching for matching candidate hashes. The 4,096 main/independent evaluations leave 104 for
known-answer/boundary probes and any additional candidate rehashes; itemize and enforce the total cap.
Malformed/tampered evidence must fail validation before unnecessary candidate rehashing. This confirms
coverage in the specification, not successful qualification or production-scale performance.

**Tamper tests and pass/fail.** Mutate copies only: a byte in a candidate/digest/count, truncate a file,
remove/duplicate a cluster, change stage mapping, add an unlisted file, change manifest metadata, and
rewrite both a payload and its local manifest. Each must be rejected by integrity/consistency checks;
the last case must be rejected against an externally pinned manifest digest. Original fixtures remain
unchanged. PASS requires every reference label and integer statistic to match, all numerical tolerances
to pass, every digest/encoding to match, and every invalid/tamper case to fail closed. Any failure blocks
qualification. A defect is diagnosed and corrected; repeat the same fixtures, retain all Q entries and
reports. No randomized retry-until-pass rule. After an attempt begins, requalification is allowed only
under the existing amendment policy and cannot justify repeating a valid attempt.

**Power is separate.** Analytical tails and explicitly modelled power calculations belong in the
statistical review (addendum 7), never in the QA2 pass gate. Historical QA2 simulations are not acceptance
probabilities for this deterministic replacement. No per-prefix biased hashing engine is required solely
for QA2. Existing confirmatory controls P1/P2/N1/N2 remain as proposed.

### 3.8 Seeds, run attempts and retry policy (pre-registered)

**Seed commitment procedure** (revision 4). This defines the procedure only: **no execution seed has been
generated**, and the beacon source is decision D5. The aim is that nobody, including the Director, can know
the seed before the protocol and code are irrevocably fixed, so seeds cannot be screened in advance.

| Step | Action | Recorded in |
|---|---|---|
| **S1. Freeze** | G1 passed and QA2 passed. The code is tagged as the release candidate. The confirmatory configuration is complete **except** `seeds.master: derived-from-beacon`. Compute the configuration SHA-256 and the seedless plan fingerprint (the plan with the seed field set to the placeholder) | pre-registration record |
| **S2. Pre-registration commit `C_pre`** | Commit the pre-registration record: code commit and tag, configuration SHA-256, seedless plan fingerprint, A3 exclusion digest, QA2 evidence manifest hashes, the beacon specification (source, the **reveal round `R*`** as an explicit number, retrieval URL, verification method), and the derivation formula below | git commit `C_pre` |
| **S3. External witness** | Before `R*` is published, `C_pre`'s commit hash is sent to the Architect, or pushed with Director approval. This establishes that the commitment predates the beacon value. `R*` must be at least 24 h after the witness time | the Architect's acknowledgement, quoted in the seed record |
| **S4. Reveal and derive** | After `R*` is published: `master = int.from_bytes(SHA-256("hashlab-exp002-master-v1|" + C_pre + "|" + str(R*) + "|" + beacon_randomness_hex)[:8], "big")`. If `R*` is unavailable, wait for that exact round; only transport fallback is allowed (3.8.1) | seed record |
| **S5. Seed record commit `C_seed`** | Commit the beacon round, its randomness and signature (or the beacon's verification data), the derived master seed, the full plan fingerprint and the configuration SHA-256 with the seed inserted. Anyone can recompute S4 | git commit `C_seed` |
| **S6. Attempt** | Registry entry `A1` committed (below), then `hashlab run` | registry |

Sub-seeds, permutation keys and the A2 prefix key derive from the master seed with the existing
domain-separated `derive_seed`. Smoke runs (`S` entries) and QA2 (`Q` entries) use labels distinct from
`hashlab-exp002-master-v1` and are fixed before `C_pre`. Their labels cannot select the confirmatory stream; distinct labels do not mathematically guarantee
unequal finite seed values. QA2 no longer needs random qualification draws.

**Attempt registry procedure.**

- **File.** `docs/experiments/002-run-registry.md` is initialized before the first smoke/qualification
  entry; C_pre binds its existing history/tip. It is append-only, and every change is its own commit,
  so initial S/Q entries precede C_pre and git history is the audit trail.
- **Entry types:**
  - `S` (smoke) and initial `Q` (qualification), allowed only before `C_pre`; amendment requalification Q
    entries are allowed later only when explicitly required by an approved F1/F3 amendment;
  - `A` (confirmatory attempt), allowed only after `C_seed`, numbered `A1, A2, …` without gaps.
- **Before each run:** commit a `started` entry with:
  - entry id and UTC time;
  - code commit;
  - configuration SHA-256;
  - full plan fingerprint;
  - the exact command line.

  The `started` entry's commit hash is passed to the harness and written into the run's `environment.json`.
  This binds the evidence to the entry (implementation item).
- **After each run:** commit a `result` entry with the run id, status, failure class (3.8) or `valid`, and the
  manifest SHA-256.
- **Completeness audit (at G4).** Every evidence directory whose configuration hash equals the confirmatory
  configuration must appear in the registry, and every `A` entry must have a sealed evidence directory or a
  recorded F1 crash.
- **Determinism closes the remaining gap.** An unregistered private run would reproduce the registered
  run's results exactly, because the seed and code are fixed. It could change nothing except by a code
  change, and every code change after `C_pre` requires an amendment with Architect review of the diff and
  re-qualification.
- No entry is ever deleted, and no sealed evidence directory is ever deleted.

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

#### 3.8.1 Proposed beacon pin and deterministic fallback (D5; review required)

Use drand **mainnet quicknet**, not quicknet-t or an automatically selected default chain. The
[official quicknet announcement](https://docs.drand.love/blog/2023/10/16/quicknet-is-live/)
and [protocol specification](https://docs.drand.love/docs/specification/) were checked on 2026-10-11.
Pin the following tuple in C_pre:

- chain hash: 52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971;
- scheme: bls-unchained-g1-rfc9380; beacon id: quicknet;
- period: 3 seconds; genesis Unix time: 1692803367;
- public key (96-byte G2, lowercase hex):
  83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a.

**Verification status:** this tuple matches official published documentation. The live chain /info
endpoint could not be retrieved in this review. Current service availability and agreement of live
/info with this pin **require confirmation before freeze**. No public round value was retrieved and
no execution seed was derived. Archive the exact /info bytes and independently verify the chain hash
from the pinned information, rather than trusting a relay's self-asserted hash.

Use a reviewed, version-pinned client supporting the exact RFC9380 scheme, with verification enabled
and chain hash/public key pinned. The [official client](https://github.com/drand/drand-client) and
[scheme implementation](https://github.com/drand/drand/blob/master/crypto/schemes.go) are starting
points; an immutable revision, dependencies and successful historical verification vectors must be
pinned before freeze. Validate the requested round, signature encoding/subgroup membership, scheme-specific
BLS signature over SHA-256(uint64-big-endian(round)) (48-byte G1 signature, RFC9380 G1 domain) and randomness=SHA-256(decoded signature). Quicknet is unchained:
previous_signature is not a trust anchor. Checking randomness against signature alone is insufficient.
Reject wrong chain, wrong round, bad signature or malformed randomness; archive raw responses and checks.

**Witness and round selection.** C_pre names one explicit future positive integer R* and its scheduled
time genesis+(R*-1)*3. An independent timestamped witness must acknowledge the full C_pre hash at least
24 hours before that time. C_pre binds code, complete seedless configuration, QA2 references, derivation,
chain pin and outage rule; the witness retains the record off-machine. If the witness deadline is missed,
that commitment is ineligible: halt and record the failure, rather than opportunistically selecting a
later value under it. A replacement precommitment requires Architect review and full disclosure.

**Byte-exact derivation (preserves S4 v1).** Hash UTF-8/ASCII bytes, no BOM, spaces or terminal newline:

    hashlab-exp002-master-v1|<C_pre>|<R*>|<randomness_hex>

C_pre is the full lowercase 40-character git commit id (current repository object format); R* is unsigned
base-10 with no leading zeros; randomness_hex is exactly 64 lowercase hex characters from the verified
32-byte randomness. SHA-256 returns 32 bytes; take the first eight **raw bytes**, interpret unsigned
big-endian (0..2^64-1). Do not slice hex characters or reduce modulo a smaller range. The seedless
configuration must preserve this uint64 exactly; test JSON/JavaScript precision loss above 2^53 in
qualification. Sub-seeds use the existing frozen domain-separated derive_seed specification. Other git
object formats need a reviewed derivation amendment. C_pre does not contain its own hash: the later seed
record names it. No execution seed is generated by this document.

**Outage/fallback rule.** Replace the former next-published-round policy. The target remains R* forever.
Query https://api.drand.sh/<chain-hash>/public/<R*>; alternate transport is
https://api2.drand.sh/<chain-hash>/public/<R*> (availability checked before freeze). A verified cached
response for exactly the same round is also acceptable. Retry these fixed relays in order; logging
failure and delay never changes the round, chain, code, derivation or seed. Relay disagreement or a
verification error halts derivation for independent investigation. If unavailable, wait indefinitely,
recording an outage after 24 h; there is **no alternate round or alternate beacon**. Permanent loss
leaves this experiment unexecuted. A replacement is a separately approved experiment with disclosure
of this abandoned commitment, not an F1-F3 retry. This policy trades liveness for freedom from selective
round choice. Anyone may supply the uniquely verifying R* response; nobody may select a replacement
value based on observed candidate results or seed preferences.

#### 3.8.2 Minimum independent verifier (D7; specification only)

Before freeze, appoint a reviewer/author independent of the main implementation, pin the verifier source
revision and environment, and qualify it against QA2 fixtures. It must run read-only from an off-machine
copy and must not import HASHLAB statistical, aggregation or classification functions. A generic crypto
or numerical dependency is acceptable if separately pinned and its known-answer vectors are checked.

Minimum checks:

1. Anchor the manifest digest to the independent witness; verify every listed file hash/size, manifest
   self-hash, schema, expected inventory and absence of extra/unlisted evidence. Reject path traversal,
   missing/truncated files, duplicates, invalid integers, NaN/infinity and inconsistent status.
2. Verify C_pre, its timing, chain pin, beacon signature/round, seed derivation, configuration/plan hashes,
   code revision, registry binding, all attempts, amendments and final-attempt eligibility.
3. Recompute all per-cluster/stage/arm totals, denominators, success-record counts and cluster moments;
   verify exact 3,000-by-10,000 geometry, stages, prefix uniqueness, nonce bounds, success membership,
   exclusions and overlap evidence. Recompute every stored successful digest with an independent SHA-256
   implementation and check digest < target and candidate encoding.
4. Independently recompute exact tests, Holm, CP critical counts/endpoints, t statistics/df/endpoints,
   hull, nine-cell labels, controls/gates, failure classes and claim scope. Use QA2's tolerances and
   fail closed near unresolved numerical boundaries; classifications and integer counts match exactly.
5. Produce a separate signed or independently witnessed report with input manifest digest, verifier
   revision, environment, checks, discrepancies and explicit limitations; never alter sealed evidence.

Rehashing successes checks positive records but **cannot establish absence of omitted successes**.
Minimal evidence/statistical verification must state that limitation. Candidate-generation correctness
and completeness require independent full regeneration and rehashing of all evaluated candidates (a
separate audit requiring authorization), or an explicitly approved stronger evidence scheme. A sampled
audit is diagnostic, not a proof of all 180.2M outcomes. Freeze must decide whether minimal verification
or a full audit is required and who will perform it; no audit execution is authorized here.

#### 3.8.3 Off-machine archival of Experiment 001 (D9; proposed, not performed)

Keep the sealed run 20261011T205056Z-exp001-fc1d75fc and v0.2.0 untouched. Director/custodian procedure:

1. Verify its nine payload hashes and byte sizes, manifest self-hash and 11-file inventory read-only.
   Record the run id, complete manifest digest, tag object id and dereferenced code commit in an external
   inventory. The review's checked digest is recorded in addendum 7.4.
2. Copy exact bytes to an archive staging location outside the sealed directory. Include the 11 evidence
   files, a repository bundle containing v0.2.0 and its reachable history, reproduction documentation,
   dependencies/environment records available from that release, and the separate inventory. Do not
   regenerate results or add analyses inside the original. Give the outer archive its own hash inventory.
3. Transfer to two independent off-machine destinations: an institutional/object-store immutable copy
   with retention/versioning and an offline/removable copy held by another custodian. Check access and
   retention policy with the Director; record receipts, destination identifiers and UTC timestamps.
4. At each destination, independently recompute archive and per-file hashes. Sign or timestamp the
   manifest digest/inventory through a witness retained outside both the source and archive account.
   A local manifest rewritten alongside payloads is not an authenticity anchor.
5. Restore a copy to a separate directory and reverify inventory, hashes and repository tag/commit.
   Record a periodic annual read/restore check and retain prior inventories. Only then mark archival
   complete; report failures and repair copies from verified bytes without touching the source.

Current status: local integrity verified; no transfer, external receipt or restore test was performed by
this review. Destination, custodian and retention selection remain D9 decisions.

### 3.9 Independent replication

1. **Computational reproducibility (always).** After sealing, an independent verifier recomputes:
   - every recorded success (candidate bytes are stored);
   - a seeded 1% audit sample of the other inputs.

   It uses a different SHA-256 implementation (for example another OpenSSL major version or a reference
   implementation) and an independent reimplementation of the samplers for the audit sample. On the
   Director's decision, a full deterministic rerun on a second machine must reproduce every count exactly.
   Statistical verification separately reproduces stored-count calculations without candidate hashing.
   Audit reconstruction needs the frozen generator order, arm/stage denominators, recorded-success
   indices, audit seed and a byte-exact sampling format. The proposed format, candidate replay cost
   and limitations are documented in [Review 008](../reviews/architecture-review-008-operational-recovery.md).
   Its format and audit-seed provenance must be approved before freeze; no audit seed is selected here.
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
- **Overlap audit results** (3.3), the 3,000 A2 prefixes, and the 3,000 A2 and 3,000 N2 per-cluster success
  counts, stored in the evidence. The per-cluster counts are needed to recompute the cluster t interval
  independently.
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
| *Separate, before freeze:* QA2 end-to-end/known-answer tests (3.7.1) | *<=4,200 hashes* | *<=8,400 blocks if all probes <=80 B* |
| *Separate, before freeze:* QA2 synthetic statistical fixtures (3.7.1) | *0 candidate hashes* | *0 candidate-hash blocks* |

The confirmatory totals exclude qualification, independent verification and small file-integrity hashes.
QA2 includes both 2,048 execution hashes and 2,048 independent re-hashes (4,096), plus at most 104
known-answer/boundary evaluations. The two-block allowance assumes all probe inputs are also <=80 B;
QA2 3.7.1 does not mandate vector lengths, so itemize their actual compression blocks.
Confirmatory execution plus the QA2 cap is <=180,204,200 candidate/known-answer hashes.
It is <=240,208,400 compression blocks only under that probe-length assumption, excluding
file-integrity hashes and verifier work. Longer known-answer vectors need separate block accounting.

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
| N2 generation (30M × 80 B) and A2 membership check (3,000 prefixes) | BLAKE2b stream | about 1–2 min |
| A2 input construction (3,000 prefixes × 10,000 nonces) | concatenation; 3,000 BLAKE2b prefix derivations | under 1 min |
| **Total, single process** | | **about 15–45 min**. Uncertainty about 2×, until measured at G2 |

- **Memory:** under 1 GB. There are no deduplication sets; the exclusion set has 60,721 entries; E001 is
  streamed.
- **Storage:** about 100 MB per attempt (successes about 75 MB, batch log about 5 MB, the rest small).
- **Verifier:** statistical recomputation needs no candidate hashing. For `s` recorded successes among
  180.2M inputs, re-hash all `s` and sample about 1% of the remaining 180.2M - `s` inputs. At the
  illustrative `s` = 704,000, this is about 1,794,960 sampled non-successes and 2,498,960 total
  candidate re-hashes, about 3.33M compression blocks if successes are spread proportionally by
  input width. These are workload estimates, not a success-count guarantee. Candidate reconstruction
  may replay up to the complete 180.2M-input generation stream, plus exclusion/overlap work; sparse
  hashing does not imply sparse generation. Audit-index generation, file-integrity checks and I/O
  are additional costs. No verifier wall-time guarantee is made before implementation measurements.
  See 3.9 and the Review 008 operational note for deterministic audit reconstruction and assurance.
- **The dominant cost is engineering and review** (D8), not compute.

### 3.13 Go / no-go criteria

| Gate | Who | Go when | Otherwise |
|---|---|---|---|
| **G0** Design approval | Architect, then Director | Decisions in section 5 resolved; this document amended | No implementation |
| **G1** Implementation acceptance | Architect review; Director runs tests | See the list below this table | Fix and re-review |
| **G2** Pre-execution | Director | Smoke run passes and its throughput is reported. **QA2 passes** on the release-candidate commit (3.7.1). Dry-run plan shows m = 3, n = 15M per stage, the alpha allocation, the power tables, and the E and D audit results of 3.3. Seed procedure S1–S5 completed: `C_pre` witnessed before `R*`, `C_seed` committed. Clean tree; release tagged; written approval | No attempt |
| **G3** Run validity | Analysis (automatic) | Status complete; integrity passes; P1 detected; at least one P2 detected; neither P2 `WITHIN`; no replicated null-control deviation; audit results recorded and consistent with 3.3 | F2, F3 or F4, per section 3.8 |
| **G4** Post-run decision | Architect and Director | See the outcomes below this table | |

G1 requires all of the following:

- the samplers pass the exactness checks of 3.2.4 on small analogs;
- unranking is a bijection;
- every **M** property is tested;
- the margin rule and the A2 hull rule (2,999 df) match reference values. The A2 per-cluster aggregation is
  tested on synthetic counts against an independent recomputation;
- the negative-lift control is tested;
- blinding of progress and failure output is verified;
- all existing tests pass;
- Experiment 001 evidence verifies and re-analyses identically.

G4 outcomes:

- **All arms `equivalent-within-margin`.** H_S is falsified for the three confirmatory estimands at ±2%
  (A1/A3 population fractions; A2 evaluated-input model mean). No-go for any
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
| Over-claiming equivalence | The wording names the arm's confirmatory estimand: A1/A3 population fraction or A2 evaluated-input model mean, within ±2% at `T = 2^248`, `sha256`, this implementation. Never "SHA-256 has no structural bias" |
| Over-claiming deviation | At 30M per arm, tiny artifacts become significant. Every `REP` is a candidate until 002-R |
| Over-generalizing A2 | Clustered design with a stated population (3.2). Confirmatory claims refer to the evaluated inputs only; population statements are labelled model-conditional (H-A2). No claim about real block headers, `sha256d` or other nonce ranges |
| Reading an A2 difference flag as an average effect | Stated distinction (3.1, 3.2): the A2 difference test rejects the strict input-level null; average-level statements come only from the margin analysis |
| Treating a probabilistic guarantee as exact | Guarantee classes M / E / D / P / C (3.3) |
| Economic misreading | No economic labels |

## 4. Proposed configuration outline (non-executable)

> **Outline only.** This is not a valid HASHLAB configuration. It uses keys the `v0.2.0` schema does not
> support and contains placeholders. Do not copy it into `configs/`.

```text
# OUTLINE ONLY -- NOT A VALID HASHLAB CONFIG -- DO NOT EXECUTE
schema_version: <TBD: 2>
experiment: {id: "002", name: structure-class-margin, specification: docs/experiment-002.md}
engine: sha256                                       # decided, Architecture Review 003
target: {equivalent_leading_zero_bits: 8}            # T = 2^248, p0 = 1/256
seeds: {master: derived-from-beacon,                 # 3.8 S1-S5; NOT generated; beacon source = decision D5
        derivation: "SHA-256('hashlab-exp002-master-v1|' + C_pre + '|' + R* + '|' + beacon_hex)[:8]",
        rng: mt19937, prf: blake2b-keyed}
quantities: {A1: theta (design-based), A2: model-mean (rho_mod), A3: theta (design-based),
             all_arms_difference: strict-model-null, observed_fraction: reported-not-inferred}
qualification: {config: separate (002-qual-a2), results_root: results-qual/, before: C_pre}   # 3.7.1

arms:                                               # primary family, m = 3
  - id: A1-lowint-w8
    population: {encoding: be-bytes, width: 8, range: [2^20, 2^32)}       # |U1| = 4,293,918,720
    sampling: {method: srs-without-replacement, algorithm: vitter-D, split: hypergeometric}
  - id: A2-prefix-nonce-w80
    population: {prefix_bytes: 76, prefix_distribution: uniform, nonce: {bytes: 4, order: little, block: [0, 10000)}}
    sampling: {method: two-stage-cluster, clusters: 3000, nonces_per_cluster: 10000, prefix_source: blake2b-keyed,
               nonce_assignment: same-block-all-clusters, enumeration: complete-ascending,
               stage_assignment: {discovery: clusters 0-1499, validation: clusters 1500-2999}}
    analysis: {difference: strict-input-level-null, margin_estimand: model-mean-of-evaluated-inputs (rho_mod),
               margin_interval: hull(clopper-pearson, cluster-t-2999df),
               population_statement: model-conditional-H-A2, non-confirmatory}
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
    - {id: N2-w80, source: blake2b-stream, reject: [A2], per_stage: 15000000,
       pseudo_clusters: {size: 10000, per_stage: 1500}, analysis: same-as-A2}
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

| # | Decision | Status (through Architecture Review 006) | Note |
|---|---|---|---|
| D1 | Primary direction: Option 2, with Option 3 deferred | Accepted by the Architect | |
| D2 | Margin `δ` = ±2% | **Provisionally approved** (Director) | |
| D3 | Engine for A2: `sha256` | Decided (Architecture Review 003) | |
| D4 | Alpha split 0.005 difference + 0.005 margin | **Provisionally approved** | Proven usage is ≤ 0.008389 (3.5) |
| D5 | Mainnet drand quicknet pin, exact future round, witness and same-round-only transport fallback (3.8.1) | **Proposed; not frozen** | Live /info confirmation, pinned client and historical signature vectors required before freeze |
| D6 | Population definitions | A2 decided (Architecture Review 003); A1 and A3 as proposed | |
| D7 | Execution environment; independent verifier implementation; optional second-machine rerun | **Open** | |
| D8 | Implementation scope, now also covering: deterministic QA2 fixtures and its small integration test; binding the registry entry hash into `environment.json`; the seedless plan fingerprint | **Open** | |
| D9 | Experiment 001 follow-ups (archive; status update; optional re-execution audit) | **Open** | |
| D10 | Retry ceiling: 3 attempts of classes F1–F3 | **Provisionally approved** | |
| D11 | n = 15M per arm per stage | **Provisionally approved** | |
| D12 | A2 confirmatory scope restricted (now stated precisely: model mean `ρ_A2^mod`, 3.1) | **Provisionally approved**; Architect accepts in principle | |
| D13 | A2-path positive control | **Reduced QA2 design approved by Architect (Review 006)**; implementation/run still unauthorized | |
| D14 | Keep the hull rule for A2 | **Provisionally approved** | |
| D15 | Retain CP/t hull classification using the independently verified extremal theorem, withdraw universal heterogeneous CP coverage wording; optional elementary Chernoff alternative in addendum 7.3 | **Review 005 results provisionally accepted (Review 006)**; final gate pending | Fixed decision tails valid; no self-contained CP theorem proof supplied. No sample-size, cutoff or alpha change proposed |

Until these decisions are made, nothing in this proposal is implemented or executed.

## 6. Final documentation gate (Architecture Review 006)

The auditable theorem/threshold table, fresh FWER calculation, QA2 coverage matrix, live-beacon
checklist and concise blockers are in [addendum section 8](../reviews/experiment-002-protocol-readiness-addendum.md#8-architecture-review-006-final-documentation-gate).
The retained rule has W_LO=115,839, W_HI=118,519, B_LO=113,851 and B_HI=120,546;
15M per stage and 0.005/0.005 allocation are unchanged. The outward combined bound is <=0.008389.

Python regression tests are **NOT RUN** because the venv's referenced Python311 interpreter is missing.
Node probability calculations are not pytest results. QA2 has not run. Experiment 001's sealed 11 files
and v0.2.0 were reverified unchanged. No experiment or execution seed was generated.

Before freeze/execution: obtain final approval, repair/pin Python and complete authorized implementation,
regressions/G1/QA2/G2, pin independent high-precision references and verifier/audit scope, verify the
live beacon/client/witness arrangements, and arrange the off-machine Experiment 001 archive.
The approved reduced QA2 design does not authorize its implementation or execution.

## Appendix: reproducing the calculations

The following records describe historical calculations from revisions 2–4, run offline with
`python -I -B` in session scratch space, outside the repository. They are not current regression results.
Review 005/006 Node checks and Python NOT RUN status are separately recorded below:

- **Power and margin tables:** implementation A, `hashlab.statistics.inference` at `v0.2.0`; implementation
  B, independent log-space binomial sums and bisection Clopper–Pearson; plus a normal-approximation
  cross-check.
- **A2 (revision 3):** two independent simulation engines (addendum section 1.3):
  - a numpy direct simulation with exact per-cluster Binomial(10⁴, `p_j`) counts and the full decision
    procedure;
  - a pure-Python sufficient-statistic engine.

  Plus the exact two-point lower bound. The revision 2 Monte Carlo for 30 clusters is superseded.
- **Revision 4:**
  - Hoeffding tail-inequality verification: exact Poisson-binomial dynamic programme on 29,230 small-n
    vectors, plus exact two-binomial convolutions at n = 3 × 10^7 at the protocol's boundaries;
  - exact hypergeometric worst-case bounds and a monotonicity check for A1 and A3;
  - QA2 operating characteristics with the exact per-cluster binomial engine;
  - properties of the Chernoff fallback interval.

  Details are in the addendum, sections 1.2 and 4.
- **A3:**
  - cardinality by three methods plus brute-force analogs;
  - exact re-enumeration of the Experiment 001 8-byte candidates from the sealed configuration and seeds
    (generation only; the `random-bytes-w8` stream's keyed BLAKE2b was evaluated to generate candidates,
    with nothing tested against a target);
  - rank/unrank checks;
  - Monte Carlo of the Algorithm S + hypergeometric prototype and of the Feistel alternative.
- **Throughput:** prototype figures come from scratch code on the Director's machine. They are estimates,
  not measurements of production code.

**Review 005 calculations:** independent Node finite-law recurrences and heterogeneous small-n checks;
reproduction details, numerical limitations and current evidence checks are in addendum 7.4. Earlier
Python/Monte Carlo results above were not rerun in this review.
