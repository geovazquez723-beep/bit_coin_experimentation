# R9-M1B1 structural policy and reference catalog — Review 048 handoff

Prepared 2026-10-12 against accepted HEAD
`c38755b2ec99fffa60bdd39176ac17ee9487ca03`, branch
`feat/e001-independent-qualification`. Structural implementation and deterministic
synthetic qualification only. Stop for Architecture Review 048; all additions
remain uncommitted and unstaged.

## Assignment inventory and authoritative inputs

Exactly four new assignment files:

- `src/hashlab/experiments/exp002_r9_policy.py`
- `tests/test_exp002_r9_policy.py`
- `docs/reviews/r9-m1b1-e001-preservation.json`
- `docs/reviews/r9-m1b1-structural-policy-handoff.md`

No existing tracked file was modified. Before editing, branch/HEAD matched the
assignment, tracked diff and index were empty. Read the M1B decision proposal,
R9 governance migration and solo governance proposals, Review 043 adoption,
M1A handoff, accepted M1A source/tests and E4 governance/evidence contracts.
Confirmed legacy names in `exp002_foundation.py`, `exp002_governance.py`,
`exp002_provenance.py` and `evidence/manifest.py`. The M1B proposal was already
untracked; it is preserved along with Review 039/040 and `.venv313/`.

## Identities and code-defined profiles

Implemented the three assigned identities exactly:

- `hashlab-exp002-r9-structural-policy-profile-v1`
- `hashlab-exp002-r9-reference-catalog-v1`
- `hashlab-exp002-r9-structural-policy-findings-v1`

Policy and catalog require all four bindings, byte-for-byte in canonical JSON:

| Binding | Exact value |
|---|---|
| active_protocol | `proposal-revision-9\|hashlab-exp002-a2-encoding-v1\|hashlab-exp002-a1-a3-subseed-encoding-v1` |
| scientific_baseline | `proposal-revision-8\|hashlab-exp002-a2-encoding-v1\|hashlab-exp002-a1-a3-subseed-encoding-v1` |
| governance | `hashlab-exp002-solo-governance-v1` |
| secondary | `hashlab-exp002-secondary-statistics-proposal-v2` |

Both parsers compare against exact code-defined documents. Input policy cannot
rewrite check applicability, add schemas, introduce predicates or appoint trust.
The policy declares the fixed field/type matrix, opaque terminals, exact scopes,
check positions/rationales and resource bounds. These definitions are candidates
for Review 048, not authenticated policy adoption or production scientific checks.

Catalog also recognizes the existing two M1A record schemas, source/environment
inventory schemas and human-channel-export-opaque-v1, exactly as specified by the
assignment. The five legacy schemas are the confirmed seedless-plan-v2,
full-plan-binding-v1, accounting-v2, outer-manifest-v1 and hashlab-manifest-v1
identities. No wildcard or other proposed R9 schema is admitted.

## APIs and explicit version boundary

- `parse_structural_policy(data: bytes)` -> `UntrustedStructuralPolicy`
- `parse_reference_catalog(data: bytes)` -> `UntrustedReferenceCatalog`
- `parse_synthetic_declaration(data: bytes)` -> `UntrustedSyntheticDeclaration`
- `recognize_attempt_id(study, label)` -> namespace/number tuple
- `check_structural_policy(record, profile, catalog, supplied_artifacts)` ->
  `StructuralPolicyFindings`

All results remain untrusted. The checker revalidates directly constructed value
objects, rather than trusting their class alone. Imports are limited to standard
library dataclasses/hashlib/json/re and the accepted M1A module's pure parsing
helpers/value types/constants. No package re-export, CLI, runner, service,
execution import, filesystem resolver, plugin or callback evaluator is added.

**M1A incompatibility:** v1 Ref cannot represent the B1 policy, inventory or human
export types. M1A parser, identities, fixtures and tests are unchanged. Passing
an M1A record to the B1 checker fails explicitly; failed v1 parsing never selects
B1. The additional parser is caller-selected and accepts only a qualification
object with `qualification_only="synthetic-b1"`. It uses `record_schema` as a
synthetic target declaration, not a `schema` claim that this object implements
M1A. This is not a v2 production record, compatibility adapter or silent upgrade.

