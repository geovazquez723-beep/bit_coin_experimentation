# Experiment 002 secondary statistical clarification — approved v2 specification

Date: 2026-10-12 (America/Los_Angeles). Prepared under Architecture Review 029;
corrected under Review 030. Review 032 confirms Review 031's authorization to
implement this approved v2 specification and its versioned secondary binding.
**CURRENT STATUS: implemented for Review 033 qualification; no experiment execution.**

**Proposal identity:** `hashlab-exp002-secondary-statistics-proposal-v2`.
This version supersedes the unversioned Review 029 draft's A3 six-stratum
proposal with the three fixed groups directed by Review 030. The accepted
Experiment 002 protocol identity is unchanged. E3 now binds this secondary
identity in seedless-plan v2 and accounting v2. No operational execution artifact
or release identity has been selected. The proposal-era authorization/status
statements below are historical; Review 032's explicit authorization supersedes
them. The statistical specification and 36-slot family remain unchanged.

Revision 8 names five secondary procedures but leaves the dispersion statistic,
complete family, alpha, aggregation and edge-case rules unspecified. This
proposal supplies choices for Architect review. It makes no amendment to the
accepted confirmatory hypotheses, estimands, sample sizes, alpha budgets,
CP/t hull or classification matrix. E3 records raw diagnostics only and marks
the secondary specification unbound. Approval must precede implementation and
any new versioned plan binding. Existing Experiment 001 analyses stay unchanged.

## Proposed exploratory family and interpretation

Use A1,A2,A3,N1,N2, separately in D and V. Do not pool stages for secondary
tests, select tests based on primary flags, or use positive-control digests in
uniformity tests (their engines are deliberately biased).

One fixed family of **36** exploratory p-values:

- Leading-zero, first-byte and last-byte tests: 5 streams × 2 stages × 3 = 30.
- Cluster dispersion: A2,N2 × 2 stages = 4.
- A3 fixed weight-group success heterogeneity: 2 stages = 2.

Proposed exploratory alpha **0.01**, Holm across all 36, with strict rejection
`adjusted_p < 0.01`. This is a separate exploratory convention, never added to
the approved confirmatory error budget and never used for run-validity, H_S,
REP, margin or cryptographic/economic conclusions. Maintain the full family
even when a member cannot be calculated: assign p=1 for correction, retain an
explicit `not-testable` status and no raw p-value. Canonical ordering is arm
A1,A2,A3,N1,N2, then D,V, then leading-zero, first-byte, last-byte; append
A2-D,A2-V,N2-D,N2-V dispersion, then A3-D,A3-V weight-group tests. Ties retain this
order; Holm adjusted values are the step-down running maximum. No stochastic
reference calculation or data-dependent alpha allocation is proposed.

All distributional nulls below are **models** for supplied observations, not
theorems about deterministic SHA-256 or design-based population bounds. A2
heterogeneity does not make its prefix-population inference confirmatory.

## 1. Leading-zero-bit distribution

Null: supplied 256-bit digests are independent and uniformly distributed.
For exact leading-zero count L, P(L=j)=2^(-j-1), j=0,...,255, and
P(L=256)=2^(-256). Inputs: a complete 257-bin histogram per arm/stage with
integer nonnegative counts summing to the accounted digest total n. Every
evaluated digest contributes, including failures and successes.

Let K be the largest integer in [1,256] for which n/2^K >=5. Use individual
bins 0,...,K-1 and one pooled tail L>=K. Expected individual counts are
n/2^(j+1), tail n/2^K. Pearson statistic Q=sum((O-E)^2/E), reference chi-square
with **K df**, since K+1 categories have all probabilities fixed. For n=15M,
K=21, 22 bins and 21 df. Select K from n alone; never merge based on observed
zeros. The chi-square reference is an approximation, explicitly labelled.

Edges: n=0 or no K>=1 gives not-testable; invalid histogram length, impossible
counts or mismatch with digest accounting is an input error, not p=1. Empty
observed bins with E>=5 remain in Q. An all-zero digest has L=256 and is
included in the pooled tail. Use integer comparisons for selecting K.

Deterministic reference vectors: n=1280, raw bins L=0..8 equal
[640,320,160,80,40,20,10,5,5], all later bins zero. K=8, Q=0, df=8, p=1.
Move 8 observations from bin 1 to bin 0: Q=3/10, df=8,
p=exp(-3/20)*sum((3/20)^j/j!, j=0..3). A vector with n=9 is not-testable;
n=10 admits K=1 and expected [5,5]. These include exact bin-selection edges.

