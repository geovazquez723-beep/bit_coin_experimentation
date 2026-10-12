# Research Director decision — Revision 9 policy adoption

Decision identity: `hashlab-director-decision-review043-revision9-adoption-v1`.
Recorded 2026-10-12 (America/Los_Angeles). Append-only decision record: retain
these bytes; any clarification or superseding decision must be a separate record.

## Authority and exact decision

Authority is the human Research Director's explicit instruction supplied in
Architecture Review 043, “Research Director authorization”:

> The Research Director explicitly approved Experiment 002 Revision 9 as HASHLAB's solo-research governance policy, with Level 2 as the target.

This records a directly supplied human approval, not an AI-inferred approval,
cryptographic signature, external timestamp, institutional witness or independent
human scientific audit. The AI engineer records the decision; the Director is
the authorizing actor. No external receipt or key is asserted.

Adopted governance identity: `hashlab-exp002-solo-governance-v1`.
Adopted protocol policy identity:

```text
proposal-revision-9|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1
```

Frozen, authoritative scientific-baseline identity retained unchanged:

```text
proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1
```

Secondary identity remains `hashlab-exp002-secondary-statistics-proposal-v2`.
Level 2 — Externally Verifiable Solo Research is the target, not a claim that its
operational requirements are satisfied. Level 1/2 must not be presented as
independently human-audited research. Statistical design, populations, encodings,
budgets, classifications, failures and scientific safeguards remain frozen.

## Exact adopted documents and accepted state

Adoption concerns the policy specified in
`docs/proposals/experiment-002-solo-governance-revision-9.md`, raw working-copy
SHA-256 `3c2595faaad948c5957a992b99eb8cda40d27f961bac3d39f6c4cb47a9b35979`.
The accompanying historical Review 042 handoff is
`docs/reviews/architecture-review-041-revision-9-governance.md`, SHA-256
`afe42df74ad214f628e9b55c1baa32a400a1e8a74d7a03e60151c1c636f4f822`.
Both documents are preserved verbatim, including their proposal-era status.
This separate dated decision supplies adoption provenance; it does not rewrite
history. File digests here refer to UTF-8 working-copy bytes; future Git checkout
line-ending conversion must be distinguished from raw byte identity.

Accepted engineering parent: `c26dc40975bc213f67773d6c5fe1709a4843ea76`.
Branch: `feat/e001-independent-qualification`.
Initial tracked diff/index empty. Pre-existing untracked inventory: `.venv313/`,
the two adopted documents above, `architecture-review-039-external-readiness.md`
and `architecture-review-040-e6-preparation.md` under `docs/reviews`.
Readiness/E6 documents and unrelated environment remain untouched and unstaged.
Revision 8/encoding/secondary source input pins were reverified unchanged.
All eleven E001 original files match prior SHA-256, size, inventory and `mtime_ns`;
manifest and historical source/contract verification report no errors.

## Authorized scope and prohibitions

Review 043 authorizes only scoped documentation closeout (this decision plus
the two preserved proposal/handoff files as one documentation commit) and
preparation of a separate, uncommitted governance migration architecture design
and Review 044 handoff. No governance implementation/schema/test migration is
authorized. The existing accepted E1–E5 implementations retain their status and
Revision 8 evidence semantics until separately approved migration.

Prohibited: accepted E1–E5 code changes; historical E001 enumeration or candidate
SHA-256 evaluation; QA2 implementation/execution; E002 candidate generation,
hashing or execution; selection of seed/master/beacon round/commitment/witness;
release creation or operational dispatch; automatic retry/repair/resumption;
push/merge/tag. Do not commit the migration proposal before Architecture Review 044.

Policy adoption is distinct from migration acceptance, operational readiness,
G1 acceptance, QA2 qualification, G2 decision and action-specific execution
authorization. None of those outcomes is granted by this decision. Missing
scientific prerequisites, exact historical reproduction/exclusion qualification,
external timestamp/retention readiness and engineering integration remain
blocking at their corresponding gates. No past failed/blocked result or receipt
is reclassified. Later material actions require distinct explicit Director
approval bound to exact revision/source/scope and operation.
