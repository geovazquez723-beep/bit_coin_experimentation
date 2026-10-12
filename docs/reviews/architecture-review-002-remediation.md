# Architecture Review 002: remediation record

> **Current disposition:** Architecture Review 006 final documentation gate is recorded in section 11;
> Review 005 is provisionally accepted and the reduced QA2 design is approved.
> Sections 1–10 are historical records; their universal heterogeneous CP-coverage wording, QA2 cost,
> beacon fallback and rounded FWER claims are superseded as specified there. No freeze, implementation
> or execution is authorized.

- **Review:** Architecture Review 002 of Engineering Assignment 004
- **Verdicts received:**
  - Experiment 001 closeout: **ACCEPTED**, subject to wording cleanup.
  - Experiment 002 proposal: **CONDITIONAL**; revisions required before implementation is authorized.
- **Branch:** `docs/experiment-002-design`, on `v0.2.0` / `ef595f5c2f2166923fd277def39708409f564419`.
  Uncommitted.
- **Scope of this remediation:** documentation only.
  - No experimental code, statistical implementation, configuration or test was changed.
  - No experiment was executed.
  - Experiment 001 evidence was read, never written.
  - No commit, push or tag.
- **Status:** awaiting Architect review. **No implementation authorization has been granted.**

## 1. Findings and corrections

| # | Finding | Correction | Where |
|---|---|---|---|
| 1 | Experiment 001 closeout must consistently distinguish a null-consistent result from proof of the null | Added a terminology table: *null-consistent*, *not detected*, *equivalence*. Every disposition and interpretation sentence is reworded (summary, sections 5, 6, 7, 8, 10, 11, 12 and 13), and the probabilistic `random-bytes-w8` overlap expectation is labelled "not verified". **No observation, statistic, p-value, interval or count changed** | `experiment-001-scientific-review.md`, revision 2 |
| 2 | Combined FWER of 0.01, split 0.005 / 0.005; independently recalculated exact power, confidence levels, joint power and equivalence power near ±2%; classification of simultaneous findings | Difference: Holm at 0.005 (first step 0.001667 two-sided; validation one-sided Holm at 0.005). Margin: Bonferroni at 0.005, giving one 99.667% interval per arm. Combined primary claims ≤ 0.01. All powers recomputed exactly by two independent implementations (section 2). Sample size raised to **15M per arm per stage** to restore joint power. Exhaustive 3 × 3 classification of difference outcome × margin outcome, including `BEYOND` | proposal 3.1, 3.4–3.6 |
| 3 | A2 is a clustered prefix-and-nonce design, not uniform sampling of 80-byte inputs | A2 is defined as a two-stage cluster design. Population: uniformly random 76-byte prefix × nonce block `[0, 10^6)`. 30 i.i.d. prefixes from a keyed BLAKE2b stream; distinctness verified. Every prefix gets the same complete, ascending nonce block. Clusters 0–14 form Stage D, 15–29 Stage V. The populations to which conclusions do and do not apply are listed. The margin interval is the hull of the exact Clopper–Pearson interval and a cluster-level t interval (29 df). The difference test is interpreted as a test of the strict input-level null | proposal 3.1, 3.2 (A2), 3.6 |
| 4 | Formalize overlap and exclusion guarantees; distinguish mathematical, enumerated, deterministic and probabilistic | Five guarantee classes: **M** mathematical, **E** exact enumeration, **D** deterministic verification, **P** probabilistic (bound reported, never zero), **C** computational assumption. Every pair of sets is assigned a class. Revision 1's probabilistic N2–A2 statement became a **D** check. Only uniqueness within N2 remains **P** (≈ 2^-591) | proposal 3.3 |
| 5 | Define the precise A3 population after excluding Experiment 001; verify cardinality; show the sampler is unbiased | `U3 = C3 \ X3`, with `|C3| = 82,128,984` (three independent methods plus brute-force analogs), `|X3| = 60,721` (exact enumeration, digest recorded) and `|U3| = 82,068,263`, with its composition by Hamming weight. Sampler: Knuth's Algorithm S over ranks (exact SRS given an ideal RNG), then an exact hypergeometric split. Proof sketch plus a Monte Carlo demonstration of uniform inclusion. Unranking is verified as a bijection | proposal 3.2 (A3, 3.2.4) |
| 6 | Pre-registered run-attempt and retry policy | Committed run registry; one seed per experiment; deterministic reruns; blinding of failed attempts; failure classes F1 implementation, F2 incomplete, F3 integrity, F4 statistical control, each with its retry rule; a valid attempt is final; a new seed means a new experiment; full disclosure of attempts | proposal 3.8 |
| 7 | Reconcile sample size, power and workload with the revised alpha; assumptions, formulas, independent checks, realistic resources | Formulas and assumptions stated, including the conservative binomial treatment of finite populations. Exact tables from two implementations with a normal cross-check. Workload recomputed: 180.2M SHA-256 evaluations, 240.2M compression blocks. Time estimate revised from "minutes" to **15–45 min single-process**, dominated by candidate generation, based on stated measured and assumed rates | proposal 3.6, 3.12 |
| 8 | Resolve internal contradictions | 18 contradictions in revision 1 resolved (section 3 below) | proposal throughout |

