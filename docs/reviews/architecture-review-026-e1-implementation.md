# Architecture Review 026 — E1 completion submission

This is the preserved Review 026 submission. Architecture Review 027 approved
the exact seed contract and numerical-abort policy with mandatory attempt
disclosure and no discretionary seed replacement. Current closeout results are
in [Architecture Review 027](architecture-review-027-e1-closeout.md).

Date: 2026-10-11 (America/Los_Angeles). Stop for Architecture Review 027.

**Algorithm D is implemented and the E1 engineering checks pass.** This is a
submission for acceptance, not an Architect declaration of E1 completion or
authorization to execute Experiment 002. Proposed A1/A3 sub-seed labels remain
documentation-only. The capped exact-arithmetic failure policy is explicit below.

## Branch and preservation

Continued on `feat/experiment-002-e1` at unchanged HEAD
`8a27da2cc5e886f0094c67d8d000905959b187f2`, the qualification-evidence commit.
Protocol baseline `c0a6d35` and the accepted proposal are unchanged. No index
entries existed or were added. Existing untracked E1 work was retained and
extended. `.venv313/` and unrelated environments/files were preserved.
No commits, pushes, merges or tags were made in Review 026.

The qualified Python is `C:\repo\hashlab\.venv-py313-review024\Scripts\python.exe`,
Python 3.13.0, as documented in Review 024. Test XML, temporary directories and
the pre-regression integrity snapshot are confined to that ignored environment.

## Algorithm D implementation and review

`src/hashlab/candidates/vitter.py` implements Vitter's published geometric
Algorithm D variant, followed by Method A for the dense tail. A1's engineering
adapter now uses it; A3 retains integer Algorithm S with immutable exclusions.
Both selection and stage-allocation seeds are explicit engineering arguments.
No proposed domain labels are implemented or selected automatically.

See the [source-level correspondence and algebraic review](architecture-review-026-algorithm-d.md)
for the primary-source links, D1–D5 mapping, exact skip/envelope equations,
inverse-geometric endpoint certification, Method A law and fixed-size induction.
That review separates the published method from our independent algebraic
checks, numerical implementation policy, tests and accepted RNG assumption.
It is an Engineer review, not an external reviewer certification.

All probabilistic decisions use integer randomness and enclosing arithmetic.
A Decimal logarithm supplies a search hint only; certified comparisons determine
the proposal skip. There is no population array or retained selected-sample set.
Out-of-support proposals are rejected; no clamping or replacement of the final
eligible rank is permitted. Invalid inputs, exhausted/broken bit sources and
uncertifiable arithmetic fail closed.

The mathematical unbiased SRS argument is for ideal independent bits and an
uncapped rejection process. The concrete implementation follows the same
decisions until it either completes or raises a failure. It caps each lazy
variate at 4,096 bits, precision at 1,600 digits, and rejection attempts per rank
at 4,096. A cap never forces a decision. **Exact uniformity conditional on no
resource abort is not claimed.** No cap hit occurred in the fixtures. Review 027
should assess this resource/failure policy before production acceptance; a cap
failure is a blocking failure, never grounds to search another seed.

## Focused and regression results

Commands ran with `PYTHONDONTWRITEBYTECODE=1`, using the qualified interpreter:

```text
python -m pytest tests/test_vitter.py -q -p no:cacheprovider
125 passed in 0.80s

python -m pytest tests/test_vitter.py tests/test_exp002_e1.py -q -p no:cacheprovider
180 passed in 1.02s

python -m pytest tests -q -ra -p no:cacheprovider --basetemp .venv-py313-review024/pytest-review026-temp --junitxml .venv-py313-review024/pytest-review026-results.xml
420 passed in 4.49s
```

There are 240 unchanged existing regression tests, 55 foundation tests, and 125
sampling tests; no failures or skips. Sampling tests include:

- All tiny N=1..13 geometries and sample counts, across ten fixed engineering seeds.
- Exact rational skip masses against independent combination counts; exact
  envelope and production acceptance/squeeze enclosures, including sparse cases.
- Every subset and exact first-/second-order inclusion probabilities through N=8.
- Exhaustive random-branch enumeration of the actual independent integer
  Algorithm S reference through N=5, compared with D's exact sequential law.
