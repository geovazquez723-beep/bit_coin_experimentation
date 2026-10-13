# E002-I2 controls — implementation and bounded qualification

Prepared 2026-10-12 on `feat/e002-i2-controls`, base HEAD
`3167c4ce66adabcc22743d99fc76e4f57316a711`. Unstaged and uncommitted.

All five controls are implemented and the bounded fixture is independently
verified. **Full regression is not entirely green:** two unchanged legacy
session-snapshot tests fail as detailed below. No I2 scientific/implementation
defect was identified. Director acceptance and disposition of the existing
regression environment remain outstanding; this report does not declare the
user's all-regressions-pass completion standard satisfied.

## Authorization and changes

The human Director approved D1–D5 in
[`e002-i2-control-byte-specification.md`](../proposals/e002-i2-control-byte-specification.md),
including C1=`[2^20,2^32)`, complete C3 rejection, N1 source indices strictly
below 30,999,999, and exact floor-quantized positive/negative effects. The proposal
now records that approval while retaining definitions, KATs and alternatives.
The user's request authorizes implementation and bounded qualification only.

| Added/updated file | Purpose and public interfaces |
|---|---|
| `docs/proposals/e002-i2-control-byte-specification.md` | Updated approval status and binding clarifications; original specification retained. |
| `src/hashlab/experiments/exp002_controls.py` | `control_keys`, `Feistel64`, `inverse_history`, `load_control_history`, `ControlGeometry`, `PermutationControls`, `ByteStream80`, `N2Controls`, `n2_assignment`, `accepted_record`, `ControlEngine`. Deterministic providers and digest transformations; no research dispatcher. |
| `src/hashlab/experiments/exp002_i2_synthetic.py` | `fixture_spec`, `fixture_inputs`, `run_fixture`: fixed 14-evaluation engineering path using existing I1/E3 records, accumulator, authentication and durable-write primitives. |
| `src/e002_verify/controls.py` | Independent control key, Feistel/inverse, stream, A2 prefix, bias, replay and accounting calculations; `verify_fixture` requires a separately retained completion hash. No producer imports. |
| `tests/test_exp002_i2.py` | 76 tests covering KATs, boundaries, rejections, repeated evidence, authentication and hostile/incomplete artifacts. |
| `tools/qualify_e002_i2.py` | Separate-process `produce`/`verify` CLI for this fixed fixture; no configurable production geometry or execution command. |
| `docs/reviews/e002-i2-controls-synthetic-handoff.md` | This result and review limitations. |

Existing modules, tests, frozen configurations/protocol identities, A1/A2/A3
encodings, generic positive engine and statistical boundaries were not edited.
New controls coexist with I1; I3 must integrate them into the full shared path.
`ControlEngine.evaluate` performs one base SHA-256 evaluation and returns raw
and effective digest hex, mode, U32 threshold, transformation flag and strict
effective success. `transform` operates on supplied digests without hashing.
The positive modes match the existing `BiasedControlEngine` byte for byte.

Production provider geometry remains N1/N2 15M per stage and P1/P2+/P2−
200,000/15M/15M. Smaller geometry requires the fixture domain and is separately
capped. These library interfaces do not grant production seed selection or
execution permission. P controls share one permutation and cursor. N2 keeps
block tails and never restarts by stage or deduplicates.

N2 engineering records use the existing E3 stage-local index and V cluster
offset 1500, even with only two records per stage. Production geometry gives
exactly the approved global accepted-order cluster numbering. Production
source/raw indices and offsets remain separate from accepted record indices.

## Complete historical evidence and overlap accounting

The producer authenticates all eight retained S1.4 files and the original
sealed/source identities through the existing loader, then reads every retained
occurrence in `producer/occurrences.bin`. It validates ordinal, phase, attempted
index, enumeration index, outcome, length and total, and applies the approved
Feistel inverse to all 7,000,000 historical 8-byte occurrences. **It never
regenerates E001 streams or hashes historical candidates.**

Results: **7,000,000 occurrences; 6,048,573 distinct inverse skip indices**.
The 60,721-member A3 exclusion subset is authenticated but is not the N1/P skip
population. The index is bound to its permutation key. Fixture-key caching is
in-process only, uses immutable skip indices, and reauthenticates retained bytes
before reuse. Production requires the complete-history identity and count.

The reference separately authenticates and reads the complete retained
occurrence file into raw-value membership. A bijection preserves cardinality,
so the distinct raw-value count independently verifies the distinct inverse
index count. It computes forward/inverse overlap checks for bounded attempts;
it does not import or trust the producer index. This is complete verification
of the bounded fixture, not an independent full production inverse-index build.

Every attempted index has an audit row; rejected attempts carry all applicable
reasons but count once in the rejected-attempt total. Accepted ordinals do not
advance on rejection. Source exhaustion never wraps or reduces a quota.
Injected tests cover repeated historical occurrences outside A3, C1/E001 and
C3/E001 overlaps, P allocation across skipped indices, and N2 membership
rejection at a stage boundary. No extra N2 uniqueness guarantee or deduplication
is introduced; the approved probabilistic assumption remains explicit.

## Retained synthetic evidence

Repository-relative local evidence directory:
`.tmp/e002-i2-qualification/`. This is review evidence, not a sealed experiment
directory, externally timestamped archive, QA2 result or execution commitment.

