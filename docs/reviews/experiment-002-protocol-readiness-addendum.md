# Experiment 002: statistical review and protocol-readiness addendum

- **Revision:** 6 (Architecture Review 013; approved A2 encoding cross-reference). It supersedes revision 5.
  Review 013 adds the approved byte contract and KAT cross-reference (section 9); statistical content
  is unchanged. The following Review 006 verification record is historical.
  Review 005 results are provisionally accepted and the reduced QA2 design is approved. Section 8
  records this pass; section 7 retains Review 005. Simulations are historical; QA2 has not run.
- **Basis:** `docs/proposals/experiment-002-research-design.md`, revision 8;
  A2 encoding `hashlab-exp002-a2-encoding-v1` (proposal 3.2).
- **Status:**
  - The research direction, A2 Option B and the restricted A2 scope are accepted in principle.
  - D2, D4, D10, D11, D12, D13 and D14 are provisionally approved by the Director.
  - Review 011 authorizes implementation and bounded qualification conditionally. Reviews 012–013
    block E1 pending fresh Director diagnostics and the approved interpreter passing its 240-test
    regression baseline. This pass is documentation only. **Confirmatory execution is not authorized.**
    Protocol freeze remains pending; no execution seed has been generated.
- **Method:** Review 013 updates documentation without calculations or hashing. Review 006 used
  offline Node calculations; see 7.4 and 8.2 for results and limitations. Earlier
  revisions used Python. No Experiment 002 candidate hashing, implementation or execution was performed.
  - "Proven" means a mathematical argument, possibly resting on a cited theorem and an explicitly named
    model.
  - "Exact computation" means a finite numerical evaluation.
  - "Simulation" means Monte Carlo evidence, **never a proof**.

## 0. Changed conclusions in revision 3 (historical; section 7 supersedes coverage and precision)

| # | Earlier statement | Revision 3 statement | Why |
|---|---|---|---|
| C1 | A2's confirmatory estimand was "the evaluated inputs" | It is the **model mean probability** `μ_A2` of the evaluated inputs (`ρ_A2^mod = μ_A2/p0`). The **observed fraction** `f_A2` is reported but is never the object of an inferential claim | The phrase "evaluated inputs" conflated an observed number with a model parameter |
| C2 | A1 and A3 margin claims were justified by the binomial (Bernoulli) model, with a finite-population check | A1 and A3 margin claims are **design-based statements about the structural population fraction `θ_a`**. They are proven by exact hypergeometric computation plus monotonicity, for **every** fixed hash function. No SHA-256 model is needed | Stronger and model-free. Error bounds tighten: A1 0.0016086, A3 0.0001149 |
| C3 | The Hoeffding citation was "Theorem 4", paraphrased | The cited result is the one stated in the paper's abstract (secondary sources number it Theorem 5, a corollary of Theorem 4). The one-sided tails are **derived** from it, with exact conditions (1.2(2)). Full text not accessed. Verified numerically | Required by Architecture Review 004 |
| C4 | `REP` asserted "strict null false, with the direction observed in Stage D". A wrong-direction bound of 4.1 × 10⁻⁶ was given | `REP` is **non-directional**. The direction only describes `f_a` | The 4.1 × 10⁻⁶ bound assumed homogeneity. Under heterogeneity, a directional claim about `μ_a` is not within budget (2.3) |
| C5 | Combined bound ≤ 0.01 (0.00995 with exact sizes) | Revision 3 reported 0.0083867; Review 005 corrects outward reporting to **0.008389** | Finite-population improvement holds; prior rounding was downward |
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

2. **A2 fixed margin classification events (proven within the model via a verified theorem).**
   The required pointwise binomial comparisons hold outside the one-count band around the mean.
   A readable primary research source now verifies the theorem statement; see section 7.1 for the
   derivation, all four thresholds and independent numerical checks. Universal nominal one-sided CP
   endpoint control fails (7.1 counterexample). That example does not disprove full two-sided coverage;
   no universal two-sided CP guarantee is established here. Retain the CP/t **classification** rule.
   Independence remains essential.
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
5. **No finite-sample guarantee for the cluster t interval has been established at this tail level.**
   A generic normal-approximation Berry–Esseen upper-bound formula is already about 0.0087 at 3,000
   clusters with standardized third absolute moment one; it cannot certify a 0.00167 tail, and does not
   directly establish Studentized coverage. This is not a lower bound on the actual approximation error.
   Population-level behaviour in 1.3 is simulation evidence only.
