# Architecture Review 029 — E2 preserved; E3 foundation handoff

Date: 2026-10-12 (America/Los_Angeles). Stop for Architecture Review 030.

## Accepted E2 milestone

Verified `feat/experiment-002-e2` at accepted E1 commit
`dbcbd223953b2e3e39149567026b2513bd7e24af`. Read the complete Review 028
handoff and verified its exact five-file inventory. The only unrelated
untracked directory was pre-existing `.venv313/`.

Using qualified `.venv-py313-review024/Scripts/python.exe`, the full precommit
regression suite passed: **543 passed in 13.47s**, no failures/skips.
Staged exactly:

- `docs/reviews/architecture-review-028-e2-statistics.md`
- `src/hashlab/statistics/exp002.py`
- `tests/exp002_reference.py`
- `tests/fixtures/exp002-e2-synthetic.json`
- `tests/test_exp002_e2.py`

The staged inventory was five files, 24,925 insertions. Committed as
**`b8b74f83819be74e0c0c2f66916740331b850692`**,
`Accept Experiment 002 E2 statistical milestone`. Immediately afterward only
`.venv313/` remained untracked. Created `feat/experiment-002-e3` directly from
that commit. No push, merge or tag was performed.

## Exact E3 changed-file inventory

All four are new and uncommitted:

- `src/hashlab/experiments/exp002_foundation.py`
- `tests/test_exp002_e3.py`
- `docs/proposals/experiment-002-secondary-statistics-proposal.md`
- `docs/reviews/architecture-review-029-e3-foundation.md` (this handoff)

No accepted E1/E2 source, statistical engine, protocol, dependency declaration,
sealed evidence or existing test file was modified.

## Versioned foundation contracts

`Plan(code_commit, config=Config())` is immutable and seedless. The accepted
Config rejects changed frozen fields, execution masters, sample sizes,
target, alpha, encoding identities and thresholds. Plan metadata additionally
binds primary populations, A2 nonce/stage geometry, 13 primary/control streams,
positive-control lifts, accepted E001 identity and exclusion counts/digest.
It marks scientific/operational prerequisites unestablished and secondary
statistics unbound. The code identity is caller-supplied; tests use a visibly
synthetic 40-character identity, not a selected release or execution plan.

Fingerprint contract is SHA-256 of ASCII domain
`hashlab-exp002-seedless-plan-v1`, a NUL byte, and canonical plan JSON bytes.
Canonical JSON uses sorted string keys, compact separators, ASCII escaping,
exact integer decimal text and no floats, NaN, coercions or duplicate keys.
There is no trailing newline. Plan read-validation compares all fields to the
versioned reconstructed contract and rejects missing, extra or changed fields.
Integer consumers must support arbitrary precision for the target. This is
an E3 foundation schema for review, not a completed operational precommitment.

`CandidateRecord` binds schema, arm, stage, stage-local sequential index,
canonical candidate hex and cluster identity where required. Primary/null
stages are D/V; positive controls use a single accounting stage C (a record
notation, not a new statistical stage). Trial limits are frozen 15M except
P1's 200k. Input sizes remain 8 bytes or 80 bytes. A1 bounds and A3 structural
membership are checked. A2 validates nonce LE32 against local stream position,
and A2/N2 cluster id must equal index//10000 plus the V offset of 1500.
This does not itself prove exclusion membership or prefix provenance.

`SuccessRecord` includes the candidate record and caller-supplied 32-byte
digest, requiring the strict digest <2^248 target. Pure canonical serializers
and readers do no candidate hashing and reject unknown schema fields. A
success file is canonical record bytes followed by LF per record. The
read-only file validator rejects truncated/oversized lines (4,096-byte cap).

`Accumulator` consumes supplied candidate records and digests. Per-stream
indices must start at zero and increase consecutively, detecting duplicate,
missing and reordered accounting records without retaining the candidate set.
Streams may interleave. It retains trial/success counts, 256-bin first/last-byte
histograms, 257-bin leading-zero histograms, and 1,500 trial/success counters
per clustered stage. These are raw counts only: no secondary p-values or
confirmatory labels are computed. Snapshots are detached JSON data.

`SuccessIndexCollector` uses a caller-owned sink and configurable capacity
1–65,536, default 4,096. It flushes tuples of arm/stage/index, retaining at most
capacity records. `Accumulator` can also emit success JSON to a supplied sink.
The collector owns no files. Caller sinks must preserve bounded memory rather
than collect all chunks; fixed counter storage and a 10,001-record synthetic
test with capacity seven verify the foundation's bound. No production sample
or candidate set is retained or generated.

