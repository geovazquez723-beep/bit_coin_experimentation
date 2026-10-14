# E002-I3 full-system integration — bounded qualification

2026-10-13, America/Los_Angeles. Branch `feat/e002-i3-integration`.
Base: **`bd9e7e0981d126021ba29af6a0f7ee278815c8d6`**. PR #2 was confirmed
merged, origin fetched, and local main fast-forwarded before this branch was
created. Unrelated work and retained evidence were preserved. No commit or push.

**Result:** all eight streams operate through one shared synthetic evaluation,
accounting and evidence path. Complete independent bounded verification passes;
repeat producer evidence is byte-identical. No unresolved scientific integration
defect was identified. This qualifies the specified bounded system, not production
execution, mining advantage, QA2 or operational readiness.

## Implementation and interfaces

All nine deliverables are new files; no accepted implementation, test, protocol
or threshold was edited.

| File | Responsibility |
|---|---|
| `src/hashlab/experiments/exp002_integration.py` | `run_fixture`, `evaluate_record`, `eligibility`, `fixture_spec`, `count_fixtures`: one shared loop over accepted I1 providers and I2 control providers; exclusive deterministic persistence. |
| `src/hashlab/experiments/exp002_integration_statistics.py` | `statistical_inputs`, `infer_synthetic_counts`, `persisted`, `disclosure`: E3 effective counts into unchanged E2 and secondary v2 interfaces; explicitly scoped diagnostics. |
| `src/e002_verify/integration.py` | `verify_fixture`: independent combined reconstruction, rehash, success evidence, accounting, input and inference verification against an external completion pin. |
| `src/e002_verify/integration_statistics.py` | Independent input/count-fixture construction, finite-law CP checks, primary/null Holm decisions, cluster hull, positive gates, all 36 exploratory slots and correction. |
| `src/e002_verify/binomial_reference.py` | Unchanged LF-normalized copy of accepted `tests/exp002_reference.py`: Decimal finite-law binomial recurrence. |
| `src/e002_verify/secondary_reference.py` | Unchanged LF-normalized copy of accepted `tests/exp002_secondary_reference.py`: exact Pearson algebra and independent half-integer gamma recurrence. |
| `tests/test_exp002_i3.py` | 68 focused integration, supplied-digest, statistical, fault and independent verification tests. |
| `tools/qualify_e002_i3.py` | Separate-process producer/verifier CLI for the fixed fixture only. |
| `docs/reviews/e002-i3-full-system-integration-handoff.md` | This handoff. |

I1/I2 **provider functions**, not their report-writing runners, feed the shared
loop. It validates eligibility, performs exactly one base SHA-256 evaluation,
applies the accepted I2 transformation to the supplied digest, adds the effective
digest to the existing E3 accumulator, and persists one record. A shared E3
success sink collects effective successes. Source/accepted indices, population
ranks, raw offsets, stage/cluster IDs and all rejection reasons are retained.
Success records are reconciled with E3 accounting before completion.

Raw/effective digests, mode, threshold, transformation flag and strict effective
target decision remain distinct. Primary arms use identity transformation;
P1/P2+/P2− use their approved engines. N2 receives no extra deduplication.
N1/P eligibility is checked against structural classes and the complete inverse
history; A1/A3 accepted candidates also receive complete-history membership
checks. A3 rank/exclusion and A2 prefix/nonce checks precede hashing.

Persistence reuses E3 canonical records/accounting and E4 path, inventory and
durable-write primitives. Completion is created last; there is no overwrite,
retry or resume. This synthetic completion contract does **not** fabricate an
E4 production `FullPlanBinding`, external proof, manifest seal or gate receipt.
Production governance sealing remains a separately qualified boundary.

## Fixture specification and evidence

The accepted composition is unchanged: A1/A2/A3 each 32 D + 32 V; N1/N2 each
2 D + 2 V; P1/P2+/P2− each 2 C. **206 SHA-256 candidate evaluations and
274 compression blocks per producer execution**. The verifier independently
rehashes the same **206 / 274**. Integrity hashing and BLAKE2b generation/inverse
audit work are separately excluded from candidate SHA-256 counts.

