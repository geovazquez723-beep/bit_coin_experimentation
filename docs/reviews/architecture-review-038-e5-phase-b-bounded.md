# Architecture Review 038 — E5 Phase B bounded engineering handoff

Prepared for Architecture Review 039. Uncommitted synthetic infrastructure only.

## Baseline, branch and exact scoped inventory

Verified accepted E5 Phase A HEAD
`9d31eda5d7f20af00824ccdbe1452f8509567952`, initial branch
`feat/experiment-002-e5`, empty index and unchanged accepted tracked files.
Created `feat/e001-reconstruction-phase-b` from that commit. Both untracked
Review 038 documents were preserved with historical text retained; continuation
sections clarify sequencing/provenance rather than overwrite historical findings.
Phase A adapter, contract, reference tests and 4096 fixture cap are unchanged.

Exact nine-file Phase B inventory:

1. `docs/proposals/e001-reconstruction-phase-b-proposal.md` — preserved proposal plus v2 sequencing correction.
2. `docs/reviews/architecture-review-037-numerical-reproduction-decision.md` — preserved memo plus read-only provenance/exact-comparison specification.
3. `src/hashlab/experiments/e001_phase_b.py` — bounded producer, dedup/accounting/chunks/checkpoints/disclosure contracts.
4. `src/hashlab/experiments/e001_phase_b_verification.py` — read-only verifier bridge and fixture final-record validation.
5. `src/e001_verify/__init__.py` — isolated verifier exports.
6. `src/e001_verify/core.py` — independent MT/streams/dedup/membership/ranks/digest calculations.
7. `tests/fixtures/e001-mt19937-synthetic-v1.json` — pinned synthetic current-runtime reference vectors.
8. `tests/test_e001_phase_b.py` — synthetic qualification and fault injection.
9. `docs/reviews/architecture-review-038-e5-phase-b-bounded.md` — this handoff.

All nine remain untracked/uncommitted. Preexisting `.venv313/` remains excluded.
No accepted E1–E5 Phase A source/test/protocol or sealed evidence was changed.

## Public APIs, identities and boundaries

`e001_phase_b.FixturePlan`: exact ordered historical eight-byte generator kind/
ordinal metadata, visibly synthetic keys (default 1/2), reduced D/V counts;
rejects wrong source/manifest/config/contract/schema and geometry above 4096
TOTAL occurrences across all generators/phases. Identity
`e001-reconstruction-fixture-plan-v1`. Fixed historical pins match Phase A;
metadata equality is not external authentication of a production run.

`fixture_rows(plan)`: deterministic (ordinal, phase, raw index, eight-byte value)
stream, using accepted historical generator definitions with synthetic geometry.
Seeded streams restart at phase boundaries; seedless streams continue at the
reduced discovery offset. Patterned validation replay is bounded by the reduced
plan, not the historical 500000 offset. No real historical large-offset replay.

`ExactDedup`: exclusively creates a new SQLite store, BLOB primary key
(generator ordinal,candidate bytes), exact eight-byte key checks, first phase/
index retained. Different generators do not deduplicate each other. Discovery
values persist into validation; a prior-discovery value is cross-phase even if
repeated again in validation. No replacement/top-up draw is generated. Uses FULL
synchronous commits, DELETE journaling, configured cache/page/record limits;
transaction/resource failure poisons the object and rolls back the transaction.
No reopen/resume/repair/retry API exists. Existing committed evidence is retained.
This is fixture storage, not a qualified production durable registry/backend.

`account_rows(plan,rows,store)`: strict geometry/order/type accounting with
unique/within/cross counts, raw A1 hit and distinct-hit counts, A3 occurrence and
distinct-value counts, increasing ranks, exact numeric-order BE exclusion digest,
and global first A3 provenance/counts. Same values remain separate occurrences.
Wrong geometry/provenance poisons accounting's store. Identity
`e001-producer-fixture-accounting-v1`; producer_complete=True means local structural
coverage only; final_acceptance is always false. No 60721 production count is
assumed, inserted or claimed. Exclusion SHA-256 follows the approved set-encoding
contract; no candidate research SHA-256 is evaluated.

`encode_chunk` / `decode_chunk`: canonical `HLE1OCC1` binary format, 18-byte header
(magic, ordinal, phase, first uint32 index, uint32 count), then uint32 BE index +
exact eight-byte value per record. At most 4096 records; strict contiguous indices,
length, supported ordinal, phase and width checks. No cross-stream chunks.

`ChunkWriter`: one-use new empty directory, bounded buffer (default 64 records),
fixed total byte reservation, exclusive output writes and fsync. Strict plan
position coverage before producer-complete manifest. Failures retain writer.lock
and partial/torn chunks and poison the writer. No overwrite or auto retry.
`read_chunks`: read-only externally PINNED manifest hash, plan/schema/exact file
inventory, per-file size/hash checks, contiguous chunk names, exact occurrence
geometry/order. Manifest capped at 1 MiB and chunks at 4096 records. The caller
must exhaust the iterator to establish full coverage; independent verification
does so. Identity `e001-fixture-outer-manifest-v1`; this is a separate bounded
schema, not E001's original manifest or the proposed full audit output contract.

