# R9-M1A contract foundation — architecture review handoff

Implemented 2026-10-12 against accepted documentation HEAD
`b5b035a861dbc7af37af7e445ad88a86761458e7`. Uncommitted; stop for Architecture
Review. Branch remains `feat/e001-independent-qualification`. No commit, push,
merge, tag, release, operational approval, experiment, historical enumeration,
seed/round selection, recovery or execution controller was introduced.

## Exact assignment file inventory

All six files are new, untracked and unstaged:

1. `src/hashlab/experiments/exp002_r9_contracts.py`
2. `tests/test_exp002_r9_contracts.py`
3. `tests/fixtures/exp002-r9-director-synthetic-v1.json`
4. `tests/fixtures/exp002-r9-algorithmic-synthetic-v1.json`
5. `docs/reviews/r9-m1a-e001-preservation.json`
6. `docs/reviews/r9-m1a-contract-foundation-handoff.md`

No existing tracked file changed. Existing untracked files/directories preserved:
`.venv313/`, `docs/reviews/architecture-review-039-external-readiness.md`, and
`docs/reviews/architecture-review-040-e6-preparation.md`.

## Public APIs and trust boundary

New module: `hashlab.experiments.exp002_r9_contracts`. No package re-export,
CLI/entry point, adapter, execution import, or change to an accepted serializer.

`parse_record(data: bytes)` accepts canonical ASCII JSON bytes for exactly the
Director and algorithmic schemas below. Returns frozen
`UntrustedDirectorApproval` or `UntrustedAlgorithmicReport`. Their nested values
are frozen `RecordCommon`, `Bindings`, `Source`, `Scope`, `Producer`, `Ref`,
`Finding`, and `Coverage` value records, with immutable tuples for arrays.
RecordCommon is the shared base. Direct construction of these value types also
creates only untrusted values; callers needing structural validation must use
`parse_record`. There is no conversion to authenticated evidence or authorization.
Decoded decimal strings become exact Python integers in Ref/Coverage; there is
no new public serializer or implicit legacy conversion.

`check_reference_graph(root: bytes, artifacts: dict[Ref, bytes], *,
opaque_schemas: frozenset[str] = frozenset()) -> tuple[Ref, ...]` checks only
caller-supplied in-memory content. It verifies exact size, SHA-256 and implemented
record schema identity, bounded dependency traversal, and active-path cycles.
Returned references are unique in deterministic first-encounter order. A shared
subgraph is traversed on every path, so an earlier shallow traversal cannot hide
excessive later depth. Missing bytes fail. Unimplemented schemas fail by default.

An explicit caller-selected subset of the *other proposed* schema identities may
be treated as opaque terminal bytes. These get exact digest/size checks only;
their content, dependencies and claimed schema semantics are not validated.
Neither implemented schema can be made opaque. The synthetic graph fixture uses
this explicit terminal boundary. This API supplies no filesystem/network resolver,
does not follow links, and makes no completeness claim about opaque dependencies.
Future trusted resolution and schema dispatch need separate architecture review.

No approval authentication, actual timestamp verification, G1/QA2/G2 evaluator,
scientific recomputation or trust-root selection exists. Role, decision, matched
findings, coverage and recorded times remain declarations. Complete-looking
algorithmic claims and approved-looking Director claims both parse without
becoming truth, permission or E4 VerifiedEvidence. Python frozen dataclasses and
Final annotations are API boundaries, not protection against malicious Python.

## Exact identities

| Definition | Identity |
|---|---|
| Active protocol | `proposal-revision-9\|hashlab-exp002-a2-encoding-v1\|hashlab-exp002-a1-a3-subseed-encoding-v1` |
| Scientific baseline | `proposal-revision-8\|hashlab-exp002-a2-encoding-v1\|hashlab-exp002-a1-a3-subseed-encoding-v1` |
| Governance | `hashlab-exp002-solo-governance-v1` |
| Secondary | `hashlab-exp002-secondary-statistics-proposal-v2` |
| Parser | `hashlab-exp002-r9-strict-parser-v1` |
| Reference policy | `hashlab-exp002-r9-bounded-references-v1` |
| Implemented Director schema | `hashlab-exp002-r9-director-approval-v1` |
| Implemented algorithmic schema | `hashlab-exp002-r9-algorithmic-verification-v1` |