## 2. Revised calculations

All calculations were offline and run outside the repository with `python -I -B`. No SHA-256 success
evaluation was performed.

### 2.1 Error budget

| Family | Budget | Per-test level |
|---|---:|---|
| Difference, discovery (Holm, m = 3) | 0.005 | first step 0.005/3 = 0.001667 two-sided |
| Difference, validation (Holm over flagged arms) | 0.005 | 0.005/j one-sided, with j = number flagged, j ≤ 3 |
| Margin (Bonferroni, m = 3) | 0.005 | 0.001667 per side; interval level 1 − 2(0.001667) = 0.996667 |
| **Total for primary claims** | **0.01** | |

A false `REP` claim requires a false discovery, so it is bounded by 0.005. For each arm, only one of a false
`WITHIN` or a false `BEYOND` is possible, each with one-sided probability ≤ 0.001667. Across 3 arms that is
≤ 0.005.

### 2.2 Sample size

- Difference, planning formula at power 0.95, `e = 2%`:
  `(z_{0.999167} + z_{0.95})² · (1 − p0) / (p0 e²) = (3.144 + 1.645)² · 637,500 ≈ 14.6M`.
- Margin at `ρ = 1`, power 0.9: `(2.935 + 1.645)² · 637,500 ≈ 13.4M` pooled.
- Result: **n = 15M per arm per stage** (30M pooled).
- Revision 1's 13M under the new alpha would give a joint power at ±2% of only 0.857–0.895.

### 2.3 Exact power, n = 15M per stage

Implementations A (`hashlab.statistics.inference`) and B (independent log-space code) agree to every
printed digit.

| Effect | Discovery | Joint discovery and replication (3 flagged … 1 flagged) |
|---|---:|---:|
| ±1.0% | 0.234 / 0.237 | 0.071–0.103 / 0.072–0.104 |
| ±1.5% | 0.685 / 0.693 | 0.517–0.584 / 0.528–0.594 |
| **±2.0%** | **0.954 / 0.958** | **0.926–0.942 / 0.933–0.948** |
| ±2.5% | 0.998 / 0.998 | 0.997–0.998 / 0.998 |

### 2.4 Margin power near the boundary (A1, A3; exact Clopper–Pearson 99.667%; n = 30M)

- `WITHIN` region: `ρ̂ ∈ [0.98849, 1.01136]`.
- P(`WITHIN`) by true `ρ`:
  - 0.980: **0.00166**
  - 0.985: 0.114
  - 0.990: 0.699
  - 0.995: 0.987
  - 1.000: 0.99991
  - 1.005: 0.985
  - 1.010: 0.680
  - 1.015: 0.108
  - 1.020: **0.00166**
- The exact size at the margin boundary is 0.00166 ≤ 0.001667.
- The normal approximation agrees to within 0.011.
- `BEYOND` region: `ρ̂ ≥ 1.02866` or `ρ̂ ≤ 0.97153`.
- P(`BEYOND`): 0.108 / 0.114 at ±2.5%; 0.675 / 0.703 at ±3%; 0.984 / 0.989 at ±3.5%.

### 2.5 A2 hull rule (Monte Carlo, 30 clusters × 10^6, 40,000 replicates). Superseded by section 8

> The 30-cluster A2 design was replaced by Option B in Architecture Review 003. These figures are kept as a
> record only.

P(`WITHIN`) at true `ρ̄`, for between-prefix heterogeneity `τ` = 0 / 0.005 / 0.01:

