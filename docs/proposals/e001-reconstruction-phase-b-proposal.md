# E5 Phase B — complete historical E001 reconstruction proposal v1

Architecture Review 037 documentation for Review 038.
Proposal identity: `hashlab-e001-reconstruction-phase-b-proposal-v1`.
Status: proposed, not approved or implemented. No enumeration authorization.

## Accepted baseline and closeout

E5 Phase A commit: `9d31eda5d7f20af00824ccdbe1452f8509567952`.
Parent E4: `1a332d8c1ace2c36fa80bc8b808b3d72eba3e255`.
Branch remains `feat/experiment-002-e5`.

Review 037 closeout staged exactly the seven files in
[the Phase A handoff](../reviews/architecture-review-036-e5-phase-a.md).
Historical contract SHA-256, all eight historical source pins, sealed manifest,
eleven evidence hashes/sizes/inventory/mtime_ns and unchanged E1–E4 source were
rechecked. Qualified CPython 3.13: 79 focused tests passed in 3.73s;
832 full regressions passed, two existing symlink-privilege skips in 19.37s.
The accepted historical source/contract/test files are not edited by this proposal.
The Phase A 4,096-occurrence fixture limits remain unchanged.

## Scope and fixed identity

Reconstruct exactly **7,000,000 attempted eight-byte occurrences**, not seven
million globally distinct candidates. These are the seven E001 eight-byte
generators, in their original resolved-config order, each discovery then
validation, each 500,000 attempts. Do not include the three sixteen-byte streams,
positive-control 200,000 inputs, hashes, success outcomes or E002 samples.

| Config ordinal / ID | Raw discovery indices | Raw validation indices | Historical enumeration indices |
|---|---|---|---|
| 0 seq-be-w8 | 0..499999 | 0..499999 | 0..499999 then 500000..999999 |
| 2 uniform-be-w8 | 0..499999 | 0..499999 | per-phase draw ordinal, 0..499999 |
| 4 pattern-bytes-w8 | 0..499999 | 0..499999 | primitive-output ordinal 0..499999 then 500000..999999 |
| 6 struct-gray-w8 | 0..499999 | 0..499999 | continuing index 0..999999 |
| 7 struct-stride-w8 | 0..499999 | 0..499999 | continuing index 0..999999 |
| 8 struct-bitrev-w8 | 0..499999 | 0..499999 | continuing index 0..999999 |
| 9 random-bytes-w8 | 0..499999 | 0..499999 | per-phase draw ordinal, 0..499999 |

Bindings are mandatory, not parameters to choose at audit time:

