# Experiment 002: statistical review and protocol-readiness addendum

- **Revision:** 2 (Architecture Review 003). Revision 1 evaluated the 30-prefix A2 design; this revision
  evaluates the approved **Option B** (3,000 prefixes × nonces `0..9,999`).
- **Basis:** `docs/proposals/experiment-002-research-design.md`, revision 3.
- **Status:**
  - The research direction is approved in principle.
  - **Protocol freeze, implementation and execution are not authorized.** No execution seed has been
    selected.
  - No sample size, error budget or decision rule was changed. One claim was **restricted**: A2's
    confirmatory margin claim now refers to the evaluated inputs (section 1.6). This restriction is
    submitted for review as decision D12.
- **Method:** offline calculations outside the repository, with `python -I -B`. No SHA-256 success
  evaluation, and no experiment, was run. Simulation results are evidence, **not proofs**, and are labelled
  as such.

## 1. A2 (Option B): estimands, guarantees and operating characteristics

### 1.1 Design

- 3,000 i.i.d. uniform 76-byte prefixes, each with the complete nonce block `0..9,999`, engine `sha256`.
- Clusters `0..1,499` form Stage D and clusters `1,500..2,999` form Stage V. Each stage has 15M inputs; the
  arm has 30M.
- Per-cluster ratio: `r_j = k_j / (10^4 · p0)`. The expected count per cluster under the null is 39.06.

### 1.2 Two nulls and two estimands

| Object | Definition | Used by |
|---|---|---|
| Strict input-level null `H0_A2` | every evaluated input succeeds independently with probability exactly `p0` | difference analysis (D, then V) |
| `ρ_A2^cond` | mean success probability of the 30M evaluated inputs, divided by `p0`, under the input-level Bernoulli model (input `i` succeeds independently with probability `p_i`) | **confirmatory** margin analysis |
| `ρ̄_A2` | expected success fraction over a uniformly random prefix with nonces `0..9,999`, divided by `p0` | model-conditional, **non-confirmatory** population statement |

The relationships:

- Heterogeneity between prefixes with `ρ̄_A2 = 1` makes `H0_A2` false. The difference test may then reject
  correctly, while `ρ_A2^cond ≈ ρ̄_A2 ≈ 1`.
- `ρ_A2^cond` is a random quantity, because it depends on which prefixes were drawn. It approximates
  `ρ̄_A2` unless the deviation is concentrated in rare prefixes.

### 1.3 What is proven, and what is not

1. **Difference analysis (proof, given the model).** Under `H0_A2`, every stage total is exactly
   Binomial(15M, `p0`), whatever the clustering. The exact tests therefore have their exact sizes:

   | Test | Size |
   |---|---:|
   | Two-sided discovery | 0.0016560 |
   | One-sided validation | 0.0049685 |

2. **Margin claims about `ρ_A2^cond` (proof, given the input-level Bernoulli model).**
   - The hull's `WITHIN` event is a subset of the Clopper–Pearson `WITHIN` event, and the same holds for
     `BEYOND`.
   - The pooled count is Poisson-binomial with mean `n·p̄`. By Hoeffding (1956, Theorem 4), for `c ≤ n·p̄ − 1`,
     `P(S ≤ c)` is at most the binomial value with the same mean; the upper tail is symmetric.
   - At the margin the decision boundaries are at least 1,000 counts from the mean (for example
     `W_HI = 118,519` against 119,531).
   - Hence, for **any** heterogeneity:

     | Event | Bound |
     |---|---:|
     | P(false `WITHIN`) for `ρ_A2^cond` | ≤ 0.0016629 |
     | P(false `BEYOND`) for `ρ_A2^cond` | ≤ 0.0016632 |