- Every geometric support interval in a small sparse case; explicit D2 forbidden
  tail rejection, D3 acceptance, D4 acceptance/rejection and dense-tail behavior.
- Empty/full/singleton cases, allocation counts, invalid types/ranges, duplicate
  prevention, pinned replay, alternate allocation seeds and generator exhaustion.
- Bad search hints, ambient Decimal precision isolation, interval power enclosure
  at multiple precisions, exact-bit-boundary refinement and fail-closed caps.
- Supplementary frequency comparisons and bounded-memory checks.

Distributional tests alone are not used to establish Algorithm D correctness.
The finite exact checks support, but do not replace, the source/algebraic review.

Pinned engineering replay: N=1,000, n=10, selection seed 7 yields
`[5,298,308,589,705,709,761,825,927,965]`.
N=100, D=2, V=2, selection seed 7, allocation seed 8 yields
`[(D,1),(V,11),(V,87),(D,89)]`. These are fixture sub-seeds, not execution seeds.

## Bounded fixture performance and memory

Each timing is the median of three consumptions without tracemalloc. Memory is
a separate traced consumption. Both algorithms include identical stage counts
and explicit seeds 7/8; all ranks are consumed and discarded, not collected.
Maximum engineering population was 200,000 and maximum emitted sample 18,000.
No production-size sampler was invoked.

| N | Emitted | Algorithm | Median seconds | Peak traced bytes |
|---:|---:|---|---:|---:|
| 20,000 | 100 | D | 0.014215 | 9,336 |
| 20,000 | 100 | S | 0.004461 | 6,600 |
| 20,000 | 1,000 | D | 0.095919 | 9,432 |
| 20,000 | 1,000 | S | 0.004715 | 6,696 |
| 20,000 | 18,000 | D | 0.112060 | 8,876 |
| 20,000 | 18,000 | S | 0.009109 | 6,696 |
| 200,000 | 100 | D | 0.016142 | 9,368 |
| 200,000 | 100 | S | 0.043897 | 6,600 |

Exact interval certification has overhead on small/dense cases. In the more
sparse 200,000-rank fixture, D is about 2.7 times faster than scanning with S.
These are local observations, not production forecasts. Memory checks show no
sample retention; the structural argument is absence of any output collection
in either sampling iterator. D has capped per-variate numerical workspace.
A3 exclusions and A2 prefix plans retain their separate O(exclusion count) and
O(prefix count) storage contracts.

## Proposed sub-seed encoding

The [documentation-only A1/A3 contract](../proposals/experiment-002-a1-a3-seed-encoding-proposal.md)
contains the four exact ordered label triples, complete ASCII derivation
messages, unsigned big-endian conversion, four full SHA-256/sub-seed KATs and
standalone Python and PowerShell/.NET reproductions. Both implementations agree
on every digest and integer; the existing HASHLAB derivation agrees separately.
The master zero is a public test input only. Labels are absent from sampler code,
and no confirmatory master or beacon value was selected. Architect approval is
required before binding the proposal into production identity.

## Existing foundation recheck: guarantees versus evidence