The synthetic object has exactly qualification_only, record_schema, identities,
scope, verification_kind, decision, scope_complete, references and findings.
Its scope has study/operation/attempt/stage. References are explicit flat field
names from the matrix below. It deliberately lacks unsupported M1A approval IDs,
times, actor assertions, subjects, constraints, scope/method refs and dependency
records. Those content contracts need future versioned review. Positive tests
qualify synthetic pre-execution declarations, not complete real approvals.

## Operation-scope and check matrices

All admitted scopes use study `experiment-002`, attempt=null and stage=null.

| Synthetic target | Operation | Verification kind |
|---|---|---|
| Director | policy-adoption | null |
| Director | migration-implementation | null |
| Algorithmic | migration-implementation | qualification |
| Algorithmic | migration-implementation | evidence-integrity |

All other actions, kinds, studies, attempts and stages fail B1 consistency.
The separate future attempt recognizer admits E002-S/Q/A and E001-H with canonical
1..4294967295, checks study association and creates no registry/retry state.
Legacy integer journal IDs remain unchanged.

Director synthetic declarations have no findings. Both algorithmic scopes require
these exact ordered entries, with no omission, duplication, reordering or extras:

| Position | Check | Applicability | Evidence category | Fixed N/A rationale |
|---|---|---|---|---|
| 0 | synthetic-required | required | human-channel opaque export | forbidden |
| 1 | synthetic-optional | optional | exact five legacy identities | Synthetic optional evidence is not supplied. |
| 2 | synthetic-na | not-applicable | none | Synthetic design scope excludes execution. |

A missing evidence set requires explicit state=missing, except the fixed N/A
cases. Required checks cannot self-exempt. Optional missing/N/A entries remain in
the ordered result. Evidence arrays are sorted by schema/digest without duplicate
pairs. Matched/mismatched are unrecomputed claims, never scientific findings.
An asserted complete scope does not establish broader coverage.

## Field-to-type matrix

| Field | Exact permitted type | Synthetic requirement |
|---|---|---|
| bindings.policy_ref | structural-policy-profile-v1 | required; exact supplied profile bytes |
| bindings.source.inventory_ref | source-inventory-v1 | required |
| producer.tool_source_ref | source-inventory-v1 | required |
| bindings.environment_ref | environment-inventory-v1 | optional |
| producer.tool_environment_ref | environment-inventory-v1 | required |
| authorization_evidence_ref | human-channel-export-opaque-v1 | required Director only |
| bindings.seedless_plan_ref | legacy seedless-plan-v2 | optional algorithmic only |
| bindings.full_plan_ref | legacy full-plan-binding-v1 | optional algorithmic only |
| synthetic.catalog_ref | reference-catalog-v1 | required; exact supplied catalog bytes |
| findings.synthetic-required.evidence_refs | human-channel-export-opaque-v1 | explicit missing if absent |
| findings.synthetic-optional.evidence_refs | exact five legacy identities | optional, entry retained |
| findings.synthetic-na.evidence_refs | none | empty |

Names abbreviated above use the exact constants in the implementation. Every
unlisted field fails, including subject/constraints/scope/method/input/reference
arrays, predecessors and operational refs. Catalog recognition of M1A record
identities does not permit them in an evidence field. They cannot become opaque.

## Inventories, resource bounds and opaque behavior

The B1 source inventory is an exact object with schema, object_format=sha1,
40-lowercase-hex commit, and entries. Environment inventory has schema/entries.
Each entry has safe flat id, lowercase SHA-256 and decimal-string byte count
0..uint64 maximum. At most 128 entries, sorted unique IDs. These small newly
implemented declaration contracts are explicitly reviewable B1 definitions;
no environment probing or source-origin verification occurs. Inventory entries
are declared byte pins, not Ref edges and not resolved files. Unknown dependency
fields fail; no missing source content is silently fetched or treated as verified.

Inherited canonical parser preflight rejects >65536 bytes, >16 JSON container
levels, non-ASCII, duplicate keys, numbers/constants and noncanonical encodings.
Exact shapes reject unknown/missing fields and untyped booleans. Reference
occurrences and supplied map entries are capped at 128; aggregate root plus
unique referenced artifacts at 1048576 bytes. Each referenced size and SHA-256
must match explicitly supplied in-memory bytes before typed decoding.

