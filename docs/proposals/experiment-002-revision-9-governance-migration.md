# Experiment 002 Revision 9 governance migration — architecture proposal

Design identity: `hashlab-exp002-r9-governance-migration-proposal-v1`.
Prepared 2026-10-12 for Architecture Review 044. **DESIGN ONLY; UNCOMMITTED.**
Policy adoption is recorded in
`../reviews/architecture-review-043-director-revision-9-adoption.md`.
Documentation milestone: `c77800f952620b3f846b95eba81d1fbc99a7a8a9`;
accepted implementation baseline: `c26dc40975bc213f67773d6c5fe1709a4843ea76`.
No implementation, new executable schema, tests, service, identity/key selection,
release or execution action is authorized or supplied by this proposal.

## 1. Immutable scientific baseline and architecture boundary

All contracts below bind these exact identities:

- `active_protocol`: `proposal-revision-9|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1`.
- `scientific_baseline`: `proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1`.
- `governance`: `hashlab-exp002-solo-governance-v1`.
- `secondary`: `hashlab-exp002-secondary-statistics-proposal-v2`.

The scientific requirements in the adopted proposal I01–I24 and Revision 8
normative sources remain unchanged. No new schema changes candidate bytes,
sampling law, population, size, statistical cutoff, control or retry eligibility.
Revision 8 code and receipts retain their original meaning and accepted status.
Version dispatch must occur before parsing/validation; no permissive R8/R9 union
decoder or implicit conversion of receipt types is proposed.

Proposed architecture separates read-only artifact parsing, local recomputation,
external receipt validation, Director authorization validation and gate evaluation.
Each returns typed findings with evidence references. Gate evaluators expose no
generator/engine/runner import or callable execution capability. Any future action
controller is separately reviewed and authorized; it is not implemented here.

## 2. Canonical representation and common required fields

The following is a precise proposed byte contract for **new R9 artifacts only**.
Preserved payloads/legacy receipts retain their own bytes and schemas.

Canonical JSON: ASCII bytes, UTF-8-compatible, sorted object keys, compact `,`/`:`
separators, `ensure_ascii=true`, no BOM or terminal newline. Reject duplicate or
unknown keys, missing required keys, malformed UTF-8, NaN/infinity, floating JSON
numbers, coercions and noncanonical byte encodings. Re-encoding must equal input.
Strings use the standard JSON escaping produced by the accepted canonicalizer;
new field/enum names are ASCII. No Unicode normalization of existing text/bytes.
Booleans permitted only where a schema explicitly declares a boolean; integer
fields must never accept booleans. These proposal schemas use decimal strings
for nonnegative counts/indices/sizes to avoid cross-language uint64 precision
loss: `0` or `[1-9][0-9]*`, with explicit field bounds. No sign/exponent/leading
zero. Numeric comparison uses exact integers, never lexicographic string order.
Reported noninteger statistics are referenced in preserved numerical artifacts
or explicit decimal-string fields, never used as rounded gate cutoffs.

SHA-256 pins are exactly 64 lowercase hex characters. Git commits are exactly 40
lowercase hex and `object_format=sha1`; other formats require a separate reviewed
derivation/identity amendment. UTC times are `YYYY-MM-DDTHH:MM:SSZ`; subsecond or
service uncertainty is retained in raw receipt and normalized outward-conservative
time bounds, not silently rounded into compliance. Timestamp arithmetic must
honor the service's bounded uncertainty; unbounded time cannot pass timing gates.
Archive/evidence names are safe flat names, reject traversal/absolute paths,
duplicates, symlinks, Windows junctions/reparse points and unsupported entries;
metadata and hashing are read-only and bounded. Trusted directory/concurrency
limitations must remain explicit until separately qualified.

Definitions used by every contract:

- `Ref={schema,sha256,bytes}`; schema is exact artifact identity, sha256 hashes
  complete canonical artifact bytes (or exact raw bytes for declared opaque
  formats), bytes is exact decimal length bounded by the approved resource policy.
  No embedded self-hash. Referenced content must be resolved and verified, not
  treated as verified from a syntactically valid digest. Missing content blocks.