3. **No uniform guarantee for `ρ̄_A2` (proof by a two-point argument).**
   - Let `Q_π` be the prefix population in which a fraction `π` of prefixes have `ρ_j = 1 + 0.02/π` and the
     rest are exactly null. Then `ρ̄ = 1.02`. Feasibility needs `ρ_j ≤ 256`, so `π ≥ 0.02/255 = 7.84 × 10⁻⁵`.
   - Couple the samples under `Q_π` and under the null population: they coincide whenever no affected
     prefix is drawn, which has probability `(1 − π)^3000`.
   - So for any decision rule, `P_Q(WITHIN) ≥ P_null(WITHIN) − [1 − (1 − π)^3000]`.

   | `π` | P(no affected prefix) | Lower bound on false `WITHIN` (any rule with `P_null(WITHIN) = 0.99987`) |
   |---|---:|---:|
   | 0.01 | 0.0000 | none (trivial) |
   | 0.001 | 0.0497 | ≥ 0.0496 |
   | 0.0001 | 0.7408 | ≥ 0.7407 |
   | 7.84 × 10⁻⁵ (all-success prefixes) | 0.7903 | ≥ 0.7902 |

   **No interval procedure** with useful power at J = 3,000 can control false `WITHIN` for `ρ̄_A2` uniformly
   over all prefix populations. The cluster t interval cannot either.
4. **The cluster t interval has no finite-sample guarantee** even for well-behaved populations at this tail
   level.
   - The Berry–Esseen error bound, `0.4748 · E|X − μ|³ / (σ³ √J)` with `E|X − μ|³ / σ³ ≥ 1`, is at least
     0.0087 at J = 3,000.
   - That is larger than the 0.00167 tail being controlled.
   - Its population-level behaviour is therefore known **only from simulation** (1.4).

### 1.4 Operating characteristics (simulation evidence)

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
   bounds of 1.3(3) and agree across both engines.
4. **Errors about the confirmatory estimand `ρ_A2^cond`.** In every cell they are at or below the proven
   bound, within simulation error:
   - largest observed rate 0.00177 ± 0.00012, in the homogeneous boundary case, where `ρ_A2^cond = ρ̄ = 1.02`
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
- Using Clopper–Pearson alone for the confirmatory `ρ_A2^cond` label would raise this power (0.93 at
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

### 1.5 Degrees of freedom and assumptions

- **Cluster t interval:** `J − 1 = 2,999` df, pooled over both stages. Prefixes are i.i.d. and stage
  assignment is fixed by index, so the 3,000 `r_j` are i.i.d. under the population model.
  `t_{0.998333, 2999} = 2.9376`, against `z = 2.9352`.
- The between-cluster variance absorbs **any** dependence among nonces within a cluster.
- **Assumption H-A2** (population statements only): the deviation of per-prefix rates from `ρ̄_A2` is not
  concentrated in prefixes of prevalence below about 5%.
  - Even under H-A2, the population-level error is approximately nominal (≤ about 1.2×), not exactly
    nominal (Table 1).
  - H-A2 cannot be verified from the data. The secondary heterogeneity test (χ² over clusters, per stage)
    detects only gross violations.

### 1.6 Restriction of the A2 claim (decision D12)

- A2's **confirmatory** margin labels refer to `ρ_A2^cond` and carry the qualifier
  `estimand: evaluated-inputs`.
- A population sentence ("under H-A2, `ρ̄_A2` is also within ±2%") may accompany a `WITHIN` or `BEYOND`
  label. It is **model-conditional and non-confirmatory**.
- A2 difference flags are reported as rejections of the strict input-level null.

## 2. Family-wise error after the A2 change

### 2.1 Claims

The classification cells and the propositions they assert are those of revision 1 of this addendum, with
A2's propositions re-scoped:

| Proposition | A1, A3 | A2 |
|---|---|---|
| Deviation | strict null false (direction observed) | strict input-level null false; the direction refers to the evaluated inputs |
| Within | `|ρ_a − 1| < δ` | `|ρ_A2^cond − 1| < δ` |
| Beyond | `ρ_a ≥ 1 + δ` or `ρ_a ≤ 1 − δ` | the same for `ρ_A2^cond` |

### 2.2 Bound

- **Difference family.** A false `REP` requires a false discovery. Holm controls this at 0.005 under any
  dependence. Exact, under the strict null with 3 independent arms: 0.0049599. A wrong-direction `REP` has
  probability ≈ 4.1 × 10⁻⁶ per arm.
- **Margin family.** Per arm, a false `WITHIN` or false `BEYOND` has probability at most
  `max(0.0016629, 0.0016632) + η`, with `η ≈ 10⁻²²`:
  - for A1 and A3: exact Clopper–Pearson, and conservative under the finite-population model by exact
    hypergeometric computation;
  - for A2: about `ρ_A2^cond`, via 1.3(2).

  Across 3 arms: ≤ 0.0049897.
- **Combined:**
  `P(any false confirmatory claim) ≤ 0.005 + 0.005 = 0.01`. With exact sizes, ≤ **0.00995**.

### 2.3 Conditions and exclusions

The 0.01 bound holds **conditionally** on:

- the input-level Bernoulli model for the difference tests and for A2's `ρ_A2^cond` (the null model of
  HASHLAB, extended to arbitrary per-input probabilities for A2);
