# Architecture Review 033 — E3 closeout and E4 governance foundation

Prepared for Architecture Review 034. E4 is uncommitted and does not enable execution.

## Accepted E3 closeout

Verified branch `feat/experiment-002-e3`, parent HEAD
`b8b74f83819be74e0c0c2f66916740331b850692`, empty index and the exact ten-file
inventory in Review 032. Staged only that inventory and committed it as
`df3b96b4ce81979c1d0ea21cab3725af362e6479`.
Created `feat/experiment-002-e4` at that commit. No push, merge or tag.
The relevant tree was clean after the commit; preexisting `.venv313/` remained excluded.

The independent secondary builder reproduced the complete pinned JSON bytes
(Windows newline convention included): 1,152,727 bytes, 27 component vectors
and two complete 36-slot families. Focused E3: 166 passed in 1.99s.
Full E3 regression: 709 passed in 15.40s.
E1/E2 implementation and primary statistical decisions were unchanged.

## Exact E4 source inventory

- `src/hashlab/experiments/exp002_governance.py`
- `src/hashlab/experiments/exp002_journal.py`
- `src/hashlab/experiments/exp002_provenance.py`
- `tests/test_exp002_e4.py`
- `docs/reviews/architecture-review-033-e4-foundation.md`

All five are new, untracked files pending Architect acceptance. No accepted
E1–E3 source, tests, scientific protocol or sealed evidence was modified.

## Contracts and failure behavior

`FullPlanBinding` v1 binds the accepted seedless plan fingerprint, exact
protocol and secondary identities, supplied seed-record digest and resolved
configuration digest. It is explicitly a reference envelope, not an executable
resolved plan. `CommitmentContract.verify` checks seedless/configuration/seed
references and external commitment, timing, beacon and seed-record evidence.
No seed, beacon round or witness is selected or accepted as a raw secret.

A `Claim` is a declaration. `verify_claim` requires a nonempty receipt and an
external verifier returning exactly True. Exceptions propagate. `VerifiedEvidence`
is an in-process trust-boundary object, not a signature system or sandbox against
malicious Python callers. The verifier must authenticate exact claim kind,
subject, evidence digest and passing outcome. Timing and beacon correctness
remain obligations of the external verifier implementation.

`check_eligibility` requires all thirteen separately verified conditions bound
to the full-plan fingerprint: E001 reconstruction, overlap audits, G1, QA2
statistics, QA2 hashing, G2, precommitment, witness timing, beacon verification,
seed record, registry history, release approval and director authorization.
Missing, duplicated, unverified or mismatched proofs fail closed. Even a complete
synthetic proof set returns `execution_enabled=False`. This foundation supplies
no runnable dispatch path and performs no QA2 hashing qualification.

`AttemptJournal` v1 stores canonical, sequential event files chained by SHA-256.
Attempt numbers are gap-free and a result can follow only its unresolved start.
Starts disclose UTC, command, code/configuration/full-plan/seed-record identities.
Results disclose run identity/status, validity/failure class, manifest reference,
mandatory disclosure digest and numerical-abort flag. Entries are created with
exclusive creation, flushed and fsynced. There is no overwrite or delete API.

Every append requires an externally verified prior history pin, including the
zero genesis pin. This detects rewritten or truncated histories when the
verifier retains the true latest anchor. A structural read without an anchor
is explicitly not authentication. Pending starts cannot be retried. Valid final
results cannot be retried; seed replacement is forbidden. F4 cannot retry the
same code. F3, changed-code/configuration/plan retries and escalation beyond
three attempts require independently verified retry-review evidence. The review
verifier must check approved amendment, root cause, requalification, disclosure,
unchanged seed and post-amendment labeling as applicable; a local declaration
is insufficient.