- `Scope={study,operation,scope_ref,attempt,stage}`. study is `experiment-002` or
  `e001-historical-reconstruction`; operation is a fixed enum appropriate to the
  contract; scope_ref identifies the exact approved geometry/input/output/budget
  specification; attempt is null or exact typed attempt ID; stage is null or
  D/V/C. Free-text notes cannot broaden this scope.
- `Bindings={active_protocol,scientific_baseline,governance,secondary,policy_ref,
  source,configuration_ref,seedless_plan_ref,full_plan_ref,environment_ref}`.
  source=`{object_format,commit,inventory_ref}`. Policy is a separately Director-
  approved immutable versioned bundle defining actors/trust roots, receipt
  validation, archival, time, revocation, expiry and gate predicates. No such
  service-specific bundle is selected here. Configuration/plan/environment refs
  are explicit null only where a contract allows pre-execution design absence.
- `Producer={actor_id,role,tool_source_ref,tool_environment_ref}`. Roles are
  `director`, `operator`, `algorithmic-verifier`, `external-service`,
  `human-auditor`, `archive-operator`, `gate-evaluator`. One human may hold multiple
  solo roles; role strings alone authenticate neither identity nor independence.
- `Finding={check_id,state,evidence_refs,reason}` with state `matched`, `mismatched`,
  `missing`, `unverifiable`, `not-applicable`. Applicability is fixed by policy,
  not chosen after results. An empty findings list cannot satisfy a required check.
- `RecordCommon={schema,bindings,scope,producer,recorded_at,predecessor_ref}`.
  Each artifact has all these keys plus the fields listed below; predecessor_ref
  is explicit null for first/independent records and a verified Ref otherwise.
  `recorded_at` is a declared local time unless independently authenticated;
  it never establishes prereveal chronology by itself.

Every contract below uses RecordCommon (therefore all four identity bindings)
and the same canonical byte rules. Exact schema-field sets are the common set
plus each listed set. Required nullable fields are still required keys. Nested
objects use only the listed fields. Ordered arrays preserve production order;
unordered inventories use filename order, checks use approved check-ID order,
refs sort by `(schema,sha256)` and reject duplicates. Do not sort away historical
array discrepancies. Raw signatures/service envelopes are stored as separate
opaque artifacts with declared format and bounded length, not normalized.

## 3. Proposed versioned contracts

Trust bootstrap and dependency ordering: the initial policy bundle is directly
approved by the human Director, with retained human-origin evidence rooted in
the adoption decision. It cannot authenticate itself through a verifier/policy
that it alone appoints. Its external trust roots and validation criteria need
separate explicit approval before operational use. Policy bytes exclude their
later approval/receipt digests; approvals bind those already fixed policy bytes.
Later policy transitions reference the preceding approved policy and preserve
all earlier decisions/receipts. No self-authenticating policy or invented key.

### 3.1 Research Director approval

Schema: **`hashlab-exp002-r9-director-approval-v1`**.
Additional required fields: `approval_id`, `decision`, `action`, `constraints_ref`,
`subject_refs`, `release_ref`, `seed_commitment_ref`, `gate_decision_refs`,
`authorization_evidence_ref`, `not_before`, `not_after`, `supersedes_ref`.

decision=`approved|denied|withdrawn`; action is exactly one of
`policy-adoption`, `migration-implementation`, `protocol-freeze`, `g1-acceptance`,
`qa2-execution`, `e001-enumeration`, `e001-audit-acceptance`, `release-creation`, `commitment-publication`,
`seed-procedure`, `exp002-execution`, `retry`, `interpretation`, `publication`.
scope.operation must equal action. approval_id is a nonempty policy-unique ASCII
ID; not_before/not_after are UTC bounds; supersedes_ref is null or a prior approval
Ref, never an overwrite. constraints_ref is the exact permitted budgets/operation
and prohibitions, with no implicit sub-actions. subject_refs names every artifact
being approved, not an unspecified mutable branch/latest file.

Only the human Director can authorize; an AI/tool may record directly supplied
approval and must preserve its human-origin evidence reference. Authentication
validates the designated human-origin channel or separately approved self-signing
policy; it does **not** mint an ExternalTimestamp or HumanAudit type. A copied
operator-written “approved” string without acceptable human-origin evidence is
unverifiable. No signing key is mandated or selected now; authoritative channel
retention/identity policy must be approved before machine-verifiable use.

