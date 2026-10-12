# Algorithm D source correspondence and correctness review

Architecture Review 026. Implementation:
`src/hashlab/candidates/vitter.py`. Engineer's source review, independently
checking the probability identities against the published method; this is not
an external reviewer sign-off or a claim that tests constitute a proof.

Review 027 disposition: the Architect directly reviewed this artifact and
conditionally accepted E1. The numerical-abort policy below is approved with
mandatory disclosure of every attempt and no discretionary seed replacement.
See the Review 027 closeout report for current verification and benchmarks.

## Published source and chosen variant

[Vitter, Faster Methods for Random Sampling (1984)](https://www.ittc.ku.edu/~jsv/Papers/Vit84.sampling.pdf),
section 4, D1–D5 and equation (4-5), supplies the geometric-proposal variant.
[Vitter, An Efficient Algorithm for Sequential Random Sampling (1987)](https://www.ittc.ku.edu/~jsv/Papers/Vit87.RandomSampling.pdf),
section 2 and Appendix, supplies the D/Method A structure and `alpha=1/13`.
We implement fresh geometric proposals, without the optimized beta/Vprime
recycling. The parameter choice is published Algorithm D, not Algorithm Z or
reservoir sampling. Interval arithmetic changes how comparisons are certified,
not their probabilities. The log estimate locates a skip; certified comparisons
decide it. No published source code is copied.

| Published step | Implementation correspondence |
|---|---|
| D1 | `vitter_ranks` permanently switches to `_method_a_skip` once `13*n >= N`; singleton/full cases are explicit |
| D2 | `_geometric_skip`: geometric proposal; out-of-support proposals return `None` and are regenerated |
| D3 | `_skip`: squeeze probability; certified `_Uniform.compare` |
| D4 | `_acceptance` and `_mass_factors`: full falling-product ratio, using the shorter form; same acceptance U as D3 |
| D5 | `vitter_ranks`: emit offset+skip, advance offset, reduce remaining N and n |
| Method A | `_method_a_skip`: single U, successive survival products; inverse-CDF stop |

The following is an independent algebraic verification of this implementation,
not a further paraphrase of the source or an empirical argument.

## Skip law, envelope and rejection calculation

Let N and n be remaining eligible population and remaining sample count. The
first selected rank must skip `s` in `[0,N-n]`. Counting all completions gives

```text
f(s) = C(N-s-1,n-1) / C(N,n)
     = (n/N) * product(i=0..s-1, (N-n-i)/(N-1-i))
     = (n/N) * product(i=0..n-2, (N-s-1-i)/(N-1-i)).
```

These equivalent forms explain `_mass_factors` and its `min(s,n-1)` factors.
For `1<n<N`, set `q=(N-n)/(N-1)`, `g(s)=(1-q)*q**s`, and
`c=n*(N-1)/((n-1)*N)`. Thus `c*g(s)=(n/N)*q**s`.
Every factor of the first product is at most q, so `f(s)<=c*g(s)`.
Every factor is at least `(N-n-s+1)/(N-1)`, giving

```text
h(s) = (n/N) * ((N-n-s+1)/(N-1))**s <= f(s)
h(s)/(c*g(s)) = ((N-n-s+1)/(N-n))**s.
```

The D3 expression in code follows by cancellation. For s=0, the empty power is
one and acceptance is certain. D4 computes the exact rational expression for
`f/(c*g)` using interval enclosures. The same U is retained, so squeeze failure
does not create another independent acceptance opportunity. For each legal s,
one proposal's acceptance probability mass is `g(s)*f(s)/(c*g(s))=f(s)/c`.
Summing legal masses gives `1/c`. Conditioning a rejection attempt on acceptance
therefore yields f(s); repetition does not change that law. Out-of-support
proposals are rejected, never clamped, wrapped or reflected.

## Proposal and dense-tail checks

The geometric inverse uses a single uniform V and identifies the integer s with
`q**(s+1)<V<q**s`, ignoring equality events of ideal probability zero. First
rejecting `V<q**(N-n+1)` rejects precisely the forbidden tail. Then either the
Decimal log hint's two endpoints are certified or binary search finds the same
interval. Each comparison refines the original V's bits, never redraws them.
No real-valued density normalization is needed for this discrete variant.

For Method A, the survival product at s is
`P(S>s)=product(i=0..s,(N-n-i)/(N-i))`. It is decreasing, reaches zero at
`s=N-n`, and stopping when U exceeds it has probability f(s). This path is
independent of Algorithm S's per-record integer draws. The implementation
recomputes products on comparison/refinement rather than carrying a rounded
quotient; it is not the fastest Appendix implementation.

When n=1, `randrange(N)` directly gives an unbiased eligible rank. When n=N,
all remaining ranks are required and skip=0. Empty samples emit nothing.

## Fixed-size, population and stage invariants

Inductively `0<=skip<=N-n`, so after D5, `N'=N-skip-1>=n-1=n'`.
The offset strictly increases; emitted ranks are ordered, unique and in range.
One decrement per emitted rank gives exactly the requested count on successful
exhaustion. There is no retry of an exhausted generator and no implicit top-up.
A1's encoding adds `2^20` and uses eight big-endian bytes; bounding size by
`2^32-2^20` keeps the last eligible value strictly below `2^32`.

Multiplying the conditional f(s) values along any sorted n-subset telescopes
to `1/C(original_N,original_n)`. Consequently each rank's inclusion probability
is n/N and each pair's is `n*(n-1)/(N*(N-1))`. This establishes the ideal SRS
law by counting and induction, rather than by frequency tests.

The independent stage RNG chooses D with integer probability `remaining_D /
remaining_total`. It consumes the selected stream once. Its labeled partitions
have probability `1/C(n,D)` and exact D/V counts; stages cannot share ranks.
Selection and allocation state never perturb each other's RNG draws. Separate
MT19937 instances remain conditional on the accepted ideal-RNG assumption.

## Arithmetic, memory and fail-closed policy

`_Uniform` draws independent 64-bit chunks and keeps a dyadic interval enclosing
the ideal real variate. `_Bounds` encloses each positive ratio, multiplication
and division with directed rounding. Integer powers use outward-rounded
repeated squaring, not fractional `Decimal.power`. The monotonicity of those
operations on nonnegative inputs establishes enclosure by induction.
[Python's Decimal contexts](https://docs.python.org/3.13/library/decimal.html#rounding-modes)
provide the directed rounding. Contexts are local and fixed; callers cannot
change acceptance by changing the ambient Decimal precision.

Only disjoint intervals decide a comparison. Ambiguity refines the same bits
and increases precision; it does not compare a rounded point value with a
threshold. The search hint uses a fixed Decimal context rather than platform
libm. Basic probability operations have no logarithm or fractional power.

Refinement is capped at 4,096 bits per variate and 1,600 decimal digits; proposal
attempts are capped at 4,096 per selected rank. Exhausted/broken test bit sources,
invalid geometry/seeds, invalid arithmetic, underflow and cap exhaustion raise
`SamplingError`. A failure may occur after a partial stream: callers must discard
its eligibility as a completed sample, retain failure evidence, and follow
governance; no seed replacement, forced acceptance, redraw-on-ambiguity or
numerical fallback to another sampling law is authorized.

The mathematical SRS proof is for the uncapped ideal-bit process. The concrete
implementation is coupled to that process until a fail-closed abort. Its decisions
never knowingly introduce rounding bias. **We do not assert that conditioning
on the absence of a resource abort preserves an exactly uniform law.** A cap hit
blocks the experiment; it must not become a silent retry-until-success procedure.
Architecture Review 027 approves this explicit numerical/resource policy with
mandatory attempt disclosure and no discretionary seed replacement. Operational
registry persistence remains a later dependency. Numerical safety is not established merely by no observed
failures in fixtures.

No arrays, sets or lists hold population ranks or selected ranks. Per-sampler
state and capped numerical workspace do not grow with the number selected.
Geometric proposal certification adds integer-power work logarithmic in the
skip and, for a bad hint, binary-search work logarithmic in N. D4 has up to
`min(s,n-1)` factors; this is a faithful D variant, not a claim of reproducing
the optimized Appendix's runtime constants. No production-scale performance
claim is made.

## Verification scope

The tests check all tiny geometries; exact skip masses and envelope inequalities;
every subset and first-/second-order inclusion probability through N=8; and
actual Algorithm S random-branch enumeration through N=5. Exact checks use
`Fraction`/combinations separately from production Decimal arithmetic.
Additional probes cover every legal geometric interval in a small sparse case,
D2 tail rejection, D3 acceptance, D4 acceptance/rejection, dense tails, singleton
endpoints, collision prevention, allocation counts, deterministic replay,
incorrect hints, ambient context isolation, bit-boundary refinement and failure
caps. Frequency comparisons are supplementary engineering tests only.

These checks support the derivation and source correspondence; they do not
prove every possible implementation path or substitute for independent Architect
review. Focused/regression counts and bounded benchmark observations are in the
Review 026 E1 report.