Invalid input or audit/sink failure poisons an accumulator permanently and
propagates the original exception. It cannot subsequently publish a snapshot,
add a record or finish. Collector sink failures similarly prohibit retries.
Partial external sink writes are not rolled back; future operational handling
must disclose and persist failures. `finish()` requires every frozen stream
to be complete and closes/flushed indices; partial snapshots are explicitly
incomplete and cannot be mistaken for complete accounting.

`ControlProvider`, `OverlapAudit` and `E001Reconstruction` define supplied
record/digest, per-record audit and reconstruction interfaces, without any
provider implementation or execution dispatch. `E001ExclusionRequest` pins
the accepted E001 run/manifest, 7M eight-byte and 3M sixteen-byte records,
zero A1 intersection, 60,721 A3 exclusions and approved exclusion digest.
`AuditResult` distinguishes M/E/D/P/C, validates measured count consistency,
and forbids measured counts for unchecked probabilistic bounds/computational
assumptions. References remain mandatory; bounds are never converted to an
assertion of verified zero overlap.

`ExecutionManifest` is versioned **E002 execution metadata**, a prospective
payload under the unchanged `hashlab-manifest-v1` outer sealing convention.
It binds plan fingerprint, code identity, accepted protocol identity,
partial/complete/aborted accounting status and a sorted unique payload list.
Every `EvidenceFile` has a safe canonical basename, exact byte size and SHA-256.
The schema rejects traversal, Windows device names, aliases caused by case or
trailing dots, duplicate entries and self-referential outer manifest files.
It does not create attempts, select timestamps, choose seeds or seal evidence.

`validate_accounting` checks all 13 streams and their canonical ordering,
histogram sums, target-success equivalence, first-byte/leading-zero consistency,
cluster order/totals and true completion. `validate_success_records` checks
ordered unique per-stream success indices, bounds against accounted records,
success totals and cluster totals in bounded memory.

`validate_evidence` reads a flat foundation payload collection, checks its
externally supplied metadata digest pin and plan/code binding, rejects links,
missing/unlisted files, verifies sizes and SHA-256 with a 64KiB buffer, caps
accounting JSON at 2MB and applies accounting/success structural checks. A
complete collection requires the success file even when empty. Tampering with
both a payload and local metadata fails against the unchanged supplied pin.
The utility performs no writes. It is not a runner or an independent full
scientific evidence verifier.

## Secondary clarification proposal

The separate proposal defines candidate leading-zero, first-byte, last-byte,
cluster-dispersion and A3 weight-success heterogeneity procedures. Each states
its null/statistic, inputs/aggregation, df/reference law, edge cases, deterministic
reference vectors and relation to approved QA2 dispersion requirements.

Proposed family: 36 tests across A1/A2/A3/N1/N2, separate D/V, with a separate
.01 exploratory Holm convention. This alpha, family, fitted-p dispersion and
A3 statistic are **approval requests only**. No proposal procedure is
implemented or bound into a plan, no primary budget is changed, and the new
diagnostic counters do not evaluate exploratory tests. Symbolic reference
vectors are specified; independently verified numerical p/log-p values must
be pinned after approval before implementation qualification.

## Tests and scope proof