For exp002-execution/retry: source, resolved configuration, seedless/full plans,
environment, release_ref and seed_commitment_ref must all be nonnull and exact;
gate_decision_refs must name valid G1/QA2/G2 records for that binding. Constraints
include one exact allowed attempt/operation and deterministic same-seed rules.
For pre-seed policy/design actions, future release/seed/full plan refs may be null
but authorization cannot later be upgraded to execution. Missing, expired,
withdrawn, mismatched or wrong-action approval blocks authorization; denial is
not recoverable by a tool's recommendation. Written approval is permission for
the scoped action only, never scientific PASS evidence.

### 3.2 Algorithmic verification report

Schema: **`hashlab-exp002-r9-algorithmic-verification-v1`**.
Fields: `verification_kind`, `input_refs`, `method_ref`, `reference_refs`,
`findings`, `coverage`, `implementation_separation_ref`, `shared_dependencies_ref`,
`limitations_ref`, `first_mismatch_ref`.

verification_kind=`statistical|candidate-reconstruction|evidence-integrity|
historical-compatibility|overlap|qualification|combined`.
coverage=`{unit,expected,checked,scope_complete}` where unit is exact approved
`occurrences|records|files|checks`, expected/checked are decimal strings and
scope_complete=`complete|partial|unknown`. This is structural coverage, not a
truth/validity pass boolean. first_mismatch_ref is null only when none observed.

An operator/verifier tool can produce this artifact; pins identify its method,
source/environment and immutable inputs. Independent algorithms/import isolation,
reference provenance, exact counts/labels and boundary-safe numerical checks are
technically recomputable. Shared Python/crypto libraries and same Codex authorship
must be disclosed. A self-produced report is a claim until checks are recomputed
at the claimed scope. Numerical uncertainty/mismatch fails the affected finding;
missing inputs/incomplete scope blocks gate use. Neither different AI session nor
the report's schema establishes independent human review or chronology.

### 3.3 Authenticated external timestamp receipt envelope

Schema: **`hashlab-exp002-r9-external-timestamp-v1`**.
Fields: `service_id`, `authority_policy_ref`, `subject_refs`, `purpose`,
`raw_receipt_ref`, `trust_material_ref`, `service_time_bounds`,
`verification_method_ref`, `verification_report_ref`.
purpose=`preregistration|evidence-seal|verification-report|approval-retention`;
service_time_bounds=`{earliest_utc,latest_utc}` encloses the service-attested time.

External service issues the opaque raw receipt; operator may create the envelope.
Its authenticity comes from independently validated service evidence, not
producer.role=external-service or envelope fields. A separate service adapter
must check signature/subject/algorithm/trust chain/time/retention and approved
authority policy, using pinned code/dependencies/reference vectors. Report ref
records these checks; replay must revalidate them. For preregistration subjects
must include exact C_pre and preregistration bundle references; conservative
latest_utc must be at least24h before the frozen R* schedule. A local timestamp,
signed Git object alone or service timestamp for unrelated bytes fails.

Missing receipt, uncertain time, wrong subject or invalid signature fails the
receipt; unavailable trust/expiry/revocation evidence blocks it. No provider/root
is selected. Long-term validity at issuance versus present certificate expiry
requires explicitly approved archival-validation policy and retained trust data;
there is no automatic expiry waiver or assumed perpetual validity. The evidence
proves the service's time/content claim only, not execution honesty/completeness.

### 3.4 External attempt-history checkpoint receipt

Schema: **`hashlab-exp002-r9-history-checkpoint-v1`**.
Fields: `history_id`, `sequence`, `entry_id`, `entry_kind`, `entry_ref`,
`history_head_sha256`, `previous_head_sha256`, `previous_checkpoint_ref`,
`registry_commit`, `receipt_ref`, `retention_policy_ref`, `retention_evidence_ref`,
`latest_head_evidence_ref`, `checkpoint_findings`.
entry_kind=`started|result|failure-disclosure`; sequence is decimal≥1.
entry_id distinguishes S/Q/A and actual audit attempt domains. First predecessor
is null only with approved empty-head pin; every later checkpoint links exactly
to the prior retained head/checkpoint. registry_commit is exact Git40 string.