| `ρ̄` | `τ = 0` | `τ = 0.005` | `τ = 0.01` |
|---|---:|---:|---:|
| 1.000 | 0.9994 | 0.9983 | 0.9846 |
| 1.005 | 0.963 | 0.945 | 0.860 |
| 1.010 | 0.568 | 0.517 | 0.395 |
| 1.020 (boundary) | 0.0010 | 0.0011 | 0.0014 |

All boundary values are within the nominal 0.00167. The t quantile is `t(0.998333, 29) = 3.1982`.

### 2.6 Controls (exact, one-sided 0.001)

| Control | Power |
|---|---:|
| P1, +25%, 200k | 0.99976 |
| P2+, 15M | 0.959 |
| P2−, 15M | 0.963 |
| At least one of P2± detected | 0.9985 |

### 2.7 A3 population and sampler

- `|C3| = 82,128,984`. The complement formula, the split identity and a bit-level DP agree. Brute force on
  16-, 20- and 12-bit analogs agrees.
- Exact enumeration of all 7,000,000 Experiment 001 8-byte candidates (all of them distinct):

  | Generator | In A1 | In A3 |
  |---|---:|---:|
  | `struct-bitrev-w8` | 0 | 60,439 |
  | `pattern-bytes-w8` | 0 | 282 |
  | `seq-be-w8`, `uniform-be-w8`, `struct-gray-w8`, `struct-stride-w8`, `random-bytes-w8` | 0 | 0 |

- `|X3| = 60,721`; digest `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`.
- `|U3| = 82,068,263`.
- Unranking: an exhaustive bijection on the analogs; 200,009 round trips on the full class with 0 failures.
- Algorithm S + hypergeometric split prototype (analog: 2,354-element class, 100 excluded, 300 + 300 drawn,
  6,000 seeds):
  - stage D inclusion uniform: χ² scaled for sampling without replacement p = 0.89;
  - stage V inclusion uniform: p = 0.61;
  - pairwise inclusion 0.01517 against the theoretical 0.01766 (1.5 SE);
  - 0 violations.
- Feistel alternative: p = 0.26 / 0.84. It passed, but it is not recommended for the inferential arms
  (no meaningful proven PRP bound on small domains; 20 times slower).
- **Correction to the engineer's own interim check.** An unscaled χ² on inclusion counts under sampling
  without replacement is under-dispersed by `1 − k/N`, which first produced a misleading p ≈ 1.0. The
  scaled statistic is the one reported.

### 2.8 Workload

180.2M SHA-256 evaluations; 240.2M compression blocks; about 703,900 expected successes. Estimated 15–45
minutes single-process; under 1 GB of memory; about 100 MB of evidence per attempt. Basis and assumptions
are in proposal 3.12.

## 3. Contradictions in revision 1, now resolved

| # | Revision 1 | Revision 2 |
|---|---|---|
| 1 | Total primary alpha ≤ 0.02 (0.01 + 0.01) | 0.01 total (0.005 + 0.005) |
| 2 | P1 threshold 0.01/3, P2 threshold 0.001 | All positive controls at one-sided 0.001 |
| 3 | "P2 equivalent with probability ≤ 0.0033" | ≤ 0.00167, matching the 99.667% interval |
| 4 | "All arms drawn uniformly without replacement by a keyed bijection", while A2 used sequential nonces | A1 and A3: exact SRS (Algorithm S or D). A2: cluster design. Feistel only for controls |
| 5 | H_S "supported" by any replicated deviation, including one inside the margin | Corroboration only for `REP` + `BEYOND`; `WITHIN` falsifies H_S whatever the difference outcome |
| 6 | Five labels; some combinations (unreplicated + equivalence; beyond margin) undefined | Exhaustive 3 × 3 matrix, including the discordant cells |
| 7 | "Overlap audit must report zero" alongside a probabilistic N2–A2 bound | Guarantee classes; N2–A2 is deterministic; only N2-internal uniqueness is probabilistic and reported as a bound |
| 8 | "A1 excludes everything below 2^20" treated as disjointness from all of Experiment 001; `random-bytes-w8` unverified (expected 2 × 10⁻⁴) | Exact enumeration including `random-bytes-w8`: 0 |
| 9 | "N1: exact intersection check (expected about 10⁻⁵)", with no method | Inverse-permutation index check of all 7M candidates (class D) |
| 10 | "First complete run whose gates pass is confirmatory", which permits rerunning until the gates pass | Failure-class policy; F4 forbids same-code reruns; a valid attempt is final |
| 11 | Configuration outline: `permutation_index_range` applied to A2; 13 clusters; 13M; alpha 0.01 + 0.01 | Outline rewritten to match the text |
| 12 | Power 0.94 at 13M under alpha 0.01 per family | Recomputed under 0.005; n = 15M |
| 13 | "Minutes of compute", ignoring generation cost | 15–45 min, with stated measured and assumed rates |
| 14 | TOST at 0.01/3 alongside a "99.33% interval" | One consistent level: 99.667% |
| 15 | A2 equivalence on a pooled binomial interval, ignoring between-prefix heterogeneity | Hull of the exact interval and the cluster-level t interval |
| 16 | Control input streams and their disjointness unspecified | Defined: N1 permutation indices; P controls at indices ≥ 2^63; rejection rules |
| 17 | Proposal section 1 called Experiment 001 "a valid null" | "Valid null-consistent result; does not prove the null" |
| 18 | Comparison table: about 156M hashes, 94% power, "about 18% of Option 0" | 180.2M, joint 0.926–0.948, about 21% |