Exclusive writer locks are never stolen. Any failure after lock acquisition
leaves the lock and existing bytes intact and blocks subsequent writes.
`inspect_partial` is read-only. `disclose_failure` exclusively creates and fsyncs
a sidecar retaining every regular partial artifact's size and digest, including
torn entries and the lock. Calling code must invoke this disclosure interface
when an append fails; there is deliberately no operational exception handler or
runner. Disclosure storage failures propagate; no software can guarantee a
successful write to failed storage. Recovery has no write/repair API.

The E4 outer seal uses its own `hashlab-exp002-outer-manifest-v1` contract,
leaving E001's `hashlab-manifest-v1` untouched. Sealing requires a verified
completeness claim bound to the entire proposed outer manifest digest. It binds
plan identities, attempt/source/accounting provenance and exact flat payload
inventory. Both seal files use exclusive durable creation; a partial seal is
preserved and cannot be silently resealed. `verify_seal` independently recomputes
file hashes/sizes/inventory and verifies the external manifest pin read-only.
Completeness verification is an external interface, not a claim that these
metadata checks prove scientific execution completeness.

## Qualification and preservation

Qualified environment: `.venv-py313-review024/Scripts/python.exe` (Python 3.13),
bytecode disabled and pytest cache provider disabled.
Final focused E3/E4: 192 passed in 2.18s (166 accepted E3 + 26 E4).
Final full regression: 735 passed in 15.33s; no failures or skips.

Synthetic tests cover missing witnesses and qualification, incorrect plan
hashes, unverified audits/declarations, duplicate/missing proofs, gaps and
duplicate attempts, rewritten starts and tail anchors, interruptions, actual
partial-write injection, durable numerical-abort disclosure, partial seals,
incomplete evidence, altered payloads, prohibited retry paths and the retry
ceiling. Import-surface checks constrain governance to metadata/persistence
modules. SHA-256 is used only for metadata, receipts and supplied evidence;
there is no candidate generator/hash engine import, seed derivation or runner.

Experiment 001 directory `results/20261011T205056Z-exp001-fc1d75fc` verified with
the existing manifest verifier. All eleven file hashes, sizes, exact inventory
and nanosecond modification times match the pre-work snapshot and the earlier
Review 032 snapshot. Manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
Accepted tracked E1–E3 source and statistical tests have no diff against HEAD.

## External dependencies and limits

This is an offline, single-owner filesystem foundation. Parent directories must
be trusted and not concurrently mutated by another process; file locks serialize
cooperating journal writers. Platform fsync does not qualify Windows directory
metadata or physical hardware power-loss behavior. No stale-lock recovery,
filesystem ACL enforcement or crash repair is implemented. These require review
and platform qualification before operational use.

External receipt authentication, latest-anchor persistence, external witness
identity/timing, resolved-plan/seed derivation validation, release and approval
records, E001 reconstruction, overlap audits, full QA2 qualification and retry
amendment review remain unresolved operational dependencies. No real values
were selected. The persistent journal is not yet integrated with the protocol's
Git-committed formal S/Q/A registry; this implementation covers A attempt events
only. No registry publication or discretionary retry is enabled.

No scientific decisions, sample sizes, populations, alpha budgets or statistical
rules changed. No confirmatory subset, candidate hashing, QA2 hashing exercise,
production benchmark, execution seed, beacon selection, witness selection,
release identity selection, publication or E4 commit occurred.

Stop for Architecture Review 034.


## Architecture Review 034 continuation — hardening for Review 035

The preceding Review 033 findings are retained as historical results. This
continuation supersedes its E4 test counts and partial-disclosure behavior.
Branch remains `feat/experiment-002-e4`, HEAD remains accepted E3
`df3b96b4ce81979c1d0ea21cab3725af362e6479`. E4 is not committed.

Exact files edited for Review 034:

- `src/hashlab/experiments/exp002_provenance.py`
- `src/hashlab/experiments/exp002_journal.py`
- `tests/test_exp002_e4.py`
- `docs/reviews/architecture-review-033-e4-foundation.md`