Operator constructs the entry/envelope; external timestamp/retention service
authenticates content/time/storage promises via receipt_ref (timestamp schema)
and retention evidence. A history checker validates gap-free immutable entries,
prior receipts and one designated history per approved scope. Started entries
must be committed and externally checkpointed before their action; result or
partial/failure disclosure checkpoint precedes any next attempt. Interrupted
records/locks/torn bytes retained; no journal repair or automatic resumption.

Retaining an old signed head does not prove it is latest. latest_head_evidence_ref
must establish the approved freshness/lookup or previously independently retained
monotone pin needed for the transition. If the chosen service cannot provide
that check, the operation blocks; current design does not pretend timestamps
alone prevent rollback. Approved externally published checkpoint inventory may
provide a solo substitute, with its exact freshness/suppression limitations
disclosed. Stale/forked/duplicate/gapped/replayed/wrong-scope entries fail; missing
freshness/retention blocks. Private omitted actions remain a single-operator risk.

### 3.5 Solo archive and restoration records

Schemas: **`hashlab-exp002-r9-solo-archive-v1`** and
**`hashlab-exp002-r9-restore-verification-v1`**.

Archive fields: `original_inventory_ref`, `archive_inventory_ref`,
`source_bundle_ref`, `dependency_inventory_ref`, `destination_records`,
`prior_external_anchor_refs`, `copy_report_ref`, `restore_due_utc`, `limitations_ref`.
Each destination_record=`{destination_id,failure_domain,control,storage_policy_ref,
copy_receipt_ref,verification_report_ref}`; control=`operator|independent-custodian`.
Two distinct off-machine failure domains required for target Level 2; at least one
offline or retention/version protected. IDs are declarations until actual receipt/
restore evidence validates them. Operator ownership does not establish independence.

Restore fields: `archive_ref`, `destination_id`, `restored_inventory_ref`,
`prior_external_anchor_refs`, `verification_tool_ref`, `findings`,
`original_preservation_report_ref`, `next_check_due_utc`.

Archive operator can produce both; independent tool/hash implementation can
recompute file bytes/sizes/inventory/source references at destinations and restored
directory against prior external pins. Never write originals, include new audit
files inside E001, overwrite failed restores or infer archive validity from copy
success. Missing originals/entries, altered bytes or unsafe filesystem entries
fail integrity; absent destinations/receipt/restore/fresh retention evidence
block archival completeness. Annual restore checks and retained prior reports
remain required. Claims are solo retention unless separate custody attestations
actually exist. Schema common R9 binding describes this new archive record;
original E001 payloads retain their historical source/manifest identities.

### 3.6 Optional independent human audit attestation

Schema: **`hashlab-exp002-r9-human-audit-v1`**.
Fields: `reviewer_identity_ref`, `appointment_ref`, `conflict_disclosure_ref`,
`independence_policy_ref`, `reviewed_refs`, `methods_ref`, `findings`,
`limitations_ref`, `signed_statement_ref`, `authentication_report_ref`.

Only an actually appointed separate human auditor supplies the authenticated
statement; AI/operator may package it. Verify signer/appointment/scope/conflicts,
signature or approved direct human-origin authentication, and exact reviewed
artifact pins. Same producer author/AI session cannot self-attest independence;
mere schema/role string is invalid evidence. Forged/conflicted/wrong-scope or
unverifiable audit blocks a Level3 claim. Absent human audit is explicit
`not-performed` assurance at Level2, never a synthetic placeholder attestation.
No human auditor is appointed by this proposal.

### 3.7 G1, QA2 and G2 decision records

Schemas: **`hashlab-exp002-r9-g1-decision-v1`**,
**`hashlab-exp002-r9-qa2-decision-v1`**,
**`hashlab-exp002-r9-g2-decision-v1`**.
Fields common to these three: `criteria_ref`, `findings`, `component_evidence`,
`assurance_state`, `decision`, `director_decision_ref`, `limitations_ref`.
decision=`pass|conditional|blocked|fail`; component_evidence is an ordered list
of `{requirement_id,evidence_refs}` fixed by criteria_ref. Gate decision is a
derived report, not permission to dispatch; no execution_enabled field/capability.