- the finite-population SRS model, or the Bernoulli model, for A1 and A3, with the sampler's RNG treated as
  ideal;
- a correct implementation (gate G1);
- **a single confirmatory attempt** (proposal 3.8). An accepted F4 rerun after primary statistics were seen
  falls outside the bound.

It **excludes**:

- population statements about `ρ̄_A2` (approximate under H-A2 only; 1.3, 1.4);
- secondary tests, controls and Experiment 002-R.

## 3. A3 exclusion-set verification (unchanged)

The procedure and results of revision 1 are retained without change:

- input provenance against the sealed manifest;
- three derivations: package, clean room, analytic;
- acceptance values: `struct-bitrev-w8` 60,439; `pattern-bytes-w8` 282; all others 0; `|X3| = 60,721`;
  digest `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`.

**Retained limitation:** the sealed run did not record individual candidates (`record_successes: false`), so
`X3` is regenerated, not observed. An optional deterministic re-execution of Experiment 001 would check the
1,000 sealed per-batch success counts; it needs Director approval.

Effect: on provenance ("fresh data") only, not on A3's statistical validity.

## 4. Protocol-readiness status

| # | Concern | Status | Affects confirmatory validity? |
|---|---|---|---|
| R1 | A2, 30-prefix design: false `WITHIN` uncontrolled under rare-prefix effects | **Resolved, superseded** by Option B together with the claim restriction | n/a |
| R2 | A2 population-average guarantee | **Resolved by restriction.** No uniform guarantee is possible (proven); the confirmatory claim is restricted to `ρ_A2^cond` (D12, pending acceptance) | No, for confirmatory claims once D12 is accepted. Population statements are model-conditional |
| R3 | A2 strict null vs average estimand | **Resolved:** distinguished in the proposal (3.1, 3.2, 3.4) and here (1.2) | No |
| R4 | A2 false `BEYOND` under heterogeneity (revision 1, L3) | **Resolved:** simulated (1.4) | No |
| R5 | A2 cluster-t small-sample behaviour (revision 1, L2) | **Resolved as far as possible:** 2,999 df; simulation within error for regular heterogeneity; no finite-sample proof (1.3(4)) | No, for confirmatory claims (they do not rely on the t interval) |
| R6 | Combined 0.01 FWER | **Resolved, conditional:** bound re-derived with explicit conditions (2.3) | Conditional on the stated models and a single attempt |
| R7 | A3 exclusion set regenerated, not observed | **Conditional** (documented limitation) | No, provenance only |
| R8 | Implementation not written (samplers, hull rule, classification, blinding, N2 pseudo-clusters) | **Blocking for execution**, by design, until G1 | Yes, until G1 |
| R9 | F4 rerun path exposes statistics | **Conditional** (policy and disclosure) | Yes, if used |
| R10 | Decisions D2, D4, D5, D7, D8, D9, D10, D11, D12, D13, D14 | **Open** | D12 is required for the A2 claim scope; D5 (seed procedure) is required before freeze |
| R12 | A2 power under strong prefix heterogeneity (`WITHIN` 0.22 at `ρ̄ = 1`, lognormal τ = 0.3) | **Conditional:** known trade-off of the hull rule (D14) | No. It reduces informativeness, not validity |
| R11 | Scope limits (class averages; A1 motivated post hoc; ±2% margin is a judgement; throughput estimates) | **Accepted limitations** | No |

**Readiness.** No statistical blocker remains in the design, provided D12 is accepted. Protocol freeze still
requires the open decisions, and execution still requires implementation and the G1 and G2 gates.

**Stop for Architect review. No implementation or experiment execution is authorized.**