The closed B1 topology has one reference edge from synthetic root to terminal
profile/catalog/inventory/opaque content. It never reaches the inherited maximum
8-edge resolution depth: nested graph fields fail at their first unsupported
edge. Cyclic/deep graphs are rejected structurally rather than traversed. This
phase does not claim to implement a general recursive B1 bundle resolver.
Unrelated map entries are not read. No retrieval, retries, recovery or repairs.

Only the exact human export and five field-permitted legacy identities receive
`bytes-matched-content-unverified`. Their content is not decoded or normalized;
internal schema, dependency completeness, authorship, chronology, scientific
truth, provenance and operational eligibility remain unverified. Policy/catalog
and inventories always require typed validation; implemented records cannot be
downgraded. Every overall result is `structural-scope-only`, trust=`untrusted`,
with explicit limitations and no approval/scientific PASS/receipt/gate/capability.

## Qualification and preservation

Qualified runtime: CPython 3.13.0,
`.venv-py313-review024/Scripts/python.exe -B`.

Focused final run: **187 passed** (117 B1 + 70 unchanged M1A), 0.37 seconds.
Full final regression: **1076 passed, 2 skipped**, 27.61 seconds. Both skips are
existing E4 symlink cases at `tests/test_exp002_e4.py:259`, Windows WinError 1314
(required privilege unavailable). These two cases remain unqualified here;
no new skips were introduced.

Positive cases cover exact profile/catalog, both Director scopes, both algorithmic
kinds, exact opaque bytes, all five legacy terminal names, explicit missing and
optional N/A entries, and all future attempt namespaces at 1/uint32 maximum.
Negative cases cover wrong identities; catalog expansion; missing/duplicate/
unknown keys; malformed/noncanonical/numeric/oversized/deep JSON; all scope,
check-order/applicability and reference-type failures; missing/changed bytes;
opaque typed content; unsafe/duplicate/numeric/overflow inventory entries;
unsupported recursive/cyclic dependency fields; reference/map/aggregate limits;
and explicit M1A incompatibility without fallback. AST/API checks assert import
isolation and absence of file/eval/exec calls and operational public functions.
Approved/matched/complete synthetic assertions only produce untrusted results.

All original tracked files remain identical to accepted HEAD, including E1–E5,
M1A, E4 VerifiedEvidence, legacy serializers, schemas, receipts, package entry
points and governance documents. Tracked/index diffs empty; whitespace check
passed. New code has no scientific or execution dependencies. Same Python,
stdlib SHA-256 and Codex authorship are shared; these tests are synthetic
engineering qualification, not independent human scientific review.

The accompanying preservation JSON contains before/after exact eleven-file
inventories, SHA-256, byte size and observed .NET UTC mtime ticks (100 ns).
Zero differences. Read-only `verify_manifest` returned `[]`; manifest SHA-256 is
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
This establishes observed-session preservation only, not historical mtime origin,
sealing chronology or provenance. File integrity checks did not enumerate or
hash research candidates. No E001 file was written.

## Remaining Director decisions and final working state

Review 048 should accept/amend the precise synthetic profile, check inventory,
field rules, inventory content contracts, API/version boundary and limited
closed topology. Production scientific inventories and the full record v2
content contracts remain deferred. Human-origin channel designation and actual
qualification, retention, withdrawal/freshness/time mechanisms and any future
authentication/permission controller need separate explicit authorization.
No G1/QA2/G2 or operational readiness decision follows from this work.

Index empty and tracked tree clean. Complete intended untracked inventory:

```text
?? .venv313/
?? docs/proposals/experiment-002-r9-m1b-decision-proposal.md
?? docs/reviews/architecture-review-039-external-readiness.md
?? docs/reviews/architecture-review-040-e6-preparation.md
?? docs/reviews/r9-m1b1-e001-preservation.json
?? docs/reviews/r9-m1b1-structural-policy-handoff.md
?? src/hashlab/experiments/exp002_r9_policy.py
?? tests/test_exp002_r9_policy.py
```

No commit, push, merge, tag, external integration, execution, seed selection,
release or operational authority was created. Stop for Review 048.
