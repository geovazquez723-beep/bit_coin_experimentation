# Review 042 handoff — proposed Revision 9 solo-research governance

Prepared under the supplied Architecture Review 042 assignment. Filename follows
the assignment's explicit suggestion; this is the requested Review 042 handoff,
not an invented Review 041 acceptance or adoption record.

**Revision 9 is PROPOSED ONLY. G1 not passed; QA2 not qualified; G2 not authorized.**

## Deliverables and exact scope

1. `docs/proposals/experiment-002-solo-governance-revision-9.md` — new proposal.
2. `docs/reviews/architecture-review-041-revision-9-governance.md` — this new handoff.

These are the only two new task files. No accepted implementation, tests,
Revision 8 text, secondary/encoding specification or sealed E001 file changed.
No commit, push, merge, tag, release or operational action occurred.

| Requested deliverable | Exact proposal location |
|---|---|
| Proposed amendment/authority/transition | §§1,8–9 |
| Frozen scientific register | §2, I01–I24, with complete normative source clauses incorporated |
| Revision 8 versus 9 requirement matrix | §4, M01–M43 and all E4 eligibility/retry proof kinds |
| Three assurance levels | §3 |
| Solo G1/QA2/G2 and pass/conditional/blocked/fail | §5 |
| Written approvals/commitments/custody/attempts/retries | §6 |
| Historical exclusion/runtime/numerical claims | §6 “E001 exact qualification and claim categories” |
| Threat model/residual limitations | §7, all eight requested threat classes |
| Publication/migration compatibility | §8 |
| Open Director decisions | §9 and this handoff below |

The requirement matrix records source, purpose/risk, category, treatment,
assurance lost, required compliance evidence and current code/later-change
status. Each G1 bullet, QA2 constituent, G2 constituent and commitment/custody/
verification requirement is mapped. Scientific clauses are retained in full by
exact source reference; register summaries are an index, not replacement rules.

## Established baseline and preserved input identities

Branch remains `feat/e001-independent-qualification`; accepted HEAD remains
`c26dc40975bc213f67773d6c5fe1709a4843ea76`. Initial tracked diff and index empty.
Pre-existing untracked `.venv313/` and both E6/readiness documents were preserved.

Accepted milestone history used as evidence, not new gate approvals:

| Milestone | Accepted commit |
|---|---|
| E1 | `dbcbd223953b2e3e39149567026b2513bd7e24af` |
| E2 | `b8b74f83819be74e0c0c2f66916740331b850692` |
| E3 | `df3b96b4ce81979c1d0ea21cab3725af362e6479` |
| E4 | `1a332d8c1ace2c36fa80bc8b808b3d72eba3e255` |
| E5 Phase A | `9d31eda5d7f20af00824ccdbe1452f8509567952` |
| E5 bounded Phase B | `c26dc40975bc213f67773d6c5fe1709a4843ea76` |

Authoritative scientific identity established from Revision 8 header, Review 027
closeout, SEED contract and accepted code:

```text
proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1
```

Approved secondary identity established from proposal v2 header and Review 032:
`hashlab-exp002-secondary-statistics-proposal-v2`. Historical pending wording
inside that proposal is explicitly superseded by its approved header; the
statistical specification has not been changed here.

The formal E002 registry/configuration and R8 §4 outline specification path are
future artifacts, not existing authoritative execution records. No such record
was invented. Review 032 documents the user-supplied Review 031 authorization;
no separate local Review 031 file is claimed. Historical “missing Python/E1
blocked” statements remain historical; accepted later component evidence is
identified separately, not rewritten into old text. No missing scientific
identity was filled in by inference.

Read-only SHA-256 pins captured before drafting (raw working-copy bytes, not
source LF normalization). These inputs were rechecked unchanged afterward:

| Input | SHA-256 |
|---|---|
| `docs/proposals/experiment-002-research-design.md` | `d3984943aa42f6c3f760bae85141139c1141e2eaa937dae36f1dfdcec7d2e8ee` |
| `docs/proposals/experiment-002-a1-a3-seed-encoding-proposal.md` | `e329d418a58fca14126441a57bbee25f26e477562248927eeffc84b5f6746420` |
| `docs/proposals/experiment-002-secondary-statistics-proposal.md` | `a76b3d441ae5d9b81330107984bf13cae6c7a9bc6515a6375a97fb86e927c440` |
| `docs/reviews/experiment-002-protocol-readiness-addendum.md` | `9b2d78318305fc7e9d57a2531d3668ee464700350f7dbd5db0ffec949825edb9` |
| `docs/reviews/architecture-review-008-operational-recovery.md` | `43f165526d5d7cf5c7fded38df92dc9f8233094e76b19fa423b17dcd7fc056ad` |
| `docs/proposals/e001-reconstruction-phase-b-proposal.md` | `86ed77def6c6dc1ee42c05958bf57044a2fb8a9e52c8aa7468ad3e9e2e04d699` |
| Preserved `docs/reviews/architecture-review-039-external-readiness.md` | `63843c51f8825625e6151f6012c078d5fa9df44ad625ad9b00959b0ed4609806` |
| Preserved `docs/reviews/architecture-review-040-e6-preparation.md` | `f46642549873eed29abb861f37ab88bf2129dc4f768bc92eef3c17667501fa75` |
| `docs/research-charter.md` | `1cd643b1f27c4ef2e6726af5afa87b5bdf44e2b4513e5ac10334ea1fb9c9c632` |