`Checkpoints`: immutable exclusive canonical files, hash chain plus caller-supplied
expected head, monotonically nondecreasing checked count bounded by fixture
geometry. Identity `e001-fixture-checkpoint-v1`; every status is incomplete. Locks,
torn writes, gaps and wrong/replaced heads block further appends. Checkpoints are
diagnostic, not resumable state; they do not authenticate external custody or
claim that SQLite scratch matches a complete output. No automatic recovery.

`incomplete_attempt`: strict canonical `e001-fixture-incomplete-v1` disclosure
bytes, exact partial file inventory fields, source plan binding, checked count,
original error and incomplete status. Retry authorization and final acceptance
are false. This pure contract does not automatically catch/write every caller
failure; future integration must durably persist it with exclusive creation and
report failure to disclose. No operational exception handler/dispatcher is added.

`e001_verify.MT19937`, `classify`, `verify_rows`: independent reduced-fixture
reproduction. Identity `e001-independent-fixture-report-v1`; checks exact bytes,
ordering/geometry, independently deduplicates, computes A1/A3 counts, eligible
ranks, numeric-order set digest and first A3 provenance. No HASHLAB imports.

Bridge public APIs:

- `independent_report`: fully consumes validated chunks and independently
  regenerates expected synthetic bytes/counts. Identity
  `e001-bound-independent-fixture-report-v1`, binding manifest/plan/source/config.
- `validate_report`: exact canonical report equality to independent recomputation;
  missing, wrong or forged fields fail. Local correctness is not authentication.
- `validate_producer_accounting`: exact independent comparison of every serialized
  producer count, membership/rank/digest and A3 first-provenance field; malformed,
  changed or incomplete accounting cannot pass as matching.
- `acceptance_subject`: domain/schema-bound plan+completed-manifest+report digest.
- `validate_final_record`: requires matching independently recomputed report and
  externally verified receipt binding that exact subject/manifest. Identity
  `e001-final-fixture-record-v1`; only decision fixture-only and
  e_audit_accepted=False are legal. Forging a local final acceptance bool fails,
  even with a synthetic test verifier returning True. No historical final E pass
  can be issued by these modules. External verifier callbacks remain a trust
  boundary, not supplied signature/custody infrastructure.

## Final acceptance sequencing correction

Proposal v2 explicitly separates producer completeness, authenticated independent
verification, external outer anchoring and final E-audit acceptance. Full historical
producer/independent/checkpoint artifacts must keep e_audit_passed=false.
The separately proposed externally authenticated final record references the
completed outer manifest, independent report/receipt and external outer receipt.
It is issued AFTER those artifacts and stored outside the sealed producer
manifest. Nothing earlier hashes that later decision record, preventing cycles.
Its issuer/signature/trust policy and exact evidence must be verified before an
accepted string has authority. The full historical record is a proposal only;
this bounded implementation only validates fixture-only records with acceptance
false. No real witness, authority, seed, round, release or passing receipt was
selected or produced. Toy receipts are visibly SYNTHETIC-UNAUTHENTICATED.

## Independent reference evidence and compatibility limitations

The independent package imports only hashlib, itertools and math (plus its own
core from __init__). AST import-isolation test rejects HASHLAB and random imports.
The bridge imports the package; the package does not import the bridge or producer.
Its formulas, direct periodicity test, per-generator dictionaries and binomial
rank counting differ from producer KMP/generator/SQLite/E1 rank implementations.
Generic BLAKE2b and SHA-256 dependencies are shared; cryptographic implementation
independence is not claimed. No statistical/decision function is imported.

MT specification: 624 unsigned 32-bit words, integer seed as low-to-high 32-bit
limbs, array initialization with constants 19650218/1664525/1566083941, standard
397-offset twist and temper masks. getrandbits uses high bits for a short word,
low-to-high word assembly for multiword draws, no state consumption for zero bits.
Supports only explicitly bounded nonnegative uint64 fixture seeds and widths
0..128; it does not use CPython random.Random internally.

Pinned vectors: `tests/fixtures/e001-mt19937-synthetic-v1.json`, schema
`e001-mt19937-synthetic-v1`, SHA-256
`3a3c8b91fe74542a10e2de8ef12886e10441ebbc02a6b2de1c8cd8c2fba304be`.
Five synthetic integer seeds (0,1,2,2^32,2^64-1), widths
1/31/32/33/64/65/128, three repeated width cycles. The expected values were pinned
from the qualified CPython 3.13.0 reference, not generated by the MT under test.
Additional bounded comparisons cross several state boundaries and cover zero-bit
behavior. Each individual test stays within the 4096-occurrence fixture budget;
no repeated tests concatenate into a seven-million audit.