## 4. Checks performed

| Check | Result |
|---|---|
| Experiment 001 evidence: manifest hashes and self-hash re-verified after all work | No mismatch; directory unchanged (11 files, no `analyses/`) |
| `v0.2.0` tag | Still resolves to `ef595f5c2f2166923fd277def39708409f564419` |
| Tracked files changed | None (`git diff --stat` empty). New or modified untracked files are listed in section 7 |
| Relative links in the three documents | Resolve |
| Offline test suite (`pytest -q -p no:cacheprovider`, bytecode writing disabled) | 240 passed |
| Calculations | Two independent implementations plus normal and Monte Carlo cross-checks (section 2) |

## 5. Decisions remaining for the Director or Architect

| # | Decision |
|---|---|
| D1 | Approve Option 2 as the direction (Option 3 deferred) |
| D2 | Margin `δ` = ±2% |
| D3 | Engine for A2: `sha256` (recommended) or `sha256d` |
| D4 | Confirm the provisional 0.005 / 0.005 split |
| D5 | Seed selection and commitment procedure |
| D6 | Population definitions (A1 range; A2 prefix length, shared nonce block `[0, 10^6)`, 30 clusters; A3 weight cap 6 with the Experiment 001 exclusion) |
| D7 | Execution environment; independent verifier implementation; optional second-machine rerun |
| D8 | Implementation scope (samplers, A2 analysis, classification, negative-lift control, blinding, verifier, registry, schema 2, `v0.3.0`) |
| D9 | Experiment 001 follow-ups (archive; status update of `docs/experiment-001.md`; optional re-execution audit) |
| D10 | Retry ceiling before escalation (proposed: 3 attempts of classes F1–F3) |
| D11 | n = 15M per arm per stage |

## 6. Remaining scientific risks

1. **RNG and PRP assumptions (class C).**
   - SRS exactness for A1 and A3 holds relative to an ideal RNG; MT19937 is assumed adequate.
   - Control streams rely on Feistel and BLAKE2b pseudorandomness.

   Both are unrelated to SHA-256, but neither is proven.
2. **The Experiment 001 exclusion set depends on regenerating the candidates** with `v0.2.0` code. The plan,
   seeds and counters reproduce, but `record_successes: false` means there is no candidate-level record from
   the sealed run to compare against. Mitigation: the optional Experiment 001 re-execution audit (D9).
3. **The A2 margin rule is validated by Monte Carlo** (normal approximation to cluster counts), not
   analytically. Power falls under strong between-prefix heterogeneity: 0.985 at `τ = 0.01`, `ρ̄ = 1`.
   Under heterogeneity, the A2 difference test rejects the strict null even when `ρ̄ = 1`.
4. **Class averages do not bound sub-populations.** For example, A3 is 90% weight-6 inputs.
5. **A1 was motivated post hoc.** This is disclosed and mitigated by fresh, disjoint data, but the choice of
   class still reflects a look at the data.
6. **Throughput estimates come from prototypes.** Two-block hashing was not measured, and Vitter's
   Algorithm D was not prototyped. Both must be measured at G1 and G2.
7. **Blinding and failed-attempt handling depend on the implementation.** An F4 attempt exposes primary
   statistics; the policy requires full disclosure but cannot remove that information.
8. **The ±2% margin is a judgement.** Its relation to a cryptographically meaningful distinguisher is not
   calibrated. Effects inside ±2% stay undetermined unless detected.
9. **Single implementation in the main run.** Mitigated, not removed, by the independent verifier and the
   conditional Experiment 002-R.