6. **Self-contained alternative (not adopted).** Section 7.3 proves the Chernoff interval, computes its
   integer regions and homogeneous power, and distinguishes a Chernoff-only rule from a t-hull variant.
   No self-contained proof of the CP extremal theorem is claimed in this review.

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

## 2. Family-wise error (outward rounding corrected by Review 005)

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
| A1 margin | < 0.001609 | design-based, exact computation |
| A2 margin | < 0.001664 | Hoeffding (1956) within the model |
| A3 margin | < 0.000115 | design-based, exact computation |
| **Total** | **≤ 0.008389** | budget 0.01 |

- **Model-free reading.** If SHA-256 is treated as a fixed function with no probability model, only the A1
  and A3 margin claims keep a frequentist guarantee (outward bound <0.001724 together). The difference claims and the A2
  margin claim are then statements about a model.

### 2.3 Why `REP` is no longer directional

- A directional claim would be "`μ_a > p0`" (or `<`). Under heterogeneity, the two stages can have different
  model means, for example `μ_D > p0 ≥ μ_V` while the overall mean is at most `p0`.
- Then Stage D flags almost surely, and the error probability is governed by Stage V alone, up to 0.005 per
  arm, or 0.015 for three arms, which exceeds the budget.
- The earlier bound of 4.1 × 10⁻⁶ (addendum revision 1) assumed homogeneity. The direction of a `REP` is therefore reported only
  as a description of `f_a`. Directional statements about averages come only from `BEYOND`.

### 2.4 Conditions and exclusions

The bound ≤ 0.008389 holds conditionally on:

- the independent-Bernoulli model, for the difference claims and the A2 margin claim (any heterogeneity);
- an exact SRS sampler (ideal RNG), for A1 and A3;
- the independently verified extremal theorem for the current classification rule (7.1);
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

## 4. A2 engineering qualification QA2 (D13; replacement specification)

Proposal 3.7.1 is authoritative: synthetic 3,000-cluster statistical fixtures, independent recomputation,
all nine labels, null/positive/negative/heterogeneous/boundary/contradictory/invalid cases, and a small
2,048-candidate hashing integration test with independent rehashing and tamper rejection. Total hashing
budget <=4,200 candidate/known-answer evaluations plus file-integrity hashes, replacing 90M.

This is a **specification only**. No QA2 implementation, fixture corpus or QA2 execution exists from this
review. PASS is deterministic agreement and rejection of every malformed/tampered case, not a sampled
classification or an estimated P(pass). Mathematical power remains separate in sections 1.3 and 7.3.
QA2 precedes C_pre; the code revision that passes must be bound in precommitment. The existing amendment
and valid-attempt finality policies remain. No qualification result creates a confirmatory rerun right.

## 5. Seed commitment and attempt registry (summary of proposal 3.8)

Detailed source pin, byte encoding, outage policy, verifier and archival requirements are in proposal
3.8.1–3.8.3. Live /info and pinned-client verification remain pre-freeze checks.

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

- entry types `S`, `Q` (initial qualification before `C_pre`; later only under an approved mandatory amendment) and `A` (after `C_seed` only);
- initialized before the first S/Q entry, with the pre-seed history bound in C_pre;
- append-only, one commit per entry;
- completeness audit at G4.

Because seed and code are fixed, an unregistered private run would reproduce the registered results exactly.
The only remaining lever is a code change, which requires an amendment, review and re-qualification.
**No seed has been generated.**

## 6. Protocol-readiness status