G1 additional fields: `regression_report_ref`, `sampling_report_refs`,
`statistical_reference_refs`, `control_report_refs`, `blinding_report_ref`,
`historical_qualification_refs`, `overlap_capability_refs`, `platform_report_refs`.
QA2 additional fields: `g1_ref`, `qa2_action_approval_ref`, `release_ref`,
`fixture_inventory_ref`, `production_path_report_ref`, `evaluation_ledger_ref`,
`algorithmic_report_refs`, `q_history_checkpoint_refs`.
G2 additional fields: `g1_ref`, `qa2_ref`, `release_ref`, `smoke_report_ref`,
`e001_acceptance_ref`, `overlap_report_refs`, `precommitment_ref`,
`prereveal_timestamp_ref`, `beacon_verification_ref`, `seed_commitment_ref`,
`history_checkpoint_ref`, `archive_ref`, `audit_policy_ref`.

Evaluator recomputes criteria/identities and evidence cross-links; Director may
record acceptance but cannot turn failed mandatory science into pass. Mandatory
missing implementation/input/authentication/approval→blocked, observed invalid
qualification/mismatch/forbidden action→fail. Conditional is only for explicitly
optional assurance enhancements, cannot enable target Level 2 execution. PASS needs
all mandatory criteria. A gate's source/config/environment must match qualification
and actual release; reusing component results requires explicit compatibility
evidence, not automatic transitive approval.

Gate-acceptance Director approvals bind the exact already existing input evidence,
criteria, source, environment and intended gate scope, not the digest of the
gate decision that will later reference the approval. The evaluator independently
derives the decision from those inputs. QA2-execution approval precedes QA2 and
binds G1/release/fixtures; exp002-execution approval follows completed G2 and
binds its digest. This ordering prevents approval/gate reference cycles.

G1 retains all R8 bullets and exact historical requirements;86 discrepancies and
unresolved original-runtime provenance cannot be silently waived. QA2 retains
same actual production path, exact fixtures/labels/critical counts, allowed
numerical tolerance,2048+2048+≤104≤4200 evaluations and retained Q history. G2
retains frozen release, complete audits, G1/QA2, S1–S5, ≥24h prereveal time, fixed
beacon, restored evidence readiness and Director pre-execution decision. Synthetic
component evidence cannot supply missing integrated QA2 hashing evidence.

### 3.8 Final E001 audit acceptance under solo governance

Schema: **`hashlab-e001-r9-solo-audit-acceptance-v1`**.
Fields: `historical_source_ref`, `historical_manifest_ref`, `historical_contract_ref`,
`audit_attempt_ref`, `audit_scope_ref`, `completed_manifest_ref`,
`producer_accounting_ref`, `algorithmic_report_refs`, `historical_compatibility_refs`,
`external_outer_anchor_ref`, `history_checkpoint_ref`, `director_approval_ref`,
`criteria_ref`, `findings`, `assurance_state`, `decision`, `limitations_ref`.
decision=`accepted|rejected|pending`; scope.operation=`e001-audit-acceptance`.

New acceptance record is produced by Director/recording tool after read-only
validation of complete historical evidence. Exact original source commit
ef595f5c2f2166923fd277def39708409f564419, manifest
546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b,
contract and configuration/seed pins must match accepted E5 contracts. Verify
all 7000000 raw occurrences,14 stream boundaries, historical seeded phase restarts,
dedup precedence, patterned continuation, attempted/unique accounting, A1 zero,
distinct A3 exact 60721/count/ranks/approved digest and first provenance. Expected
values cannot be copied into the observed report. Authenticate full inputs,
source/environment, external completed-manifest anchor and disclosed attempt
history; Director approval does not supply missing independent algorithms or
historical source/runtime equivalence. Strict numerical reproduction findings
remain separately explicit; no tolerance-based historical identity pass.

Allowed Director approval action for this decision is `e001-audit-acceptance` with
Scope.study=e001-historical-reconstruction and exact acceptance subject_refs;
it does not authorize enumeration, hashing or E002. Enumeration itself needs
separate `e001-enumeration` approval. Approval subject_refs bind the completed
manifest, algorithmic reports, criteria and external receipt, not the later final
record or its own approval digest. This prevents an approval/final-record cycle.
The record is pending if required evidence is missing/unverifiable, rejected on
mismatch, accepted only when every mandatory criterion and authorization match.
An accepted string alone has no effect. Missing optional human audit limits the
claim to solo algorithmic verification/anchoring, not independently audited science.