## 7. Files

- Updated: `docs/reviews/experiment-001-scientific-review.md` (revision 2, wording only)
- Updated: `docs/proposals/experiment-002-research-design.md` (revision 2)
- Created: `docs/reviews/architecture-review-002-remediation.md` (this document)

At the time of revision 2, all three were untracked. They were later committed as `cde1fe3` on
`docs/experiment-002-design`, as authorized by the revision 2 disposition.

## 8. Architecture Review 003 (Option B for A2), proposal revision 3

> Historical record. Addendum section numbers in this section refer to addendum **revision 2**. Revision 3
> renumbered them (section 9).

**Disposition received:**

- Option B approved for A2: 3,000 independently sampled 76-byte prefixes; nonces `0..9,999` per prefix;
  1,500 prefixes per stage; 30M A2 inputs; `sha256`.
- The ±2% margin and the 0.005 / 0.005 alpha split are unchanged.
- The revision 2 disposition had already accepted the Experiment 001 closeout and approved the research
  direction in principle. Freeze, implementation and execution remain unauthorized.

| # | Required work | Resolution | Where |
|---|---|---|---|
| 1 | Proposal revision 3 with Option B throughout | Population, prefix derivation (3,000 prefixes), stage allocation (clusters 0–1,499 / 1,500–2,999), 2,999 df, N2 pseudo-clusters matched to the A2 analysis path, overlap guarantees (3,000-prefix distinctness check; N2 membership check against the 3,000 prefixes and nonces `0..9,999`), evidence content (per-cluster counts), workload, the A2 reading of the 9-cell matrix, configuration outline, decisions D3 and D6 marked decided, new decisions D12 and D13 | proposal 3.1–3.14, 4, 5 |
| 2 | Recalculate A2 power and operating characteristics; do not assume unchanged power | Direct simulation with exact per-cluster binomial counts and the full D / V / margin procedure, plus an independent sufficient-statistic engine; difference and replication power, `WITHIN` and `BEYOND` power, and size at the boundaries | addendum 1.4; proposal 3.6 |
| 3 | False `WITHIN` and false `BEYOND` under homogeneous and heterogeneous populations, including mixtures at 20%, 5%, 1%, 0.1% and rarer | Simulated: homogeneous; normal, t₃ and lognormal variation; mixtures at 20%, 5%, 1%, 0.1%, 0.01% and the feasibility limit 0.0078%. Exact two-point lower bounds for the rare mixtures | addendum 1.3, 1.4 |
| 4 | Distinguish the strict input-level null from the population-average estimand | Three objects defined: `H0_A2`, `ρ_A2^cond` and `ρ̄_A2`. A2 difference flags are reported as strict-null rejections only | proposal 3.1, 3.2, 3.4; addendum 1.2 |
| 5 | Justify any population-level guarantee, or restrict the claim; never present simulation as proof | **Restricted.** A uniform guarantee for `ρ̄_A2` is shown impossible (two-point argument; ≥ 0.79 false `WITHIN` at the feasibility limit). The confirmatory claim moves to `ρ_A2^cond`, whose error bound is proven given the input-level Bernoulli model (hull ⊆ Clopper–Pearson; Hoeffding 1956). Population statements are model-conditional under H-A2, supported by simulation only, and labelled as such | proposal 3.2; addendum 1.3, 1.6; decision D12 |
| 6 | Reassess the combined 0.01 claim with conditional assumptions | ≤ 0.01 (exact-size value 0.00995) for confirmatory claims, conditional on the stated models, a correct implementation and a single attempt. A2 population statements are excluded | proposal 3.5; addendum 2 |
| 7 | Preserve the A3 procedure, Experiment 001 evidence, `v0.2.0` and the retry safeguards | Unchanged. Evidence re-verified; tag unchanged; proposal 3.8 untouched | addendum 3; section 4 checks |
| 8 | Update the addendum and this record with resolved, conditional and blocking status | Addendum section 4 status table; this section | addendum 4 |

**Key A2 numbers** (addendum 1.3, 1.4):

| Quantity | Value |
|---|---|
| Errors about `ρ_A2^cond` | ≤ 0.0016632 (proven given the model); simulations agree |
| Population-level false `WITHIN` | 0.0012–0.0020 under regular heterogeneity or prevalence ≥ 5%; 0.0041 at 1%; 0.050 at 0.1%; 0.74–0.79 at ≤ 0.01% |
| Population-level false `BEYOND` | ≤ 0.0019 |
| Homogeneous power | equal to A1 and A3 for difference tests; `WITHIN` power 0.99993 at `ρ = 1` |
| Power under heterogeneity | reduced; for example `WITHIN` 0.22 at lognormal τ = 0.3 (decision D14) |