| Area | Invariant/assumption | Recheck and limits |
|---|---|---|
| Configuration | Exact versioned field set; fixed represented constants, no coercion | Frozen-field/shape/type rejection tests pass. Seedless library schema; no execution configuration created. Scientific procedures are not executed. |
| A1 boundaries | Offset+rank is in `[2^20,2^32)` | Endpoints/predicates and new sampler range checks pass. D ranges are zero-based eligible ranks. |
| A3 indexing | Weight/colex bijection excluding the initial all-low-bit segment | Exhaustive independent tiny-class enumeration and full-domain boundary round trips pass; class size 82,128,984, eligible size 82,068,263 unchanged. |
| A2 encoding | Frozen labels/messages, keyed BLAKE2b, 76-byte prefixes and LE32 nonce | All three approved prefix/example-candidate KATs pass. Full derivation SHA-256 `f9b8be...9c1043` independently rechecked. No candidate SHA-256 evaluation. |
| Prefix uniqueness | Validate immutable complete prefix collection before streaming | Collision and malformed-prefix rejection pass; only tiny engineering prefix collections generated. No 3,000-prefix execution plan generated. |
| Stage allocation | Integer hypergeometric split of one unique selection | Exact D/V counts, replay and disjointness pass. A2's fixed 1,499/1,500 boundary checks pass. |
| A1 vs A3 | Top 32 bits zero vs nonzero | Mathematical disjointness plus predicate tests. |
| 8-byte vs 80-byte | Byte length differs | Mathematical disjointness plus tests. |
| E001 exclusion | A1 empty intersection, A3 exact exclusion intersection | Tiny synthetic audit tests pass. Production 7M-candidate reconstruction has NOT been performed; fixed count/digest validation remains mandatory. |
| Seed/registry interfaces | Typed digest/record validation, ordering and numbering rules | Tests pass. Added explicit exclusion population validation, strict UTC record syntax, and basic valid/F2 status consistency. Interfaces are not operational governance evidence. |
| Sampling uniformity | Ideal independent RNG choices plus exact skip/partition laws | Algebraic argument and exact finite tests; MT19937 is still treated as ideal, not proved ideal. Concrete resource-abort caveat above. |

No frozen hypothesis, hash target, sample size, population limit, seed-derivation
algorithm, A2 byte contract or statistical decision threshold was changed.
`candidates/base.py`, `candidates/random.py` and the accepted proposal remain
identical to protocol baseline `c0a6d35`.

## Later dependencies and remaining review gates

1. Architect approval of the proposed A1/A3 seed-label contract before binding
   it into a production plan. Current code requires explicit sub-seeds.
2. Architect assessment of source correspondence and exact-arithmetic resource
   abort policy. No external independent implementation review is claimed.
3. Later complete E001 candidate reconstruction, A1 zero-intersection audit,
   A3 exclusion count/digest verification and identity-bound plan integration.
4. Operational append-only registry persistence, separate commits, externally
   witnessed precommitment, beacon/client verification and seed-record binding.
   Current in-memory flags/records do not verify those external facts.
5. Later-phase orchestration, controls/overlap audits, statistical/evidence paths,
   QA2/G1/G2 acceptance and production performance qualification remain outside
   this pass. No execution gate is declared satisfied by these engineering tests.

## Experiment 001 integrity

All nine payload SHA-256 digests and sizes, manifest self-hash and exact 11-file
inventory match. All eleven content hashes, sizes and nanosecond last-write
timestamps are unchanged across the full regression run. Manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
Tag `v0.2.0` still dereferences to
`ef595f5c2f2166923fd277def39708409f564419`.
This is local integrity verification, not off-machine archival or historical
authenticity certification. No sealed evidence was modified.

## Exact changed-file inventory and Git status

Existing untracked files extended in this pass:

- `src/hashlab/experiments/exp002.py`: A1 D adapter; stricter exclusions/registry validation.
- `tests/test_exp002_e1.py`: additional existing-foundation rejection checks.
- `docs/reviews/architecture-review-025-e1-implementation.md`: historical text preserved; continuation link appended.

New untracked files created in this pass:

- `src/hashlab/candidates/vitter.py`.
- `tests/test_vitter.py`.
- `docs/proposals/experiment-002-a1-a3-seed-encoding-proposal.md`.
- `docs/reviews/architecture-review-026-algorithm-d.md`.
- `docs/reviews/architecture-review-026-e1-implementation.md` (this report).

No tracked files changed, and the index is empty. Final expected short status:

```text
?? .venv313/
?? docs/proposals/experiment-002-a1-a3-seed-encoding-proposal.md
?? docs/reviews/architecture-review-025-e1-implementation.md
?? docs/reviews/architecture-review-026-algorithm-d.md
?? docs/reviews/architecture-review-026-e1-implementation.md
?? src/hashlab/candidates/vitter.py
?? src/hashlab/experiments/exp002.py
?? tests/test_exp002_e1.py
?? tests/test_vitter.py
```

No E2/E3/E4 implementation, confirmatory candidate hashing, full-scale population
sampling, experiment execution, execution-seed selection or beacon-round
selection occurred. Stop for Architecture Review 027.
