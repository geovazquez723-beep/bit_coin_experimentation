# Architecture Review 035 — E4 closeout and G1 readiness gap assessment

Prepared for Architecture Review 036. Assessment only; no implementation or execution authorization.

## E4 closeout

E4 milestone commit: `1a332d8c1ace2c36fa80bc8b808b3d72eba3e255`.
Parent: `df3b96b4ce81979c1d0ea21cab3725af362e6479`.
Branch: `feat/experiment-002-e4`.

Before staging, verified the branch, exact parent, empty index, no tracked
changes and exact five-file inventory from the Review 034 continuation in
[the E4 handoff](architecture-review-033-e4-foundation.md):

1. `src/hashlab/experiments/exp002_governance.py`
2. `src/hashlab/experiments/exp002_journal.py`
3. `src/hashlab/experiments/exp002_provenance.py`
4. `tests/test_exp002_e4.py`
5. `docs/reviews/architecture-review-033-e4-foundation.md`

Only those files were staged and committed. E1–E3 sources were unchanged.
After commit the only untracked entry was preexisting `.venv313/`, excluded.
No push, merge, tag or release identity was created. This assessment is the
only new post-commit file; no accepted E1–E4 source was edited.

Qualified Python: `.venv-py313-review024/Scripts/python.exe` (3.13).
Bytecode disabled; pytest cache disabled; temporary fixtures confined to the
ignored qualified environment.

- E4 focused: **44 passed, 2 skipped in 0.50s**.
- Full regression: **753 passed, 2 skipped in 15.59s**.
- Both skips retain actual file/directory symlink tests in
  `tests/test_exp002_e4.py:252`: WinError 1314, insufficient creation privilege.
  They are environment limitations, not passing symlink qualifications.
  Actual Windows junction rejection passed (`:265`); mocked symlink/special-file/
  reparse metadata rejection passed (`:308`).

E001 `results/20261011T205056Z-exp001-fc1d75fc` retains all eleven original
file hashes, sizes, inventory and nanosecond modification times against the
retained pre-E4 snapshot. Existing `verify_manifest` reports no errors.
Manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.

## Assessment method and gate separation