| # | Concern | Status | Affects confirmatory validity? |
|---|---|---|---|
| R1 | Observed, model and population quantities conflated | **Resolved** (proposal 3.1.1–3.1.2; C1) | No |
| R2 | A2 heterogeneous inference | **Mathematical disposition prepared** (7.1): fixed tails valid by independently verified theorem; universal CP coverage withdrawn; no standalone CP theorem proof supplied | Review 005 provisionally accepted; final Architect gate remains |
| R3 | A1 and A3 margin claims | **Resolved, strengthened**: design-based and model-free (1.2(3); C2) | No (ideal-RNG assumption only) |
| R4 | Combined FWER | **Resolved**: ≤ 0.008389, with the conditions of 2.4 | Conditional on the stated models and a single attempt |
| R5 | Directional `REP` | **Resolved by withdrawal** (2.3; C4) | No |
| R6 | A2 population fraction `θ_A2` | **Accepted limitation**: no uniform guarantee is possible; non-confirmatory only | No, for confirmatory claims |
| R7 | A2 engineering qualification | **Reduced design approved (Review 006)**, zero-hash statistical fixtures plus small hashing integration (proposal 3.7.1); not implemented or run | Must pass before freeze |
| R8 | Seed commitment and registry | **Resolved in specification** (section 5). Quicknet proposed; live chain/client confirmation open (D5) | D5 must be decided before freeze |
| R9 | Independence assumption (difference claims; A2 margin) | **Accepted limitation**: HASHLAB's null model, never claimed as a theorem | These claims are model-relative by construction |
| R10 | A3 exclusion set regenerated, not observed | **Conditional** (provenance only) | No |
| R11 | Implementation (samplers, hull, classification, blinding, QA2 engine, registry binding) | **Blocking for execution** until G1, QA2 and G2 | Yes, until then |
| R12 | F4 rerun path | **Conditional** (policy and disclosure) | Yes, if used |
| R13 | Open decisions: D5, D7, D8, D9, D15 final disposition | **Open operational/final gates** | D15 results provisionally accepted; freeze not authorized |

**Readiness.** Prepared for final Architect review, not freeze. Review 005 results are provisionally
accepted and the reduced QA2 design is approved; section 8 records the final documentation gate.
D5 needs chain/client confirmation and witness
acceptance; D7 needs verifier ownership and audit scope; D8 implementation remains unauthorized; D9
archival destinations/custodians remain open. G1, deterministic QA2 and G2 are still future gates.

**Stop for Architect review. No implementation or experiment execution is authorized.**

## 7. Architecture Review 005: independent mathematical disposition (2026-10-11)

This section supersedes the theorem-access status, precision claims and QA2 specification of revision 3.
The review started from clean branch docs/experiment-002-design at 1c046cf. No Experiment 002 code,
execution or execution seed was produced. Earlier simulations and test-suite results above are historical,
not rerun results of this review.

### 7.1 D15: valid fixed decision tails; no claim of universal CP coverage

Let S be a sum of independent Bernoulli variables, m = sum p_i, and B ~ Binomial(n,m/n).
The required inequalities **are valid**:

- P(S <= d) <= P(B <= d) for integer d <= m-1;
- P(S >= d) <= P(B >= d) for integer d >= m+1.

