# Architecture Review 032 — E3 secondary completion for Review 033

Date: 2026-10-12 (America/Los_Angeles).

Review 032 accepts the E3 foundation following direct Architect source/test
review and confirms authorization under Review 031 to implement approved
`hashlab-exp002-secondary-statistics-proposal-v2`. No separate Review 031 file
was present locally; the user's Review 032 instruction supplies the explicit
authority and identifies the exact specification. No additional scientific
design choices or secondary family changes were introduced.

## Branch and complete E3 inventory

Branch remains `feat/experiment-002-e3`, HEAD remains accepted E2 milestone
`b8b74f83819be74e0c0c2f66916740331b850692`. No E3 commit exists.

Complete uncommitted E3 inventory (ten files, including earlier foundation work):

| File | Review 032 disposition |
|---|---|
| `src/hashlab/experiments/exp002_foundation.py` | Authorized v2 binding and A3 accounting/validation additions |
| `src/hashlab/statistics/exp002_secondary.py` | New pure exploratory count engine |
| `tests/test_exp002_e3.py` | Update only schema/binding expectations and synthetic A3 accounting |
| `tests/test_exp002_secondary.py` | New focused qualification and isolation tests |
| `tests/exp002_secondary_reference.py` | New independent high-precision reference implementation |
| `tests/fixtures/exp002-secondary-v2-reference.json` | New pinned explicit synthetic numerical fixtures |
| `tools/build_exp002_secondary_references.py` | Reproducible synthetic reference builder |
| `docs/proposals/experiment-002-secondary-statistics-proposal.md` | Update current authorization/status; retain v2 statistical specification |
| `docs/reviews/architecture-review-029-e3-foundation.md` | Append Review 032 continuation; preserve historical findings |
| `docs/reviews/architecture-review-032-e3-secondary.md` | This Review 033 handoff |

All ten remain untracked relative to the accepted E2 commit. Pre-existing
`.venv313/` is excluded. No tracked modifications or staged entries. No push,
merge, tag, release identity, execution seed, beacon round or precommitment
was selected. Temporary integrity snapshots and pytest outputs are inside the
already ignored qualified Python environment.

## Statistical contracts and fixed family

`analyze_secondary(accounting)` accepts only complete, validated v2 accounting.
It returns an exploratory-only result envelope with approved identity, .01
alpha, Holm correction, fixed family size 36 and immutable ordered outcomes.
No stage pooling or selection by primary flags occurs. Each outcome retains
exact rational Q, df, raw p/log-p, explicit underflow status, adjusted p/log-p,
flag, role and not-testable reason. The laws are approximate model references,
not finite-population guarantees or cryptographic/economic conclusions.

Canonical fixed order:

1. A1,A2,A3,N1,N2, each D then V, each leading-zero, first-byte, last-byte: 30.
2. A2-D,A2-V,N2-D,N2-V cluster dispersion: four.
3. A3-D,A3-V fixed weight-group heterogeneity: two.

Positive-control digests do not enter this family. Non-testable slots remain
present with no raw Q/df/p/log-p and correction-only p=1. They are never flagged.
No adaptive merging, group removal, slot deletion or hidden second hypothesis
is implemented. Histograms/counts reject negative, fractional, boolean,
missing/extra and over-capacity values.

`leading_zero` uses integer selection of the largest K with n>=5*2^K, bins
0..K-1 plus pooled tail, exact Pearson Q and K df. `uniform_byte` uses 256
fixed bins, n>=1280 and 255 df. Empty observed bins remain valid when expected
counts qualify. Neither method fits probabilities from observed histograms.

`cluster_dispersion` requires 1,500 explicit clusters with 10,000 trials each.
It fits p_hat=sum(K_j)/15M and computes exact
`sum((K_j-10000*p_hat)^2)/(10000*p_hat*(1-p_hat))`, with **1499 df**.
Expected successes/failures >=5 are checked as integer stage totals >=7500
and <=14,992,500, including exact equality. Degenerate fitted variance or
under-threshold expectations is not-testable; unequal/missing geometry or
impossible counts is an error. Constant nondegenerate cluster counts give
Q=0,p=1. Only the upper-tail dispersion test is used.

`a3_groups` aggregates six raw weight trial/success counts exactly into
weights 1–4, weight 5, weight 6. The eligible group populations remain
(631413,7407537,74029313). It forms the 2×3 success/failure Pearson statistic
with **2 df**, fits the common rate and computes p=exp(-Q/2). Qualification
uses integer comparisons N_g*S>=5*n and N_g*(n-S)>=5*n for every fixed group.
An empty group, zero fitted variance or expected count below five makes the
whole slot not-testable; there is no reduced-df alternative. A zero observed
count is permitted when the expected cells qualify.

Holm adjustment uses a monotone running maximum in log space, retaining
underflow tails and the full 36-member multiplier. Ties use stable canonical
order. Strict comparison to .01 is unchanged. `holm_exact` independently
exposes the 36-probability rational correction contract, including exact
equality/non-rejection. For numerically calculated tails, an adjusted log-p
within 2e-12 of log(.01) raises ArithmeticError pending higher precision;
it is never rounded into a flag. Tests cover strict equality and adjacent
rational values at every one of the 36 Holm ranks.

## Authorized schema/accounting changes

- `hashlab-exp002-seedless-plan-v1` -> **v2**, including fingerprint domain
  `hashlab-exp002-seedless-plan-v2` followed by NUL and canonical JSON.
  The secondary binding contains exact approved identity, .01/Holm, role,
  all 36 ordered slots, fixed groups and group population counts.
