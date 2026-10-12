# Architecture Review 044 handoff — Revision 9 adoption and migration design

Prepared 2026-10-12 under Review 043. Policy adopted; migration **design only**.
No implementation or operational gate acceptance/authorization follows.

## Documentation milestone

Commit: **`c77800f952620b3f846b95eba81d1fbc99a7a8a9`**.
Parent: `c26dc40975bc213f67773d6c5fe1709a4843ea76`.
Branch: `feat/e001-independent-qualification`.

Exact committed inventory (three newly tracked documentation files):

1. `docs/proposals/experiment-002-solo-governance-revision-9.md`.
2. `docs/reviews/architecture-review-041-revision-9-governance.md`.
3. `docs/reviews/architecture-review-043-director-revision-9-adoption.md`.

The first two were preserved verbatim, including historical proposal status;
the append-only decision records the Director's explicit Review 043 approval,
adopted identities, Level 2 target, scope and prohibitions separately. Exact
staged names/content were checked against reviewed files; staged diff passed
`git diff --cached --check`. No unrelated files staged. No push/merge/tag.

## New uncommitted migration design

`docs/proposals/experiment-002-revision-9-governance-migration.md` specifies exact
common identity bindings/canonical fields, typed evidence states, trust bootstrap,
failure behavior, reference ordering and these proposed schemas:

| Contract | Exact proposed identity |
|---|---|
| Director approval | `hashlab-exp002-r9-director-approval-v1` |
| Algorithmic report | `hashlab-exp002-r9-algorithmic-verification-v1` |
| External timestamp | `hashlab-exp002-r9-external-timestamp-v1` |
| History checkpoint | `hashlab-exp002-r9-history-checkpoint-v1` |
| Solo archive | `hashlab-exp002-r9-solo-archive-v1` |
| Restore verification | `hashlab-exp002-r9-restore-verification-v1` |
| Optional human audit | `hashlab-exp002-r9-human-audit-v1` |
| G1 / QA2 / G2 | `hashlab-exp002-r9-g1-decision-v1`, `hashlab-exp002-r9-qa2-decision-v1`, `hashlab-exp002-r9-g2-decision-v1` |
| Solo E001 final audit acceptance | `hashlab-e001-r9-solo-audit-acceptance-v1` |
| Supporting envelopes / compatibility | `hashlab-exp002-r9-plan-envelope-v1`, `hashlab-exp002-r9-evidence-envelope-v1`, `hashlab-exp002-r9-compatibility-decision-v1` |

All bind active Revision 9 protocol, adopted governance, frozen Revision 8
scientific baseline and unchanged secondary v2 identities. Existing payloads
and seals retain their exact bytes/version. These are specifications, not new
implemented schemas or currently valid receipts.

The explicit compatibility tables in proposal §5 map E1–E5 interfaces and every
E4 eligibility kind plus retry-review/evidence-completeness/outer-manifest.
Scientific component evidence is reusable only at its established scope under
a documented compatibility decision. Old organizational approvals are not
automatically migrated; old failed/blocked outcomes are not rewritten.

## Trust, approval and execution boundaries

Five separate states: local data; algorithmic verification; external time/
retention; Director permission; optional independently authenticated human audit.
No single passing boolean or role string substitutes for them. Existing E4
`VerifiedEvidence` remains unchanged for R8; local approval never becomes external
authentication. New proposed types/validators operate in parallel.

Director approval is direct human permission for exact source/environment/
scope/action. External receipt is a validated service claim about exact bytes,
time or retention; neither proves honest capture. Algorithmic agreement does not
establish organizational independence. Same-author Codex verification is disclosed.

Even fully passing G1/QA2/G2 cannot dispatch. A future separately reviewed action
boundary requires distinct `exp002-execution` approval for exact release, full
plan/config/environment/seed commitment and eligible attempt. Gate acceptance,
policy adoption or QA2 approval cannot substitute. No controller or action is
implemented. Final E001 approval is a separate `e001-audit-acceptance` action,
not enumeration or G1/E002 execution permission. Approvals bind prior evidence;
later decisions bind approvals, without self-hash/reference cycles.

## Proposed qualification and open decisions

Proposal §7 specifies synthetic negative cases for missing/wrong-action approval,
identity/scientific-baseline mismatch, invalid timestamps, expired/unverifiable
authority, false human-audit claim, rollback/fork/stale history, incomplete or
rewritten inventory, invalid legacy reuse, unapproved retries/seed replacement,
execution without separate permission, forged state assertions, cyclic references,
interrupted writes and malformed canonical values. **None implemented or run.**

Still requires Director/Architect approval: exact schema/criteria and human-origin
approval/withdrawal authentication; service/trust roots and expiry/archive policy;
fresh-head lookup/retention/outage policy; two off-machine failure domains and
restore evidence; platform/resource/release qualification. No service, key,
authority, round, seed, commitment, witness or release selected.

Material blockers remain: complete E001 provider/exact exclusion audit, original
runtime provenance/compatibility and86 numerical discrepancies; real controls/
overlap audits/P2− engine; E002 independent reconstruction/verifier; production
blinding/evidence/registry integration; A1 feasibility and Windows/SQLite/disk/
whole-process RSS; actual QA2, beacon verification and audit-seed format policy.
Governance adoption does not waive scientific prerequisites or establish readiness.

## Preservation and final Git inventory

Read-only preservation checks use qualified Python3.13 with bytecode disabled;
no tests, candidate generation, statistical recomputation, QA2 or experiment ran.
All eleven E001 filenames, SHA-256, sizes and nanosecond mtimes match the retained
pre-existing snapshot; manifest verification and historical source/contract pins
report no errors. E001 manifest remains
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
Accepted E1–E5 code, Revision 8 scientific design, encoding/secondary identities
and preserved readiness/E6 documents remain unchanged.

Exact new uncommitted file inventory:

1. `docs/proposals/experiment-002-revision-9-governance-migration.md`.
2. `docs/reviews/architecture-review-043-r9-migration-handoff.md` (this handoff).

Also untracked and preserved: `docs/reviews/architecture-review-039-external-readiness.md`,
`docs/reviews/architecture-review-040-e6-preparation.md`, and `.venv313/`.
Tracked working tree clean; staging index empty; HEAD is the documentation commit
above. No automatic retries/repair/resumption, code changes, hashing, operational
dispatch, release or push/merge/tag. Migration proposal remains uncommitted.

Stop for Architecture Review 044. Separate acceptance and implementation
authorization are required before any migration work.
