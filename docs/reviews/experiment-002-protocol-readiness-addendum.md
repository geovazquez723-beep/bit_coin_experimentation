# Experiment 002: statistical review and protocol-readiness addendum

- **Revision:** 3 (Architecture Review 004). It supersedes revision 2, which evaluated A2 Option B, and
  revision 1, which evaluated the 30-prefix A2 design.
- **Basis:** `docs/proposals/experiment-002-research-design.md`, revision 4.
- **Status:**
  - The research direction, A2 Option B and the restricted A2 scope are accepted in principle.
  - D2, D4, D10, D11, D12, D13 and D14 are provisionally approved by the Director.
  - **Protocol freeze, implementation and execution are not authorized. No execution seed has been
    generated.**
- **Method:** offline calculations outside the repository, with `python -I -B`. No SHA-256 success
  evaluation, and no experiment, was run.
  - "Proven" means a mathematical argument, possibly resting on a cited theorem and an explicitly named
    model.
  - "Exact computation" means a finite numerical evaluation.
  - "Simulation" means Monte Carlo evidence, **never a proof**.

## 0. Changed conclusions in this revision

| # | Earlier statement | Revision 3 statement | Why |
|---|---|---|---|
| C1 | A2's confirmatory estimand was "the evaluated inputs" | It is the **model mean probability** `μ_A2` of the evaluated inputs (`ρ_A2^mod = μ_A2/p0`). The **observed fraction** `f_A2` is reported but is never the object of an inferential claim | The phrase "evaluated inputs" conflated an observed number with a model parameter |
| C2 | A1 and A3 margin claims were justified by the binomial (Bernoulli) model, with a finite-population check | A1 and A3 margin claims are **design-based statements about the structural population fraction `θ_a`**. They are proven by exact hypergeometric computation plus monotonicity, for **every** fixed hash function. No SHA-256 model is needed | Stronger and model-free. Error bounds tighten: A1 0.0016086, A3 0.0001149 |
| C3 | The Hoeffding citation was "Theorem 4", paraphrased | The cited result is the one stated in the paper's abstract (secondary sources number it Theorem 5, a corollary of Theorem 4). The one-sided tails are **derived** from it, with exact conditions (1.2(2)). Full text not accessed. Verified numerically | Required by Architecture Review 004 |
| C4 | `REP` asserted "strict null false, with the direction observed in Stage D". A wrong-direction bound of 4.1 × 10⁻⁶ was given | `REP` is **non-directional**. The direction only describes `f_a` | The 4.1 × 10⁻⁶ bound assumed homogeneity. Under heterogeneity, a directional claim about `μ_a` is not within budget (2.3) |
| C5 | Combined bound ≤ 0.01 (0.00995 with exact sizes) | ≤ 0.005 + 0.0033867 = **0.0083867** | Follows from C2 and the exact A2 suprema |
| C6 | D13 was an optional in-run A2 positive control | D13 is realized as a **separate qualification test QA2**, run before freeze (section 4) | Prevents a discretionary confirmatory rerun |
| C7 | The seed procedure was "Director-chosen and committed" (D5) | The exact procedure S1–S6 is defined, with a recommended public beacon (section 5). D5 now concerns only the beacon source | Prevents seed screening before commitment |

## 1. Quantities, guarantees and operating characteristics

### 1.1 Three quantities

For arm `a`, `E_a` is the set of evaluated inputs (30M), `U_a` is the structural population, and
`Y_x ∈ {0, 1}` is the SHA-256 success of input `x`.

| Symbol | Quantity | Nature | Used for |
|---|---|---|---|
| `f_a` | observed success fraction over `E_a` | known exactly after hashing | statistic; reported; **no inferential claim** |
| `μ_a` | mean of the model probabilities `p_x` over `E_a`, where the `Y_x` are independent Bernoulli(`p_x`) and the `p_x` are arbitrary | hypothetical model parameter | difference claims (strict null `p_x = p0`), all arms; **A2 margin claim** |
| `θ_a` | success fraction over all of `U_a` | deterministic, unknown | **A1 and A3 margin claims** (design-based). A2 (`θ_A2`): non-confirmatory only |