## 2. First-byte uniformity

Null: the first digest byte is independently uniform on 0,...,255. Input:
256-bin first-byte histogram per arm/stage, total n. Pearson Q against E=n/256
in every bin; reference chi-square with **255 df**, no fitted parameters.
This is an approximate reference, not an exact multinomial p-value.

Edges: n=0 or n<1280 gives not-testable (E<5); do not collapse byte bins.
Observed empty bins remain in the statistic if expectations qualify. Reject
negative/fractional counts and total mismatches. Q=0 gives p=1. Very large Q
may have a probability too small for binary64: retain log-survival or an
explicit underflow indicator, never infer an exact mathematical zero.

Reference: all 256 counts equal 10 (n=2560), Q=0, df=255, p=1.
Change the first two counts to 11 and 9: Q=1/5, df=255,
p=Q_gamma(255/2,1/10), where Q_gamma is regularized upper incomplete gamma.
n=1279 is not-testable and n=1280 with every bin 5 qualifies.

## 3. Last-byte uniformity

Null, aggregation, statistic, df, alpha family and edge cases are exactly those
in section 2, applied to the last-byte histogram, as a separate test. The same
reference vectors and expected Q/df/p apply. The first- and last-byte tests
may be dependent; Holm does not require independence. An identical histogram
does not justify deduplicating these predeclared family members.

## 4. A2 and N2 between-cluster dispersion

Proposed null: within the given stage, cluster successes K_j are independent
Binomial(b,p) with one common unknown p, b=10000, m=1500. N2 pseudo-clusters
use exactly the same aggregation. This is a heterogeneity diagnostic, not the
primary strict p0 test, the pooled margin t component or a population test.
Input: ordered stage cluster counts, cluster trial counts, stage identity and
total. Require all 1500 clusters, exactly 10000 trials each and consistent
totals. No success-only omission of zero clusters is allowed.

Fit p_hat=sum(K_j)/(m*b). Pearson dispersion
Q=sum((K_j-b*p_hat)^2)/(b*p_hat*(1-p_hat)). Reference chi-square with
**m-1=1499 df**, reflecting one fitted parameter. This is an approximation;
it is not an exact finite-sample heterogeneity law. Sum and sum of squares
permit an independent algebraic recomputation; use sufficient precision to
avoid negative variance from cancellation.

Edges: all counts zero or all counts b gives not-testable, since the fitted
variance vanishes. Constant counts strictly between 0 and b give Q=0,p=1;
zero observed between-cluster variance is valid and not division by zero.
Require b*p_hat>=5 and b*(1-p_hat)>=5 for the proposed chi-square approximation;
otherwise not-testable. Missing/duplicated IDs, incorrect stage assignment,
unequal cluster sizes or total mismatches are errors. An actual zero-success
cluster remains present. The upper-tail test detects excess dispersion only;
underdispersion is descriptive and not a second hidden hypothesis.

Reference vectors (repeat notation defines every element and position):

- [39] repeated 1500: p_hat=39/10000, Q=0, df=1499, p=1.
- [38,40] repeated 750: p_hat=39/10000,
  Q=15000000/388479, df=1499, p=Q_gamma(1499/2,Q/2).
- [0] repeated 750 followed by [78] repeated 750:
  Q=585000000/9961, df=1499, p=Q_gamma(1499/2,Q/2).
- [0] repeated 1500 and [10000] repeated 1500: not-testable.
- Small mathematical analog only, m=2,b=4,K=[0,2]: Q=8/3,df=1,
  p=erfc(sqrt(4/3)). This analog does not override production geometry or
  expected-count qualification.

For QA2's approved balanced total 58594 per stage, define q,r=divmod(58594,1500)
and vector [q+1] repeated r followed by [q] repeated (1500-r). Let
S=58594, SS=r*(q+1)^2+(1500-r)*q^2. Exact Q is
`(SS-S^2/1500)/(10000*(S/15000000)*(1-S/15000000))`; df=1499.
For the approved concentrated-stage fixture, use 1125 zeros then 375 balanced
counts summing to 58594, and apply the same formula with its SS. These are
fully determined independent references, not snapshots of the E2 engine.

## 5. A3 fixed weight-group success heterogeneity

Review 030 correction: the six individual weight strata cannot meet the
expected-success criterion under expected Experiment 002 conditions. Eligible
weight 1 has only 12 population members. Replace the six-column test with
these **three fixed groups**, defined before any outcomes are observed:

| Group | Raw Hamming weights | Eligible population after E001 exclusions |
|---|---|---:|
| G1 | 1, 2, 3, 4 | 631,413 |
| G2 | 5 | 7,407,537 |
| G3 | 6 | 74,029,313 |
| Total | 1–6 | 82,068,263 |

Proposed null: conditional on the evaluated eligible inputs and their fixed
group assignments, successes are independent Bernoulli with one common
unknown p across G1,G2,G3. This examines evaluated-input success-rate
heterogeneity, not allocation frequencies, equality of group sizes or
design-based population fractions. No E001 observations are pooled. It does
not test differences between weights within G1.

**Exact aggregation, separately for each D/V stage.** Retain raw integer
trial/success counts `(n_w,k_w)` in weight order w=1,...,6, for eligible A3
inputs after the approved exclusions. Set
`n_1group=n_1+n_2+n_3+n_4`, `k_1group=k_1+k_2+k_3+k_4`;
`n_2group=n_5`, `k_2group=k_5`; `n_3group=n_6`, `k_3group=k_6`.
Below, `(N_g,K_g)` denotes these grouped counts in G1,G2,G3 order.
No estimated proportions, rounding or reweighting enters aggregation.
Require all six raw counters (zero is an explicit value), 0<=k_w<=n_w,
sum(n_w)=15,000,000 and sum(k_w) equal to the accounted A3 stage success count.
Impossible counts, invalid weights, missing counters, stage mismatch or total
mismatch are input errors, not statistical non-testability. Group trial
counts cannot exceed their eligible populations. Eligibility and individual
weight population limits must be verified by the approved population/audit
path, not inferred from these grouped counts.

The implementation would require reviewed raw-weight counters, currently
**not** part of E3's diagnostic schema. No code/schema addition, reconstruction
or hashing is authorized by this documentation correction.

**2×3 statistic and reference.** Let n=sum_g(N_g), S=sum_g(K_g), and
`p_hat=S/n`. The observed rows are successes `K_g` and failures `N_g-K_g`;
expected rows are `E_success,g=N_g*p_hat` and
`E_failure,g=N_g*(1-p_hat)`. Pearson statistic:

```text
Q = sum_g [ (K_g-N_g*p_hat)^2 / (N_g*p_hat)
          + ((N_g-K_g)-N_g*(1-p_hat))^2 / (N_g*(1-p_hat)) ]
  = sum_g (K_g-N_g*p_hat)^2 / (N_g*p_hat*(1-p_hat)).
```

Reference chi-square with **(2-1)*(3-1)=2 degrees of freedom**, fitting one
common success probability. The reference is approximate; its survival
probability is `p_raw=exp(-Q/2)`. In particular Q=0 gives p_raw=1. Never reuse
the withdrawn six-column test's 5 df.

**Expected-count qualification and edges.** Require all six grouped expected
cell counts to be >=5, including exact equality. With integer counts, compare
`N_g*S >= 5*n` and `N_g*(n-S) >= 5*n` for every g; avoid floating equality.
If any group has zero trials, p_hat is 0 or 1, or any expected cell is below 5,
mark the whole stage's member `not-testable`, no Q/reference df/raw p reported,
and correction-only p=1 in its existing Holm slot. Individual raw weights
may have zero trials or small expectations: qualification is on the fixed
grouped table only. A zero observed success count is allowed if all expected
cells qualify; observed zero alone never removes a group. Constant observed
rates across qualifying groups yield Q=0,p_raw=1. Underflow must be explicit,
with log(p_raw)=-Q/2 retained, rather than an assertion of mathematical zero.

**No data-dependent merging, splitting or removal.** G1 always means weights
1–4, G2 always weight 5, and G3 always weight 6, in that order, in both stages.
Failed qualification cannot trigger another grouping, a reduced-df test,
pooling D/V, or deletion/replacement of its family member. The **36-member
family, exploratory .01 Holm proposal, canonical ordering and two A3 stage
slots remain unchanged**.

Under SRS stage size 15M and strict p0=1/256, expected grouped trial counts are
approximately (115406.3051,1353910.1589,13530683.5360), and expected successes
(450.8059,5288.7116,52854.2326). These planning values explain the correction;
actual qualification always uses observed N_g and fitted p_hat, never population
sizes as trial counts. Qualification is not guaranteed for every possible sample.

### Independent algebraic and numerical references