One necessary engineering binding is explicit in `fixture.json`: I1 A2 uses
the accepted `E002-I1!` fixture key, whereas standalone I2's N2 membership
fixture used KAT-derived A2 prefixes. The combined N2 membership check uses
**all 3,000 prefixes under the I1 A2 fixture key**, so it excludes the actual
combined A2 population. A1/A2/A3 candidates, the N1/P permutation, N2 raw stream,
and sample geometry are retained. No production byte convention or control
effect changes. Only existing public engineering inputs are used.

Local evidence: **`.tmp/e002-i3-qualification/`**.

| Evidence | Result |
|---|---|
| `producer-final/`, `producer-repeat/` | Separate producer processes; all 12 files byte-identical. |
| `producer-final-report.json`, `repeat-report.json` | Same completion hash below. |
| `verifier-report.json` | Independent complete unified-fixture verification passes. |
| `focused.txt` | 68 passed, no skips, 84.46 s. |
| `regression.txt` | 1,476 passed, 2 failed, 2 skipped, 141.76 s. |
| `source-inventory.json` | Final deliverable hashes, base identity, preservation and repeat checks. |

Final completion SHA-256:

```text
418be192f4260ea8bc2e9863144d458e1cd54e77777dbb66a999085852d4cf6e
```

Each final directory contains `fixture.json`, `history.json`, `attempts.jsonl`,
`records.jsonl`, `successes.jsonl`, `accounting.json`, `statistical-inputs.json`,
`rejections.json`, `count-fixtures.json`, `synthetic-inference.json`,
`disclosure.json`, and `complete.json`. Total evidence size: 817,373 bytes per
directory. Final evidence is distinguished from intermediate scratch iterations.

The authenticated complete E001 retained file contributes **7,000,000 historical
occurrences / 6,048,573 distinct inverse skip indices**, not just the A3 subset.
No historical stream was regenerated. The reference independently authenticates
and reads retained history, reuses accepted independent I1/I2 reconstruction
algorithms, and imports no `hashlab` module. Every expected attempt, accepted
candidate, raw/effective digest, success record, counter, input and inference
result is checked. Bijection permits independent skip-index cardinality checking
from distinct raw history; bounded overlap decisions are independently replayed.

| Stream | Accepted | Effective successes |
|---|---:|---:|
| A1 D / V | 32 / 32 | 0 / 0 |
| A2 D / V | 32 / 32 | 0 / 0 |
| A3 D / V | 32 / 32 | 0 / 1 |
| N1 D / V | 2 / 2 | 0 / 0 |
| N2 D / V | 2 / 2 | 0 / 0 |
| P1 / P2+ / P2− C | 2 / 2 / 2 | 0 / 0 / 0 |

There are 206 total attempts and no natural rejected attempts or transformations
in final measured evidence. Unit history fixtures inject two historical rejections
and produce 208 attempts for the same 206 accepted evaluations. I2's existing
rejection/boundary tests remain active. No workload was enlarged to obtain a
desired outcome. N2 uniqueness remains probabilistic, explicitly unverified.

## Statistical interface qualification

The measured accumulator remains `complete=false` for frozen full-experiment
geometry. Its statistical-input artifact reports `frozen_geometry_complete=false`.
Calling confirmatory-size inference on it fails; no confirmatory classification
is derived from the 206 candidates.

Five separately labeled **synthetic full-geometry count fixtures**, with zero
candidate evaluations and `measured_sha256_observations=false`, qualify the
interfaces. They reuse the accepted secondary reference data, authenticated by
LF-normalized SHA-256
`3b3931f43705e5dcd787db71dc088f0bc0eaadcb44ddcf87aa52a58553d151db`.
Artificial success-count adjustments are explicitly constructed and independently
reconstructed, never presented as measured or production-complete evidence.
The E3 `complete` flag inside these artificial counts denotes geometry only.

| Count-only case | Statistical control gate | Secondary tested / flagged |
|---|---|---|
| Baseline | Pass | 36 / 0 |
| Exploratory shift | Pass; primary/control outputs unchanged | 36 / 2 |
| Replicated signals and null gate failure | Fail; A1/A3 replicated BEYOND, N1 replicated | 36 / 18 |
| Positive gate failure | Fail; P1 count 869 | 36 / 0 |
| Zero successes, not-testable secondary cells | Fail | 30 / 30; six remaining slots not-testable |