- `hashlab-exp002-accounting-v1` -> **v2**, with required `secondary_identity`.
  Each stream now has `weight_trials` and `weight_successes`: six ordered
  integer counters for A3 and explicit nulls for every other arm.
- Accumulation determines raw Hamming weight from the already supplied A3
  candidate record; it performs no candidate generation or hash evaluation.
  Validation checks lengths, ranges, stage totals and trial/success consistency,
  group population limits, known eligible weight-one cap 12, and necessary
  pooled D/V weight-one/group limits. The complete eligible per-weight audit
  remains an external reconstruction responsibility; group counts do not
  certify eligibility or uniqueness.
- Success-record read-validation independently recomputes raw-weight success
  totals from supplied record bytes and requires exact agreement with accounting.

Old/missing identities and v1 plan/accounting structures fail closed; there is
no automatic migration or coercion. Candidate record v1, success record v1,
execution metadata v1, accepted Config and protocol identities are unchanged.
Existing plan fingerprint binding prevents an old manifest from authenticating
new accounting as an unchanged plan. No operational full plan or seed is built.

## Independent numerical qualification

The pinned 1,152,727-byte JSON contains **27** individual reference vectors and
two complete 36-slot families with explicit accounting arrays, exact rational
statistics, df, raw p/log-p and independent adjusted p/flags. All are visibly
synthetic sufficient statistics, not observed research data.

The reference module and builder import no HASHLAB code. Reference Pearson
statistics use explicit success/failure cells, independently of the production
cluster and A3 simplified formulas. Probabilities use 200-digit Decimal finite
integer/half-integer gamma upward recurrence with an independently evaluated
erfc base. Production instead uses a general gamma series/continued fraction
and log survival. The reference erfc asymptotic expansion is stopped before
the least term, with an alternating remainder bound. Near-one references are
pinned as p=1/log-p=0 only when the lower-tail Chernoff bound is <exp(-250);
this is an explicit error bound, not a claim that a nonzero tail is exactly zero.

Pinned examples:

| Fixture | Exact Q | df | Numerical reference |
|---|---|---:|---|
| Balanced stage total 58594 | 495615000000/218869185791 | 1499 | p differs from 1 by <exp(-250) |
| Moderate cluster dispersion | 631000000/388479 | 1499 | p=0.012564925613531167056963418926590… |
| Concentrated stage total 58594 | 38624535615000000/218869185791 | 1499 | log(p)=-83922.1720746001373078958206024495… |
| A3 shifted, total 58594 | 13587048902972851695585000000/602488386437802962005425539 | 2 | p=0.0000126762980536581840528272958034… |

Additional vectors cover null/perturbed leading-zero and byte histograms,
chi-square references around df 1/2/255/1499, binary64 underflow, zero cluster
variance, all-zero/all-success counts, expected-cell equality and adjacent
counts, empty A3 groups and the approved raw-weight aggregation.

Two full families use the same primary stage/cluster inputs. One shifts only
an A1 last-byte histogram and A3 raw-weight success allocation. Their independent
secondary flags differ while the complete E2 classifications and positive/null
control gates remain identical. The numerical fixture builder reproduces the
committed JSON content exactly in qualification tests.

Qualification requires exact statistics/df/slot order/flags, ordinary raw and
adjusted probabilities within absolute 1e-10, and log probabilities within
absolute 3e-9 or relative 1e-13. For large log magnitudes the relative criterion
accounts for binary64 arithmetic; underflow is explicitly reported with a
finite log tail. These comparisons do not relax the Holm ambiguity guard or
permit a label mismatch. Reference code independence is algorithmic, not an
independent witness or a second person's review.

## Regression and primary isolation

Qualified interpreter: `.venv-py313-review024/Scripts/python.exe` (Python 3.13).
With `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`:

- Focused foundation/secondary: **166 passed in 1.98s**.
- Full regression: **709 passed in 15.10s**, no failures/skips.

The 75 accepted foundation tests remain present; updates are confined to
authorized version/binding expectations and algebraic synthetic A3 counters.
Tests additionally cover malformed count/geometry rejection, all 36 fixed
slots, not-testable retention, exact qualification boundaries, ties, underflow,
all Holm ranks, ambiguity failure, incompatible schemas/identities, raw-weight
accumulation, immutable inputs, success revalidation and primary/gate isolation.

Source hashes of `src/hashlab/statistics/exp002.py` and shared `inference.py`
match their before-change snapshot exactly. All 104 E2 tests pass in the full
suite. The secondary module imports no primary engine, sampler, hash engine,
seed function, registry or operational runner and calls no primary decisions.
Its only integration dependency is read-only foundation accounting validation.
Exploratory results are never passed to a primary classification or validity
gate. No evidence orchestration, release or E4 code was added.

## Experiment 001 preservation and outstanding gates

Before implementation and after the full suite, read-only manifest verification
passes for `results/20261011T205056Z-exp001-fc1d75fc`: nine payload hashes/sizes,
manifest self-hash and exact 11-file inventory. All eleven content hashes,
sizes and nanosecond mtimes equal the before-change snapshot.
Manifest SHA-256 remains
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
Local verification does not establish off-machine archival or external
historical authenticity. E001 candidates were not reconstructed or rehashed.

Statistical QA2 reference qualification is complete for this scope. Full QA2
hashing/evidence integration, independent scientific evidence verification,
actual audit/reconstruction providers, durable registry/sinks, provenance,
commitment/beacon witnesses, execution authorization and E4 remain outside
this pass. Counts cannot authenticate actual evaluated candidates. No
production performance claim, cryptographic weakness or economic claim follows.

Stop for Architecture Review 033. E3 is not committed; no push, merge or tag.