The complete pending E4 inventory remains these four files plus unchanged
`src/hashlab/experiments/exp002_governance.py`. All five remain untracked;
preexisting `.venv313/` remains excluded. No other files were edited outside
ignored qualification test scratch directories. Git index is empty.

### Corrected behaviors

Evidence inventory now hashes and counts bytes using fixed 65,536-byte reads.
The shared `file_inventory` helper retains exactly `{size, sha256}` per filename;
canonical inventory, outer manifest encoding and digest construction are
unchanged. No payload-sized bytes object is created. Memory for each file's
hashing is bounded independently of payload size; the returned inventory still
necessarily grows with the number of files. Verification remains read-only.

`require_plain` uses non-following filesystem metadata and rejects symbolic
links, all Windows reparse points (including junctions), directories where a
file is expected, and unsupported filesystem entries. Evidence roots must be
plain directories. Sealed manifest filenames are checked before exclusion
from payload inventory, so a linked manifest cannot bypass the file-type check.
The existing trusted-directory/no-concurrent-mutation prerequisite still applies;
this is not an OS-level defense against a hostile parent-directory swap race.

`inspect_partial` no longer silently filters filesystem entries. It uses the
same bounded hashing and rejects an unsupported entry, preventing creation of
a purportedly complete disclosure sidecar. Unknown regular files are included
with their exact size/digest. Existing locks, torn entries and unexpected
entries remain untouched. There is no repair, lock stealing or retry loop.

Explicit retry tests supply a review-required F3 retry with a nonempty review
reference but no acceptable proof: missing receipt, bare declared Claim and
externally verified receipt for the wrong subject each fail closed before
creating a new event. Existing history bytes remain unchanged; the failed
writer lock remains. Seed-replacement prohibition is unchanged.

### Qualification

Qualified Python 3.13 environment and no-bytecode/no-pytest-cache settings as
above. All original 26 E4 tests remain; 20 new cases were added.

- Focused E4: **44 passed, 2 skipped in 0.50s**.
- Complete regression: **753 passed, 2 skipped in 15.66s**.
- Both skips are actual file/directory symbolic-link fixtures: Windows returned
  WinError 1314 (creation privilege unavailable). The real Windows junction test
  passed, including rejection of a junction used as the evidence root.
- Deterministic metadata fixtures separately exercise symbolic-link mode,
  special-file mode and Windows file reparse attributes; all passed.
- Actual bounded files cover empty, one-byte, 64 KiB boundaries and over 2 MiB.
  Whole-file Path.read_bytes is disabled for those inventory calls, and output
  matches independent direct SHA-256 reference values.
- Logical streams of 1 MiB and 128 MiB enforce every read request at exactly
  64 KiB and compare digests against independent incremental references.
  Traced peak Python allocations remain below 512 KiB in both cases, with
  growth below 128 KiB despite a 128-fold increase in logical payload size.
  These are synthetic streams, not research sampling or production benchmarks.
- Outer-seal bytes/digest match the independent prior whole-file reference
  calculation on bounded data. Verification preserves all file bytes and
  nanosecond modification times. Existing event-chain/rewrite/interruption
  tests continue to pass unchanged.

Post-regression E001 verification passed again: all eleven hashes, sizes,
inventory and nanosecond modification times match the retained pre-E4 snapshot;
the existing E001 manifest verifier reports no errors. No E001 format or
sealing implementation changes were made. Git diff against HEAD is empty for
all tracked files, including all accepted E1/E2/E3 scientific implementation,
reference fixtures and statistical decisions.

No execution seed, beacon/witness selection, research candidate hashing,
QA2 hashing exercise, experiment dispatch, discretionary seed replacement,
publication, commit, push, merge or tag occurred. Existing import-surface and
execution-disabled gate checks pass. The external verification, witness,
qualification, formal registry integration and platform durability dependencies
listed above remain unresolved and unchanged. Actual symbolic-link creation
qualification requires a Windows environment granting that privilege.

Stop for Architecture Review 035.