The full per-element mapping (hypotheses, intervals, classifications) is proposal 3.1.2.

### 1.2 What is proven, and what is not

1. **Difference tests (proven, given the model).** Under the strict model null (`p_x = p0` for all
   `x ∈ U_a`), every stage total is exactly Binomial(15M, `p0`), for any sampler or cluster structure. The
   exact sizes are:

   | Test | Size |
   |---|---:|
   | Discovery, two-sided | 0.0016560 |
   | Validation, one-sided | 0.0049685 |
   | Holm FWER at the global null | 0.0049599 |
   | Holm FWER, any configuration | ≤ 0.005 |

2. **A2 margin claims about `μ_A2` (proven given the model, by a cited theorem).**
   - *Source.* Hoeffding (1956), *Ann. Math. Statist.* 27(3):713–721, doi:10.1214/aoms/1177728178. The
     abstract states: for integers `0 ≤ b ≤ np ≤ c ≤ n`, `P(b ≤ S ≤ c)` attains its minimum (over Poisson
     trials with mean `np`) when all `p_j = p`. The exception for `b = 0, c = n` concerns only uniqueness of
     the minimizer.
     - Verification status: the statement and its conditions were checked against the publisher's abstract
       page. The full text is subscriber-only and was **not** accessed.
     - Secondary sources: one secondary summary numbers the result Theorem 5, a corollary of Theorem 4;
       Theorem 4 gives the extrema of `P(S ≤ c)`. According to a web-search summary, a 2022 arXiv paper on
       confidence intervals for the average success probability of independent Bernoulli trials
       (arXiv:2212.12558) restates a piecewise Hoeffding (1956) lower-tail bound with thresholds at
       `nq̄ − 1` and `nq̄`. Its PDF could not be read here, so it is cited only as consistent, not as
       verified.
   - *Derivation of the needed one-sided inequalities.*
     - Setting `c = n` gives `P(S ≥ b) ≥ P(B ≥ b)` for integers `1 ≤ b ≤ np`. Hence **(L)**
       `P(S ≤ d) ≤ P(B ≤ d)` for every integer `d ≤ np − 1`.
     - Setting `b = 0` gives `P(S ≤ c) ≥ P(B ≤ c)` for `np ≤ c < n`. Hence **(U)** `P(S ≥ d) ≤ P(B ≥ d)` for
       every integer `d ≥ np + 1`.

     Here `B ~ Binomial(n, p̄)` has the same mean.
   - *Independent numerical verification* (exact; not a proof):

     | Check | Result |
     |---|---|
     | 29,230 vectors with `n ≤ 40`: random; small-probability; endpoint-heavy; all "zeros / ones / one interior value" configurations (Hoeffding's extremal structure) | max `[P(S ≤ d) − P(B ≤ d)]` over `d ≤ np − 1`: **1.7 × 10⁻¹⁵**. Max `[P(S ≥ d) − P(B ≥ d)]` over `d ≥ np + 1`: **3.3 × 10⁻¹⁵** (rounding level) |
     | Same vectors, inside the excluded band `np − 1 < d < np + 1` | violations up to **0.43**. The conditions are necessary, not decorative |
     | Protocol boundaries, n = 3 × 10^7, two-point mixtures at mean exactly 1.02·p0, π ∈ {0.5, 0.2, 0.05, 0.01, 0.001, 10⁻⁴, 0.02/255}, exact convolution | `P(S ≤ W_HI)` ranges from 0.0015125 to 0.0016629, never above the binomial 0.0016629 |
     | Same, mean 1.0199·p0 (interior), `P(S ≥ B_HI)` | 0.0013536 to 0.0014897, never above the binomial 0.0014897 |

   - *Conditions at the protocol boundaries.* `W_HI = 118,519 ≤ n·1.02·p0 − 1`; `W_LO = 115,839 ≥ n·0.98·p0 + 1`;
     `B_HI = 120,546 ≥ n·1.02·p0 + 1`; `B_LO = 113,851 ≤ n·0.98·p0 − 1`. All hold.
   - *Result.* Since the hull's events are subsets of the Clopper–Pearson events, and binomial tails are
     monotone in `p̄`, for **any** heterogeneity:
     - P(false `WITHIN`) ≤ 0.0016629 (low side 0.0016556);
     - P(false `BEYOND`) ≤ 0.0016632 (low side 0.0016553), plus ≈ 10⁻²².

     This is valid **within the independent-Bernoulli model**. The required assumption is independence, not
     homogeneity.
3. **A1 and A3 margin claims about `θ_a` (proven; exact computation; model-free).**
   - For any fixed hash function, the pooled count is Hypergeometric(`N_a`, `K_a`, 3 × 10^7), with
     `θ_a = K_a / N_a`.
   - Likelihood ratio: `P_{K+1}(k) / P_K(k) = (K + 1)(N − K − n + k) / ((K + 1 − k)(N − K))`, increasing in
     `k`. So tails are monotone in `K`, and the worst cases are at the boundary counts (numerically
     confirmed on a grid).

   | Arm | sup false claim, θ ≥ 1.02 p0 | sup false `BEYOND`-high, interior θ | low side | opposite-side term |
   |---|---:|---:|---:|---:|
   | A1 (N = 4,293,918,720) | 0.0016085 | 0.0016086 | 0.0016012 / 0.0016011 | ≈ 10⁻²² |
   | A3 (N = 82,068,263) | 0.0001149 | 0.0001124 | 0.0001117 / 0.0001141 | ≈ 10⁻³⁴ |

   The only assumption is that the SRS sampler is exact (ideal RNG).
4. **No uniform guarantee for the A2 population fraction `θ_A2` (proven).**
   - The two-point (coupling) argument: a population in which a fraction π of prefixes carries the whole
     excess is indistinguishable from the null when no affected prefix is sampled, which has probability
     `(1 − π)^3000`.
   - Any rule with `P_null(WITHIN) = 0.99987` therefore has false `WITHIN` ≥ 0.0496 at π = 0.001,
     ≥ 0.7407 at π = 10⁻⁴, and ≥ 0.7902 at π = 0.02/255.
5. **The cluster t interval has no finite-sample guarantee at this tail level.** The Berry–Esseen error term
   is at least 0.4748/√3000 = 0.0087, which exceeds 0.00167. Its population-level behaviour is known from
   simulation only (1.3).
6. **Fallback with a self-contained proof (decision D15).** If the citation in (2) is not accepted, use the
   Chernoff interval.
   - Elementary proof:
     - `E e^{tS} = Π_x (1 − p_x + p_x e^t) ≤ (1 − p̄ + p̄ e^t)^n` (AM–GM);
     - hence `P(S ≤ c) ≤ exp(−n·KL(c/n ‖ p̄))` for `c ≤ np̄`, and symmetrically for the upper tail.
   - Inverting at `α' = 0.005/3` per side gives an interval valid for any heterogeneity without Hoeffding
     (1956).
   - Cost:

     | Interval | Relative half-width | Exact boundary size | P(`WITHIN`) at ρ = 1 / 1.005 / 1.01 |
     |---|---:|---:|---|
     | Chernoff | 1.04% | 0.00017 (very conservative) | 0.999 / 0.938 / 0.431 |
     | Clopper–Pearson (current) | 0.86% | 0.00166 | 0.9999 / 0.986 / 0.673 |

   - This would be a decision-rule change and is **not** adopted without review.

### 1.3 Operating characteristics of A2 (simulation evidence)

**Engines.**

- **Engine A:** numpy direct simulation. Exact per-cluster Binomial(10⁴, `p_j`) counts; 3,000 clusters split
  1,500 / 1,500; the full procedure, with the exact discovery and validation thresholds, the exact pooled
  Clopper–Pearson regions and the t interval on 2,999 df. 120,000 replicates at the margin boundaries
  (SE ≈ 0.00012) and 30,000 elsewhere.
- **Engine B:** independent pure-Python sufficient-statistic engine. Exact binomial number of affected
  clusters; normal within-group sums; exact χ² within-group sums of squares; 200,000 replicates.

`mixπ` means a fraction π of prefixes carries the whole deviation and the rest are exactly null. A deficit
concentrated in fewer than 2% of prefixes is infeasible (rates cannot be negative), hence "n/a".

**Table 1. Population-level false `WITHIN` and false `BEYOND` at the margin**

`WITHIN` at `ρ̄ = 1.02` or `0.98`, and `BEYOND` at `ρ̄ = 1.0199` or `0.9801`, are false claims. Nominal per-side
level: 0.00167.

| Between-prefix model | false `WITHIN`, ρ̄ = 1.02 (A) | false `WITHIN`, ρ̄ = 0.98 (A) | false `WITHIN`, 1.02 (B) | Clopper–Pearson alone, 1.02 (A) | false `BEYOND`, 1.0199 / 0.9801 (A) |
|---|---:|---:|---:|---:|---:|
| homogeneous | 0.00172 | 0.00177 | 0.00146 | 0.00178 | 0.00159 / 0.00141 |
| normal, τ = 0.01 | 0.00173 | 0.00151 | | 0.00183 | 0.00149 / 0.00140 |
| normal, τ = 0.05 | 0.00172 | 0.00172 | 0.00146 | 0.00264 | 0.00142 / 0.00153 |
| normal, τ = 0.10 | 0.00187 | 0.00157 | 0.00171 | 0.00670 | 0.00145 / 0.00152 |
| t₃, τ = 0.05 | 0.00172 | 0.00157 | | 0.00248 | 0.00139 / 0.00148 |
| t₃, τ = 0.10 | 0.00153 | 0.00163 | | 0.00545 | 0.00151 / 0.00143 |
| lognormal, τ = 0.10 | 0.00195 | 0.00178 | | 0.00647 | 0.00151 / 0.00153 |
| lognormal, τ = 0.30 | 0.00172 | 0.00128 | | 0.0857 | 0.00137 / 0.00187 |
| mix, 20% | 0.00174 | 0.00168 | 0.00175 | 0.00225 | 0.00150 / 0.00173 |
| mix, 5% | 0.00196 | 0.00153 | 0.00183 | 0.00492 | 0.00148 / 0.00157 |
| **mix, 1%** | **0.00411** | n/a | **0.00382** | 0.0308 | 0.00047 / n/a |
| **mix, 0.1%** | **0.0497** | n/a | **0.0495** | 0.247 | 0.00001 / n/a |
| **mix, 0.01%** | **0.742** | n/a | **0.742** | 0.742 | 0 / n/a |
| **mix, 0.0078%** (all-success prefixes; the feasibility limit) | **0.790** (at 1.0199) | n/a | **0.790** | 0.790 | 0 / n/a |

Reading Table 1:

1. **Regular heterogeneity and mixtures with prevalence ≥ 5%.** False `WITHIN` is 0.0012–0.0020. The largest
   values (0.00195 and 0.00196, ± 0.00013) exceed 0.00167 by about 2 SE. **The population level is therefore
   approximately nominal, up to about 1.2×, not exactly.** False `BEYOND` is ≤ 0.0019.
2. **The t interval is essential at population level.** Clopper–Pearson alone reaches 0.0022–0.086 for
   τ ≥ 0.05 and for mixtures (0.0018 at τ = 0.01).
3. **Rare concentration (≤ 1%).** Population-level control fails. The values match the two-point lower
   bounds of 1.2(4) and agree across both engines.
4. **Errors about the confirmatory estimand `ρ_A2^mod`.** In every cell they are at or below the proven
   bound, within simulation error:
   - largest observed rate 0.00177 ± 0.00012, in the homogeneous boundary case, where `ρ_A2^mod = ρ̄ = 1.02`
     exactly;
   - ≤ 0.00072 under any heterogeneity;
   - `BEYOND` ≤ 0.00159.

**Table 2. Power (engine A, 30,000 replicates)**

| Model | P(`WITHIN`), ρ̄ = 1.000 / 1.005 / 1.010 / 1.015 | P(`BEYOND`), ρ̄ = 1.025 / 1.030 / 1.035 | Discovery flag / `REP` (single arm), ρ̄ = 1.02 |
|---|---|---|---|
| homogeneous | 0.99993 / 0.986 / 0.673 / 0.108 | 0.102 / 0.665 / 0.984 | 0.953 / 0.941 |
| normal, τ = 0.05 | 0.9998 / 0.974 / 0.624 / 0.095 | 0.090 / 0.613 / 0.969 | 0.946 / 0.930 |
| normal, τ = 0.10 | 0.995 / 0.918 / 0.483 / 0.070 | 0.067 / 0.466 / 0.911 | 0.921 / 0.895 |
| t₃, τ = 0.10 | 0.995 / 0.917 / 0.478 / 0.069 | 0.067 / 0.484 / 0.919 | 0.927 / 0.902 |
| lognormal, τ = 0.30 | **0.223** / 0.170 / 0.066 / 0.015 | 0.015 / 0.084 / 0.274 | 0.784 / 0.670 |
| mix, 5% | 0.9999 / 0.983 / 0.640 / 0.090 | 0.060 / 0.379 / 0.781 | 0.932 / 0.909 |
| mix, 1% | 0.9999 / 0.972 / 0.486 / 0.060 | 0.011 / 0.060 / 0.159 | 0.857 / 0.791 |

- In the homogeneous case, difference power is exactly A1 and A3's (the stage totals are Binomial(15M)).
- Under heterogeneity, **power falls**. Strong heterogeneity (lognormal τ = 0.3) makes `WITHIN` rare even at
  `ρ̄ = 1`, because the cluster t interval widens. That outcome is reported as `inconclusive-at-margin`.
- Using Clopper–Pearson alone for the confirmatory `ρ_A2^mod` label would raise this power (0.93 at
  `ρ̄ = 1`, lognormal τ = 0.3), but it would remove the population-level protection shown in Table 1. **No
  rule change is proposed.** The trade-off is listed as decision D14.

**Table 3. Difference test under heterogeneity with `ρ̄ = 1`** (the strict null is false; the average is null)

| Model | P(discovery flag) | P(`REP`) | P(`WITHIN`) |
|---|---:|---:|---:|
| normal, τ = 0.05 | 0.0028 | 0.00003 | 0.9996 |
| normal, τ = 0.10 | 0.0071 | 0.0001 | 0.996 |
| normal, τ = 0.20 | 0.050 | 0.0025 | 0.819 |
| 1% of prefixes at ρ = 2, the rest compensating | 0.0083 | 0.0001 | 0.995 |
| 5% of prefixes at ρ = 2, the rest compensating | 0.072 | 0.0052 | 0.680 |

These flags are **correct** rejections of the strict null, not evidence about the average. Moderate
heterogeneity rarely produces `REP`. When it does, the label is read as in proposal 3.4.

### 1.4 Degrees of freedom and assumptions

- Cluster t interval: 2,999 df, pooled over stages; `t_{0.998333, 2999} = 2.9376`.
- The between-cluster variance absorbs any dependence among nonces within a cluster. This matters **only**
  for the t part of the hull. The confirmatory `μ_A2` guarantee (1.2(2)) **requires** independence between
  inputs.
- **H-A2** (for non-confirmatory population sentences only): the deviation of per-prefix rates from the
  population mean is not concentrated in prefixes of prevalence below about 5%. Even under H-A2, the
  population-level error is only approximately nominal (≤ about 1.2×). H-A2 cannot be verified from the data.

## 2. Family-wise error after revision 4

### 2.1 Claims asserted by each classification cell

| Proposition | A1 | A2 | A3 |
|---|---|---|---|
| Deviation (`REP`) | strict model null false for `U_A1` | strict model null false for `U_A2` | strict model null false for `U_A3` |
| Within | `|θ_A1/p0 − 1| < δ` | `|μ_A2/p0 − 1| < δ` | `|θ_A3/p0 − 1| < δ` |
| Beyond | `θ_A1/p0 ≥ 1 + δ` or `≤ 1 − δ` | the same for `μ_A2/p0` | the same for `θ_A3/p0` |

The cells assert conjunctions of these propositions, as in proposal 3.4. `UNREP` notes, discordant cells and
`f_a` assert nothing.

### 2.2 Probability space and bound

- **Probability space.** Ω = (sampler randomness) × (independent Bernoulli(`p_x`) outcomes, with arbitrary
  `p_x`).
- The design-based bounds of 1.2(3) hold conditionally on every realization of the outcomes, so they also
  hold in Ω.
- Union bound:

| Family | Bound | Basis |
|---|---:|---|
| Difference: any false `REP` | ≤ 0.005 | Holm (strong control under arbitrary dependence); exact test sizes; a false `REP` requires a false discovery |
| A1 margin | ≤ 0.0016086 + 10⁻²² | design-based, exact computation |
| A2 margin | ≤ 0.0016632 + 10⁻²² | Hoeffding (1956) within the model |
| A3 margin | ≤ 0.0001149 + 10⁻³⁴ | design-based, exact computation |
| **Total** | **≤ 0.0083867** | budget 0.01 |

- **Model-free reading.** If SHA-256 is treated as a fixed function with no probability model, only the A1
  and A3 margin claims keep a frequentist guarantee (≤ 0.0017235 together). The difference claims and the A2
  margin claim are then statements about a model.

### 2.3 Why `REP` is no longer directional

- A directional claim would be "`μ_a > p0`" (or `<`). Under heterogeneity, the two stages can have different
  model means, for example `μ_D > p0 ≥ μ_V` while the overall mean is at most `p0`.
- Then Stage D flags almost surely, and the error probability is governed by Stage V alone, up to 0.005 per
  arm, or 0.015 for three arms, which exceeds the budget.
- The earlier bound of 4.1 × 10⁻⁶ (addendum revision 1) assumed homogeneity. The direction of a `REP` is therefore reported only
  as a description of `f_a`. Directional statements about averages come only from `BEYOND`.

### 2.4 Conditions and exclusions

The bound ≤ 0.0083867 holds conditionally on:

- the independent-Bernoulli model, for the difference claims and the A2 margin claim (any heterogeneity);
- an exact SRS sampler (ideal RNG), for A1 and A3;
- the cited theorem (or D15's fallback);
- a correct implementation (G1, QA2);
- **a single confirmatory attempt.**

It excludes:

- the A2 population fraction `θ_A2`;
- directional readings of `REP`;
- secondary tests, controls, QA2 and 002-R;
- any accepted F4 rerun (post-amendment labels).

## 3. A3 exclusion-set verification (unchanged)

The procedure and results of revisions 1 and 2 are retained:

- three agreeing derivations (package, clean room, analytic);
- `|X3| = 60,721`; digest `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`;
- **retained limitation:** the sealed Experiment 001 run did not record individual candidates, so `X3` is
  regenerated, not observed. This affects provenance only.

## 4. A2 implementation-qualification test QA2 (D13)

Specified in proposal 3.7.1. It is a separate experiment id and configuration (`002-qual-a2`), run after G1
and **before** the pre-registration commit `C_pre`, with its own seed fixed by its committed configuration.

| Sub-test | P(pass \| correct code) | Basis |
|---|---:|---|
| QA2-0 null: `WITHIN` and not `REP` | 0.99992 | 200,000 replicates, exact per-cluster binomial engine |
| QA2-1: 20% of prefixes at ρ = 1.25 (mean +5%): `REP`-high, `BEYOND`-high and the dispersion test in both stages (χ²₁₄₉₉ > 1,673.9) | 1.0000 (100,000 / 100,000) | same engine |
| QA2-2 calibration +2% (not gating) | `REP` 0.942, `WITHIN` 0.0016 | same engine |
| Recomputation from stored per-cluster counts | exact match required | deterministic |

**Why QA2 cannot create a confirmatory rerun opportunity:**

- It is completed before the confirmatory seed exists.
- The confirmatory attempt must use the qualified code commit.
- After attempt 1 starts, QA2 is repeated only inside a mandatory F1 or F3 code amendment.
- No QA2 outcome can reclassify, invalidate or justify repeating a valid attempt.

## 5. Seed commitment and attempt registry (summary of proposal 3.8)

1. **S1 Freeze.** The code is tagged after G1 and QA2. The configuration is complete except
   `seeds.master: derived-from-beacon`. The seedless plan fingerprint is computed.
2. **S2 Commit `C_pre`.** It records the configuration SHA-256, the seedless fingerprint, the A3 digest,
   the QA2 manifests, the beacon source, the explicit reveal round `R*` and the derivation formula.
3. **S3 External witness.** `C_pre`'s hash reaches the Architect (or is pushed, with approval) at least 24 h
   before `R*`.
4. **S4 Derive.** `master = SHA-256("hashlab-exp002-master-v1|" + C_pre + "|" + R* + "|" + beacon_hex)[:8]`,
   read big-endian.
5. **S5 Commit `C_seed`.** It records the beacon data, the seed and the full fingerprint.
6. **S6 Run.** A registry `started` entry is committed, its hash is written into `environment.json`, the run
   is executed, and a `result` entry is committed.

Registry rules:

- entry types `S`, `Q` (before `C_pre` only) and `A` (after `C_seed` only);
- append-only, one commit per entry;
- completeness audit at G4.

Because seed and code are fixed, an unregistered private run would reproduce the registered results exactly.
The only remaining lever is a code change, which requires an amendment, review and re-qualification.
**No seed has been generated.**

## 6. Protocol-readiness status

| # | Concern | Status | Affects confirmatory validity? |
|---|---|---|---|
| R1 | Observed, model and population quantities conflated | **Resolved** (proposal 3.1.1–3.1.2; C1) | No |
| R2 | Clopper–Pearson conservativeness under heterogeneity | **Resolved, conditional on the citation**: the theorem is identified, the one-sided tails derived with exact conditions, and verified numerically (1.2(2)). The full text was not accessed. Fallback D15 available | No, if the citation (or D15) is accepted |
| R3 | A1 and A3 margin claims | **Resolved, strengthened**: design-based and model-free (1.2(3); C2) | No (ideal-RNG assumption only) |
| R4 | Combined FWER | **Resolved**: ≤ 0.0083867, with the conditions of 2.4 | Conditional on the stated models and a single attempt |
| R5 | Directional `REP` | **Resolved by withdrawal** (2.3; C4) | No |
| R6 | A2 population fraction `θ_A2` | **Accepted limitation**: no uniform guarantee is possible; non-confirmatory only | No, for confirmatory claims |
| R7 | A2 positive control | **Resolved**: QA2, separate and pre-freeze (section 4) | No |
| R8 | Seed commitment and registry | **Resolved in specification** (section 5). Beacon source open (D5) | D5 must be decided before freeze |
| R9 | Independence assumption (difference claims; A2 margin) | **Accepted limitation**: HASHLAB's null model, never claimed as a theorem | These claims are model-relative by construction |
| R10 | A3 exclusion set regenerated, not observed | **Conditional** (provenance only) | No |
| R11 | Implementation (samplers, hull, classification, blinding, QA2 engine, registry binding) | **Blocking for execution** until G1, QA2 and G2 | Yes, until then |
| R12 | F4 rerun path | **Conditional** (policy and disclosure) | Yes, if used |
| R13 | Open decisions: D5, D7, D8, D9, D15 | **Open** | D5 and D15 needed before freeze |

**Readiness.** No unresolved statistical blocker remains in the design, provided D15 accepts the citation
(or adopts the fallback) and D5 fixes the beacon source. Freeze still requires those decisions, and
execution still requires implementation, G1, QA2 and G2.

**Stop for Architect review. No implementation or experiment execution is authorized.**