These are synthetic gate results, not operational G3 decisions. Interfaces cover
three-arm discovery/validation Holm inference, A2 CP/t hull with 2,999 df, both
null procedures, all positive detection/margin gates, all nine classification
cells, and the full fixed 36-member exploratory family. Not-testable slots keep
missing raw probabilities and correction-only p=1. Unflagged primary arms retain
absent validation p-values. Exploratory results do not change primary/control
outcomes.

Deterministic supplied-digest tests traverse the same evaluation, success sink,
accounting and input construction: P1/P2+ forced successes remain effective
successes; P2− original successes are suppressed and not collected. Their counts
also enter synthetic full-geometry inference through the same adapter. Injected
hash artifacts are unit-only and are rejected by the real-SHA independent verifier.

Independent probability comparisons use absolute tolerance 1e-10; log tails use
3e-9 plus 1e-13 relative tolerance; CP quantile tail checks use 1e-8. Exact counts,
statistics, rational quantities, decisions, schemas and nonnumeric fields require
exact agreement. Cluster interval/hull checks use 1e-12 absolute tolerance.
An extreme accepted exploratory tail exposed default Decimal exponent underflow
in the new reference adapter; independent Holm was corrected to log space.
Accepted statistical implementations and thresholds were not changed.

Synthetic diagnostics are explicitly identified and allow inspection of V.
There is no production dispatcher/disclosure path; the disclosure boundary marks
production V diagnostics unavailable, and inference requires the explicit
synthetic-count scope. No synthetic output authorizes production disclosure.

## Regression, preservation and readiness

Focused: **68 passed**. Full offline suite: **1,476 passed, 2 failed, 2 skipped**.
The only failures are the inherited identities documented in
[`e002-i2-regression-disposition.md`](e002-i2-regression-disposition.md):

- `test_e001_historical.py::test_original_sources_and_e001_preserved`
- `test_e001_tooling.py::test_accepted_sources_and_sealed_evidence_unchanged`

Both still first fail on old session-snapshot `.gitignore` expectations (351
versus 367 bytes). Their historical authentication checks pass. No new failure
or silent exception extension occurred; the suite is **not green**. The two
existing E4 symlink tests skip for Windows privilege error 1314. All I1/I2 tests
remain in the regression suite. No I3 test skipped.

All original eleven E001 files retain hashes, sizes and mtimes; old snapshots
retain their hashes. Retained I2 completion hashes remain unchanged. The tracked
tree and index have no changes against the I3 base; only the nine new deliverables
are in intended scope. Unrelated `.tmp/`, `.venv313/`, plans, R9 proposals,
reviews 039/040 and `docs/run_all_tagging.ps1` remain outside the scope.

Runtime: bundled **CPython 3.12.14 / pytest 9.1.1**, no dependencies installed;
bytecode writing disabled. This does not qualify the approved production runtime.
Separate-process measurements including complete history authentication:
producer 57.41 s / peak working set 856,129,536 bytes; verifier 6.60 s /
839,479,296 bytes. The in-memory full inverse index, independent history set and
reference caches require production resource qualification. These measurements
do not establish full experiment throughput, storage or recovery performance.
Shared host, Python/hashlib and AI authorship limit independent assurance;
no independent human audit or external timestamp is claimed.

Remaining before G1/QA2/real execution: Director acceptance of I3; full-system
qualification on the approved runtime with production resource/accounting bounds;
complete gate/evidence/archive/recovery and validation-blinding qualification;
separately authorized QA2; and the approved release, seed/beacon/commitment and
G2 execution procedures. Production execution and governance sealing remain
unavailable in this fixed synthetic CLI. This work supplies no substitute proof
or authorization for those steps and does not reopen E001 scientific recovery.

No commit, push, PR merge, tag, historical reconstruction, QA2, production seed,
beacon/commitment selection or confirmatory E002 execution occurred. Leave the
implementation and evidence for Research Director review.