Reference identities are restricted to the fourteen proposed R9 schemas, exposed
as `PROPOSED_SCHEMAS`. Besides the two implemented schemas, these are:

- `hashlab-exp002-r9-external-timestamp-v1`
- `hashlab-exp002-r9-history-checkpoint-v1`
- `hashlab-exp002-r9-solo-archive-v1`
- `hashlab-exp002-r9-restore-verification-v1`
- `hashlab-exp002-r9-human-audit-v1`
- `hashlab-exp002-r9-g1-decision-v1`
- `hashlab-exp002-r9-qa2-decision-v1`
- `hashlab-exp002-r9-g2-decision-v1`
- `hashlab-e001-r9-solo-audit-acceptance-v1`
- `hashlab-exp002-r9-plan-envelope-v1`
- `hashlab-exp002-r9-evidence-envelope-v1`
- `hashlab-exp002-r9-compatibility-decision-v1`

Recognition as a Ref identity does not implement its decoder. Legacy, source
inventory, external raw receipt and policy-bundle schema identities are not
invented or admitted by a permissive namespace pattern. Production references
to such artifacts require a separately reviewed exact allowlist extension and
opaque-format policy. These synthetic contracts therefore cannot bind a complete
real operational evidence bundle.

Canonical JSON uses sorted keys, compact separators, ensure_ascii, no BOM/newline,
and exact re-encoding equality. Duplicate/unknown/missing keys are rejected at
all nested levels. Every JSON numeric token is rejected, including float,
NaN/infinity and integers. Count/size fields use canonical nonnegative decimal
strings; booleans cannot coerce to integers. No schema currently declares a
boolean field. UTC times have exact second precision and valid calendar dates;
Git identities require sha1 plus 40 lowercase hex; digests require 64 lowercase
hex. Source commit lexical validity does not prove object existence or provenance.

Refs contain only schema/digest/size, never paths. Actor/approval/check/attempt
IDs use a bounded flat ASCII grammar `[A-Za-z0-9][A-Za-z0-9_-]*`, reject Windows
reserved device names, and cannot express paths, traversal, ADS or URLs. Ref
arrays sort by (schema,sha256) and reject duplicates. Findings retain declared
order and reject duplicate check IDs. Execution/retry declarations require all
plan/environment/release/commitment references and all three gate schema kinds;
this is only a structural completeness check, never an evaluator.

## Fixed resource policy

| Resource | Bound |
|---|---:|
| Root or referenced artifact | 65,536 bytes |
| JSON container nesting | 16, counted before JSON decoding |
| References per record (including repeated occurrences) | 128 |
| Traversed graph reference occurrences | 128 |
| Supplied artifact-map entries | 128 |
| Resolution depth | 8 edges from root, including opaque leaves |
| Aggregate root plus unique referenced content | 1,048,576 bytes |
| Coverage counts | 0 through 18,446,744,073,709,551,615 |
| Size decimal field | 0 through 65,536 |
| Findings | 128 |
| IDs | 1 through 128 ASCII characters |
| Finding reason | 2,048 characters, no controls or surrogate codepoints |

Decimal strings have at most 20 digits before conversion. Oversized input and
excessive nesting fail before JSON allocation/decoding; child size fails before
hashing. Checks are pure and bounded; resource failures do not trigger retrieval,
repair, retries or resumption. In-memory artifacts already allocated by the caller
are outside this parser's allocation guarantee. Unused map contents are not read.

## Synthetic qualification and negative matrix

Qualified runtime: CPython 3.13.0,
`.venv-py313-review024/Scripts/python.exe -B`.

- Focused: `-m pytest tests/test_exp002_r9_contracts.py -q`:
  **70 passed**, 0.17 seconds.
- Full final suite: `-m pytest -q`: **959 passed, 2 skipped**, 27.89 seconds.
  Both skips are existing E4 symlink cases at test_exp002_e4.py:259; Windows
  denied symlink creation with WinError 1314. They were not qualified here.
- `git diff --check`: passed; tracked implementation/tests/package configuration
  diff against accepted HEAD is empty. New files are listed above.

