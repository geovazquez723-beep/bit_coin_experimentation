# Architecture Review 027 — E1 closeout

Date: 2026-10-11 (America/Los_Angeles). Submit for Architecture Review 028.

## Readiness and approved contract

The Architect's Review 027 conditionally accepts E1 after direct review of the
Algorithm D implementation, tests, correctness report and seed proposal. The
four exact A1/A3 seed labels/KATs and the numerical-abort policy are approved.
Every attempt, including an aborted attempt, must be disclosed. Discretionary
seed replacement and silent retry-until-success are prohibited.

This closeout binds the approved encoding identity
`hashlab-exp002-a1-a3-subseed-encoding-v1` into the versioned configuration and
Experiment 002 protocol identity:

```text
proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1
```

The accepted scientific design remains revision 8 with its existing A2 byte
contract; this is an approved seed-encoding amendment, not a change to any
hypothesis, sample size, target, population limit or statistical threshold.
The original seed-contract filename is preserved, and its approval status is
updated without altering any of the four labels or known answers.

`arm_seed_labels`, `arm_seed_material` and `arm_subseed` are pure production
derivation interfaces. They bind the approved ordered ASCII label triples,
validate a caller-supplied uint64 master without coercion, and reuse the existing
`derive_seed`. No execution master is chosen. The existing
`src/hashlab/candidates/base.py` seed algorithm is unchanged. The sampler
primitives still permit explicit engineering sub-seeds.

No Algorithm D probability law, acceptance comparison, numerical enclosure,
precision/bit/rejection cap or random draw order changed in this closeout.
Its only source change is documentation of the mandatory disclosure policy.
Operational persistence remains a later integration dependency.

## Final verification

Qualified interpreter:
`C:\repo\hashlab\.venv-py313-review024\Scripts\python.exe`.
Runtime: `3.13.0 (tags/v3.13.0:60403a5, Oct 7 2024, 09:38:07)
[MSC v.1941 64 bit (AMD64)]`; Windows 11, build 26200.

With `PYTHONDONTWRITEBYTECODE=1`:

```text
python -m pytest tests/test_vitter.py tests/test_exp002_e1.py -q -p no:cacheprovider
199 passed in 1.02s

python -m pytest tests -q -ra -p no:cacheprovider --basetemp .venv-py313-review024/pytest-review027-temp --junitxml .venv-py313-review024/pytest-review027-results.xml
439 passed in 4.52s
```

The full suite contains 240 existing regressions, 125 Algorithm D sampling tests
and 74 foundation tests. All pass, with no skips or failures. Rejection, support
boundaries, bad randomness sources, numeric refinement and rejection-abort cap
probes are retained and pass. Forced-abort tests are synthetic failure fixtures,
not resource-cap events in the benchmark.

All three approved A2 KATs and all four approved A1/A3 KATs pass. The new
regressions check each complete ASCII message, exact byte length, full SHA-256
digest, uint64 big-endian conversion and bound production derivation result.
Additional tests reject invalid masters/domains, require the new configuration
identity fields, and check that the interface calls the unchanged seed algorithm
with the exact approved labels. Public master zero is solely a KAT input.

## Authorized real-population bounded benchmark

All six disclosed passes completed successfully on Python 3.13.0. There were
**zero resource-cap events and zero numerical aborts**. Requested/emitted counts,
rank boundaries and ascending uniqueness checks passed. Traced replay summaries
match their corresponding timing passes. Total selections across all six
engineering passes were 32,000; no pass exceeded 10,000 selections.

| Selections | Timing pass | Untraced seconds | Traced replay | Traced seconds | Peak traced bytes | Resource-cap events |
|---:|---|---:|---|---:|---:|---:|
| 1,000 | B1 | 0.772849 | B2 | 4.087582 | 6,044 | 0 |
| 5,000 | B3 | 15.979385 | B4 | 84.744142 | 6,044 | 0 |
| 10,000 | B5 | 59.036940 | B6 | 317.454014 | 6,044 | 0 |

The fixed reproducer is `tools/benchmark_exp002_e1.py`; the retained ledger is
`docs/reviews/architecture-review-027-e1-performance.json`. Each count has one
untraced timing pass followed by one memory-traced replay. Population size is
exactly 4,293,918,720; requested counts are exactly 1,000, 5,000 and 10,000.
The explicit engineering selection sub-seed is 7 throughout; it is not an
execution master. Only rank integers are sampled. No candidates are encoded or
hashed. No 30M sample, stage outcomes or confirmatory experiment is produced.

Every B1–B6 pass is written as started before sampling, then complete or aborted
with elapsed time, emitted count, error/cap information and UTC timestamps.
The ledger refuses overwrite; a failure stops this benchmark without replacing
the seed or retrying. This small engineering ledger does not claim to implement
the later operational registry. Traced-memory values measure Python allocations,
not whole-process RSS. Replay summaries check count/first/last/sum; exact
deterministic replay is additionally covered by unit tests.

Timing observations are single passes, not calibrated throughput measurements.
The 5,000-selection untraced pass overlapped the approximately five-second
regression verification on the same host; its elapsed time may include CPU
contention. The other untraced passes did not overlap the regression run.

### Engineering optimization disposition