- E001 run `20261011T205056Z-exp001-fc1d75fc`.
- Historical source commit `ef595f5c2f2166923fd277def39708409f564419`.
- Sealed manifest SHA-256 `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
- Sealed resolved config SHA-256 `d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b`.
- Phase A contract LF SHA-256 `008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04`.
- Exact original seeds, counts and source SHA-256 map in
  `src/hashlab/experiments/e001_contract.json`.

The provider must reject a mismatch rather than infer omitted inputs/defaults.
Authenticate every original file read-only against the pinned eleven-file
inventory before beginning, and reverify original bytes/sizes/mtime_ns afterward.
Source verification is against immutable Git objects and actual loaded files;
source newline normalization must never alter sealed evidence or candidate bytes.
Record all relevant generator/runner dependencies, not just a branch or tag name.

## Complete iteration and deduplication semantics

Preserve the exact pinned generator definitions:

- Sequential: start zero, unsigned eight-byte big-endian integer.
- Uniform: CPython integer-seeded Random.getrandbits(64), eight-byte BE encoding.
- Patterned: all 256 byte values; primitive motifs of length 1, then 2, then 3;
  lexicographic motif order, repeated/truncated to width 8. Reject motifs whose
  resulting candidate has a smaller period. The emitted-candidate ordinal is
  different from the number of motifs visited. Do not replace with numeric sort.
- Gray: i XOR (i>>1), eight-byte BE.
- Stride: (11400714819323198485*i) mod 2^64, offset zero, eight-byte BE.
- Bit-reversed: reverse exactly 64 bits of i, eight-byte BE.
- Random bytes: keyed BLAKE2b-512, seed encoded as 16 BE bytes; 16-byte BE block
  counter from zero, concatenate blocks and cut consecutive eight-byte slices.

Seeded discovery/validation restart independent streams using only sealed seeds:
uniform-be 11563638942429927757 / 17448145370022348540;
random-bytes 710289665967761509 / 8231496708541735395.
No seed replacement, derived new execution seed or candidate SHA-256 is allowed.
Label-material seed derivation may be verified separately as metadata, using the
already sealed hashlab-seed-v1 rule; it does not select new material.

Seedless validation continues after 500,000 attempted discovery outputs, not
500,000 accepted hashes or 500,000 visited pattern motifs. A stateful patterned
iterator may continue directly; an independently implemented index/motif mapping
must demonstrably yield the same output sequence. No stream restarts silently at
zero for validation. Phase transition and bit/nonce boundaries get exact vectors.

Historical deduplication is per generator, never across generators. Under auto,
sequential/patterned/structured are unique by construction. Uniform and random
bytes retain all distinct discovery values through validation. For each raw draw:

1. Count one attempt, regardless of duplicate status.
2. If present in the discovery set during validation, classify cross-phase duplicate.
3. Else if already seen in the current phase, classify within-phase duplicate.
4. Else classify accepted unique candidate, store first-observation provenance.

Do not top up skipped duplicates. All raw occurrences, including repeated values,
remain auditable. A global candidate value repeated in another generator remains
a separate occurrence. The sealed counts happen to report no within/cross-phase
duplicates and 500,000 unique values per stream. Recompute, do not assume, those
counts. An unexpected discrepancy blocks qualification and is retained.

## Intersections and exclusion qualification

Check A1 membership on every eight-byte raw occurrence using the frozen U1
predicate: integer in [2^20,2^32). Record A1 hit occurrence count and distinct hit
values, with first provenance and every stream's count. Required full-scope
result is zero occurrences and zero distinct values; a hit blocks acceptance.

Check A3 structural membership independently: nonzero top 32 bits, Hamming weight
1..6. Insert each eligible value into an exact global set, retaining occurrence
count and first provenance. Repeated eligible values from any generator/phase
contribute occurrences but only one exclusion. Derive rank using the accepted
weight/colex order; independently count eligible values earlier in
(weight,numeric) order to cross-check rank/unrank.

Output increasing unique ranks and separately increasing unique NUMERICAL VALUES.
The approved exclusion digest is SHA-256 of their concatenated eight-byte BE
value encodings, with no separators/header and no rank/weight-order hashing.
This is the exclusion-set/file-integrity digest, not candidate SHA-256 evaluation
or research success testing. Required production comparison:

- exactly 60,721 independently observed distinct A3 values;
- digest `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`;
- rank set, numeric value set and independent implementation agree exactly;
- all seven million attempts and fourteen stream boundaries accounted for.

These are acceptance predicates, never inserted counts or fabricated vectors.
Do not truncate at 60,721 or suppress extra values. A mismatch must retain the
actual count/digest/hits and fail. If enumeration is interrupted, no E-pass claim
is permitted even if a partial digest coincidentally matches a known value.
Reconstructing these sets does not authenticate SHA-256 research outcomes.

## Reserved bounded-memory/external-storage design

Propose a separately reviewed full-stream provider; do not lift Phase A limits.
Use a dedicated trusted local scratch directory outside the sealed evidence tree,
with exclusive attempt-directory creation, plain-file/no-reparse checks and an
owner/ACL policy. No concurrent hostile mutation is in the supported model.

A proposed disk-backed exact set backend uses SQLite BLOB primary keys for the
two seeded eight-byte streams, one generator at a time. Each row records first
phase/index, allowing the precise duplicate classification above. A distinct
global A3 table holds numeric value, rank and first provenance. Store unsigned
64-bit numeric values as fixed eight-byte BE BLOBs, not signed SQLite INTEGERs;
lexicographic BLOB order then equals unsigned numeric order. Rank fits in an
integer but must pass exact range/type validation. No Bloom filter, digest-only
key or probabilistic membership structure may decide inclusion/deduplication.

Reserve 64 MiB application working memory plus a configured 32 MiB SQLite page
cache, at most 4,096 buffered output occurrences and bounded sorting/output
buffers. These are proposed backend budgets requiring instrumentation, not
proven guarantees for Python/SQLite/OS RSS. Limit whole-process RSS separately to
512 MiB after platform qualification; enforce a recorded abort on exhaustion.
SQLite/version/transaction/journal-mode settings must be pinned and independently
qualified. Workspace/security settings and WAL files are mutable scratch state,
not authenticated audit output. Avoid using database state as an unverified resume
point. Exact full comparison can independently consume immutable occurrence files.

Reserve **2 GiB local scratch/output capacity** plus **2 GiB independently held
copy capacity**, before complete enumeration. This is a conservative proposal,
not an observed resource requirement. Seven million 12-byte occurrence records
(index uint32 BE + eight-byte value) occupy 84,000,000 bytes plus chunk headers.
Rank/value/exclusion files and database indexes/WAL/temp space add overhead;
reserving multiple copies and failure artifacts motivates the larger allowance.
If the reviewed backend cannot stay within the reservation, stop incomplete;
never delete prior evidence or silently expand scope/storage during the run.

An in-memory exact-set alternative would need an explicitly approved larger RAM
reservation (roughly 80–160 MiB per million Python eight-byte values, plus runtime,
independent implementation and exclusions). It is not the proposed default.
External sorting is another possible separately reviewed alternative; merge runs
must retain provenance and exact bytes, not change the scientific comparison.

## Independent implementation and runtime readiness

**Historical source correspondence is sufficiently established for Phase A, but
full runtime compatibility and independent reconstruction are not yet established.**
All eight pinned historical source files match immutable source objects and
loaded checkout bytes. Exact bounded fixtures cover source wiring, seed values,
encodings, initial/random-offset/phase-boundary behavior and rank/digest contracts.

The current `tests/e001_reference.py` uses the same CPython random.Random
getrandbits/randrange primitives as the implementation. It independently checks
adapter wiring and formulas but cannot detect a common MT19937 implementation,
integer-seeding or word-order defect, nor establish equality for all million
historical uniform draws. It is not an independently implemented MT engine or
an original CPython 3.11.0 runtime reproduction. Float discrepancy resolution is
separate and cannot be used to excuse candidate-byte mismatch.

Before full enumeration, appoint an independent reviewer/author and pin a
standalone reconstruction source revision/environment. It must import no HASHLAB
generator, membership/rank, dedup, aggregation or classification implementation.
Allow separately pinned generic crypto/storage dependencies with known-answer
checks. Independently implement direct deterministic formulas, patterned primitive
enumeration/continuation, BLAKE2b block layout and rank logic.

For MT19937, propose an independent implementation matching the *original pinned
CPython 3.11.0 integer seed initialization and getrandbits semantics*, derived
from an authenticated original CPython source snapshot. Exact seed initialization,
unsigned word handling and 64-bit word assembly must be specified and reviewed,
not guessed from generic MT vectors. Cross-check the sealed seeds and bounded
initial/offset/state-boundary vectors against both historical and qualified current
runtimes. Original-runtime installation is a separate approval dependency; an
independently implemented engine alone cannot retrospectively prove original
runtime behavior without that source/runtime qualification.

After that review, compare complete ordered raw occurrence streams byte-for-byte,
not only aggregate or stream digests. Independent verification can read immutable
producer chunks and generate its own expected bytes, then independently recompute
attempt/dedup/A1/A3/rank/count/digest results. Record first mismatch provenance,
stop and disclose it. Independent author qualification and witness/reporting are
external dependencies, not satisfied by this proposal's author writing tests.

## Checkpoints, interruptions and incomplete disclosure

Every complete enumeration must have separately approved, uniquely identified
attempt records, scope/source/environment pins and start evidence before work.
This is a historical audit ledger, not an E002 confirmatory A-entry or seed choice.
Retain all attempts and failures; no discretionary rerun or replacement inputs.

Propose immutable occurrence chunks of at most 4,096 records, flushed/fsynced
before their checkpoint is published. Checkpoints bind a monotonically increasing
sequence, previous checkpoint digest, immutable completed chunk hashes/sizes,
last complete generator/phase/index, cumulative counts and status. They are
**diagnostic progress artifacts, not resume tokens**. No uncommitted SQLite state
is presumed consistent or represented as durably authenticated by such a record.

Default policy: interruption closes the attempt as incomplete and retains
original evidence untouched, immutable chunks/checkpoints, the partial tail,
locks and scratch database/WAL observations. Failure disclosure records exact
partial sizes/hashes when readable; unsupported entries or unreadable storage
block a claim of complete disclosure. Persist the failure independently where
possible; disclose inability to persist rather than report completion.

No automatic lock stealing, journal repair, resume, discard-and-rerun or retry
loop. Restart from zero or a future precisely reviewed resume procedure requires
separate approval and a new append-only attempt record referencing the failed
attempt. It must use the identical sealed historical inputs and preserve all
prior evidence. The current E002 retry rules are not silently repurposed for this
new audit; Architect must approve an audit-specific retry policy before execution.

## Exact proposed output contracts

This is a schema specification, not new runtime code. All JSON below uses ASCII,
sorted keys, compact separators, no duplicate keys, no floats/NaN/infinity, exact
integer types (bool is not an integer), lowercase hex digests and explicit
schema strings. Reject unknown/missing fields. Counts are nonnegative bounded
integers; paths are flat safe basenames, with exact inventory and no reparse links.
The absence of a field never means zero or verified.

### `scope.json` — hashlab-e001-full-audit-scope-v1

Required fields: schema; proposal_identity; attempt_id (nonempty caller-supplied
audit identifier); authorization_sha256; e001_run_id; e001_manifest_sha256;
e001_config_sha256; historical_source_commit; historical_contract_sha256;
producer_commit; producer_environment_sha256; independent_verifier_commit;
independent_environment_sha256; ordered_generator_ordinals `[0,2,4,6,7,8,9]`;
ordered_phases `["discovery","validation"]`; attempts_per_stream `500000`;
expected_occurrences `7000000`; candidate_width `8`; candidate_hash_evaluations `0`;
checkpoint_limit `4096`; scratch_budget_bytes `2147483648`;
rss_limit_bytes `536870912`; external_anchor_policy_sha256.
All fixed values require exact equality. Source commits are full Git identities;
no fabricated or substitute release identity. Signature trust policy remains a
separate approved artifact referenced by hash.

### Occurrence chunks — hashlab-e001-occurrences-binary-v1

Safe filename `occ-NNNNNNNN.bin`, contiguous chunk numbers beginning 00000001.
Header: ASCII magic `HLE1OCC1` (8 bytes), config ordinal uint8, phase uint8
(0 discovery, 1 validation), first raw index uint32 BE, record count uint32 BE.
Header length 18 bytes; no padding. Body: exactly count repetitions of raw index
uint32 BE followed by eight candidate bytes. Count 1..4096; no chunk crosses a
stream boundary. Indices strictly contiguous from first index and below 500000.
File length exactly 18+12*count. Provenance derives from scope+header+index;
seedless enumeration index adds 500000 for validation, seeded index does not.
No candidate hashes/digests or research success classifications are stored.

### `streams.json` — hashlab-e001-stream-accounting-v1

Required fields: schema; scope_sha256; streams (exact fourteen ordered rows).
Each row fields: ordinal; generator_id; phase; historical_start_index; seed
(sealed uint64 for seeded streams, null for seedless); attempted; accepted_unique;
duplicates_within_phase; duplicates_cross_phase; exhausted (bool); a1_occurrences;
a3_occurrences; first_chunk; last_chunk; comparison_status (pending/match/mismatch).
Require attempted = accepted_unique + both duplicate counts. Completed rows
require attempted=500000, exhausted=false and exact agreement with sealed counts.
Seedless rows require both duplicates zero by construction plus independently
checked uniqueness; never infer it solely from row labels.

### Exclusion artifacts

`a3-values.be64`: strictly increasing unique numeric values, each exactly eight
BE bytes, no header. Its file SHA-256 is the approved exclusion digest.
`a3-ranks.be64`: strictly increasing unique weight/colex ranks, each uint64 BE,
no header. Same count; mapping must independently match the value set.
`a3-provenance.jsonl`: one canonical row per increasing numeric value, with
fields value_hex (16 lowercase hex), rank, occurrence_count, first_ordinal,
first_phase, first_index. First provenance is the earliest original iteration
position, not lexicographic generator ID. Require membership and exact count
agreement with occurrence files. These artifacts are incomplete if interrupted.

### `checkpoints.jsonl` — hashlab-e001-audit-checkpoint-v1 rows

Required fields: schema; sequence; previous_sha256 (64 zeroes only for first);
scope_sha256; chunks (newly completed ordered name/bytes/sha256 rows);
last_position (ordinal/phase/index, or null before first chunk); checked;
status (incomplete only). Each line is canonical JSON plus LF; checkpoint hash
is SHA-256 of canonical row bytes excluding the LF. A completion claim belongs
only to the final independently verified report, never a checkpoint.

### `audit.json` — hashlab-e001-full-audit-report-v1

Required fields: schema; scope_sha256; status (incomplete/rejected/verified);
checked_occurrences; streams_sha256; a1_occurrences; a1_distinct;
a3_occurrences; a3_distinct; a3_values_sha256; a3_ranks_sha256;
a3_provenance_sha256; ordering_verified (bool); dedup_verified (bool);
independent_report_sha256 (64 hex or null if not available);
independent_verification (pending/match/mismatch); source_verification
(pending/match/mismatch); e_audit_passed (bool); failures (ordered structured
rows code/position/details); limitations (explicit string list).
A partial/missing artifact digest is null, never the expected production digest.
`verified` and e_audit_passed=true require all seven million ordered comparisons,
all fourteen accounting rows, zero A1 hits, independently observed 60721 A3 values
and approved digest, provenance/source match and externally authenticated report.
No outcome authenticates candidate research hashes or grants G1/QA2/G2.

### Producer inventory and acyclic authentication order

`producer-inventory.json`: schema `hashlab-e001-producer-inventory-v1`;
scope_sha256; files (exact sorted name/bytes/sha256 rows for scope, pinned
producer/source/environment records, occurrence chunks, streams and exclusion
artifacts only). It excludes audit.json, independent.json, receipts, checkpoint
journal, outer manifest and this inventory itself. Hash its canonical bytes for
`independent.json.producer_inventory_sha256`; there is no self-reference.
Checkpoint evidence is separately bound by the outer manifest and independent
verification of the checkpoint head. Independent report checks every inventory
entry against the scope and immutable occurrence files before reporting a match.

`independent-receipt.json`: schema `hashlab-e001-independent-report-receipt-v1`;
attempt_id; scope_sha256; independent_report_sha256; authority_id; policy_sha256;
verification_method; issued_at_utc; signature_or_receipt. It authenticates the
independent report before final audit.json is issued. Add required field
`independent_report_receipt_sha256` (hex/null) to audit.json. Pending/missing
receipt means e_audit_passed=false; a locally declared match is insufficient.

Order: producer files -> producer inventory -> independent report -> verified
independent receipt -> audit report -> outer manifest/digest -> external outer
receipt/off-machine verification. Thus neither the independent report nor its
receipt depends on the outer manifest that later includes them. Final acceptance
requires the external outer pin even after an independently verified audit report
exists. No schema consumes its own hash or a later receipt's hash.

### Independent report, failures and outer seal

`independent.json`: schema `hashlab-e001-independent-audit-v1`; scope_sha256;
producer_inventory_sha256; verifier_commit; verifier_environment_sha256;
checked_occurrences; raw_bytes_match; counts_match; dedup_match; membership_match;
ranks_match; exclusion_digest_match (all explicit bool); discrepancies (ordered
position/field/producer/independent rows); limitations. It is separately issued
and authenticated by the appointed independent party, not a local passing flag.

`failure.json` when applicable: schema `hashlab-e001-audit-failure-v1`;
attempt_id; scope_sha256; last_checkpoint_sha256 (hex/null); failure_class;
last_position (object/null); checked_occurrences; partial_inventory (exact
name/bytes/sha256 rows where readable); disclosure_complete (bool);
undisclosed_entries (name/reason rows); original_error; retry_authorized=false.
Never include exception-dependent primary research statistics.

`manifest.json`: schema `hashlab-e001-audit-manifest-v1`; scope_sha256;
attempt_id; status (complete/incomplete/rejected); files (exact sorted
name/bytes/sha256 rows, excluding this manifest and its digest sidecar);
checkpoint_head_sha256 (hex/null); source_verification_receipt_sha256 (hex/null).
`manifest.sha256`: exact outer manifest digest as lowercase ASCII hex plus LF.
No self-reference; immutable exclusive writes, fsync and platform-qualified
metadata durability. Incomplete manifests must retain failures/limitations and
may never imply an E-pass. Scratch databases live outside this sealed inventory;
any retained diagnostic snapshots are explicitly listed and marked scratch copies.

External receipt is a separate custody artifact, not embedded in the manifest
it authenticates. Proposed receipt schema `hashlab-e001-audit-anchor-v1` fields:
schema; attempt_id; scope_sha256; manifest_sha256; independent_report_sha256
(hex/null); latest_checkpoint_sha256 (hex/null); authority_id;
policy_sha256; verification_method; issued_at_utc; signature_or_receipt.
An approved external verifier authenticates all fields, authority/trust roots,
latest-attempt history and anti-rollback evidence. Declared verified booleans do
not authenticate themselves. No witness or signature provider is selected here.
A separate copy must be independently verified off-machine before final E-audit
acceptance; copying a local self-hash alone is insufficient.

## Resource estimate, bounded qualification and approvals

Algorithmic work: seven million raw generator outputs and membership checks;
one million MT draws; 125,000 BLAKE2b blocks; patterned motif visits slightly
exceed emitted count due to primitive-word rejection. Database duplicate checks
cover two million seeded occurrences. Independent recomputation approximately
doubles generator/membership work, but uses no research SHA-256. Candidate-file
integrity and exclusion-set hashes remain allowed metadata/evidence operations.

Wall time is unqualified. Reserve a minutes-to-hours engineering window only as
a rough scheduling estimate; do not promise it or extrapolate Phase A parsing
costs. Disk/cache/independent-engine costs require an approved bounded pilot.
Require 2 GiB local plus 2 GiB independent copy and proposed memory budgets above,
subject to measurements and explicitly recorded capacity checks before full scope.

First seek approval to implement only the standalone Phase B backend and
independent verifier with bounded synthetic fixtures. Keep Phase A unchanged.
Initial qualification stays <=4096 occurrences per fixture, including duplicate
and phase-transition fixtures, forced primitive motifs, malformed provenance,
false counts/digests, overflow, disk-full, torn-write, locked-directory and
external-anchor failure injection. Phase transitions can use explicit synthetic
small geometry for backend tests; this is not a complete historical audit.
Real historical large-offset MT/pattern windows require their own replay-budget
approval because seeking can hide a large enumeration. No pilot may quietly
cover the seven-million scope by repeated bounded calls.

Required approvals BEFORE any complete enumeration:

1. Architect approves this scope/schema/dedup/storage/checkpoint/failure design,
   audit-specific restart policy and unchanged scientific protocol.
2. Architect accepts the separately implemented producer and independent verifier,
   pinned source/runtime dependencies and exact bounded reference qualification;
   MT19937 compatibility gaps must be explicitly closed, not waived by common-runtime
   agreement. Original-runtime provisioning, if required, has separate authorization.
3. Director/resource owner approves fixed occurrence scope, no candidate hashing,
   memory/disk/time reservation, abort policy and independent reviewer/custodian.
4. External provenance/anti-rollback/archival verification policy and authorities
   are approved, functioning and independently checked before claims are accepted.
5. A separate written execution authorization names the fixed historical audit and
   reviewed revisions; no full enumeration follows merely from design acceptance.

No Phase B provider/backend/schema implementation, larger fixture cap, full
E001 enumeration, candidate SHA-256, E002 sample, QA2 hashing, new seed/beacon/
commitment, operational dispatcher or release identity was created.
Stop for Architecture Review 038.


## Review 038 handoff status

After the accepted Phase A commit, only these documentation files were created:

- `docs/proposals/e001-reconstruction-phase-b-proposal.md`
- `docs/reviews/architecture-review-037-numerical-reproduction-decision.md`

They remain untracked/uncommitted. Git index empty; no tracked modifications;
preexisting `.venv313/` remains excluded. Branch `feat/experiment-002-e5`, HEAD
`9d31eda5d7f20af00824ccdbe1452f8509567952`. Post-commit E001 hash/size/inventory/
nanosecond-mtime verification remains unchanged. Tests were rerun before the
scoped milestone commit; only documentation followed, so no production tests or
new reconstruction runs were needed afterward. No accepted source or Phase A cap
changed. Stop for Architecture Review 038.

## Review 038 sequencing clarification — proposal v2

Current proposal identity: `hashlab-e001-reconstruction-phase-b-proposal-v2`.
The v1 draft above is retained as design history. This section supersedes its
`audit.json` status/e_audit_passed interpretation and final-acceptance sequencing;
no E001/E002 scientific rule changes. Review 038 authorizes bounded engineering
only, not a complete audit or any passing externally authenticated receipt.

Four distinct states must be represented:

1. **Producer completeness:** locally recomputed occurrence/count/file coverage.
   A completed local producer is not authenticated independent verification.
2. **Authenticated independent verification:** independent report recomputation
   and a separately authenticated report receipt. A local match flag is not a receipt.
3. **External outer anchoring:** completed manifest digest and report bound in a
   receipt authenticated against an approved authority/custody policy.
4. **Final E-audit acceptance:** separate authorized acceptance record, verified
   against the completed manifest AND its authenticated external receipt, after
   all scientific predicates and complete scope have been independently checked.

Replace producer audit.json `status=verified` with `status=producer-complete`.
Keep `e_audit_passed=false` in every producer/independent/checkpoint/incomplete
artifact. Report independent match/authentication as distinct states; never
materialize a producer-side final acceptance boolean from local declarations.
The outer manifest seals producer/independent evidence, not a later decision.

Proposed full historical final record schema `hashlab-e001-final-acceptance-v1`:
required fields schema; scope_sha256; attempt_id; completed_manifest_sha256;
independent_report_sha256; independent_report_receipt_sha256;
external_outer_receipt_sha256; authority_policy_sha256; acceptance_authority_id;
decision (accepted/rejected); issued_at_utc; limitations; signature_or_receipt.
The record itself is stored outside the already completed producer manifest.
Verification authenticates the authorized issuer and exact scope/attempt,
completed manifest inventory, independent report/receipt, external outer receipt,
all seven-million-occurrence predicates and custody/anti-rollback policy.
The string accepted has no effect until that evidence is independently verified.
An opaque local bool or an in-process object is never final acceptance authority.

Acyclic order:
producer evidence -> independent report and authenticated independent receipt ->
producer audit report -> completed outer manifest -> external outer receipt ->
separate externally authenticated final acceptance record. Neither producer
manifest nor external outer receipt includes the digest of that later record.
A separately retained custody inventory may hash the final record afterward;
it must not rewrite the producer seal. Missing evidence means pending/rejected,
never accepted. This sequencing contract remains a full-audit proposal only.

Bounded Review 038 implementation uses separate explicitly synthetic schema
identities (`e001-...-fixture-...-v1`), not the full historical contracts above.
Its final record validator accepts only decision fixture-only with
`e_audit_accepted=false`, and requires a receipt verifier for exact completed
manifest/report binding. It cannot assert historical acceptance even with a toy
passing fixture callback. No real witness/authority or passing receipt was chosen.
The independent verifier is a separate import-isolated package; original-runtime
and separately appointed author/custody qualification remain external dependencies.

Phase A remains accepted and unchanged, including its fixture cap. The new
bounded backend has a separate hard cap of 4096 synthetic occurrences per plan;
all test geometries remain below the per-test authorization. No full provider,
large-offset historical replay, automatic retry/resumption/repair or dispatcher
is implemented. Runtime numerical identity remains separately unresolved.