| Test family | Outcome |
|---|---|
| Two checked-in positive canonical fixtures | Accepted as untrusted frozen values |
| Approved Director without authenticated human-origin evidence | Structurally accepted; no auth/verify API |
| Algorithmic matched/complete false assertion | Structurally accepted; no recomputation or promotion |
| Duplicate root/nested JSON keys | Rejected |
| Unknown or missing fields at every fixture object level | Rejected |
| Whitespace, newline, BOM, alternate escapes, malformed/non-ASCII bytes | Rejected |
| Numeric integers/floats/exponents, NaN, positive/negative infinity, bool counts | Rejected |
| Signed/leading-zero/exponent decimal strings and oversized integer strings | Rejected |
| Uint64 exact upper boundary | Accepted exactly; one above rejected |
| Wrong active/scientific/governance/secondary identities | Rejected |
| Wrong Git object format, uppercase/short commit, incomplete source | Rejected |
| Malformed digest/schema/unsafe ID/reference/device/ADS/path | Rejected |
| Unsupported record schema version | Rejected before contract field validation |
| Oversized bytes/excessive lexical nesting/reference and finding limits | Rejected |
| Duplicate Ref arrays, check IDs, wrong scope/action/study, reversed times | Rejected |
| Invalid calendar/date precision/timezone, incomplete execution declaration | Rejected |
| Missing referenced bytes, size/digest mismatch, unsupported traversal | Rejected |
| Cycle | Active-stack rejection with synthetic digest oracle |
| Actual depth 8 accepted / depth 9 rejected; graph >128 edges | Qualified using supplied byte graphs |
| Aggregate bytes | Boundary rejection tested with reduced test-only limit |
| Import isolation | AST asserts only dataclasses/datetime/hashlib/json/re/typing |

Real content-addressed cycles require a digest fixed point; the cycle test replaces
only SHA-256's test oracle to exercise the branch. All production size/digest
checks remain mandatory. No test claims to authenticate a synthetic receipt.
Approved policy-specific finding order, applicability and coverage truth are
deliberately not inferred from untrusted declarations.

## E001 and legacy preservation

`r9-m1a-e001-preservation.json` retains before/after snapshots for all eleven
sealed files, including exact SHA-256, byte sizes and observed UTC .NET ticks
(100 ns units). Inventory/content/size/mtime differences: **zero**. Read-only
`verify_manifest` returned `[]`. Manifest SHA-256 remains
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.

The baseline snapshot was taken at the start of this assignment. Equality proves
only observed-session preservation; Git does not retain original mtimes, and
this does not establish historical sealing-time metadata or provenance. File
access times were not used as preservation evidence. No E001 evidence file was
written, enumerated as research candidates or numerically reinterpreted.

All accepted tracked E1–E5 source/tests and Revision 8 constants/serializers are
unchanged. E4 VerifiedEvidence and its tests are unchanged. Existing schemas and
receipts remain exact, without silent upgrades. Regression results support
preserved tested behavior, subject to the two platform skips above.

## Complete final Git status and open decisions

Index empty; no tracked modifications. `git status --short`:

```text
?? .venv313/
?? docs/reviews/architecture-review-039-external-readiness.md
?? docs/reviews/architecture-review-040-e6-preparation.md
?? docs/reviews/r9-m1a-contract-foundation-handoff.md
?? docs/reviews/r9-m1a-e001-preservation.json
?? src/hashlab/experiments/exp002_r9_contracts.py
?? tests/fixtures/exp002-r9-algorithmic-synthetic-v1.json
?? tests/fixtures/exp002-r9-director-synthetic-v1.json
?? tests/test_exp002_r9_contracts.py
```

Architecture review must confirm the proposed bounds and new parser/reference
policy identities, exact legacy/opaque/policy/source schema allowlist, and the
explicit terminal policy. The proposal does not define a full typed attempt-ID
domain or policy-approved check order; this foundation validates flat IDs,
study/action consistency and unique checks only. Scope operations are limited
to the proposal's Director action enum; adding report-only operations requires
reviewed versioning. Authentication/withdrawal, external timestamps/trust roots,
history freshness, scientific findings, gate evaluation and any action controller
remain separate future work. No declaration closes existing scientific blockers.

Implementation is ready for the next Architecture Review and remains uncommitted.