**Yes: these observed costs justify targeted profiling and engineering
optimization before production performance qualification.** Keep this reviewed
implementation as the correctness reference. No speed optimization was made
during this closeout. Any optimization must preserve the exact sampling law,
certified comparisons, approved abort limits/disclosure policy and deterministic
behavior requirements, with renewed correspondence and regression review.

Untraced cost per selected rank rises from approximately 0.773 ms to 3.196 ms
to 5.904 ms. Memory stays flat in these observations. Code inspection explains
a plausible mechanism: in very sparse samples, the geometric squeeze can often
fail, requiring the full exact falling product in D4. This is an implementation
analysis, not an instrumented count of D4 calls or a production timing estimate.
Arithmetic/context reuse and repeated-certification costs merit profiling;
a different published proposal variant would require a separate source and
numerical review before adoption.

The benchmark n-squared/N ratios are approximately 0.000233, 0.00582 and 0.0233.
The frozen 30M sample has a very different starting ratio, about 209,599, and
the sampler's remaining n/N geometry changes during a stream. Therefore neither
linear nor quadratic extrapolation of these sparse-fixture timings establishes
a 30M runtime or the rate of production D4 calls. The current implementation's
production throughput is an unresolved later performance question, not an
observed scientific failure or a newly changed protocol rule. No production
qualification or full sample was run to answer it.

## Experiment 001 preservation

All nine payload SHA-256 digests and byte sizes, manifest self-hash and exact
11-file inventory pass read-only verification. All eleven content hashes,
sizes and nanosecond last-write timestamps match the snapshot taken before this
closeout's benchmarks and full regression run. Manifest SHA-256:

```text
546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b
```

The `v0.2.0` tag still dereferences to
`ef595f5c2f2166923fd277def39708409f564419`. No sealed evidence is modified.
Local integrity verification does not establish off-machine archival or
independent historical authenticity.

## E1 blockers versus later dependencies

The earlier A1 Algorithm D implementation, approved-label binding and numerical
policy approval blockers are resolved. **No known E1 correctness blocker remains;
E1 is ready for Architect acceptance at Review 028.** The bounded benchmarks
have completed and their performance limitation is disclosed. Recommended
optimization/performance investigation precedes later production qualification;
it is not represented as completed optimization or an execution authorization.
Final E1 readiness/performance disposition remains the Architect's decision.

Later dependencies, not represented as completed E1 work:

- Full E001 candidate reconstruction, A1 zero-intersection audit and A3 exclusion
  count/digest verification before constructing an eligible production plan.
- Binding all approved identities into later seedless/full plan fingerprints,
  evidence and pre-registration using the versioned configuration.
- Persistent append-only operational attempt registry, committed started/result
  entries, mandatory numeric-abort disclosure and same-seed amendment/retry rules.
- Externally witnessed commitment, beacon/client verification, seed-record
  binding and Director authorization. No beacon round or master is selected.
- Controls and complete overlap audits, orchestration, statistical/evidence paths,
  independent verification, QA2/G1/G2 and later production performance acceptance.

## Exact repository inventory

Branch: `feat/experiment-002-e1`. HEAD is unchanged:
`8a27da2cc5e886f0094c67d8d000905959b187f2`. Protocol baseline commit `c0a6d35`
is retained. There are no staged entries and no new commits.

Tracked file changed in this closeout:

- `docs/proposals/experiment-002-research-design.md`: approved seed encoding and
  protocol identity; scientific design remains unchanged.

All eight pre-existing untracked E1 files are preserved:

- `docs/proposals/experiment-002-a1-a3-seed-encoding-proposal.md`: approved status and binding.
- `docs/reviews/architecture-review-025-e1-implementation.md`: closeout link appended.
- `docs/reviews/architecture-review-026-algorithm-d.md`: records approval/disclosure condition.
- `docs/reviews/architecture-review-026-e1-implementation.md`: historical provenance note added.
- `src/hashlab/candidates/vitter.py`: disclosure obligation documented; algorithm unchanged.
- `src/hashlab/experiments/exp002.py`: approved identities and derivation interfaces.
- `tests/test_exp002_e1.py`: new complete KAT, contract and rejection regressions.
- `tests/test_vitter.py`: unchanged, retained and rerun.

New files in this closeout:

- `tools/benchmark_exp002_e1.py`.
- `docs/reviews/architecture-review-027-e1-performance.json`.
- `docs/reviews/architecture-review-027-e1-closeout.md` (this report).

Final `git status --short`:

```text
 M docs/proposals/experiment-002-research-design.md
?? .venv313/
?? docs/proposals/experiment-002-a1-a3-seed-encoding-proposal.md
?? docs/reviews/architecture-review-025-e1-implementation.md
?? docs/reviews/architecture-review-026-algorithm-d.md
?? docs/reviews/architecture-review-026-e1-implementation.md
?? docs/reviews/architecture-review-027-e1-closeout.md
?? docs/reviews/architecture-review-027-e1-performance.json
?? src/hashlab/candidates/vitter.py
?? src/hashlab/experiments/exp002.py
?? tests/test_exp002_e1.py
?? tests/test_vitter.py
?? tools/
```

The `tools/` entry contains exactly `tools/benchmark_exp002_e1.py`.

Pre-existing `.venv313/` is untouched and remains untracked. Qualification test
XML/temp/snapshot artifacts remain inside the already ignored approved environment.
No merge, push, tag, commit, E2 implementation, execution seed selection or
confirmatory experiment occurred. Stop for Architecture Review 028.