Commands use `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, and the qualified
Python 3.13 environment. Full-suite temporary artifacts stay in the ignored
qualified environment; no artifacts enter E001 evidence.

- Focused E3: **75 passed in 0.45s**.
- Full regression: **618 passed in 13.56s**, no failures/skips.
- `git diff --check`: clean; no staged changes.

Tests cover canonical known bytes and independent fingerprint encoding,
roundtrips, altered identities/geometry/alpha/seeds, malformed records,
strict target equality and adjacent digest values, stream gaps/repeats,
cluster stage/boundary accounting, fixed counter and chunk capacities,
audit/sink exceptions and permanent failure, snapshot alias isolation,
incomplete finalization, histogram/cluster inconsistencies, read-only
verification, missing/unlisted/tampered evidence, local metadata rewrites,
unsafe paths and missing/duplicate/reordered success records.

A complete accounting/manifest test constructs algebraic synthetic summaries
without iterating the production trial count. Repeated literal candidate bytes
and supplied zero/FF/boundary digests in tests are explicitly artificial,
not actual hash observations or unique candidate samples. An AST check excludes
generator, seed, engine and statistical calls from the foundation. SHA-256 is
used solely for metadata fingerprints and file integrity, never to evaluate a
candidate. E2 remains unchanged and count-only. No new CLI, runner, seed,
beacon, precommitment, confirmatory subset, full-scale sample or benchmark exists.

## Experiment 001 preservation

Before E3 and after full regression, read-only `verify_manifest` passed for
`results/20261011T205056Z-exp001-fc1d75fc`. All nine payload hashes and byte
sizes, manifest self-hash and exact 11-file inventory passed. Every content
hash, byte size and nanosecond mtime equals the pre-E3 snapshot retained in
the ignored qualified environment.

Manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
The existing `v0.2.0` tag dereferences to
`ef595f5c2f2166923fd277def39708409f564419`. No evidence file was rewritten.
This checks local integrity and preservation, not independent archival or
historical authenticity. No E001 candidate reconstruction was run.

## Remaining decisions and limits

- Architect acceptance/version freeze of these E3 record/plan/metadata contracts.
- Approval or revision of secondary proposal choices and future A3 weight counters.
- Full executable plan, actual control providers, complete overlap/exclusion
  reconstruction, and attachment/verification of required audit proof records.
  Optional audit callbacks in this foundation cannot establish run eligibility.
- Operational registry, failure persistence, commitment/beacon/witness machinery,
  complete provenance inventory, outer evidence sealing and run orchestration
  remain unimplemented here. There is no execution authorization path.
- The flat payload validator does not yet validate an entire outer sealed run
  directory, independent candidate reconstruction, digest authenticity or absence
  of omitted successes relative to unobserved hashes. Structural success counts
  can only be checked against supplied accounting. “Complete” is accounting
  completeness, not scientific validity. Concurrent file mutation is not a
  supported validation mode; no snapshot-isolation guarantee is claimed.
- External pin retention/authenticity, durable sink behavior and transactional
  failure handling remain caller/integration responsibilities. Interface types
  do not certify external implementations. No performance qualification was run.
- G1/QA2/G2, independent evidence verification, small hashing integration and E4
  remain outstanding and unauthorized in this foundation pass.

Final branch `feat/experiment-002-e3`, HEAD
`b8b74f83819be74e0c0c2f66916740331b850692`. Four E3 files above are untracked;
pre-existing `.venv313/` is excluded. No tracked modifications, staged files,
E3 commit, push, merge or tag. Stop for Architecture Review 030.

## Review 030 continuation — documentation correction only

On 2026-10-12, Review 030 identified that the proposed six individual A3
weight strata cannot meet expected-success qualification under expected
Experiment 002 conditions; eligible weight 1 has only 12 population members.
The proposal is now `hashlab-exp002-secondary-statistics-proposal-v2`, replacing
that test with fixed groups weights 1–4 (631,413 eligible), weight 5 (7,407,537)
and weight 6 (74,029,313), a 2×3 Pearson table and 2 df. It specifies exact
raw-weight aggregation, grouped expected-cell qualification, not-testable
behavior, no adaptive group changes, and independently checked rational and
numerical reference vectors. The 36-member exploratory Holm family is unchanged.

Only the secondary proposal and this appended note changed in this continuation.
The historical findings and test results above are preserved. Production code,
tests, E2 decisions and plan bindings are unchanged; no secondary procedure was
implemented. Reference calculations used synthetic counts, Fraction and Decimal
without HASHLAB imports; no regression rerun was needed for this documentation
correction. Remain on `feat/experiment-002-e3`, with no commit, push, merge or
tag. The revised proposal remains unapproved and unbound. Stop for Architect approval.

## Review 032 continuation — accepted foundation and secondary completion

Review 032 accepts the foundation after direct Architect source/test review and
reaffirms Review 031 authorization of secondary specification
`hashlab-exp002-secondary-statistics-proposal-v2`. The implementation now adds
all 36 exploratory slots, independently pinned numerical references and A3
raw-weight counters. The explicitly authorized seedless-plan/accounting schemas
are v2 and bind the approved secondary identity; incompatible v1 structures are
rejected. Candidate/success records, execution metadata, E2 decisions and
operational-gate logic are unchanged. Earlier findings/statuses above remain
historical. See `architecture-review-032-e3-secondary.md` for the complete
Review 033 source inventory, numerical qualification, tests and limitations.
E3 remains uncommitted on `feat/experiment-002-e3`; no execution is authorized.