Store final record **outside** the completed producer seal. Acyclic order:
producer evidence→algorithmic report→completed manifest→external outer receipt→
Director approval→final acceptance record→optional later custody inventory.
No manifest includes its own hash or later receipt/acceptance digest. Producer
coverage, algorithmic findings, external authentication and Director acceptance
remain distinct. E5 fixture schemas and validator stay permanently incapable
of historical acceptance; new production scope/validator requires later approval.

## 4. Separate evidence states and trust evaluation

`assurance_state` is a required object in gate/final records:

```text
local:              {state: present|partial|missing, evidence_refs: [...]}
algorithmic:        {state: matched|mismatched|incomplete|unverified, evidence_refs: [...]}
external:           {state: authenticated|invalid|unverifiable|missing, evidence_refs: [...]}
director:           {state: approved|denied|missing|unverifiable, evidence_refs: [...]}
human_audit:        {state: authenticated|invalid|unverifiable|not-performed, evidence_refs: [...]}
```

Each nested object has exactly state and evidence_refs. States are recomputed
by the relevant validators, not trusted because present in JSON. A present local
file does not imply matched calculations; a matched report does not imply external
time; a valid timestamp does not imply Director approval; approval is not human
independent review. No single boolean replaces this vector. Required checks must
identify actual receipts/reports, including policy/validation-time scope. Missing
human audit at Level2 is disclosed; invalid purported audit cannot be silently
dropped to advertise Level3. Invalid advertised evidence remains a discrepancy.

Proposed future types (design names only): `LocalArtifact`,
`AlgorithmicCheckResult`, `AuthenticatedTimestamp`, `AuthenticatedHistoryCheckpoint`,
`ValidatedDirectorApproval`, `AuthenticatedHumanAttestation`, `GateFinding`.
Construct authenticated types only via approved validators; deserializing a claim
cannot manufacture them. These new names do not subclass, alias or mutate E4
VerifiedEvidence. Type encapsulation is an API correctness boundary, not a security
proof against malicious Python/operator code; externally verifiable receipts and
disclosed trust policy supply the independent claims they actually support.

## 5. Explicit compatibility mapping

Proposed support envelopes needed for unambiguous new bindings:
`hashlab-exp002-r9-plan-envelope-v1`,
`hashlab-exp002-r9-evidence-envelope-v1`,
`hashlab-exp002-r9-compatibility-decision-v1`.
All use RecordCommon. Plan adds `legacy_plan_ref`, `scientific_config_ref`,
`approval_policy_ref`, `assurance_target` (level2); evidence adds `payload_inventory_ref`,
`accounting_ref`, `history_entry_ref`, `plan_envelope_ref`; compatibility adds
`legacy_refs`, `new_subject_refs`, `reused_check_ids`, `recomputed_check_ids`,
`findings`, `limitations_ref`, `director_approval_ref`. Future schemas are proposed,
not applied to current files. No envelope can confer broader scientific coverage
than the underlying payload; new source/plan hashes require actual reviewed binding.