| Artifact | Result |
|---|---|
| `producer-final/complete.json` | Final producer completion hash below. |
| `producer-repeat/complete.json` | Separate producer process; all seven evidence files byte-identical to `producer-final`. |
| `producer-report.json`, `repeat-report.json` | Both return the same completion hash. |
| `verifier-report.json` | Independent complete bounded-fixture verification succeeds. |
| `focused-final.txt` | 76 passed, no skips, 61.15 s. |
| `regression-final.txt` | 1,408 passed, 2 failed, 2 skipped, 99.87 s. |
| `legacy-recheck.txt`, `legacy-snapshot-diagnosis.json` | Isolated reproduction and read-only diagnosis of the pre-existing snapshot failures. |

Final producer completion SHA-256:

```text
94f31a1ed9adccedf6d71e31468c05fe0ba6a0c8d68bec35d95c943445b56f0b
```

`producer-final` and `producer-repeat` each contain `fixture.json`, `history.json`,
`attempts.jsonl`, `records.jsonl`, `accounting.json`, `rejections.json`, and
`complete.json`. Completion is exclusively created and durably written last;
exceptions leave partial bytes, with no valid completion claim. There is no
resume/overwrite path. The independent verifier requires exact inventory,
canonical bytes, a retained completion pin, all expected attempts/records and
complete agreement on digests, indices, assignments and accounting. Re-sealed
corruptions, truncation, incorrect claims and interrupted writes are rejected.

Each final producer execution used exactly **14 real candidate SHA-256
evaluations / 18 compression blocks**. The verifier separately used **14 / 18**.
Integrity hashes and BLAKE2b key/generation/inverse-audit work are separate from
these candidate SHA-256 counts. Only engineering input zero in the approved
fixture domain was used; no experiment seed was selected.

| Control | Accepted | Attempts | Rejected | Effective successes |
|---|---:|---:|---:|---:|
| N1 | 2 D + 2 V | 4 | 0 | 0 |
| N2 | 2 D + 2 V | 4 | 0 | 0 |
| P1 | 2 C | 2 | 0 | 0 |
| P2+ | 2 C | 2 | 0 | 0 |
| P2− | 2 C | 2 | 0 | 0 |

There were no natural historical/A2/structural hits or digest transformations
in this tiny fixture. Workload was not enlarged to create successes. Supplied
digest tests verify positive and negative transformations at threshold−1,
threshold, strict target equality, zero and maximal digest values; no candidate
regeneration or second SHA-256 evaluation occurs. Fixed count-only fixtures
exercise the unchanged statistical gates. No statistical classification is
claimed from 14 candidate evaluations; the existing E3 accounting remains
`complete=false` for the full frozen experiment.

KAT qualification checks the two complete key derivations, five published
permutation/inverse pairs, six round states, full round-message/digest, three
80-byte stream vectors, retained block tails, every approved digest boundary,
exact rational probabilities and all 3,000 independently generated fixture A2
prefixes. Additional tests cover random/boundary inverse identities, strict N1
limit and uint64 P exhaustion, final BE128 stream counters, rejection counts,
raw offsets and production cluster/stage boundaries. A fresh-process test
confirms the verifier imports no `hashlab` module.

## Regression results and limits

Runtime: bundled **CPython 3.12.14**, pytest 9.1.1 from the existing local
site-packages. The `.venv313` launcher points to an unavailable Python311
installation, so it was not used. This is not qualification of the previously
approved production interpreter/environment. `PYTHONDONTWRITEBYTECODE=1` was
set; no dependencies were installed or modified.

Focused command: `python -B -m pytest tests/test_exp002_i2.py -q`.
Full command: `python -B -m pytest -q`. Runs used separate local `--basetemp`
directories; logs above retain complete failures and skips.

Two full-suite failures, independently reproduced without importing I2:

1. `test_e001_historical.py::test_original_sources_and_e001_preserved`.
2. `test_e001_tooling.py::test_accepted_sources_and_sealed_evidence_unchanged`.

Both first fail comparing `.gitignore` with older S1.2/S1.3 local session
snapshots: expected 351 bytes, current CRLF checkout 367 bytes. Normalized
content matches the unchanged base HEAD. Further old protected-file snapshot
differences also exist; this work does not rewrite them or infer they are all
line-ending-only. Git reports no tracked diff. The two tests' actual historical
source authentication and sealed-manifest checks pass before their local
session-snapshot assertions. All eleven original sealed E001 files match both
old snapshots in hash, size and mtime. No old snapshot, source or sealed file
was modified to force a passing result.

Two skips: the existing E4 symlink inventory tests cannot create symlinks under
the available Windows privileges (`WinError 1314`). No I2 tests were skipped.

Production resource qualification remains separate: this straightforward
in-memory inverse-index implementation is complete but not a claim of bounded
production memory. Separate-process fixture measurements, including complete
historical authentication/index construction: producer 55.03 s / peak working
set 853,389,312 bytes; reference 4.67 s / 834,723,840 bytes. Shared Python,
hashlib, host and AI authorship limit independence; no independent human audit
or externally authenticated provenance is asserted.

## Remaining work toward I3

- Integrate A1/A2/A3 and all five controls into one shared workflow, preserving
  raw/effective digests, rejection audits, effective success records and E3/E4
  failure semantics. This I2 fixture does not replace or modify the I1 path.
- Extend the independent reader to the combined workflow and all required
  inference/evidence slots; retain explicit synthetic versus production scope.
- Disposition the pre-existing session-snapshot regression environment without
  rewriting historical evidence; qualify the required production runtime and
  full-scale resources before claiming all readiness gates pass.
- Complete separately authorized full-system qualification, QA2, audit/seed
  provenance and operational approvals before any real E002 execution.

No commit, push, merge or tag; no QA2, historical reconstruction, confirmatory
E002, production seed, beacon, commitment, protocol or threshold change occurred.
