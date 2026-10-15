# E002 independent production verification and evidence finalization — implementation handoff

2026-10-13 (initial) and 2026-10-14 (Director decisions and final review), America/Los_Angeles.
Branch `feat/e002-production-verification`, created from updated `main` at exact base
**`3b4002fe91e852b1216f99e52763cf5a54e83ef5`** (PR #4 confirmed `MERGED`, 2026-10-14T03:50:54Z).
Everything is **unstaged and uncommitted** awaiting the final Research Director review.

**Implemented and boundedly qualified:** an independent full-domain reconstruction of every E002
candidate stream, an independent streaming verifier for `hashlab-e002-kernel-chunks-v1`, a versioned
finalization and claim-separation layer built from the accepted E4/R9 components, a fail-closed
external-receipt adapter, a receipt-gated path from independently verified evidence to a production
`VerifiedCapture`, and independent checking of privately persisted measured statistics.
**Production activation remains unconditionally disabled, and real capture issuance is unavailable**
(no receipt service, trust root, credential or signature scheme exists). This is bounded
implementation qualification. It is **not** a full-production verification, G1, QA2, a production
audit, an execution authorization or confirmatory scientific evidence.

## 0a. Final Director decisions D1 and D2 (2026-10-14, applied before the PR)

| # | Decision | Disposition |
|---|---|---|
| D1 | Seeded execution identity: the SHA-256 of the actual resolved, **seeded** configuration is used in the attempt journal and full-plan binding; the frozen seedless configuration digest and seedless plan fingerprint committed in C_pre stay separate; S5 record, C_seed, full plan, registry and environment reconcile to the same seeded configuration; frozen preregistration bytes never change after reveal | Implemented as already designed and now pinned by tests. `FullPlanBinding.resolved_config_sha256`, the journal `started.config_sha256` and the report's `seeded_config_sha256` are the seeded digest; `config_sha256`/`seedless_plan_sha256` are the frozen seedless values. Substitution tests: a binding built from the seedless digest has a different fingerprint and is refused; seeded and seedless digests swapped in any report field are refused; a journal carrying the seedless digest is refused at capture; a different seed record changes the seeded digest and fingerprint. The retained preregistration bundle contains only seedless identities (asserted: it contains neither the seeded digest nor the record digest) and is never rewritten. **Open reconciliation item:** the production kernel's `environment.json` has no configuration field and the writer is disabled, so "execution environment reconciles to the same seeded configuration" is enforced through the journal, the verification report and the full-plan binding, not yet through `environment.json`. |
| D2 | R9 M19 external timestamp must bind BOTH the exact C_pre identity and the SHA-256 of the complete preregistration bundle; verify both subjects, the bundle-to-commit relationship, the predetermined round and the 24 h lead; stay fail-closed | Implemented. The witness block of the seed record gains `bundle_sha256`; the timestamp claim subject is `SHA-256(canonical{schema, c_pre, preregistration_bundle_sha256})` (`timestamp_subject`), so a C_pre-only subject, a bundle-only subject, or a mixed subject is refused. `parse_preregistration_bundle` checks the retained bundle against the witnessed digest, the predetermined round `R*`, the pinned chain, and the frozen seedless plan and configuration identities repeated in the commitment; `verify_c_seed` (reused with the `C_pre` commit id) checks that the retained bundle is byte-identical to the file in the C_pre commit; the 24 h lead and `scheduled = genesis + (R*-1)*3` are checked. Production verification requires the bundle. The bundle layout (`hashlab-e002-preregistration-bundle-v1`) is a proposed schema. No timestamp service is approved, so the capture gate remains unreachable; no receipt, timestamp or round was generated or selected. |

Items 4–8 of the finalization assignment are unchanged and re-confirmed by the tests below: private statistics keep their bindings and
`publication: not-authorized`; only `full` verification exists with the audit policy and resource qualification open; the A1 rare
refinement divergence (§3 A) is preserved with no implicit G1 waiver; shared OpenSSL SHA-256 is recorded as **failing** the independent-implementation
requirement (§3 B); production execution, production capture issuance and external receipt verification remain unavailable.

## 0. Director decisions and final-review disposition (2026-10-14)

| # | Decision | Disposition |
|---|---|---|
| 1 | Seed record: keep `hashlab-e002-seed-record-v1` as a *proposed* versioned schema; reconcile with R8 §3.8 S1–S5, §3.8.1 and adopted R9; derivation unchanged; select no seed | Done (§4). The record now carries C_pre, fixed R*, the pinned chain tuple, scheduled time, the beacon signature and randomness, the C_pre witness reference and exact master. A separate `hashlab-e002-seed-commitment-v1` (C_seed content) carries seedless/seeded configuration and the full-plan fingerprint, plus `C_seed` as an external git pin. Derivation (`hashlab-exp002-master-v1|C_pre|R*|randomness_hex`, first eight bytes, big-endian) is untouched and still equals the producer's. No seed, round or beacon was selected or fetched. |
| 2 | Official capture eligibility requires pre-reveal C_pre timestamp, pre-execution started-attempt checkpoint, and post-verification result/manifest anchoring with prior-head continuity; keep claims separate; no service approved so real issuance stays unavailable | Done (§5–§6). `authenticate_production_capture` requires each as its own externally verified claim, plus the sealed manifest. Algorithmic verification, receipt verification, execution authorization and Director acceptance remain four separate claims; the last two are neither required nor accepted as substitutes. The receipt adapter still raises `FinalizationUnavailable`. |
| 3 | Private statistics approved, with exact capture binding, integrity protection, normal-path restrictions, F1–F4 preserved | Done (§6). The statistics file binds the accounting digest, plan fingerprint and capture completion pin, is created exclusively, set read-only and marked `publication: not-authorized`; the independent check and `require_statistics_for_capture` refuse any mismatch. `RestrictedInference`, F4 disclosure and the always-rejecting `disclose_final` are unchanged. Private persistence is not publication authorization. |
| 4 | Full independent regeneration and rehash preferred; no sampled mode; final audit policy stays open until resources and SHA-256 independence are qualified | Done. Only `full` exists; other mode strings raise; the plan's `audit_decision` remains `unresolved`. Resource figures are projections (§9) and SHA-256 independence is **not** established (§3). |

## 1. Repository preparation and inventory

* `git fetch origin`; local `main` fast-forwarded `16f8b30 → 3b4002f`; PR #4 `MERGED`; branch created from it.
  No reset, clean or protected-path checkout.
* Base inventory: `.tmp/e002-production-verification/base-inventory.json` (SHA-256 of all **166** tracked
  files, size/SHA-256 of all **20** `results/` files, and the pre-existing untracked set).
* Final comparison: `.tmp/e002-production-verification/final-inventory.json` (generated at the first review; the
  review corrections add no tracked-file change): **zero tracked files modified**, all 20 protected `results/`
  files byte-identical, all eight pre-existing untracked paths present, `HEAD` unchanged.

## 2. Changed-file inventory (all new; no accepted file edited)

| File | Role |
|---|---|
| `src/e002_verify/production.py` | Independent geometry, seed derivation, certified Algorithm D, Algorithm S + colex enumeration, A2, Feistel/N1/P, N2, complete expected-attempt stream. |
| `src/e002_verify/production_evidence.py` | Independently restated frozen plan, S1–S5 seed record and commitment parsers, binding checks, streaming chunk verifier, public report. |
| `src/e002_verify/production_statistics.py` | Independent complete-accounting check and recalculation check of persisted measured statistics. |
| `src/hashlab/experiments/exp002_finalization.py` | Seed record/commitment builders, claim ledger, receipt adapter, report parser, receipt-gated capture authentication, outer sealing, R9 record builder, restore check. |
| `src/hashlab/experiments/exp002_kernel_bounded.py` | Fixed 78-evaluation production-format fixture producer (public master 0, KAT domain). |
| `src/hashlab/experiments/exp002_kernel_statistics.py` | Private, exclusive, bound persistence of statistics from an authenticated capture. |
| `tests/test_exp002_production_components.py` (81 tests), `tests/test_exp002_production_verification.py` (112), `tests/test_exp002_finalization.py` (75) | New: 268 tests. |
| `tools/qualify_e002_production_verification.py` | Roles `produce-bounded` and `verify` only; no production/QA2/quota/seed role. |
| `docs/reviews/e002-production-verification-handoff.md` | This handoff. |

Working copies follow the repository's `core.autocrlf=true` convention. Local evidence and logs are under
`.tmp/e002-production-verification/` (`final3/` is the reviewed run; `final2/` the previous review run; `qualification/` and `final/` are
earlier intermediate runs, retained; `bench/` holds probes and microbenchmarks).

## 3. Review checks A and B

### A. A1 uniform-boundary discrepancy — disposition: no law disagreement; residual identified

**What the "discrepancy" was.** Both samplers draw a lazy uniform `U` known only to a 2⁻⁶⁴-wide interval and
decide each comparison `U < p` only when the interval lies entirely on one side of `p`; otherwise they draw
another 64-bit block and retry (never redraw on ties). My first report called a possible path difference a
"divergence probability below 10⁻¹⁰". The review asked for the exact mechanism and reproducible branches.
Two distinct situations exist:

1. **Genuine straddle** (`p` inside the interval, probability about 2⁻⁶⁴ per comparison, order 10⁻¹¹ per full run).
   Both implementations refine the same uniform and make the same sequence of comparisons (`U < q^(N−n+1)`, then
   hint `h`: `U < q^h` and not `U < q^(h+1)`, else binary search; D3 then D4 on one further uniform). This
   was **not** a disagreement and is now reproduced deterministically: 2,800 scripted-block scenarios per tail
   (placing the interval at `floor(p·2⁶⁴)−1/0/+1` for the proposal, D3 and D4 thresholds, including the exact
   dyadic case q = 1023/1024) give identical skips **and identical numbers of consumed blocks** in the producer
   and the independent verifier; the tests assert that both the refining (more than 3 blocks) and the clear
   branches are exercised. Hint agreement (producer `Decimal` vs verifier floating point) is 20,000/20,000 on
   random production-density states (3,000 asserted in the suite).
2. **Enclosure width.** The producer certifies each comparison with 40-digit outward `Decimal` enclosures
   (relative half-width up to about 3·10⁻³⁸ after a 143-term product); the verifier uses at least 192-bit
   enclosures that widen with the uniform's precision. If an exact probability lies *outside* the uniform interval
   but within the producer's enclosure width of an edge, the producer refines and the verifier decides at
   once, consuming fewer blocks. The per-comparison probability is about twice that width (below 10⁻³⁷, roughly
   10⁻²⁸ per full run). This mechanism is injected in `test_enclosure_width_is_the_only_residual_difference_and_it_fails_closed`
   (decisions agree; only block consumption differs).

**Reconciliation.** The verifier matches the approved deterministic acceptance law in every reproducible branch,
without importing the producer sampler and without changing the frozen algorithm. It cannot be made bit-identical
to the producer in situation 2 without re-implementing the producer's 40-digit `Decimal` enclosure arithmetic,
which would destroy independence and has no scientific benefit. **Remaining defect:** none in law; only a
fail-closed false rejection (stream mismatch, never a false acceptance) with probability about 10⁻²⁸ per full run.
**G1 consequence:** not a blocker. G1 should record the policy that a verifier mismatch is investigated, not
waived, and should require the producer to log (privately) any comparison that refined its uniform, so a mismatch
can be attributed.

### B. SHA-256 independence — disposition: **not independent** (Revision 8 §3.9 not yet satisfied)

| Role | Implementation | Runtime/library (this machine) |
|---|---|---|
| Producer | `hashlab.hashing.sha256.SHA256Engine.digest` → `hashlib.sha256` | CPython 3.12.14, `_hashlib` backed by **OpenSSL 3.5.8** |
| Verifier | `hashlib.sha256` (in `production_evidence`) | the same interpreter and library |

§3.9 requires a *different SHA-256 implementation* (for example another OpenSSL major version or a reference
implementation) for the always-on computational reproducibility check. The present rehash is the same library in
the same runtime, so it checks candidate bytes, ordering and counts but is **not** an independent SHA-256
confirmation. The verifier report now states this explicitly
(`independence.sha256.shared_with_producer: true`, `r8_3_9_independent_implementation: false`) and a test pins it.
FIPS 180-4 known-answer vectors (empty, `abc`, two-block, one-million-`a`) pass for the shared library, which
establishes correctness of that build only. **Remaining qualification requirement:** rehash all accepted candidates
(or the approved audit set) with a different implementation — a second OpenSSL major or an audited reference
implementation (a stdlib-only pure-Python implementation is possible and would add roughly two hours of single-thread
time for about 2.4×10⁸ compression blocks; this is a projection) — qualified by known-answer vectors, with versions
and hashes pinned. No dependency was installed and no full audit was run. BLAKE2b (Feistel, N2, A2 prefixes) and MT19937 are
likewise shared with the producer and are listed as shared dependencies.

## 4. Seed record and commitment (S1–S5, §3.8.1, adopted R9) — Decision 1

`hashlab-e002-seed-record-v1` (proposed) fields and rules, verified by `parse_seed_record` independently of the producer:

`schema`, `kind='beacon'`, `c_pre` (40 lowercase hex git id), `beacon{chain_hash, scheme, beacon_id, period, genesis_unix,
public_key_hex, round (R*, canonical decimal, 1 ≤ R* < 2⁶⁴), scheduled_unix, signature_hex (48 bytes), randomness_hex}`,
`witness{receipt_sha256, witnessed_unix, bundle_sha256}`, `master` (decimal), `domain='experiment-002'`. Rules: chain tuple equals the §3.8.1 pin;
`scheduled_unix = genesis + (R*−1)·period`; `witnessed_unix + 24 h ≤ scheduled_unix`; `randomness_hex = SHA-256(signature)`;
`master` equals the exact S4 derivation; `bundle_sha256` is the second timestamp subject (D2). `public-engineering` (master `0`) is accepted only for the bounded fixture.
`hashlab-e002-seed-commitment-v1` (the S5 `C_seed` content, deliberately *outside* the record so no digest is circular)
holds `c_pre`, `seed_record_sha256`, `preregistration_bundle_sha256`, `master`, `seedless_plan_sha256`, `config_sha256`, `seeded_config_sha256`
(configuration with the derived master inserted) and `full_plan_sha256` (the `FullPlanBinding` fingerprint, restated
independently and equal to the producer's). `C_seed` itself is a git commit id supplied as an external pin;
`verify_c_seed` checks that the commit contains exactly the supplied documents. Decision D1 (approved):
`FullPlanBinding.resolved_config_sha256` and the journal `config_sha256` use the **seeded** configuration digest.

The verifier proves the evidence was generated from *that* record. It does **not** verify the BLS signature, subgroup or
RFC 9380 domain (no pinned client exists), the witness timestamp receipt, live chain `/info`, relay agreement, or the
contents of the `C_pre` commit; the report records `beacon_signature` and `witness_receipt` as `not-verified`.

## 5. Contract reconciliation table (S4 / R9)

| Protocol requirement | Implemented field / validation | Evidence source | Missing verification or operational dependency |
|---|---|---|---|
| S1 freeze: configuration complete except master; seedless fingerprint | `config_sha256`, `seedless_plan_sha256` (independently restated, equal to producer) in the commitment | seed commitment (C_seed) | G1/QA2 pass, release tag and pre-registration record content are not implemented |
| S2 `C_pre` commit (code, config, plan fp, exclusion digest, QA2 hashes, `R*`, URL, method) | `c_pre` 40-hex id; `R*`; pinned chain tuple | seed record | Bundle-to-commit relationship is checked when the commit contents are supplied; git object authenticity is unanchored |
| S3 witness ≥ 24 h before `R*` | `witness.receipt_sha256`, `witnessed_unix`; lead arithmetic checked; capture requires claim `external-timestamp` bound to both `C_pre` and the bundle digest (`timestamp_subject`) | seed record + timestamp proof | Authenticated timestamp service/trust root (bundle digest now bound, D2) |
| S4 derivation, uint64 | exact message, SHA-256, first 8 bytes big-endian; `master` field recomputed | seed record; verifier and producer agree on public vectors | none beyond S5 authenticity |
| §3.8.1 beacon verification | chain tuple, period/genesis, scheduled time, 48-byte encoding, randomness = SHA-256(signature) | seed record | BLS verification, subgroup/domain checks, pinned client and historical vectors, live `/info`, relay fetch and disagreement handling, same-round fallback |
| S5 `C_seed` | commitment document; `C_seed` pin; `verify_c_seed` | git commit | Registry/Git integration and external anchoring of the commit |
| S6 registry `started` (commit, config, plan fp, command, UTC) | `AttemptJournal` `started` event bound to `full_plan`, `seed_record`, `code_commit`, seeded `config_sha256`; claim `history-checkpoint` on its head | journal + checkpoint receipt | Started-entry hash written into the run `environment.json` (kernel writer is disabled); registry file; checkpoint service |
| `result` entry (run id, status, class, manifest) | journal `result`: `valid`, `complete`, `manifest = outer pin`; claim `history-checkpoint` on its head with `previous_head`/sequence continuity to the started checkpoint | journal + receipts | Receipt service; result classification for F1–F4 is the existing E4 path |
| R9 M28/§3.8.2 independent verification | full regeneration/rehash report, no producer imports; claim `independent-verification` | `verification.json` + proof | Independent SHA-256 (§3 B), appointed verifier identity, restored-copy run, signed/witnessed report |
| R9 M29 manifest anchor | `seal_evidence`/`verify_seal`; claims `evidence-completeness` and `outer-manifest` | manifest | External anchor of manifest digest is the post-verification checkpoint above |
| R9 M30 authorization separation | five claim kinds, independent ledger; Director approval and acceptance never accepted as substitutes | claim ledger | Director approval/acceptance records and policy evaluator |
| R9 M23/M26 blinding and statistics | private statistics bound to accounting, plan and completion pins; F1–F4 unchanged | `statistics.json` | Access control; publication authorization adapter |

**Circularity check — none found.** Order and what each pin may depend on:
(1) seed record digest `R` ← C_pre, beacon, witness only; (2) master and seeded configuration ← `R`;
(3) `FullPlanBinding` fingerprint `F` ← seedless plan, `R`, seeded configuration; (4) C_seed commitment ← `R`, `F` (not inside `R`);
(5) `started` journal event ← `F`, `R`, commit, config; started checkpoint ← its head;
(6) kernel evidence (producer completion) ← seed-derived streams only, no `F`/manifest/receipt;
(7) verification report ← completion pin, `R`, `F`, commitment, accounting digest;
(8) outer manifest `M` ← sealed files (`complete.json`, chunks, accounting, `verification.json`), `F`, provenance — never receipts or the result head
(a test asserts the sealed inventory); (9) `result` journal event ← `M`; result checkpoint ← the head after it (continuity to step 5);
(10) capture eligibility ← steps 1–9; (11) statistics (private) ← capture; (12) separate Director acceptance ← all of the above, never an input to them.
The finalization record/`disclosure` digest in the `result` event may list only claims known before the result head;
post-result anchoring and acceptance are recorded afterwards.

## 6. Capture, statistics and claim separation

Five claims are distinct kinds, each requiring its own E4 `VerifiedEvidence` bound to the `FullPlanBinding` subject and an
exact evidence digest; `claim_ledger` reports them independently: capture (local pin and replay), independent verification
(`independent-verification`, `statistics-verification`), authenticated receipts (`external-timestamp`, `history-checkpoint`,
`solo-archive`), disclosure authorization, and execution authorization.

`authenticate_production_capture` (the only route to a production `VerifiedCapture`) requires all of: production plan type;
`ProductionPlan.validate_local_inputs` (observed runtime, committed source, authenticated S1.4); `FullPlanBinding` agreement;
a parsed report binding completion pin, plan, commit, seedless/seeded configuration, full-plan fingerprint, `C_pre`, `C_seed` and
seed commitment with no over-claims; externally verified `seed-record` and `independent-verification` proofs; a sealed root whose
`verification.json` equals the report, with externally proven `outer-manifest`; `external-timestamp` on `timestamp_subject(C_pre, bundle digest)`; a journal
with exactly one `started` then a `valid`/`complete` `result` whose manifest equals the sealed manifest, anchored by a
`registry-history` proof; two `history-checkpoint` proofs on the started and result heads whose receipt bytes match the proofs
and chain (`previous_head`, sequence + 1, same issuer); and complete local accounting replay. Bounded, engineering, partial,
unsigned, unsealed or synthetic evidence fails a gate; with no approved receipt service none can be issued.
`commit_statistics` then persists statistics privately (exclusive create, read-only, bound to accounting/plan/completion,
`publication: not-authorized`); `require_statistics_for_capture` binds the independent check to the same verified accounting.
**Honest limit:** the positive path is exercised only with unit-only doubles (a stubbed chunk replay returning artificial counts,
`SyntheticVerifier` proofs and a test-only HMAC scheme registered in the test); each gate is also tested negatively
(missing, substituted, duplicated, mismatched, discontinuous). `run_production` and `authenticate_capture(production)` still raise.

## 7. Independent reconstruction and verification interfaces

`e002_verify.production`: `Geometry`/`FROZEN`/`BOUNDED`, `master_from_beacon`, `seeds`, certified `a1_ranks`, `a3_ranks` with Gosper
enumeration cross-checked against two independent decoders, `a2_prefix`, `feistel`, `n2_stream`, `transform`, `attempts`.
`FROZEN` equals the producer's `LIMITS` (180,200,000 evaluations, 240,200,000 compression blocks). No `hashlab` import (subprocess test).
`e002_verify.production_evidence.verify_evidence(root, completion_sha256=, geometry_name=, seed_record=, audit_root=, repository_root=,
mode='full', expected_runtime=None, allowed_extra=(), seed_commitment=None, c_seed=None, c_seed_files=None)` checks: pin and inventory;
byte-equal independently restated plan; source inventory/commit; runtime; authenticated history; **every attempt** against the independent
stream (arm, stage, rejection mask, source/raw index, accepted ordinal, rank, offset, cluster); **every accepted candidate rehashed** with raw
and effective digests; framing, hashes, trailers, quotas, exact evaluation/block totals; byte-equal accounting and completion. The public report
contains no counts or statistics and carries explicit false claims for receipts, disclosure, execution, G1 and QA2. The production geometry
requires the beacon record, commitment and `C_seed`. The production completion/environment contract (scope `production`,
`hashlab-e002-kernel-production-environment-v1`, `committed;git-verified`) is defined by the verifier because no production writer exists.

## 8. Bounded producer/verifier evidence and tests

* **Fixture.** Public master 0 (KAT domain), full 4,293,918,720-rank A1 population, the first 4,096 A3 ranks with real exclusions, 3,000
  production-derived prefixes: **78 evaluations, 106 compression blocks** (80 attempts with the unit history's two injected rejections).
* **Real retained history** (`final3/`): producer 55.2 s, 857,509,888-byte peak working set; separate independent verifier **7.8 s /
  841,183,232 bytes**; 78 attempts reconstructed and 78 rehashed; evidence 68,684 bytes in 7 files; completion SHA-256
  `1ea96251618b42c6c151fd36215eaafc5af9f436ed08200722ac3fd9dada044a`.
* **Agreement.** A1 matches the producer on ten parameter sets (including the full population, the accepted I1 dense reference and the first 300
  draws at the frozen N and n = 30M); analogs at density N/n = 143 agree for 20,000 and 100,000 samples; A3 agrees on seven exclusion shapes and
  the first 500 full-class draws with all 60,721 real exclusions; Feistel, N2 and digest transformations agree in both domains. Exact-law checks:
  certified enclosures contain the exact D3/D4 probabilities and the accepted-skip law equals the hypergeometric pmf (Fractions).
* **Boundary** (§3 A), **seed/commitment** (§4: 24 single-field rules, extra/missing/noncanonical fields, git-backed `C_seed`), **corruption**
  (20 resealed semantic and 9 resealed metadata mutations all rejected; transport tampering; scope/geometry cross-use), **determinism** (byte-identical
  replay; exactly 78 hashes), **failure retention** (failed attempts retained, never resumed or replaced), **claims/receipts/capture gates**.

| Run | Result |
|---|---|
| Focused (components 81 + verification 112 + finalization 75 + accepted kernel 92) | **360 passed**, 0 skipped, 32.63 s |
| **Full offline regression** (`final3/regression.txt`) | **1,836 passed, 2 failed, 2 skipped in 160.01 s** — *not green* |

The two failures are the inherited E001 snapshot tests `test_e001_historical.py::test_original_sources_and_e001_preserved` and
`test_e001_tooling.py::test_accepted_sources_and_sealed_evidence_unchanged` (both `.gitignore` size 367 vs 351), documented baseline
exceptions for earlier engineering milestones and **not G1 approval**; the two skips are the Windows symlink-privilege tests (`WinError 1314`).
Earlier figures (1,766 for the first implementation, 1,821 after the first review) are superseded; baseline 1,568 + 268 new tests = 1,836. No new failures. Runtime: bundled CPython 3.12.14, pytest 9.1.1.

## 9. Resource projections (not measurements)

Measured: analog-scale microbenchmarks (`bench/`) — A1 verifier 47–59 µs and producer 101–114 µs per sample at N/n = 143; A3 scan 0.45 µs per rank;
Feistel 5.9 µs; N2 0.94 µs; per-row verification 1.15 µs; producer-side transport replay about 11 µs per row. Bounded full runs above are measured.
**Projections** extrapolated from those rates to the frozen geometry (never executed at scale): verifier CPU about **40–50 minutes** single-threaded
plus I/O (A1 ≈ 24–30 min, Feistel ≈ 6 min, rows ≈ 3.5 min); producer-side capture replay about 33 minutes; evidence about **26 GB** in about
43,995 chunk files; memory about 0.85 GB (dominated by the retained-history set, 841 MB measured at bounded scale). A pure-Python independent SHA-256
(§3 B) would add roughly two hours (projection). No production-density benchmark was run.

## 10. Unimplemented or unauthenticated dependencies and remaining G1 blockers

* No approved external verifier, trust root, credential, signature scheme, beacon client (BLS, RFC 9380), timestamp, history-checkpoint, archive,
  retention, disclosure or Director-authorization service; all fail closed. No production writer exists.
* **SHA-256 and shared libraries are not independent** (§3 B). Final audit policy is unresolved (Decision 4).
* Seed record/commitment layouts are proposed; the preregistration-bundle layout is proposed; started-entry hash and the seeded configuration digest are not yet written into `environment.json` (kernel writer disabled).
* Verifier mismatch policy (§3 A) and private logging of producer refinements are not implemented.
* The positive capture path is unit-only; the full-geometry stream loop is exercised only at the bounded geometry.
* Statistics are plaintext in an operator-readable directory; blinding is the normal-path boundary only. OS power-loss durability, the production
  runtime image and the R9 schemas other than the Director/algorithmic records (restore-verification, plan/evidence envelopes, human audit,
  G1/QA2/G2 decisions) remain unqualified or proposed.
* For G1 (not provided here): production-scale independent verification on the approved runtime/hardware, production-density producer and blinding
  qualification, independent SHA-256 qualification, closure of the strict E001 numerical/runtime disposition, the two inherited snapshot failures and
  the symlink-privilege skips; then separately authorized QA2, G2 smoke, release/freeze, commitments/beacon procedure and exact-attempt execution approval.

No candidate-selection science, frozen geometry, sampling procedure, threshold or control transformation changed. Nothing is committed, staged, pushed
or merged.