All vectors below are synthetic and not SHA-256 observations. The first four
are mathematical small-table analogs, exempt only from the 15M total for
reference algebra; they do not change production geometry. Raw vectors listed
below additionally check the fixed weight aggregation. For qualifying vectors,
compute Q both by the six-cell formula and the simplified three-term formula
using exact rational arithmetic. The numerical references were independently
calculated without importing HASHLAB inference or E3 code, using 70-digit
Decimal exp(-Q/2), cross-checked with binary64 math.exp (absolute difference
<1e-15). No secondary procedure was implemented in the repository.

| Reference | Group trial vector N | Group success vector K | Qualification | Exact Q | df | Numerical raw p |
|---|---|---|---|---|---:|---:|
| Constant rates | (1000,1000,1000) | (10,10,10) | qualifies | 0 | 2 | 1 |
| Perturbed rates | (1000,1000,1000) | (11,9,10) | qualifies | 20/99 | 2 | 0.903923902295282443922440217076 |
| Expected cells exactly 5 | (500,500,500) | (5,5,5) | qualifies | 0 | 2 | 1 |
| Expected successes below 5 | (500,500,500) | (5,5,4) | not-testable: every expected success is 14/3 | — | — | absent; correction-only 1 |
| Population-scale near common rate | (115404,1353892,13530704) | (451,5289,52854) | qualifies | 70602522226695585000000 / 602488386437802962005425539 | 2 | 0.999941409282345093697311569465 |
| Population-scale shifted rate | (115404,1353892,13530704) | (551,5289,52754) | qualifies | 13587048902972851695585000000 / 602488386437802962005425539 | 2 | 0.0000126762980536581840528272958034 |

For the two population-scale vectors, the exact stage total is 15M and success
total is 58594. Their grouped expected successes are
`(450.7987984, 5288.663189866666..., 52854.538011733333...)`; every expected
success and failure qualifies. Numerical Q values are respectively
`0.000117184868316103445268726173071306` and
`22.5515532063712094593184953041671`.

Raw-weight reference vectors, in weight order (1,2,3,4,5,6):

- Constant/perturbed small analog: n_w=(0,0,0,1000,1000,1000),
  k_w=(0,0,0,10,10,10) or (0,0,0,11,9,10). Empty individual weights within G1
  are valid; G1 as a whole qualifies and the df remains 2.
- Population-scale vectors: n_w=(2,100,3000,112302,1353892,13530704),
  k_w=(0,0,12,439,5289,52854) or (0,0,12,539,5289,52754).
  These aggregate exactly to the two table rows above, including only two
  sampled weight-1 inputs, rather than an impossible large weight-1 stratum.
- Empty fixed group: n_w=(0,0,0,0,1500000,13500000),
  k_w=(0,0,0,0,5859,52735). G1 has zero trials: not-testable, not a 1-df test.
- On either population-scale n_w vector, all k_w=0 or k_w=n_w is
  not-testable due to zero expected successes or failures. A negative count,
  k_w>n_w, missing weight counter or incorrect stage total is an input error.

These A3 algebraic/numerical vectors are checked references for this revised
proposal. Independent numerical verification of the other proposed chi-square
procedures and their full pinned QA2 fixtures remains outstanding.

## QA2 relationship and approval requests

The approved QA2 requires per-stage secondary dispersion statistics/df/p-values
on null and concentrated synthetic cluster fixtures, separately recomputed by
a verifier that does not import HASHLAB statistics. Section 4 supplies the
missing candidate definition. On approval, pin full arrays and independently
computed numerical p-values/log-p-values before implementation qualification.
The symbolic gamma/erfc references in sections 1–4 specify mathematical targets;
they are not claims of completed numerical reference verification. Section 5's
revised 2-df A3 vectors include independently checked numerical references.

Proposed numerical qualification: exact count/order/df/statistic algebra;
absolute error <=1e-10 for ordinary probabilities, relative/log-space checks
for underflow tails; independent chi-square reference implementation. No
tolerance may excuse a Holm label error. If uncertainty straddles a cutoff,
qualification fails pending higher precision. Include tied p-values, exact
alpha equality, not-testable members, all fixed-family orderings and
malformed-input rejection. None of these tests modifies primary QA2 criteria
or permits the deferred hashing integration exercise to run now.

Architect decisions requested: approve/revise the 36-member family and separate
.01 exploratory alpha; the fitted-p rather than fixed-p0 dispersion null;
upper-tail-only dispersion; the no-merge expected-count rule; inclusion of N1/N2;
and the A3 three-fixed-group success-rate test rather than population-allocation
heterogeneity. The grouping itself follows Review 030's correction. Approve
any raw-accounting schema addition for A3 weights separately. Until approval,
all remain documentation-only and no proposed p-value enters a plan or result.