| Existing interface/type | Proposed R9 relationship | Reuse rule / unchanged boundary |
|---|---|---|
| E1 Config/PROTOCOL_IDENTITY, A1/A3 seed APIs, A2 encoding, Vitter D | Preserve scientific implementation; new plan envelope binds R9+R8 baseline+unchanged encoding IDs | R8 config/plan bytes remain exact; do not change constants in place or claim old schema validates R9. Later explicit source/config migration necessary. |
| E2 Stage/Arm/analyze/controls and secondary count engine | Reports reference unchanged count outcomes and SECv2 | Reuse exact scientific references/tests within source/geometry; governance never changes classification/control thresholds. |
| E3 Plan v2/accounting v2/CandidateRecord/SuccessRecord/evidence validator | New plan/evidence envelopes bind unchanged payload schemas or separately reviewed new versions | No silent accounting format conversion, success proof or complete execution inferred from structural validation. |
| E4 Claim/ExternalVerifier/VerifiedEvidence/require_verified | Preserve all R8 behavior; new R9 typed validators parallel | Never cast DirectorApproval into externally verified Claim, never accept permissive alwaysTrue callback as service authentication. |
| E4 FullPlanBinding/CommitmentContract | New plan envelope plus specific algorithmic/timestamp/seed reports | Keep old fingerprint/identity semantics; new full binding and seed derivation need independent exact validation. |
| E4 check_eligibility | New read-only R9 G1/QA2/G2 evaluator architecture | Old function remains R8 and execution_disabled. New gate cannot expose dispatch or substitute for specific action approval. |
| E4 AttemptJournal and retry-review | New history/checkpoint/Director retry policy at a separately versioned boundary | Preserve old chain/canonical bytes/locks/failed disclosures. No automatic adapter changes old external-history/retry semantics. |
| E4 evidence-completeness / outer-manifest proof and seal/verify_seal | New local/algorithmic/evidence-envelope findings plus external outer timestamp | Legacy receipts remain legacy; no local inventory declared as authenticated completeness. New seal integration needs explicit review, retain E001 manifest format. |
| E5 PhaseA contract/history pins; PhaseB ExactDedup/chunks/checkpoints/core | Scientific reference component evidence retained; later full provider/report and solo final acceptance type separate | Fixture 4096 caps and historical false unchanged; same Codex author disclosed, not Level3 independence. |
| E6/readiness documents | Historical R8 ownership/provenance findings referenced unchanged | R9 changes organizational requirements prospectively; scientific gaps/old blocked verdicts not rewritten. |

Exact E4 evidence-kind mapping (not an executable adapter):

| R8 kind | R9 technical evidence / authority |
|---|---|
| e001-reconstruction | Full solo audit acceptance + exact algorithmic reports; Director decision distinct from external outer anchor |
| overlap-audits | Complete algorithmic E/D/M reports and preserved P/C disclosures |
| g1 | G1 decision with Director acceptance and exact required component checks |
| qa2-statistical | QA2 statistical reports, unchanged independent references and cutoffs |
| qa2-hashing | QA2 actual production-path report/evaluation ledger, never synthetic count substitute |
| g2 | G2 decision; no dispatch permission |
| precommitment | Exact C_pre/bundle plus authenticated external timestamp |
| witness-timing | New authenticated external timestamp timing finding, explicitly different semantic type |
| beacon-verification | Pinned actual beacon cryptographic verification report, same fixed round rules |
| seed-record | Exact deterministic seed/full plan/config verification report and C_seed |
| registry-history | History checkpoint, prior chain and externally retained fresh head check |
| release-approval | Action-specific Director approval for release; release artifact identity verified separately |
| director-authorization | New Director approval for the exact specific action, not an external scientific attestation |
| retry-review | Root cause/amendment algorithmic findings + specific Director retry approval + external previous history checkpoint |
| evidence-completeness | Exact inventory/accounting/coverage findings at specified scope; no proof of unknown omitted outcomes |
| outer-manifest | Completed manifest recomputation plus authenticated external retained digest |

Old evidence reuse requires a new compatibility decision with exact old/new pins,
established scope/checks, preserved old verdict and separately recomputed R9
binding. Old scientific references may support identical arithmetic/encoding
claims. Old organizational approvals/witnesses do not automatically satisfy R9
policy or action scope; verify actual semantics under explicitly approved policy.
No old failed/blocked outcome becomes pass, no mixed receipt family without
documented decision, and no fresh QA2 qualification inferred from component tests.

## 6. Action-specific execution authorization boundary

Future read-only evaluation order: parse strict versions→verify identities/input
inventory→recompute scientific/algorithmic checks→validate external receipts and
history→validate Director approvals→record G1/QA2/G2 findings. Outputs are immutable
reports only. No evaluation calls a candidate generator, hash engine or dispatcher.

Even G1/QA2/G2 PASS is insufficient for an execution action. A separately reviewed
future action validator must require a distinct approved `exp002-execution`
Director record, exact release source/inventory, actual environment, approved
scope/geometry/budget, full plan/config/seed commitment, current G2 record and one
eligible attempt. Recheck approval validity/withdrawal, same bindings and latest
history; commit/checkpoint started entry before action. `protocol-freeze`,
`g1-acceptance`, `qa2-execution`, policy adoption and generic “ready” cannot satisfy
this authorization. A retry requires its own Director `retry` approval plus all
unchanged scientific retry restrictions; cannot use initial execution permission
to authorize a replacement seed or second valid run.