The original CPython v3.11.0 source was inspected read-only for seed/word semantics,
with official links in the provenance memo. Bounded current-runtime agreement
plus source inspection does NOT qualify the original runtime, historical million-
draw streams or independently appointed author/custody. No original executable
was run. Full historical compatibility remains explicitly unqualified.

## Failure/resource qualification and results

Synthetic coverage includes exact BE bytes/headers, phase transitions, within/
cross-phase duplicates, same value in different generators, first provenance,
patterned primitive boundaries, missing/duplicate/corrupt chunks, rewritten
checkpoint heads/gaps, torn writes, retained locks/tails, disk-full injection,
actual SQLite page-reservation exhaustion, rollback/poisoned transaction behavior,
incorrect bindings/counts/digests, forged/missing reports, missing/forged receipt,
invalid local final acceptance, configured output/record/cache/page limits and
independent import isolation. No original data copies are mutated outside ignored
temporary fixture directories; no actual device was filled.

Measured Python traced memory:

- Chunk writer, 32 versus 1984 generated synthetic occurrences: final focused
  peaks 13,856 and 28,833 bytes. Including readback, this individual test processes
  4032 occurrences; it never approximates full scope. Buffer limited to 64 rows.
- SQLite/accounting, 1024 synthetic occurrences: traced Python peak 28,184 bytes;
  configured SQLite cache 64 KiB. Native SQLite/OS/RSS is not captured by tracemalloc.
- Actual SQLite page-limit test aborts at its configured 65536-byte main-file
  reservation, retains the database and rejects subsequent operations. Journal/
  filesystem metadata/native allocation peaks still need platform qualification;
  main database page limits are not a complete device/RSS quota guarantee.

Initial qualification exposed a test expectation error: 2000 rows fit inside the
64 KiB SQLite cap. The test now attempts at most 4096 synthetic rows and exercises
the real SQLITE_FULL/page-cap failure. Earlier failed results were not hidden;
no scientific input, historical result or retry policy was changed.

Final focused/full counts appear below. Qualified environment remains Python
3.13.0 in `.venv-py313-review024`, SQLite 3.45.3; bytecode and pytest cache disabled.
Ignored test scratch directories retain fault-injection evidence. No production
benchmark, whole-RSS qualification or operational filesystem durability claim.

## Numerical provenance and external dependencies

The preserved numerical memo now records static local dependency metadata hashes,
current original-runtime path observation and failed binary-provenance inspection,
public official artifact listings and an exact future comparison specification.
No original runtime was downloaded/installed/executed/replaced. The 86 accepted
numerical discrepancies are unchanged; no historical analysis regeneration or
tolerance-based identity pass occurred. Numeric token, binary64 bit, type, array
order, timestamp and complete-file identity checks remain separate and exact.

Remaining dependencies before complete enumeration or acceptance:

- Appointed independent author/reviewer and approved original-runtime/source/
  binary/dependency qualification; bounded algorithm agreement is insufficient.
- Real external report/outer receipt/final-authority verifiers, trust roots,
  anti-rollback/latest-head storage and off-machine archival/custody.
- Platform ACL/no-follow/concurrent-mutation policy, directory metadata durability,
  power-loss/SQLite native/RSS/disk-journal qualification and resource reservation.
- Reviewed full historical geometry/provider, exact historical dedup/patterned
  continuation and complete evidence contract/integration. Bounded synthetic
  accounting cannot establish absence of omitted historical records.
- Separate approval for full enumeration, any restart procedure, runtime execution
  and exact numerical reproduction. No auto retry/resumption/repair exists.

This foundation grants no full E audit, G1 acceptance, QA2 or G2 authorization.
Stop for Architecture Review 039.

## Final qualification and repository state

- Focused Phase B suite: **57 passed in 7.92s**.
- Complete regression: **889 passed, 2 skipped in 27.41s** under qualified
  Python 3.13.0. Both skips are the preserved E4 symlink tests: Windows
  `WinError 1314` (client lacks symbolic-link privilege); coverage remains present.
- Final read-only preservation check: all 11 Experiment 001 files match the
  pre-existing snapshot exactly in SHA-256, size, inventory and `mtime_ns`.
  Sealed manifest verification returns no errors; historical contract/source pins
  validate. Accepted E1–E5 Phase A tracked files have no diff.
- Branch: `feat/e001-reconstruction-phase-b`.
- HEAD: `9d31eda5d7f20af00824ccdbe1452f8509567952` (accepted E5 Phase A).
- Staging index: empty. The nine files listed above are untracked Phase B work;
  the pre-existing unrelated `.venv313/` remains untracked and untouched.
- No commit, push, merge, tag, release identity, historical enumeration,
  candidate SHA-256 evaluation, QA2 or operational execution was performed.

Ready for Architecture Review 039; external dependencies listed above remain open.