**What changed in the decision rules:** nothing. The thresholds, intervals, budgets and the 9-cell matrix
are unchanged. The only substantive change is the **scope of A2's confirmatory margin claim**
(evaluated-inputs estimand). It is submitted for acceptance as D12. N2's pseudo-cluster analysis adds no
hashes and no primary claims.

## 9. Architecture Review 004 (final protocol clarification), proposal revision 4

**Disposition received:**

- The Architect accepts the research direction, A2 Option B and the restricted A2 scope in principle.
- The Director provisionally approves D2, D4, D10, D11, D12, D13 and D14, subject to the clarifications
  below.
- Documentation and offline verification only. No seed is selected.

| # | Required work | Resolution | Where |
|---|---|---|---|
| 1 | Distinguish the observed fraction, the model mean probability and the unsampled population fraction | Three symbols, `f_a`, `μ_a` and `θ_a`, defined and used throughout. `f_a` is never the object of a claim | proposal 3.1.1; addendum 1.1 |
| 2 | State which quantity each A1, A2 and A3 hypothesis, interval and classification addresses | Per-element mapping table. Difference claims: strict model null, all arms. Margin: `θ` (design-based) for A1 and A3; `μ_A2` (model-based) for A2 | proposal 3.1.2, 3.4; addendum 2.1 |
| 3 | Verify Clopper–Pearson conservativeness under heterogeneity; theorem, conditions and one-sided tails; or an alternative | Theorem identified (Hoeffding 1956, the result stated in its abstract; revision 3's "Theorem 4" citation corrected). Both one-sided tails derived, with exact conditions (`d ≤ np − 1`, `d ≥ np + 1`), checked at every protocol boundary, and verified numerically (29,230 exact cases; protocol-scale mixtures). Full text not accessed. **Alternative:** a Chernoff interval with a self-contained proof (D15). **Additionally:** A1 and A3 no longer rely on the theorem; they are proven design-based by exact hypergeometric computation | proposal 3.2 (A2), 3.2.5; addendum 1.2 |
| 4 | Recheck the combined 0.01 bound | ≤ 0.005 + 0.0033867 = **0.0083867**, in an explicit joint probability space. The model-free reading covers only A1 and A3. Conditions and exclusions listed | proposal 3.5; addendum 2 |
| 5 | A2-path positive control as a separate qualification test | QA2 (`002-qual-a2`): pre-freeze; separate configuration, seed and evidence; predeclared pass criteria with P(pass \| correct code) of 0.99992 and > 0.9999; exact recomputation check; non-discretionary repeat policy | proposal 3.7.1; addendum 4 |
| 6 | Exact seed-commitment and attempt-registry procedure, without generating a seed | Steps S1–S6: freeze; `C_pre`; external witness before beacon round `R*`; derivation formula; `C_seed`; registry-bound attempt. Registry entry types, binding of each entry into the evidence, and a completeness audit. **No seed generated** | proposal 3.8; addendum 5 |
| 7 | Update the proposal and addendum; record changed conclusions and unresolved limitations | Proposal revision 4; addendum revision 3 with its changed-conclusions table (C1–C7) and status table (R1–R13) | addendum 0, 6 |

**Changed conclusions** (addendum C1–C7):

- A2's confirmatory quantity is the model mean `μ_A2`, not the observed fraction.
- A1 and A3 claims are design-based, with bounds tightened to 0.0016086 and 0.0001149.
- The Hoeffding citation is corrected.
- `REP` is no longer directional; the earlier 4.1 × 10⁻⁶ direction bound assumed homogeneity.
- The combined bound is now 0.0083867.
- D13 is now a separate qualification test.
- The seed procedure is specified.

**Unresolved:**

- D15: accept the citation, or adopt the Chernoff fallback, which would change A2's decision rule.
- D5: the beacon source.
- D7, D8, D9.
- Independence (the model assumption) remains, by construction, the basis of every difference claim and of
  A2's margin claim.

## 10. Architecture Review 005: independent review and proposed disposition

**Scope and starting state.** Documentation and offline calculations only, on clean branch
`docs/experiment-002-design` at `1c046cf`. The previous reasoning was independently checked against
a readable primary research source and new finite-law numerical calculations. No seed was generated,
no Experiment 002 code or qualification was implemented or run, and no commit/push/tag/branch change
was made. Experiment 001 remains scientifically closed as null-consistent.

### 10.1 Decision register for Architect review

| Item | Proposed disposition | Approval / remaining dependency |
|---|---|---|
| D15: heterogeneous Bernoulli inference | Retain fixed CP/t hull classifications. All four decision-tail inequalities are valid by the verified Hoeffding extremal theorem. Withdraw universal heterogeneous CP confidence-set coverage; explicit n=2 counterexample in addendum 7.1 | Architect accepts cited-theorem basis; no self-contained proof of the CP extremal theorem supplied. Elementary Chernoff alternative and homogeneous power documented in 7.3 |
| FWER precision | Existing rule satisfies 0.01 budget under stated models. Replace downward-rounded 0.0083867 with outward <=0.008389 | No change to 0.005/0.005 allocation, 15M per stage, 30M pooled, margin or integer cutoffs |
| D13 / QA2 | Replace 90M extra hashes with committed synthetic per-cluster fixtures, independent recomputation, all nine labels, and <=4,200 small integration/known-answer hashes plus file-integrity hashes | Proposed specification only; no fixtures/test implementation or execution authorized here. Future deterministic pass required before freeze |
| D5 / seed governance | Pin mainnet drand quicknet tuple and exact future R*, byte-exact v1 derivation, >=24h witnessed precommitment; transport fallback for same R* only, otherwise wait | Official documented parameters verified; live /info unavailable in this review. Confirm live tuple, relay availability, pinned client/version and historical signature vectors before freeze; no actual R* or seed selected |
| D7 / independent verifier | Independent read-only evidence/statistical verifier, external digest anchor, exact aggregation/labels and separately checked numerical routines | Appoint owner and pin source/environment; decide full outcome audit scope. Checking only successes cannot detect omitted successes |
| D8 / implementation | Deterministic QA2 replaces per-prefix biased hashing engine needed solely for qualification; registry/amendment binding retained | Implementation remains unauthorized; G1, QA2 and G2 are future gates |
| D9 / Experiment 001 archive | Exact-byte copies to two off-machine destinations, independent digest witness, destination checks and restore verification | Choose custodians/destinations/retention. Procedure documented only; no transfer or archive completion claimed |

### 10.2 Mathematical conclusions and assumptions

Addendum 7 is the current mathematical disposition. Pointwise binomial tail domination is valid only in
the stated outside-mean regions; convex order alone does not prove it. The unfinished hinge calculation
was not a disproof and was not used as a guarantee. A primary paper now verifies the necessary theorem
statement. The self-contained MGF/AM-GM proof establishes the optional Chernoff alternative, not the CP
extremal theorem. Chernoff-only homogeneous WITHIN power at ratios 1, 1.005 and 1.01 is 0.99897,
0.93764 and 0.43097; a retained t hull can only reduce those values. It is not adopted.

The current CP/t rule needs independent input-level Bernoulli outcomes for A2 and the strict-null tests;
A1/A3 margin conclusions need exact SRS under ideal RNG. Single confirmatory attempt and correct code
remain necessary. A2 population generalization is non-confirmatory; no arbitrary-heterogeneity power
promise is made. REP is non-directional. Review 005 also corrects the earlier suggestion that reduced
variance alone proves finite-population tail/power ordering, and the Berry–Esseen phrasing that could be
misread as a lower bound on actual approximation error.

### 10.3 Offline checks and preservation

| Check in this review | Result |
|---|---|
| Git starting branch / HEAD / worktree | Expected branch, 1c046cf, clean |
| Heterogeneous Bernoulli finite-law checks | 21,840 vectors, 116,520 strict-outside-band comparisons; max discrepancy 2.22e-16 (roundoff), not proof |
| Four 30M binomial decision tails and adjacent counts | Reproduced; decision-side tails below 1/600, adjacent excluded counts above it |
| A1/A3 hypergeometric boundary checks | Reproduced by independent recurrence; outward bounds <0.001609 and <0.000115 |
| Chernoff cutoffs and homogeneous power | Independently calculated from KL inversion and finite binomial sums; hull power not conflated with Chernoff-only power |
| Python/pytest | **Not run**: repository venv references missing Python311; python/py/python3 unavailable. Historical 240-pass result in section 4 is not a result of this review |
| Experiment 001 evidence | Nine payload hashes/sizes, manifest self-hash and exact 11-file inventory verified read-only; before/after byte hashes unchanged; no analyses directory |
| v0.2.0 | Annotated tag object 662bb21c714afd9b560f40845c6780132baf3d6b; dereferenced commit ef595f5c2f2166923fd277def39708409f564419 unchanged |
| Documentation checks | git diff --check passed; relative file links in all three documents resolve |
| Final scope | Only the three requested Markdown documents modified; no implementation, run, seed, commit, push, merge, tag or branch switch |

Numerical checks use floating-point recurrences of exact finite distributions, not arbitrary-precision
certification or simulation. Full method and evidence manifest digest are in addendum 7.4. Freeze should
pin high-precision QA2 references. Local manifest agreement establishes integrity against that manifest;
authenticity against an independent historical witness and off-machine archive completion remain open.

**Files changed:** proposal revision 5; protocol-readiness addendum revision 4; this remediation record.
The new specifications are in proposal 3.7.1 and 3.8.1–3.8.3. No unrelated work existed initially or was
modified. Git remains on docs/experiment-002-design at 1c046cf with these three documentation edits
uncommitted. D5, D7, D8, D9 and Architect acceptance of D15 remain open as described above.

**Stop for Architect review. Protocol freeze, implementation and execution remain unauthorized.**

## 11. Architecture Review 006: final documentation gate

**Authorization received:** Review 005 provisionally accepted; reduced QA2 design approved. Documentation
finalization and a commit containing only the three scoped documents are authorized. No push, merge,
tag, implementation, qualification, experiment or execution seed is authorized.

| Gate item | Final verification / specification status |
|---|---|
| A2 one-sided thresholds | Auditable table in addendum 8.1: W_HI 118,519<=119,530.25; W_LO 115,839>=114,844.75; B_HI 120,546>=119,532.25; B_LO 113,851<=114,842.75. Independent Bernoulli probabilities, integer thresholds and the one-count gap conditions are explicit; theorem source rechecked |
| CP coverage wording | Review 006 corrects Review 005: the n=2 example disproves one-sided alpha control only; it does not disprove two-sided 1-2alpha coverage. No universal two-sided CP guarantee is asserted; fixed classification results are unaffected |
| Combined FWER | Independently recalculated raw boundary-maxima sum approximately 0.0083867866; outward envelopes sum to 0.008388; published <=0.008389 adds 0.000001 reporting cushion. Conditions/exclusions retained; no sample size, cutoff or alpha change |
| QA2 coverage | Approved <=4,200-hash specification explicitly uses production execution/evidence entry points at small geometry; full-geometry synthetic fixtures cover all nine statistical cells and boundary/contradictory cases. Qualification NOT RUN |
| Beacon governance | Quicknet chain/key/scheme/genesis/period, future witnessed R*, exact derivation and signature verification specified; fallback only for transport of the same round. Live-service/client/witness checks explicitly REQUIRE VERIFICATION (addendum 8.4) |
| Python regression tests | **NOT RUN**: .venv references missing Python311 interpreter. Node finite-law checks are numerical review calculations, not pytest results |
| Experiment 001 | Exact 11-file inventory, all nine payload hashes/sizes, manifest self-hash and Review 005 manifest digest verified; before/after file hashes unchanged; v0.2.0 dereferences to ef595f5c2f2166923fd277def39708409f564419 |
| Prohibited work | No implementation, qualification or experiment run, execution configuration/seed generation, beacon reveal, push, merge or tag performed |

Outstanding implementation/operational blockers:

- Final Architect/protocol disposition and Director authorization; provisional acceptance does not authorize execution.
- Repair/pin Python; complete separately authorized implementation, regressions, G1, QA2 and G2.
- Independently author/pin high-precision fixture references and verifier; appoint owner and settle full outcome audit scope (D7).
- Verify live /info, relay service/schema, pinned RFC9380 client and historical verification vectors, and witness readiness before future precommitment/round selection (D5).
- Choose archival custodians/destinations/retention and complete off-machine receipts and restore checks for Experiment 001 (D9).

**Scoped files:** proposal revision 6, protocol-readiness addendum revision 5, and this remediation record.
The Review 005 edits and this finalization pass form one authorized documentation commit on
`docs/experiment-002-design`. Verify the complete diff and staged inventory before committing; report the
resulting commit hash separately (a commit cannot include its own hash). No other paths are included.
Stop after the commit and verification summary for final Architect review.