This action validator/controller is **not implemented**. No runnable operation,
entry point, shell command, release or execution capability is supplied here.
Future atomic approval-consumption/withdrawal/history races and crash disclosure
need separate architecture review before dispatch can exist. No automatic
repair/recovery/retry is introduced by this design.

## 7. Proposed synthetic qualification — not implemented or executed

All cases use visibly synthetic identifiers/opaque fixture receipts and metadata,
zero research candidates/hashes. No real authority key/service/time/round chosen.
Future tests must qualify validators against independent expected findings,
preserve historical R8 behavior and never produce real passing operational receipts.

| Case | Required future outcome |
|---|---|
| Missing Director approval; only gate PASS/adoption exists | Action blocked; no started entry/action capability. |
| Approval for QA2, wrong attempt, different environment/release/budget/action | Exact-scope mismatch, no broader permission inferred. |
| Active R9/governance/SEC mismatch or wrong scientific R8 baseline | Reject before receipt checks; no permissive fallback. |
| Bare local approval cast as external evidence | Type/authentication rejection; preserve legacy VerifiedEvidence tests/behavior. |
| Invalid timestamp/signature, unrelated digest, uncertain time, lead <24h | Invalid/blocked timing; no seed procedure eligibility or round replacement. |
| Expired/unverifiable authority, missing revocation/trust data | Block/fail according to explicit validated authority policy; no silent expiry waiver. |
| Claimed independent human audit from AI/same producer/no appointment/signature | Reject claim; Level3 unavailable; disclose discrepancy, not manufacture attestation. |
| Rollback/fork/stale head/gap/duplicate/replayed receipt/wrong history scope | Reject or block freshness; preserve bytes, no head reset/repair/new attempt. |
| Missing/unlisted/truncated/rewritten inventory plus rewritten local manifest | Fail against prior external pin; no restored copy/archive completeness claim. |
| Reuse legacy scientifically valid fixture as integrated QA2 | Reject coverage/geometry/path mismatch; no QA2 PASS. |
| Unapproved retry/F4 same code/valid final retry/seed replacement | Reject even if Director generic approval or gate PASS supplied. |
| Execution request with every gate PASS but no separate exp002-execution approval | No capability/action; separate permission mandatory. |
| Arbitrary JSON producer role/status/assurance vector assertions | Recompute typed findings; unverified claims cannot construct authenticated types. |
| Cyclic report/manifest/receipt/selfdigest references | Reject cycle; final acceptance outside producer seal. |
| Partial writer/lock/disk failure/missing checkpoint or Director withdrawal | Retain incomplete evidence, block next action, no retry/resume/repair. |
| Accepted R8 records and E001 originals read after future migration | Exact original bytes/digests/semantics; no retroactive conversion/adoption claims. |
| uint64 precision loss, boolean counts, duplicate keys/unknown fields/unsafe paths | Fail canonical/type/parser validation before unnecessary work. |

## 8. Open decisions and dependencies

Director/Architect must approve this architecture/schema set and exact policy
criteria before implementation. Still open: human-origin approval retention/
authentication/withdrawal policy; external timestamp provider/trust roots and
archival expiry validation; fresh head lookup/retention and outage policy; two
off-machine failure domains/restore cadence; source/environment/release bundle
qualification; future authorized independent human audits, if any. No identities,
services, keys, timestamps or round values are fabricated by schema design.

Scientific/engineering blockers remain from READY/E6: full E001 provider and exact
exclusion proof, original CPython provenance/compatibility and86 discrepancies,
actual controls/audits and P2− engine, independent E002 candidate/evidence verifier,
blinding/production integration, A1 feasibility, Windows/SQLite/disk/native RSS
qualification, integrated QA2, beacon client/live chain and audit-seed format policy.
No schema declaration closes those gaps. Original evidence is immutable.

Dependency order: accept architecture/policy boundaries→separately authorize
typed schema/validator implementation and synthetic qualification→resolve exact
scientific prerequisites and actual production integration→separately authorize
QA2/release/commitment procedures→later G2 and distinct execution authorization.
No next implementation or qualification activity begins here. Stop for Review 044.
