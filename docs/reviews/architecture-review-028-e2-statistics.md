# Architecture Review 028 — E1 accepted; E2 statistical implementation

Date: 2026-10-11 (America/Los_Angeles). Handoff for Architecture Review 029.

## E1 preservation

Verified branch `feat/experiment-002-e1` at
`8a27da2cc5e886f0094c67d8d000905959b187f2`. Read the complete Review 027
closeout and staged exactly its 12 named files: the research-design amendment,
approved sub-seed proposal, four Review 025–027 Markdown reports, Review 027
performance JSON, Vitter and exp002 implementations, their two test modules,
and the bounded benchmark reproducer. Git's staged inventory was 12 files,
2,385 insertions and three deletions. No benchmark was executed in this review.

The qualified `.venv-py313-review024/Scripts/python.exe` ran the complete
regression suite before the commit: **439 passed in 4.52s**, no failures/skips.
`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, and an environment-local
pytest basetemp were used throughout.

Accepted E1 milestone commit:
`dbcbd223953b2e3e39149567026b2513bd7e24af`.
Immediately after committing, the only status entry was pre-existing untracked
`.venv313/`; the relevant working tree was clean. Created
`feat/experiment-002-e2` directly from that commit. E2 remains uncommitted.

## Exact E2 inventory

- `src/hashlab/statistics/exp002.py`: count-only frozen statistical contracts.
- `tests/test_exp002_e2.py`: synthetic contracts, boundary and reference tests.
- `tests/exp002_reference.py`: independent Decimal finite-law reference.
- `tests/fixtures/exp002-e2-synthetic.json`: eight explicit 3,000-count arrays,
  geometry, stage totals and independently calculated cluster reference values.
- `docs/reviews/architecture-review-028-e2-statistics.md`: this handoff.

No existing production source, scientific protocol, Experiment 001 file,
dependency declaration or environment was changed by E2.

## API contracts

`Stage(stage, successes, trials=15000000, clusters=None)` is immutable. Stage
must be D or V; counts must be integers (booleans rejected), within range.
Clustered stages require exactly 1,500 integer counts in [0,10000] summing
exactly to the supplied stage total. The tuple position is the cluster identity;
there is no separate id field that can contain duplicates or be omitted.

`Arm(name, discovery, validation)` is immutable, requires D then V, and accepts
A1/A2/A3/N1/N2. A2/N2 require cluster tuples; other arms reject them.
`analyze(arms)` requires exactly A1,A2,A3 and returns results in that order,
independent of input order. It computes doubled-smaller-tail exact binomial
discovery tests, Holm at .005, descriptive direction by integer comparison
`256*k_D` with `n_D`, and one-sided validation only for discovery flags.
Validation Holm contains only flagged arms. Empty families produce no V tests.
Differences are NONE/UNREP/REP. Adjusted and unadjusted probabilities are kept.

`cp_margin(k,n=30000000)` returns ratio endpoints and the margin outcome.
The exact confidence expression is `1-2*.005/3`, not rounded .996667.
Pooled 30M decision regions remain W_LO=115839, W_HI=118519,
B_LO=113851 and B_HI=120546. Control 15M regions were independently calculated:
WITHIN 58126–59050, BEYOND <=56720 or >=60484. Endpoints are descriptive
binary64 approximations; these decisions use integer regions, not rounded
endpoint equality. A1/A3 retain their approved design-based finite-population
estimands and thresholds; no binomial population model is substituted.

`cluster_interval(counts)` requires exactly 3,000 counts. It computes the
unbiased variance of ratios `256*k_j/10000`, divides by 3000 for the squared
standard error, and uses frozen t=2.9376 with 2999 df. Comparisons use exact
rational squared distances, so endpoint rounding cannot change a decision.
Displayed endpoints use 60-digit Decimal arithmetic. The A2 margin is the hull
of CP and t; BEYOND requires both components beyond the same side. Pooling
always includes D and V, including when discovery is NONE.

`interval_outcome(lower,upper)` uses strict rational comparisons: equality to
.98 or 1.02 is UNDET. `classify(difference,margin)` implements all nine frozen
cells and rejects unknown outcomes. Results retain component intervals and
outcomes, stage/pooled counts, cluster sum of squares and variance, exact
descriptive stage/pooled ratios, and the UNREP note. A2 is explicitly qualified
as `model-mean-of-evaluated-inputs`. Every result states that difference tests
concern the strict model null, direction is descriptive, and no cryptographic
or economic claim follows.

`controls(nulls,p1,pplus,pminus)` requires N1,N2 and integer positive-control
counts. Each null control uses D two-sided .005/3 and V one-sided .005, per
section 3.7; nulls do not enter the primary Holm family. N2 follows the A2 hull
path. P1 uses 200k, P2± use 15M, one-sided .001, with the negative control using
the lower tail. Statistical gates require P1 detection, at least one P2
detection, neither P2 WITHIN, and no replicated null control. D-only null flags
remain diagnostic. The API returns all components; it does not assign run
validity, persist evidence or perform orchestration.

## Independent comparisons and numerical handling

The reference module imports no HASHLAB code. It uses 75-digit Decimal
binomial mass ratios about the mode, normalizes the finite-law mass, and bounds
each omitted tail geometrically below 1e-65. Small-n tests additionally use
exact integer binomial coefficients and rational probabilities.

Independent production-geometry p-values agree within absolute 1e-10.
Independent finite-law evaluations at CP endpoints agree with the target tail
within 1e-10. Reference values on both sides of every pooled and 15M control
margin cutoff give exactly the implementation's labels. Discovery and
validation critical counts and adjacent counts are tested in both directions
for all three Holm family sizes. Validation cutoffs (low/high) are:

| Flagged family | Low | High |
|---|---:|---:|
| 1 | 57971 | 59218 |
| 2 | 57916 | 59274 |
| 3 | 57885 | 59305 |

Discovery Holm low/high cutoffs for remaining family sizes 1,2,3 are
(57916,59274), (57864,59326), (57835,59356). Positive-control cutoffs at .001
are P1 high >=870, P2+ high >=59343 and P2− low <=57848. These discrete
regions also avoid floating-point equality in difference/control decisions.

The existing inference routine failed the initial independent 1e-10 tolerance
at several validation boundaries (errors up to about 1.8e-10). E2 therefore
uses a local integer-log-gamma calculation with 55-digit Decimal Stirling
arithmetic and retains the existing continued-fraction beta evaluator. The
existing inference module and Experiment 001 behavior are unchanged. This is
a numerical correctness measure, not a performance optimization.

Cluster references independently sum Decimal deviations from the mean rather
than using the production rational sum-of-squares formula. Stored fixtures
include balanced null, high, low, concentrated heterogeneity with unchanged
stage totals, fixed-total t-boundary bracketing, all-zero and all-success
counts. Tests cover all nine matrix cells both directly and through reachable
count inputs, zero variance, malformed counts/geometry, stage order, missing
clusters, inconsistent totals, contradictory D/V directions, ties, empty
discovery families and negative-control/gate failures.

## Scope proof and limitations

E2 imports only dataclasses, Decimal, Fraction, math and the numerical inference
module. An AST regression checks this dependency inventory and absence of
dynamic execution/file-opening calls. There is no candidate, sampler, engine,
hash, seed, beacon, evidence, network or subprocess interface in the module.
All new statistical tests and fixture construction operate only on synthetic
integer counts. No research candidates were generated or hashed by E2; no
confirmatory run/subset, sampling benchmark, execution seed or beacon selection
occurred. Existing regression tests were run as tests only.

Secondary procedures remain intentionally unimplemented: revision 8 names
leading-zero, first/last-byte, A2 heterogeneity and A3 weight-stratum tests, and
asks QA2 to verify a “predeclared” dispersion statistic, but does not actually
specify that statistic, its df, zero-variance handling, complete family or
secondary alpha. Inventing these would change the protocol. Review 029 must
resolve this before the requested secondary dispersion QA2 can be complete.
No exploratory value is mixed into a confirmatory result.

Full QA2 orchestration, evidence serialization/independent evidence verifier,
small hashing integration, sampler/evidence identity audits and operational
gates remain E3/E4 or separately authorized work. These APIs cannot authenticate
the origin or independence of supplied counts. The independent reference is a
separate algorithm, not an external reviewer or independently witnessed run.
Generic CP endpoint calculations are numerical, not certified enclosures; the
frozen decisions avoid endpoint ambiguity via integer/rational comparisons.
The finite-population and heterogeneous-model scientific guarantees are those
already approved in the protocol, not newly proved here. A2 prefix-population
inference is never confirmatory.

## Verification and Git disposition

Focused: **104 passed in 8.68s** using the qualified Python 3.13 environment.
Full: **543 passed in 13.20s**, no failures or skips. No E2 files are
staged or committed. `.venv313/` remains the pre-existing excluded untracked
directory. No push, merge or tag. Stop for Architecture Review 029.

Final relevant status: five new, untracked E2 files listed in the exact E2
inventory above; no tracked modifications and no staged entries. HEAD remains
`dbcbd223953b2e3e39149567026b2513bd7e24af` on `feat/experiment-002-e2`.