## Main proposed organizational changes

- The sole human may act as Director and accept design/engineering with disclosed
  AI advisory review. Each material action still needs explicit written approval
  binding scope, revision, source and permitted action; technical PASS is never
  dispatch permission.
- Level 2 is the target: independently implemented algorithms and references,
  authenticated external prereveal timestamp and retained digests, published
  reproducibility instructions and solo off-machine retention/restoration.
  Independent human scientific review/custody is an optional Level 3 enhancement,
  not falsely claimed from separate AI sessions or import isolation.
- Replace institutional witness acknowledgment only with authenticated external
  timestamp evidence. Retain the exact ≥24-hour lead, fixed future round,
  unchanged derivation and same-round-only outage policy. Missing external timing
  evidence blocks Level 2; a local clock/self-signature does not substitute.
- Replace dedicated external latest-head authority with a proposed externally
  checkpointed local/Git append-only history, disclosing that private suppressed
  actions cannot be ruled out. Existing R8 proof semantics remain unchanged until
  separately approved versioned migration.
- Replace external custody staffing with two solo-operated off-machine failure
  domains and verified restores against prior external pins. Call this backup/
  retention, not independent custody. Separate human auditor signatures remain
  an explicit optional assurance field, never implied by operator signatures.

These changes lose separate-human challenge, independent attestation and some
custody/anti-suppression assurance. They do not alter sampling, budgets, tests,
classification, fixed seed chronology, control gates or truthful limitation
disclosure. They do not make scientifically material failures nonblocking.

## Unchanged material blockers and Director decisions

Director must explicitly decide whether to adopt the proposed identities,
Level 2 target and each organizational substitution, then separately authorize
any migration design/implementation. Adoption is not execution authorization.

Still unresolved even if governance is adopted:

1. Correct complete E001 reconstruction/exclusion qualification. Exactly 7000000
   occurrences must be reconstructed with correct ordering/dedup and independent
   algorithmic count/digest/rank checks. Expected60721 is not an observed count.
   Fixture cap4096 remains; no full provider or enumeration was implemented/run.
2. Original-runtime provenance/compatibility and exact historical numerical
   reproduction. The existing executable access blocker and86 secondary
   discrepancies are not waived by solo governance. Separate explicit scientific
   disposition is required if exact identity cannot be established; under this
   proposal the strict G1 prerequisite remains unresolved/blocking.
3. Actual N1/N2/P1/P2+/P2− providers and audits, integrated blinded production
   evidence/registry paths, complete E002 independent algorithmic verifier,
   A1 production feasibility and Windows/SQLite/native RSS/disk qualification.
4. QA2 actual production-path qualification on identified source/environment,
   exact approved fixtures plus≤4200 evaluations with itemized ledger; separate
   execution approval required. Synthetic component tests cannot replace it.
5. Authenticated timestamp/history service policy and actual verifier, archival
   failure-domain/restore policy, reproducible release, beacon client/live pin
   verification, audit format/seed provenance and minimal-versus-full outcome
   audit decision. No service/key/round/seed/release selected.
6. New versioned plan/provenance/approval/receipt/final-audit contracts separating
   Director declarations, algorithmic verification, external time/retention and
   independent human attestation. Current R8 `VerifiedEvidence` must not be fed
   self-approval as if externally authenticated, and E5 fixture final records
   must remain incapable of historical acceptance.

Recommended decision order: approve/reject governance and claim limits; resolve
scientific compatibility expectations without silent waiver; approve a narrowly
scoped migration proposal and external-time/custody policies; authorize remaining
engineering and qualification separately; only then consider freeze/commitments
and a later explicit G2 execution decision. No next engineering milestone begins.

## Verification and final repository state

Documentation-only inspection and preservation checks; no regression, new tests,
statistical recalculation, candidate generation or hashing qualification was run.
Historical test evidence remains Review039:57 focused passed,889 full passed,
two Windows symlink-privilege skips. It is not represented as a new result or QA2.

Read-only E001 checks passed: all eleven original filenames, SHA-256, sizes and
nanosecond mtimes match the retained pre-existing snapshot; the existing manifest
verifier and historical contract/source pin validator reported no errors. Manifest pin
remains `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.

Final Git state: unchanged accepted HEAD and branch above; tracked diff empty;
index empty. Untracked: the two new documents, the two preserved readiness/E6
documents, and pre-existing `.venv313/`. No implementation/protocol source was
silently altered, no original evidence or unrelated environment edited.

No full enumeration/large-offset replay, historical candidate SHA-256, QA2 hashing,
E002 activity, runtime installation/execution, seed/beacon/commitment/witness
selection, release/dispatch, retry/recovery, commit/push/merge/tag occurred.

Stop for Architecture Review 042. The Director must review and explicitly decide
on the proposed amendment; no adoption or gate acceptance is asserted here.