Source baseline is the E4 commit above. Normative G1 checklist:
[proposal revision 8, section 3.13](../proposals/experiment-002-research-design.md#313-go--no-go-criteria)
(the explicit list starts at line 1280). Also assess section 3.3's M/E/D/P/C
matrix, section 3.7.1 QA2 and section 3.8.2 independent verifier requirements.
References below are repository-relative with source line or exact test name;
line numbers refer to this accepted baseline. A frozen metadata string or
caller-supplied passing claim is not evidence of operational completion.

VERIFIED means the stated narrow requirement has concrete source and passing
tests/evidence. PARTIAL means implemented in part, with independent or
operational qualification still absent. MISSING means no concrete implementation
of the stated capability was found. BLOCKED means completion depends on an
external decision, witness, resource or artifact. A broad row uses the weakest
material component; it does not erase verified subcomponents.

**G1 is not yet ready for overall implementation acceptance.** E1–E4 milestone
acceptance established component contracts, not an integrated Experiment 002
implementation. **QA2 has not passed or run**: statistical fixtures are necessary
but cannot replace its same-production-path small hashing test and independent
checks. **G2 is not authorized**: release, smoke throughput, witnessed commitments,
seed record and written approval are separate later prerequisites. No G1/QA2/G2
receipt was issued by this assessment.

## Every explicit G1 requirement

| Requirement | Status | Concrete support and remaining gap |
|---|---|---|
| Sampler exactness on small analogs (3.2.4) | VERIFIED | `src/hashlab/candidates/vitter.py:180,202,232`; `tests/test_vitter.py` tests `test_every_tiny_geometry`, `test_exact_skip_mass_and_rejection_envelope`, `test_exact_combinatorial_subset_and_inclusion_probabilities`, `test_independent_algorithm_s_exact_path_enumeration`, `test_explicit_d2_d4_paths`. A3 integer selection/partition: `exp002.py:179`, `tests/test_exp002_e1.py:test_replay_partition_exclusion` and exact Algorithm S enumeration in `test_vitter.py:80`. This verifies the small-analog law, not production throughput or a proof that MT19937 is an ideal RNG. |
| Unranking is a bijection | VERIFIED | `src/hashlab/experiments/exp002.py:104` (`HammingPopulation`); exhaustive small-domain rank/unrank inverse and ordering in `tests/test_exp002_e1.py:32`; actual population edge checks at `:41`. |
| Every M property tested | PARTIAL | A1/A3 predicates, rank/stage partition and A2 geometry have tests, but N1/P Feistel bijection, inverse, rejection and disjoint range properties have no concrete E002 control implementation/tests. See expanded matrix below. |
| Margin rule, A2 hull and 2,999 df match independent references; cluster aggregation independently recomputed | VERIFIED | `src/hashlab/statistics/exp002.py:140,155,197`; `tests/test_exp002_e2.py:34,43,63,177,184,233,255`; independent Decimal recurrence `tests/exp002_reference.py`, explicit pinned counts `tests/fixtures/exp002-e2-synthetic.json`. Statistical synthetic component qualification only; it is not full QA2 integration. |
| Negative-lift control tested | PARTIAL | Count-based negative-lift decisions pass `tests/test_exp002_e2.py:107,118,244`; `statistics/exp002.py:250`. Actual negative-lift digest engine is missing: legacy `experiments/controls.py:27` rejects nonpositive lift. E3 `ControlProvider` is only a Protocol (`exp002_foundation.py:206`). |
| Blinding of progress and failure output verified | MISSING | No E002 operational harness/progress/error renderer is implemented. Journal disclosures (`exp002_journal.py:46,155`) do not prove terminal/log/exception blinding. `test_metadata_only_import_surface` confirms absence of a runner, not privacy of a future runner. Requirement also appears in proposal section 3.8 and line 1388. |
| All existing tests pass | PARTIAL | 753 passed, no failures; two explicit environment-dependent symlink tests skipped. Their code remains. Actual junction and metadata rejection pass. Director must decide whether supported-environment symlink execution is required before signing G1; do not treat skips as passes. |
| E001 evidence verifies and re-analyses identically | PARTIAL | Hash/size/inventory/mtime verification passes for eleven files. Read-only in-memory `experiments/analysis.py:189` recomputation from sealed `results.json`/`config.resolved.json` preserves all integer counts/decisions and other normalized fields but not exact historical secondary floats; details below. |

## M/E/D/P/C coverage and exact-audit gaps

Matrix source: proposal section 3.3, lines 655–688. The plan gate requires actual
E re-enumeration and every D check recorded; accepting audit interfaces does not
satisfy those requirements.

| Property / audit | Status | Source/test/evidence and gap |
|---|---|---|
| A1 vs A3 M predicate disjointness | VERIFIED | `exp002.py:92,96`, `test_exp002_e1.py:test_populations`, `test_hamming_exhaustive`. A1 top half zero; A3 requires nonzero top half. |
| 8-byte vs 80-byte sets; E002 vs E001 16-byte set M length separation | PARTIAL | Candidate lengths enforced in `exp002_foundation.py:138`; `test_record_roundtrip`, `test_record_invalid_geometry_and_membership`. A2 encoder at `exp002.py:301`, `test_a2_kat`. Mathematical length argument is fixed in section 3.3; actual N1/P/N2 providers and their end-to-end length checks remain absent. |
| A1/E001 sequential and Gray M construction bounds | PARTIAL | Generic E001 generators exist under `src/hashlab/candidates/`; E1 tests enforce A1 boundaries. No pinned concrete E001 reconstruction adapter/tests connecting the sealed generator configuration to this M audit. |
| A3 excludes X3 by rank mapping; within A1/A3 uniqueness; D/V partition M | VERIFIED | `Exclusions` and integer selection in `exp002.py:151,179`; `test_replay_partition_exclusion`, `test_exclusion_rejection`, `test_exhaustion_and_empty`, `test_vitter.py:test_replay_and_stage_allocation`. Verified given supplied validated exclusions, not proof that those exclusions equal the sealed E001 intersection. |
| E001 E re-enumeration: zero A1 hits, 60,721 A3 exclusions and pinned digest | PARTIAL | `exp002.py:320` accepts a supplied stream; `test_exp002_e1.py:test_e001_audit_small_fixture`. `E001ExclusionRequest` pins run/count/digest (`exp002_foundation.py:217`, `test_e001_reconstruction_request_is_pinned`). `E001Reconstruction` at `:211` has no provider. Historical proposal enumeration is not a newly qualified production reconstruction or signed audit. |
| N1/P vs A1/A3 M predicate rejection, N1 vs P and N1 D/V M disjoint ranges, within N1/P M bijection | MISSING | Plan describes Feistel/rejection at `exp002_foundation.py:101`; `ControlProvider` is abstract. No E002 six-round Feistel, inverse-permutation mapping, exact reserved index ranges or corresponding exhaustive analog tests found in `src/hashlab`. |
| N1/P vs all E001 8-byte candidates D inverse-index audit | MISSING | Requires the missing control inverse and concrete E001 reconstruction. `OverlapAudit` (`exp002_foundation.py:237`) and `AuditResult` (`:244`) do not perform this check; `test_audit_guarantees` validates labels only. |
| A2 prefix distinctness D, then cluster/nonce M uniqueness and stage separation | VERIFIED | `exp002.py:293,301,307,311`; `test_exp002_e1.py:test_prefix_uniqueness_and_overlap`, `test_stages`, `test_stream_adapter`. Collision fails without redraw. Actual execution-prefix audit evidence is deferred to a future authorized plan, not available now. |
| N2 vs A2 D membership/rejection and counters | MISSING | N2 has accounting geometry (`exp002_foundation.py:309,393`) but no actual provider or overlap algorithm. The plan text and callback Protocol do not verify all N2 inputs. |
| N2 uniqueness P and RNG/PRP C assumptions | PARTIAL | `AuditResult` forbids measured zero counts for P/C claims (`:244`; `test_audit_guarantees`). Bounds/assumptions are specified in section 3.3. No integrated audit report yet; P/C must never be relabeled exact D/M verification. |

## Controls, performance and independent verification

| Capability | Status | Support and missing qualification |
|---|---|---|
| Actual N1 implementation | MISSING | `exp002_foundation.py:101,206` is specification plus interface. No E002 generator implementing the approved Feistel/rejection/inverse audit exists. |
| Actual N2 implementation | MISSING | Same plan/interface; synthetic N2 counts exercise the statistical path only (`test_exp002_e2.py:test_controls_negative_lift`; `test_exp002_secondary.py`). No approved 80-byte stream/A2-rejection provider. |
| Actual P1 / P2+ implementation | PARTIAL | Legacy `experiments/controls.py:27` implements positive digest bias; generic tests cover baseline positive controls. Missing E002 control candidate domains, stream ranges, audits, evidence provenance and integration. Existing generic engine is not an accepted E002 P1/P2 pipeline. |
| Actual P2− implementation | MISSING | Legacy control permits positive lift only; no negative mode. Count-based negative-lift classification is already verified independently and must remain unchanged. |
| Null/positive statistical gates and exploratory separation | VERIFIED | `statistics/exp002.py:250`; `test_exp002_e2.py:test_statistical_gate_failures`; `test_exp002_secondary.py:test_primary_classifications_and_control_gates_unaffected`, `test_no_primary_or_operational_dependency`. All 36 secondary slots and numerical references are component-tested; no operational gate receipt follows. |
| A1 Algorithm D production performance | PARTIAL | Correctness source `candidates/vitter.py`, small-analog tests above, accepted bounded ledger `docs/reviews/architecture-review-027-e1-performance.json`; reproducer `tools/benchmark_exp002_e1.py` was not run here. Review 027 reports 1,000/5,000/10,000 untraced selections at 0.772849/15.979385/59.036940 seconds, 6,044 traced peak bytes, no aborts. These are small single-pass observations, not evidence of 30M-selection feasibility. Review 027 explicitly recommends profiling/optimization before production qualification. No new timing extrapolation, full sample or benchmark was performed. |
| Independent candidate reconstruction | MISSING | Success records can be structurally deserialized/validated (`exp002_foundation.py:182,461`) but no separately authored E002 replay verifier reconstructs every success from the committed generator/seed/domain/stage. A2 direct encoding KATs and small sampler references are insufficient for full provenance. |
| Independent evidence/statistical reconstruction | PARTIAL | E2/secondary reference calculations (`tests/exp002_reference.py`, `tests/exp002_secondary_reference.py`, `tools/build_exp002_secondary_references.py`) do not import production statistical code. E3 `validate_evidence:556` and E4 `verify_seal:53` validate metadata/count consistency but share HASHLAB foundations; no separately authored off-machine verifier implementing section 3.8.2 and signed report exists. |
| Completeness of all outcomes | BLOCKED | Positive record rehashing cannot establish absence of omitted successes. Section 3.8.2 requires a decision on minimal verification versus separately authorized full regeneration/rehashing or an approved stronger evidence scheme, and assignment of the independent auditor. No sampled/full audit is executed or authorized by this assessment. |

## Governance, authentication and reproducibility

| Capability | Status | Support and remaining dependency |
|---|---|---|
| Local append-only chain, gap-free A attempts and fail-closed interruptions | VERIFIED | `exp002_journal.py:54`; `test_exp002_e4.py:63,75,89,97,102,108,130,137,151,281`. Every append requires exact externally verified prior history pin; interrupted bytes/lock retained. No seed replacement, valid-result retry or same-code F4 retry. |
| Journal filesystem security and power-loss durability | PARTIAL | Exclusive creation/fsync at `exp002_journal.py:39`; no lock stealing/repair. Inventory rejects reparse/special files (`:21,29`), tests `:237,265,308`. Trusted nonconcurrent parent-directory ownership remains an assumption; journal open paths do not supply OS-level no-follow handles, ACL enforcement or directory metadata durability qualification. No hostile-process/race or physical power-loss qualification exists. |
| Durable external anchoring / formal registry | BLOCKED | `AttemptJournal.append` requires a `registry-history` proof; only `SyntheticVerifier` (`test_exp002_e4.py:15`) supplies test receipts. No deployed durable latest-anchor store, anti-rollback authority or Git-committed S/Q/A registry integration. Formal registry/started-entry commit binding to `environment.json` required by proposal lines 995–1004 remains missing implementation. External custodian/storage/receipt policy must be selected and approved separately. |
| Real external verifier implementations | MISSING | `ExternalVerifier` (`exp002_governance.py:64`) is Protocol; `verify_claim:90` calls it. No witness signature, pre-reveal timing, beacon signature/round/derivation or approval authority verifier exists. Private sentinel establishes an in-process API distinction only; malicious Python code can forge/misuse it. |
| External identities/trust policy | BLOCKED | Actual independent verifier author/environment, witness/custodian, receipt trust roots and replay/revocation/latest-anchor semantics need external decisions. None selected. Approved beacon specification does not itself supply a verifying implementation or authorize selecting a round. |
| Full-plan and commitment binding | PARTIAL | `FullPlanBinding:18`, `CommitmentContract:135`, tests `test_binding_and_declared_vs_verified`, `test_commitment_missing_witness`. Exact protocol and seedless fingerprints enforced; reference-only full-plan envelope does not resolve or authenticate a real configuration/seed derivation. |
| Evidence/provenance authentication | PARTIAL | E3 typed metadata/accounting (`exp002_foundation.py:514,556`); E4 outer seal and independent read-only interface (`exp002_provenance.py:29,53`). `test_exp002_e4.py:115,158,293` verifies tamper rejection/canonical bytes/read-only behavior. Actual authentication depends on a real completeness verifier and independently retained manifest pin; neither is implemented. Outer and E3 schemas are separate and need a reviewed integrated evidence contract. A local SHA-256 self-hash is not provenance authentication. |
| QA2 statistical prerequisites | PARTIAL | E2 independent full-geometry fixtures and E3 36-slot pins are present; `test_exp002_e2.py:184,226,233`, `test_exp002_secondary.py:35,55,80,138,257`, pinned JSON. No complete separately authored QA2 evidence reader/pass report over the production integrated paths. Appointment/source/environment pinning still required; numerical fixture agreement alone does not pass QA2. |
| QA2 complete-path and hashing prerequisites | MISSING | No E002 production orchestration/test adapter binding config/plan/environment/Q-entry through generation, hashing, accounting, sealing and independent verification. Section 3.7.1 requires 2,048 main + 2,048 independent fixture evaluations and total cap <=4,200 including probes; no such hashing was performed. A miniature parallel harness would not meet that requirement. |
| Release reproducibility | PARTIAL | Accepted commits and local 3.13 test environment provide a reproducible source baseline; no E002 release environment bundle/lock, independently rebuilt release artifact, G1 signoff or QA2 release-candidate qualification. No release/tag selected. E001 historical Python 3.11 environment differs from current 3.13 recovery environment. |
| Off-machine evidence archival | BLOCKED | Proposal section 3.8.3 / D9 specifies original evidence, repository bundle, release dependencies and independently checked outer inventory. No custodian/target, transfer receipts or off-machine restore verification artifact found in reviewed repository. Local integrity verification is not proof of archival. |
| G2 pre-execution authorization | BLOCKED | Section 3.13 requires completed G1/QA2, throughput smoke result, E/D plan audits, clean tagged release, S1–S5 commitments and written Director authorization. None follows from component acceptance. `check_eligibility` (`exp002_governance.py:115`) always returns execution disabled even for complete synthetic proof sets. |

## E001 read-only reproduction finding

In-memory `analyze_results` was invoked on the sealed `results.json` and
`config.resolved.json`; the CLI analyze command was deliberately not used because
it writes an analyses directory. After excluding `analyzed_at_utc` and sorting
`secondary_tests` by canonical content, exact equality still fails in 86 floating
secondary fields only. Maximum absolute statistic difference:
`2.2737367544323206e-13`; maximum p-value difference:
`3.4083846855992306e-14`. All other normalized fields, integer counts and decisions
are exactly equal. No tolerance was adopted as a new acceptance rule.

The historical review (`docs/reviews/experiment-001-scientific-review.md:69,331`)
records timestamp/order normalization. Current recovered Python 3.13 also shows
small numerical drift; Review 008 already distinguishes compatible runtime
recovery from identical historical reproduction. Strict G1 identity therefore
needs an Architect decision or qualified original-runtime reproduction. Do not
modify E001 evidence or accepted scientific code to make it appear identical.
Evidence hashes/sizes/inventory/mtime remain exact; this finding concerns
recomputation, not evidence corruption.

## Smallest defensible next milestone and dependency order

**Propose E5: read-only E001 reconstruction and exact exclusion-audit qualification.**
Request separate approval; no implementation is authorized by this document.
Keep it narrower than a runner or QA2 integration:

1. Implement the concrete `E001Reconstruction` adapter against the pinned sealed
   configuration/seeds and immutable source identity. Add independent small
   reconstruction vectors and exact exclusion ordering/digest comparisons.
2. Integrate that adapter with `audit_e001` and emit a read-only, versioned E audit
   artifact binding the original manifest, code/environment, enumeration counts,
   zero A1 overlap and exact A3 count/digest. Place any new report outside E001.
3. Seek explicit authorization before the full seven-million-candidate E001
   enumeration; no candidate SHA-256 is needed for membership reconstruction.
   Validate the reconstruction independently before using it as a gate receipt.

This comes first because A3 population membership and N1/P inverse-overlap audits
depend on the correct X3/E001 reconstruction. It can close a scientifically
material gap without selecting a seed, building a dispatcher or running QA2.
Acceptance should require exact reconstruction vectors, negative provenance/
count/digest tests, E001 preservation and independent review; if full enumeration
is not authorized, label the artifact as fixture qualification only.

Subsequent dependencies, each needing its own scoped authorization:

1. Resolve independent-verifier ownership, audit-completeness policy, external
   anchoring/custody and historical reproduction expectations. These decisions
   constrain all later evidence and eligibility claims; do not wait until freeze.
2. Implement actual N1/P permutation/inverse, exact rejection/range accounting,
   N2 stream/A2 overlap rejection and P2− engine. Exhaustively test M analogs and
   D audit algorithms before production integration. Reuse frozen E2 decisions.
3. Independently reconstruct candidate/evidence/statistical fixtures and define
   authenticated provenance/registry bindings. Harden trusted filesystem and
   external receipt boundaries, including supported-host symlink qualification.
4. Review A1 profiling/optimization separately, preserving the accepted exact-law
   implementation as reference. Qualify production feasibility with explicitly
   bounded authorized engineering work; do not infer it from the small ledger.
5. Build reviewed non-executing integration contracts and blinding/error tests,
   then separately authorize a same-production-path QA2 adapter and qualification.
   Preserve the <=4,200 cap and independent verification; no QA2 run is implied.
6. Obtain full G1 acceptance, complete QA2, reproducible environment/off-machine
   archival and later Director-approved G2 smoke/freeze/commitment procedure.
   Only a later authorization may choose release/round/seed or enable execution.

No additional source changes, QA2 hashing, candidate evaluation, Experiment 002
execution, seed/beacon selection, release creation, push, merge or tag occurred.
Stop for Architecture Review 036.