Independent source verification: [Bancal and Sekatski, arXiv:2212.12558, section II,
equations (7)-(8)](https://arxiv.org/html/2212.12558) explicitly gives the sharp CDF lower bound
P(S <= c) >= P(B <= c) when c >= m, citing Hoeffding (1956). Taking c=d-1 proves the upper-tail
statement. Applying it to n-S, whose mean is n-m, proves the lower-tail statement. This readable primary
research source removes reliance on an inaccessible abstract alone. The original 1956 full proof was
not accessed. These deductions rely on the cited extremal theorem; **this review does not supply a
self-contained proof of that theorem or of the CP tail comparison**. This does not assert that a self-contained
proof is impossible. A self-contained alternative is
proved in 7.3. Numerical verification is supplementary, not a substitute for the theorem.

Convex order alone does not imply either pointwise tail inequality. For example, p=(0.2,0.8) gives
P(S>=1)=0.84 > 0.75 for Binomial(2,0.5), despite convex-order domination. The pair-averaging change in
P(S<=d), conditional on the other sum T, is proportional to
P(T=d)-P(T=d-1), whose sign need not be constant along an averaging path. The unfinished hinge bound
near 0.0043 is neither a counterexample nor a certificate for the required 1/600 tail level.

**Nominal one-sided CP endpoint control is not universally valid** for arbitrary heterogeneous means. With
n=2, alpha=1/600, take p_1=0 and p_2=alpha+alpha^2/8. For S=1 the CP lower endpoint is
L=1-sqrt(1-alpha). Since p_2/2 < L, the event S=1 excludes the true mean on the low side with probability
p_2 > alpha. **Review 006 correction:** this disproves one-sided alpha control only. At this vector
the full two-sided CP interval has error p_2<2alpha, so the example does not disprove two-sided
1-2alpha coverage. No universal two-sided CP coverage assertion is established by this review.
The fixed A2 classification thresholds below, far from the mean, are unaffected. Report the CP component
as a decision interval with controlled classification events; do not infer unproved universal endpoint
or confidence-set guarantees.

At n=30,000,000, p0=1/256, the boundary means are m_L=114,843.75 and m_H=119,531.25:

| False-decision component | Count event | Required comparison | Independently recomputed binomial probability |
|---|---|---|---:|
| WITHIN when mean >= H | S <= 118,519 | 118,519 <= m_H-1 | 0.0016629395 |
| WITHIN when mean <= L | S >= 115,839 | 115,839 >= m_L+1 | 0.0016556251 |
| BEYOND-high when mean < H | S >= 120,546 | 120,546 >= m_H+1 | 0.0016632431 |
| BEYOND-low when mean > L | S <= 113,851 | 113,851 <= m_L-1 | 0.0016552604 |

Here L=0.98 p0 and H=1.02 p0. Hull events are subsets of these CP events.
For false WITHIN, the applicable inequality remains valid as the mean moves farther outside [L,H];
binomial tails are monotone in that direction. For false BEYOND with mean in (L,H), both inequalities
remain valid throughout the interior. Split at p0: on each half the near-side tail is at most its boundary
value and the other tail is at most its value at p0. The latter probabilities are about 5.08e-23 and
6.67e-23. Thus the per-arm error is at most 0.0016632431 plus a negligible opposite-side term; an
outward numerical bound is **0.001664**. At exactly L or H, BEYOND is true by the stated inclusive
proposition; WITHIN remains false. Strict interval comparisons continue to apply.

**Disposition proposed for D15:** retain the existing CP/t hull **classification rule**, using the
verified extremal theorem, and correct its coverage wording. No change to sample size, alpha allocation
or integer cutoffs is necessary. If the Architect requires a proof independent of external theorems,
choose 7.3 explicitly; the self-contained CP proof has not been furnished. Do not silently substitute
convex order for that missing proof.

### 7.2 Family-wise error and finite-population cross-check

A false REP requires a false discovery; exact binomial p-values under each true strict null and Holm
strong control bound that family by 0.005. There is no added 0.005 validation charge, and no directional
model-mean claim from REP. For each arm, false WITHIN is possible only outside the margin; false BEYOND
only inside it. These disjoint parameter regimes do not require adding both worst-case errors.

Independent hypergeometric recurrence checks reproduced the earlier finite-population results:

| Arm | false WITHIN high / low | false BEYOND high / low at nearest interior integer K |
|---|---|---|
| A1 | 0.0016085134 / 0.0016011553 | 0.0016086027 / 0.0016010611 |
| A3 | 0.0001149408 / 0.0001116952 | 0.0001124161 / 0.0001140512 |

For WITHIN the boundary K values are ceil(N H) and floor(N L); for BEYOND the nearest interior values
are ceil(N H)-1 and floor(N L)+1. Hypergeometric tail monotonicity follows by coupling uniformly sampled
positions while increasing the number of successful population elements. Opposite-side tails can be
bounded by the corresponding binomial Chernoff bound for SRS (the without-replacement product moment
bound), or directly evaluated at the split near N p0. They are negligible on this precision scale.
Use outward bounds A1 < 0.001609, A2 < 0.001664, A3 < 0.000115, including opposite-side terms.
The combined bound is **< 0.008388**, reported conservatively as **<= 0.008389 < 0.01**.
The previous <=0.0083867 rounded downward: even its A2 value 0.0016632 is below the recomputed tail.
This is a precision correction, not a failure of the allocated 0.01 budget.

Conditions: exact SRS under ideal sampler randomness for A1/A3; conditional input-level Bernoulli
independence with fixed p_i for A2 and strict model-null tests; correct implementation; a single
confirmatory attempt. Conditional-on-input A2 bounds integrate over prefix sampling. No independence
between arms is needed for the union bound. Finite PRNG output is a modelling approximation to ideal
sampling. Model-free claims remain limited to A1/A3. A2 population generalization, directional REP,
controls, secondary analyses and post-amendment reruns are excluded. No power claim is uniform over
arbitrary heterogeneity or within-cluster dependence.

### 7.3 Optional conservative alternative with an elementary proof

For every real t, independence and AM-GM imply
E exp(t S)=product_i[1+p_i(exp(t)-1)] <= [1+mu(exp(t)-1)]^n.
Markov's inequality and minimization in t give
P(S>=n q) <= exp[-n D(q||mu)] for q>=mu, and
P(S<=n q) <= exp[-n D(q||mu)] for q<=mu,
where D(q||p)=q log(q/p)+(1-q) log((1-q)/(1-p)), with continuous endpoint limits.
Invert the two bounds at alpha=1/600. Their union gives at least 1-2alpha coverage for every independent
heterogeneous Bernoulli vector. Hull with the t interval can only reduce the classification events.
This proof is self-contained: it needs no binomial pointwise-tail theorem.

At the unchanged n=30M, comparing the Chernoff interval with the same margin yields:
WITHIN 116,056 <= S <= 118,299; BEYOND S <= 113,636 or S >= 120,768.
The boundary probabilities are about 0.000174 (WITHIN) and 0.000175 (BEYOND).
For a **Chernoff-only replacement** (t retained as a descriptive diagnostic rather than a gate), exact
binomial-sum planning power under homogeneous probabilities is:

| True ratio | 0.990 | 0.995 | 1.000 | 1.005 | 1.010 | 1.015 |
|---|---:|---:|---:|---:|---:|---:|
| P(WITHIN) | 0.45312 | 0.94554 | 0.99897 | 0.93764 | 0.43097 | 0.03023 |

| True ratio | 1.025 | 1.030 | 1.035 |
|---|---:|---:|---:|
| P(BEYOND) | 0.03013 | 0.42617 | 0.93335 |

These are homogeneous binomial planning probabilities, not heterogeneous power guarantees. If the t
hull is retained, these figures are **upper bounds on its power**, not exact hull power; joint cluster
count/variance calculations would be required before adopting that variant. Difference/replication
power and its 15M-per-stage sample size are unaffected. No alternative is adopted by this review.

### 7.4 Offline verification record and reproducibility

The normal shell tool could not start (helper setup error). Read-only git inspection and calculations
used Node via the available REPL. The repository .venv points to a missing Python311 installation;
python, py and python3 were unavailable. **The Python/pytest suite was not run in this review.**
No dependencies were installed and no qualification test was implemented or executed.

- Exact finite-distribution numerical calculations, not Monte Carlo: enumerate p_i in {0,1/3,2/3,1}
  for n=2..7 (21,840 vectors). Poisson-binomial polynomial convolution and binomial recurrences tested
  116,520 strict-outside-band tail comparisons; maximum positive discrepancy 2.22e-16 (roundoff).
  The equality edges and all four actual protocol inequalities were checked algebraically. Adjacent
  critical-count checks gave 0.0016785861, 0.0016714335, 0.0016788041 and 0.0016711571 respectively,
  all >1/600, confirming the four maximal/minimal integer regions.
- Large-n binomial PMF: compute log choose(n,k) by compensated summation of log((n-i+1)/i), i=1..k;
  add k log(p)+(n-k) log1p(-p). Sum lower tails with successive ratio
  j(1-p)/[(n-j+1)p], upper tails with (n-j)p/[(j+1)(1-p)], stopping after a term is <1e-15 of the sum.
- Hypergeometric PMF: exp(log C(K,k)+log C(N-K,n-k)-log C(N,n)); log factorial uses Stirling through
  1/(12x)-1/(360x^3) for x>=20, direct sums below. Lower recurrence ratio is
  j(N-K-n+j)/[(K-j+1)(n-j+1)], upper is (K-j)(n-j)/[(j+1)(N-K-n+j+1)].
- Chernoff integer cutoffs: bisection for n D(k/n||L or H) >= log(600) on the appropriate mean side;
  homogeneous power by binomial-tail sums. These are floating-point evaluations of exact finite laws,
  **not certified arbitrary-precision bounds**. Outward reporting leaves ample rounding headroom;
  freeze should pin high-precision critical-count and p-value references in QA2.
- Experiment 001: all nine payload hashes and byte sizes, manifest self-hash and exact 11-file inventory
  checked read-only; no analyses directory. Manifest digest:
  546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b.
  Annotated tag v0.2.0 object 662bb21c714afd9b560f40845c6780132baf3d6b dereferences to
  ef595f5c2f2166923fd277def39708409f564419. Payload integrity is verified, not original authenticity
  against an independent historical witness. Off-machine archival is still pending (proposal 3.8.3).

## 8. Architecture Review 006: final documentation gate

The Architect provisionally accepts Review 005 and approves the reduced QA2 design. This pass finalizes
its specification only: no Experiment 002 implementation, qualification, experiment, beacon-round
selection or execution-seed derivation is authorized or performed. Proposal revision 6 is the basis.

### 8.1 Auditable A2 threshold verification

For n=30,000,000, let S=sum of independent Bernoulli(p_i), mu=(sum p_i)/n and
B_mu~Binomial(n,mu). The established comparison theorem gives:

- lower tail: P_mu(S<=d)<=P(B_mu<=d), for integer 0<=d<=n with d<=n mu-1;
- upper tail: P_mu(S>=d)<=P(B_mu>=d), for integer 0<=d<=n with d>=n mu+1.

Independence and fixed probabilities conditional on evaluated inputs are required; identical probabilities
are not. Rechecked against [Bancal and Sekatski, section II, (7)-(8)](https://arxiv.org/html/2212.12558):
the CDF lower bound at c>=n mu yields the upper-tail comparison at c=d-1; applying it to n-S yields
the lower-tail comparison. This is an application of the established extremal theorem, not a convex-order
argument or a self-contained proof of that theorem. The guarantee concerns fixed classifications, not
universal heterogeneous CP confidence-set coverage.

Write L=0.98/256, H=1.02/256; nL=114,843.75 and nH=119,531.25.

| Error component / relevant domain | Integer event containing the hull event | Exact theorem condition at the boundary | Slack in counts | Boundary binomial tail (approx.) |
|---|---|---|---:|---:|
| WITHIN, mu>=H | S<=W_HI=118,519 | 118,519<=nH-1=119,530.25 (lower tail) | 1,011.25 | 0.0016629395 |
| WITHIN, mu<=L | S>=W_LO=115,839 | 115,839>=nL+1=114,844.75 (upper tail) | 994.25 | 0.0016556251 |
| BEYOND-high, mu<H | S>=B_HI=120,546 | 120,546>=nH+1=119,532.25 (upper tail) | 1,013.75 | 0.0016632431 |
| BEYOND-low, mu>L | S<=B_LO=113,851 | 113,851<=nL-1=114,842.75 (lower tail) | 991.75 | 0.0016552604 |

All conditions hold at the boundaries and strengthen throughout the stated domains. Monotonicity of
binomial tails puts the supremum at the displayed boundary (or its interior limit for BEYOND). Actual
CP/t hull events are subsets of these count events. Endpoint equality is handled by the protocol's
strict interval comparisons; parameter values exactly L/H are outside the open WITHIN proposition.
No cutoff, interval rule, sample size, margin or alpha allocation changes in Review 006.

**Coverage-wording correction:** the n=2 example in 7.1 violates one-sided alpha control, not full
two-sided 1-2alpha coverage (its total error is still <2alpha). Review 005's stronger wording was
unsupported and has been corrected. No universal two-sided heterogeneous CP theorem is asserted here;
the established fixed-decision tail results are sufficient for this protocol.

### 8.2 Independent error-budget recalculation and outward rounding

This pass recalculated binomial tails with log-factorial/Stirling PMFs and recurrence summation,
independently of Review 005's compensated log-product binomial PMF. It recalculated all four
hypergeometric boundary tails for A1/A3 using the finite-population recurrence in 7.4. The two binomial
methods agree within 2e-10 absolute error; tabulated digits below are planning/check precision, not
certified arbitrary-precision bounds.

| Component | Largest recomputed boundary tail (approx.) | Outward envelope used |
|---|---:|---:|
| False REP, any arm | Holm strong control under true strict nulls | <=0.005 |
| A1 margin | 0.0016086027 | <0.001609 |
| A2 margin | 0.0016632431 | <0.001664 |
| A3 margin | 0.0001149408 | <0.000115 |

A false REP requires a false discovery, so validation does not add another 0.005 charge. Outside the
margin, false WITHIN is controlled by the applicable single boundary tail. A wrong-side BEYOND label,
if interpreted directionally, is a subset of that same extreme count event. Inside the margin, either
BEYOND side is false; splitting the parameter domain at p0 bounds its near-side tail by the boundary
value and its far-side tail by the p0 value. For A2 the far-side terms are <1e-22, and for A1/A3 the
hypergeometric terms are no larger on this scale. The outward envelopes include them.

The raw numerical sum of the four displayed maxima is approximately **0.0083867866**, before the
negligible far-side terms. Summing the outward envelopes instead gives

    0.005 + 0.001609 + 0.001664 + 0.000115 = 0.008388.

The published **<=0.008389** adds another 0.000001 reporting cushion. It is deliberately looser than
the minimally rounded raw sum, not a new alpha allocation. The previous 0.0083867 was rounded downward.
The 0.01 budget therefore retains at least 0.001611 headroom under the stated conditions.
The model-free A1/A3-only subset is likewise reported outward as <0.001724. Numerical
checks are not proof; the theorem, hypergeometric monotonicity and Holm/union-bound argument establish
the structure. High-precision numerical reference values remain a pre-freeze implementation gate.
Assumptions and exclusions in 7.2 still apply: ideal SRS, conditional input-level independence, correct
implementation and one confirmatory attempt; no A2 population or directional REP guarantee.

### 8.3 QA2 coverage confirmed in specification, not in execution

Proposal 3.7.1 now explicitly requires the same production orchestration, candidate-generation, hashing,
aggregation, evidence-writing/sealing and verifier entry points, with only the small-test geometry and
non-confirmatory fixture identity differing. Its 2,048 candidates and 2,048 independent rehashes leave
104 evaluations for known-answer/boundary probes within the <=4,200 candidate-hash cap; small file
integrity hashes are separate. The acceptance report must itemize actual usage and enforce the cap.

| Path / decision requirement | Required qualification coverage |
|---|---|
| Plan/configuration, prefix and nonce generation | Production entry point and plan validation; fixed fixture key, 8 distinct 76-byte prefixes, LE32 nonces, exact stages and 80-byte candidates; endian/range boundary probes |
| SHA-256 and target comparison | Every candidate/digest independently recomputed; known answers and strict digest<2^248 |
| Cluster/stage accounting | Counts, denominators, ids/stages, stored successes and aggregate totals agree; small geometry end to end, production 3,000x10,000 geometry in synthetic fixtures |
| Evidence lifecycle | Real serialization, configuration/plan identity, environment and qualification Q-entry binding, manifest/sealing, read-only verification, independent pinned digest and retained reports |
| Integrity failure | Byte/count/stage tampering, truncation, deletion, duplication, unlisted files and rewritten local manifest rejected on copies |
| Full statistical matrix | Deterministic full-geometry null, positive, negative, heterogeneous, threshold-adjacent, contradictory and degenerate fixtures; all nine NONE/UNREP/REP x WITHIN/UNDET/BEYOND cells, both directions, Holm/tie cases, secondary dispersion statistics/df/p-values and CP/t disagreements independently recomputed |

This covers the complete A2 execution/evidence path **at small geometry as a specified acceptance
requirement**. It does not demonstrate production-scale performance, completeness of future experiment
outcomes, or successful implementation. The zero-hash fixtures establish statistical path coverage in
specification; they are not substituted for real hashing in the integration test. No QA2 test has run.

### 8.4 Beacon checklist and live-service status

Proposal 3.8.1 specifies mainnet quicknet, chain hash
52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971, pinned public key,
bls-unchained-g1-rfc9380, 3-second period and genesis 1692803367. The future integer R* and
its schedule must be bound in C_pre with an independent witness >=24h before publication.
It specifies exact derivation bytes, uint64 handling, signature/round/chain verification and
randomness=SHA-256(signature). No R* or execution seed has been selected in this pass.

| Before-freeze check | Current status |
|---|---|
| Live /info equals the complete documented chain/key/scheme/period/genesis/id pin; canonical chain hash recomputed | **REQUIRES VERIFICATION**; historical official documentation alone is not live-service confirmation |
| Primary/alternate relay TLS, availability, response schema and exact-round retrieval | **REQUIRES VERIFICATION**; api.drand.sh and api2.drand.sh are specified transport candidates, not confirmed available services |
| Immutable verifier/client revision, dependencies, exact RFC9380 support, historical good/bad signature vectors | **REQUIRES VERIFICATION**; no client installed or signature qualification run |
| Beacon current availability, round-time interpretation and independent witness readiness | **REQUIRES VERIFICATION** before committing a future R* |
| Operational outage handling and archive of retrieval/verification logs | Specified; operator ownership and readiness **REQUIRE CONFIRMATION** |

Outage behavior is nondiscretionary: retry transport for exactly R*, accept only its verifying response,
otherwise wait indefinitely and log the outage after 24h. No later round or other beacon may replace it;
permanent loss leaves the experiment unexecuted. Verification errors/disagreement halt derivation.
This review did not fetch any round randomness or generate a seed.

### 8.5 Preservation, regression status and outstanding blockers

**Python regression tests: NOT RUN.** .venv/pyvenv.cfg names
C:\Users\geova\AppData\Local\Programs\Python\Python311\python.exe; that interpreter is absent.
No environment repair or dependency installation was attempted. Node finite-law calculations above are
numerical review checks, **not pytest results**. Historical 240-pass results remain historical only.

Experiment 001's exact 11-file inventory, nine payload hashes/sizes and manifest self-hash were reverified
read-only. The manifest digest equals the Review 005 digest in 7.4; every file's before/after content hash
is unchanged. v0.2.0 still dereferences to ef595f5c2f2166923fd277def39708409f564419.
No experiment, qualification run, execution configuration, execution seed or beacon reveal was generated.
Local integrity is confirmed; independent historical authenticity and off-machine archive completion
remain operational work.

Outstanding blockers (no implementation or operations authorized by this pass):

1. Final Architect disposition/protocol freeze and Director authorization; provisional D15 acceptance
   and approved QA2 design do not authorize code or execution.
2. Repair/pin the Python environment, then implement and review samplers, A2 path, negative-lift control,
   statistical rules, blinding, registry/amendment binding and evidence schema under a new authorization;
   run Python regressions, G1, deterministic QA2 and G2 only when authorized.
3. Independently author/pin high-precision fixture references and verifier, appoint its owner, and decide
   minimal statistical/evidence verification versus a separately authorized full outcome audit (D7).
4. Complete every live-service/client/witness check in 8.4; precommitment, future round and seed remain
   unselected until the later authorized procedure (D5).
5. Select Experiment 001 archival custodians/destinations/retention, obtain off-machine receipts and
   complete destination and restore checks (D9); no archival transfer has occurred.

Only the three scoped documentation files are eligible for the authorized Review 006 commit. No push,
merge, tag, qualification or experiment execution is permitted. Stop for final Architect review.


## 9. Architecture Review 013: approved A2 deterministic encoding v1

The authoritative byte contract and all three complete KATs are in
[proposal 3.2](../proposals/experiment-002-research-design.md#a2-deterministic-encoding-v1-architecture-review-013).
Protocol identity is proposal revision 8 plus A2 encoding hashlab-exp002-a2-encoding-v1. Bind both in
future configuration, plan fingerprints and pre-registration. The amendment specifies previously open
serialization, labels and key bytes; it preserves hashlab-seed-v1, the 76-byte prefix population,
3,000 prefixes, D/V assignment, LE32 nonce block, all sample sizes and all scientific decision rules.
The Architect independently verified the three KATs before approval. Review 013 does not rerun them.

The existing seed derivation keeps canonical decimal ASCII input and big-endian extraction; only the
new A2 key serialization and index/counter fields use the approved little-endian contract. Experiment
001's 16-byte big-endian random-generator key convention is unchanged. No implementation or sealed
evidence file is modified. No execution seed, round, candidate SHA-256 evaluation or qualification run
is generated by this amendment.

E1 remains blocked until fresh Director PowerShell diagnostics resolve whether the interpreter failure
occurs locally, in Codex, or both, and the approved interpreter passes the 240-test baseline. Python
regressions remain NOT RUN in this pass. Existing beacon/verifier/archival and other execution gates
remain in force; this encoding approval does not satisfy them or authorize confirmatory execution.
