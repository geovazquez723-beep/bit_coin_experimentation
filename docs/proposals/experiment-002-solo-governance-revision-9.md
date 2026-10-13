# Experiment 002 proposal revision 9 — solo-research governance amendment

**PROPOSED ONLY. Not adopted. No gate passed and no execution authorized.**
Prepared under the supplied Review 042 assignment for Director review at
Architecture Review 042. The assignment's requested handoff filename uses 041;
this document does not infer a missing Review 041 disposition or renumber history.

## 1. Authority, identities and interpretation

HASHLAB has one human operator with AI-assisted engineering, not an institution,
independent engineering team, review board or dedicated external custodian.
The human may act as Research Director. AI Architect/Engineer functions are
advisory methodology/implementation roles, not independent human authentication.
This proposal changes organizational assurance requirements only. It does not
retroactively change Revision 8, accepted code, receipts, E001 or gate outcomes.

Accepted engineering baseline: `c26dc40975bc213f67773d6c5fe1709a4843ea76`.
Accepted scientific identity remains:

```text
proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1
```

Proposed active protocol identity, only after explicit future adoption:

```text
proposal-revision-9|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1
```

Proposed governance identity: `hashlab-exp002-solo-governance-v1`.
Scientific-baseline identity must additionally retain the complete Revision 8
identity above. Secondary identity remains
`hashlab-exp002-secondary-statistics-proposal-v2`.
No source/config/schema currently binds the proposed identities. Revision 8
requirements remain active until adoption AND separately accepted migration;
drafting or approval alone never authorizes implementation or execution.

### Normative source register

All paths are repository-relative. Section references below are exact normative
locations; they incorporate the complete applicable clauses, not just the
descriptive summaries in this amendment. **Every scientific clause is retained**;
only the explicitly listed organizational substitutions in section 4 are proposed.
Unlisted requirements remain unchanged. Historical/proposed status in a source
does not become an achieved gate here.

| Ref | Authoritative input and precedence |
|---|---|
| R8 | `docs/proposals/experiment-002-research-design.md`, revision 8, header identity and §§3.1–3.14, §5 decisions, §6 documentation gate. §4 is explicitly a non-executable outline, not a config or an additional authority. |
| ADD | `docs/reviews/experiment-002-protocol-readiness-addendum.md`, §§7–8 supersede earlier coverage/FWER/QA2 statements; §9 approved A2 encoding. |
| SEED | `docs/proposals/experiment-002-a1-a3-seed-encoding-proposal.md`, “Exact ordered labels,” “Byte and integer contract,” all KATs, approved Review 027. |
| SEC | `docs/proposals/experiment-002-secondary-statistics-proposal.md`, approved v2 header, “Proposed exploratory family and interpretation,” §§1–5 and QA2 relationship. Review 032 approval/status supersedes historical proposal-era text. |
| REC | `docs/reviews/architecture-review-008-operational-recovery.md`, “Independent verifier: proposed deterministic audit format” and workload table. Format/seed provenance remain freeze decisions; recovery commands are not authorized by this amendment. |
| E1–E4 | Reviews 027 closeout, 028 statistics, 029 foundation with continuations, 032 secondary, 033 foundation with Review 034 hardening continuation; accepted source contracts in `exp002.py`, `vitter.py`, `statistics/exp002.py`, `statistics/exp002_secondary.py`, `exp002_foundation.py`, `exp002_governance.py`, `exp002_journal.py`, `exp002_provenance.py`. |
| E5 | Reviews 036 Phase A and 038 bounded Phase B, `e001_contract.json`, `e001_reconstruction.py`, `e001_phase_b.py`, `e001_phase_b_verification.py`, `e001_verify/core.py`; accepted parent pins unchanged. |
| HIST | `docs/proposals/e001-reconstruction-phase-b-proposal.md`, especially “Review 038 sequencing clarification — proposal v2”; numerical memo `architecture-review-037-numerical-reproduction-decision.md`; discrepancy ledger `architecture-review-036-e001-numerical-differences.json`. |
| READY | Preserved `architecture-review-039-external-readiness.md` and `architecture-review-040-e6-preparation.md`; concrete missing/PARTIAL/BLOCKED implementation and provenance findings, not new scientific requirements. |
| CH | `docs/research-charter.md`, “Governance” and “Principles.” Role labels do not create external scientific independence. R8's experiment-specific no-economic-label rules govern E002. |

Source identities and working-tree preservation are pinned in the separate
handoff. Formal registry `docs/experiments/002-run-registry.md` and executable
E002 configuration are specified future artifacts, not established current
records. R8 §4's `docs/experiment-002.md` is a placeholder in that outline.
Their absence is an existing operational gap, not license to fabricate them.
Review 032 records that its user instruction supplies Review 031 authorization;
no separate local Review 031 file is asserted. All baseline scientific/encoding
identities needed for this proposal are established from the sources above.

## 2. Frozen scientific-invariant register

Each row is a preservation obligation, not evidence that implementation or
execution is complete. If a governance change would alter one, stop and seek a
separate scientific amendment; do not resolve it by operator discretion.

| ID | Exact source clauses retained | Preserved requirement / separation of concerns |
|---|---|---|
| I01 | R8 §§3.1.1–3.1.2, 3.4, 3.14; ADD §§1,2,7.1–7.2 | Engine sha256, strict digest <2^248, p0=1/256, relative margin ±2%. Observed f is descriptive; all difference claims concern strict independent-Bernoulli model null. A1/A3 margin estimands are fixed finite-population fractions, A2 evaluated-input model mean. No crypto/economic advantage claim. |
| I02 | R8 §3.2 “A1,” §§3.2.4–3.2.5; SEED complete contract | Eight-byte BE integers 2^20≤x<2^32, N=4293918720. SRS without replacement30M via Vitter D, exact hypergeometric15M/15M split. Exact RNG law, draw order and numerical-abort safeguards unchanged; no Algorithm S substitution as an optimization. |
| I03 | R8 §3.2 “A2” and “A2 deterministic encoding v1,” all KATs | 3000 uniform76-byte prefixes, each nonce0..9999 ascending, candidate prefix||LE32(n), length80. D indices0..1499, V1500..2999. Pairwise prefix distinctness blocks on collision without redraw. All domain labels, canonical decimal derivation, BE digest extraction, LE64 key, 29-byte messages and BLAKE2b parameters remain exact. No additional stage randomization. |
| I04 | R8 §3.2 “A3,” §§3.2.4–3.2.5 | Eight-byte BE, HW≤6, high32 nonzero, C3=82128984; U3=C3\X3, expected qualified U3=82068263. Weight/colex ranks, exclusion-aware Knuth S and hypergeometric15M/15M split. X3 must be derived from all7000000 historical occurrences, not assumed. |
| I05 | R8 §3.2 “Null and positive controls,” §§3.3,3.7 | N1 keyed64-bit six-round BLAKE2b Feistel, reject C1/C3/E001; first15M accepted D, next15M V, inverse-index audit. N2 keyed BLAKE2b80-byte stream,15M/stage, deterministic A2 membership rejection,1500 pseudo-clusters of10000/stage. Preserve all PRP/RNG assumptions. |
| I06 | R8 same control clauses, §§3.7,3.12 | P1+25%/200000, P2+2%/15M, P2−2%/15M, same N1 permutation with indices≥2^63, same rejection rules, biased engine. No new positive-control population or per-prefix QA2 biased engine. No replacement by synthetic counts. |
| I07 | R8 §§3.3,3.6,3.12; REC workload correction | A1/A2/A3 each15M D+15M V (90M), N1/N2 each30M (60M), P30.2M; total180.2M candidate hashes/240.2M compression blocks. Audit work/integrity hashes separate. QA2≤4200 additional evaluations, actual block accounting required. No n/power/allocation reductions. |
| I08 | R8 §3.3 entire pairwise table and gate rule | Every M/E/D/P/C guarantee retained with its type. M analog tests; E re-enumeration A1=0, X3=60721 and digest `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`; all D checks cover every relevant element with rejected hits recorded. P N2 uniqueness bound≈2^-591 reported as not verified, C assumptions never exact guarantees. |
| I09 | SEED all labels/KATs; R8 §3.2 A2 byte contract | `hashlab-seed-v1`, all four ordered A1/A3 selection/allocation label triples, integer validation, separate RNG instances, A2 confirmatory/QA2/KAT domains preserved. Distinct messages do not prove unequal seeds/independent RNG streams. No live master/round selection here. |
| I10 | R8 §§3.1,3.4–3.5; E2 “API contracts” | Exact two-sided D tests, Holm A1–A3 alpha.005; direction integer compare256k_D versus n_D, descriptive only. One-sided V only for D flags, Holm across flagged family at.005; V always collected. Empty family/ties/boundaries unchanged, NONE/UNREP/REP retained. |
| I11 | R8 §§3.2.5,3.4–3.5; ADD §§7–8; E2 API | D+V pooled regardless of discovery. CP decision confidence1−2·.005/3; frozen W_LO115839,W_HI118519,B_LO113851,B_HI120546. Strict endpoints. A1/A3 design-based decision guarantees retain finite-population estimands; no hash Bernoulli model substituted. |
| I12 | R8 A2 “Margin analysis,” ADD §§7.1,8.1; E2 API | Hull of pooled CP and t of3000 equal-size cluster ratios,2999df,t=2.9376. WITHIN requires both inside(.98,1.02), BEYOND both same outside side; equality UNDET. No universal heterogeneous CP coverage claim or confirmatory prefix-population bound; H-A2 population statement remains conditional/nonconfirmatory. |
| I13 | R8 §3.4 complete nine-cell table, §§3.9,3.13–3.14 | Preserve every label and UNREP note, all descriptive ratios/components. Any REP→artifact investigation and separately authorized002-R; discordance no scientific reading; no topping up/inference from subgroup mining. Same H_S decision meanings, no overreach. |
| I14 | R8 §3.7 and G3 §3.13; E2 control API | P1 one-sided p<.001 detected; at least one P2 detected, neither P2 WITHIN. Null D two-sided.005/3 and V one-sided.005, replicated null blocks F4; D-only diagnostic. N2 A2 analysis path, P2 CP15M regions unchanged. Organizational approval cannot override a failed statistical gate. |
| I15 | SEC entire v2 specification, E3 accepted references | Fixed36 exploratory slots:30 digest distribution,4 A2/N2 dispersion,2 A3 grouped-weight tests; alpha.01 strict adjusted_p<.01, full Holm family with not-testable correction p=1 and explicit missing raw p. A3 fixed G1 weights1–4(631413),G2w5(7407537),G3w6(74029313),2df. Raw six-weight accounting, no data-dependent merge/removal. Exploratory never changes confirmatory/control/operational decisions. |
| I16 | SEC §§1–5; R8 §3.7.1; E2/E3 references | Preserve chi-square df/qualification rules, exact aggregation, dispersion1499df, log/underflow disclosure, missing/invalid distinctions, all pinned numerical vectors and independent reference criteria. No tolerance-based discrete label pass; unresolved cutoff uncertainty fails closed. |
| I17 | R8 §3.7.1 complete specification; ADD §8.3 | QA2 exact full-geometry synthetic arrays, all9cells/contradictions/variance/threshold-adjacent/degenerate/tamper cases; counts/ordering/directions/labels exact, p/ratio≤1e-10 plus high-precision discrete references. Actual production path2048+independent2048+≤104 probes,≤4200, no seed search or probabilistic pass. No fixture-only QA2 claim. |
| I18 | R8 §§3.8–3.8.1,3.13; SEED | Fixed design before unknown beacon value/seed; C_pre then ≥24h timestamp lead to fixed R*, exact S4 bytes and uint64 handling, C_seed/full binding, same-round-only transport fallback, indefinite wait/permanent loss unexecuted. Proposed change concerns witness mechanism, never round/chain/derivation or anti-shopping objective. |
| I19 | R8 §3.8 “Blinding,” failure table; Review027 abort policy | No interim looks, top-ups, early stopping, displayed primary progress or failed F1–F3 counts. Automated counter digest comparison; F4 post-amendment full disclosure exception as specified. Numerical aborts disclosed, no seed replacement or retry-until-success. |
| I20 | R8 §3.8 registry/failure/limits, §3.13 G3/G4 | Gap-free immutable started/result S/Q/A history, all attempts including partials disclosed. Same seed/fingerprint rules, F3 root cause, F4 investigation/amendment, valid attempt final, no pooling/choosing, >3 F1–F3 escalation. Director written approvals cannot authorize a prohibited scientific retry. |
| I21 | R8 §§3.8.2–3.9; REC audit format; HIST v2 | Exact source/config/environment/evidence identities, read-only independent algorithmic reconstruction and count/statistics verification; all successes plus seeded1% other-input audit retained. Distinguish sampled diagnostics from all-outcome completeness; audit format/seed provenance still need approval. Full rehash stronger assurance remains separately authorized. |
| I22 | R8 §3.13 G1 last bullet; E5/HIST numerical memo | Sealed E001 untouched. Correct historical exclusion set/count/digest and exact historical reproduction obligation remain;86 floating discrepancies not rounded/tolerance-waived. Original-runtime provenance unavailable is a blocker for the corresponding exact claim, not an organizational inconvenience. |
| I23 | R8 §§3.8.3,3.13,CH principles | Sealed originals, file inventory and source/environment retention; off-machine byte copies and restore verification; distinct code readiness, scientific qualification, authorization, execution, verification and interpretation. Custodian organizational independence may change, integrity obligations do not. |
| I24 | R8 §§3.10–3.11 in full; E3/E4 evidence contracts | Preserve manifest-v1 sealing compatibility; preregistration config/resolved-config/plan/seed commitment/E audit/release bindings; registry; every successful candidate/stage; audit-seed provenance; overlap results, all 3000 A2 prefixes and all 3000 A2/N2 cluster counts; read-only verification; deterministic analysis-list ordering; committed off-machine archive hash inventory; Python/OpenSSL environment; exact E001 compatibility. No economic screen; descriptive exploratory throughput only. |

The complete R8 classification matrix is retained by reference, with no renamed
cell or new rule. The register is an index into frozen normative clauses rather
than a replacement or an abbreviated executable specification.

## 3. Assurance levels and permissible claims

| Level | Required properties | Permissible claim and limitation |
|---|---|---|
| 1 — Solo Reproducibility | Fixed approved protocol; exact algorithmic candidate/evidence/count reconstruction at the stated scope; pinned source/runtime/config; complete local accounting and failure reporting; separately implemented algorithms/reference calculations, adversarial tests, read-only verification. | “Solo-operated, algorithmically recomputable at the disclosed scope; AI-assisted; no independent human authentication.” Local pins do not prove chronology, honesty, complete capture or absence of suppressed attempts. Incompatible with R9's Level2 target execution gate. |
| 2 — Externally Verifiable Solo Research | All Level1 requirements plus authenticated external timestamped preregistration with required lead time, externally retained evidence/history digests, disclosed reproducible verification instructions and actual third-party access to inspect/reproduce published artifacts (or explicitly disclosed access constraints that block this claim). Off-machine restore checked against prior pins. | **Proposed E002 target.** “Solo research with externally timestamped commitments and externally retained digests, algorithmically verified at [scope].” Service guarantees must be named/qualified in actual evidence. No claim of independent human scientific audit, independent custody of operator-controlled backups, honest execution or proof of unrecorded-event absence. |
| 3 — Independently Audited Research | All Level2 plus genuinely separate appointed human reviewers/custodians authenticating named scientific/execution/evidence claims, disclosed independence/conflicts, signed reports bound to exact artifacts. | “Independently audited for [specified claims].” Not automatic coverage of all science or honesty. Optional enhancement unless a particular scientific/regulatory requirement actually requires it; its absence cannot be concealed. |

Levels are not scientifically equivalent. L1/L2 may never be described as
independently human-audited research. Claim scope is per artifact/check; a
timestamp service is not a scientific reviewer. Separate algorithms, separate AI
sessions, independent human review and independent organizational custody are
four different attributes and must be reported separately. Existing same-author
Codex verifier supplies algorithm/import separation only; no ownership fiction.

## 4. Revision 8 → proposed Revision 9 requirement matrix

Categories: S scientific, E engineering, P procedural, O organizational. Treatments:
R retain unchanged; S9 replace with defined solo equivalent below; O3 optional
Level3 enhancement; U unresolved prerequisite. Code support: C1 sampler/encoding,
C2 count statistics, C3 plan/accounting, C4 governance/journal/provenance, C5 bounded
historical adapter/verifier. “Partial” never means operational compliance.
All source requirements in the cited clause remain unless this row explicitly
substitutes the organizational portion. Evidence column defines future proof,
not current evidence. Loss column states the assurance not supplied by substitution.

| ID / exact R8 location and requirement | Purpose / class | Treatment and safeguard retained | Assurance lost | Necessary compliance evidence | Accepted code support / later change |
|---|---|---|---|---|---|
| M01 CH Governance; R8 header/§3.13: Architect design/implementation review, Director approves execution | Prevent implicit authorization; P/O | S9: human Director may approve freeze and acceptance, AI advisory review disclosed; explicit separate decisions for each action. Scientific criteria I01–I24 retained. | Separate human decision-maker/check on operator bias. | Scope/revision/source/action-bound written approvals and review findings. | C4 approval interfaces partial; new role/receipt policy required, not a fabricated external proof. |
| M02 G1 §3.13 bullet1: exact sampler checks§3.2.4 | Valid sampling; S/E | R | None | Small-analog exact-law/inclusion/partition tests, numeric-abort tests and accepted review. | C1/tests support; production readiness/performance still unresolved. |
| M03 G1 bullet2: unranking bijection | Correct A3 universe; S/E | R | None | Exhaustive analogs, full-domain reference checks under approved scope. | C1/tests support; actual exclusions still unresolved. |
| M04 G1 bullet3 and§3.3: every M property tested | Disjointness/uniqueness; S/E | R | None | Complete guarantee table→test/proof mapping. | Partial C1/C3; actual control M paths missing. |
| M05 G1 bullet4: margin/hull2999df/reference values; independent cluster recomputation | Correct inference; S/E | R algorithmic independent reference, O3 human review authentication | Human review additional, not arithmetic independence waived. | C2/C3 exact pinned references, adversarial boundary tests, declared authorship/shared deps. | Component support; integrated verifier missing. |
| M06 G1 bullet5: negative-lift tested | Both directions calibrated; S/E | R | None | Actual P2− engine/provider integration test plus count references. | C2 count decision verified; production negative engine missing. |
| M07 G1 bullet6: blind progress/failure | Avoid optional stopping; S/E | R | None | Actual stdout/stderr/failure/report tests with no primary disclosure, counter-digest tests. | Partial C4; complete blinded path missing. |
| M08 G1 bullet7: all existing tests pass | Regression correctness; E | R | None | Qualified runtime/full regression evidence, disclosed environment-specific skips and unresolved platform qualification. | Historical889pass/2skip; no new run or complete G1. |
| M09 G1 bullet8: E001 evidence verifies and re-analyses identically | Historical correctness; S/E | U retain strict obligation; human appointment O3, no numerical waiver | No loss allowed to exact requirement. | Eleven-file pins; exact original-runtime/source analysis comparison or separately reviewed disposition outside this governance-only change. | C5 bounded support;86 discrepancies/original provenance unresolved. |
| M10 §3.3 E: full E001 reconstruction0A1/60721A3/digest | Correct fresh A3 population; S/E | R full scope/exact algorithmic comparison; O3 human signature | Independent human authentication absent at L2. | Complete7M ordered accounting, exact set/digest/ranks, independent algorithmic report and Director acceptance under versioned solo policy. | C5 caps4096; full provider/audit absent; new final policy/schema required. |
| M11 §3.3 D: inverse N1/P E001, N2 membership, A2 prefix check | Prevent overlaps; S/E | R | None | Every checked element/rejection/hit, complete audit; M proofs/tests; P/C disclosures unchanged. | A2 C1 support; actual controls/audits missing. |
| M12 §3.7.1 zero-hash full geometry/all-cell/edge/dispersion fixtures | Statistical correctness independent of chance; S/E | R | None | Frozen arrays/references, every required case/df/intermediate, strict label match. | C2/C3 support; not QA2 pass. |
| M13 §3.7.1 independent recomputation/no HASHLAB inference imports,≤1e-10 and exact cutoffs | Common-mode error; S/E/O | R separate implementation/reference/import isolation, S9 solo-operated verification; O3 independent human author/attestor | Same-author/session/tool common-mode/human oversight risk disclosed. | Verifier code/env pins, reference provenance, isolation tests, highprecision criticals, discrepancies. | Reference modules partial; full verifier absent. Later authorship/assurance schema. |
| M14 §3.7.1 production-path2048+2048+≤104≤4200 | End-to-end QA2; S/E | R, including actual different implementation digest checks | None to budget/path coverage; no independent human authentication. | Q-bound config/plan/env/evidence, production entry-point coverage, enforced eval ledger. | Integrated path missing; component fixtures cannot satisfy. |
| M15 §3.7.1 tamper/manifest rewrite/ext pin/all pass, no random retries | Authenticity and deterministic qualification; E/P | R; S9 external retained timestamp/digest instead of institutional witness | Service only authenticates digest/time, not honest capture. | Copy-only tamper tests against prior external pin; retained all Q reports. | C4 local support; external service verifier missing. |
| M16 §3.7.1 G1→QA2→C_pre;§3.13 G2 release candidate | Bind qualification to actual code; P/E | R | None | Separate approval, qualified exact release candidate and amended requalification records. | Missing integrated QA2/release bundle. |
| M17 S1 freeze: G1/QA2, taggedcode/config/seedless fingerprint | Prevent outcome-driven design; S/P | R; Director written freeze approval | No separate institutional approver. | Exact approved identities, clean release source/environment, source/config/plan/QA2 pins. | C3/C4 partial; R9 binding new schema needed. |
| M18 S2 C_pre complete preregistration contents | Anti-cherry-picking; S/P | R all code/tag/config/seedless/X3/QA2/beacon/derivation/history pins | None | Immutable C_pre+artifact inventory. | C4 reference binding partial; operational preregistration absent. |
| M19 S3 and§3.8.1: independent witness acknowledgement≥24h before R*, retained offmachine | Prove prereveal chronology; P/O | S9 authenticated external timestamp on exact full C_pre plus SHA256 of preregistration bundle, retained offmachine,≥24h before scheduled same R*. No L1 local substitute for target L2. | Human witness observation/identity/custody; timestamp proves only submitted bytes/time per service. | Verifiable timestamp receipt/trust policy and timing arithmetic before reveal; no chosen service/round now. | C4 expects witness-timing verified proof; new explicitly typed timestamp proof and policy required. |
| M20 S4/S5 and§3.8.1: beacon chain/signature/round/exact seed/full plan | Prevent seed selection/tampering; S/E/P | R complete bytes/client/chain tuple/uint64 rules | No reduction to beacon cryptographic assurance; independent human investigation optional, defect remains blocking. | Pinned qualified client, raw response/signature/round, deterministic recomputation and C_seed. | C4 interfaces only; real beacon verifier missing. |
| M21 §3.8.1 deadline missed, same-round fallback/outage/disagreement | No opportunistic replacement; S/P | R; S9 Director documented investigation instead of institutional reviewer | Self-supervised investigation. | Rejected/abandoned commitment log, outage/disagreement evidence; new experiment separately approved if permanent loss. | No concrete operational client; no retry/round substitution authorized. |
| M22 §3.8 registry S/Q beforeC_pre,AafterC_seed,gapfree started/result commits | All attempts accountable; P/E | R, add external checkpoints per§6 | Local/private events could be suppressed before anchoring. | Git+local chained entries, external head receipts, evidence/entry reconciliation. | C4 local chain support; formal Gitregistry integration/external append policy missing. |
| M23 §3.8 started commit→environment hash;G4 all evidence dirs/all A entries | Bind provenance/completeness; E/P | R | Cannot detect unknown private dirs/events with operator-only enumeration. | Entry hash in actual evidence, complete disclosed-directory census and externally pinned head. | C3/C4 partial; integration missing. |
| M24 F1/F2 table same seed/fingerprint; F1 code amendment review | Legitimate recovery without new samples; S/P/O | R constraints; S9 every material retry needs explicit Director approval and advisory diff review, no automatic direct rerun | Separate human amendment reviewer absent; stricter approval doesn't change scientific eligibility. | Root cause/class, prior evidence, exact scope/code/fingerprint approval, external checkpoint. | C4 requires externally verified retry review; new declaredDirector-vs-external policy types needed. |
| M25 F3 root cause, digest checks, F1 defect path | Integrity cannot be bypassed; S/P | R; S9 Director/advisory review | Independent human forensic check. | Cause/remediation evidence and automatic unaffected-block digest agreement without revealing counts. | C4 partial; actual failure lifecycle integration missing. |
| M26 F4/Valid and>3F1–F3 limits§3.8;Review027 numericalabort | Prevent statistical selection; S/P/O | R no same-code F4/valid rerun, no pooling/new seed; >3 escalation becomes explicit Director documented exceptional review, never waiver of scientific rules | External challenge of escalation reason. | All original failures/statistics per F4 exception, defect/amendment justification, post-amendment qualifier; capledger. | C4 local rejection support; R9 policy migration required. |
| M27 §3.8 blinding/no failed primary counts/counter digest | Avoid result-informed decisions; S/E | R | Operator may access raw files outside tooling; disclose. | Actual output/error/read access controls and automatic comparisons; log inadvertent exposure before deciding validity. | Full path not implemented/qualified. |
| M28 §3.8.2 appoint separate reviewer, read-only offmachine,no inference imports | Independent verification; S/E/O | S9 mandatory separately implemented read-only verification from restored copy; O3 independently appointed human/authentication | Organizational independence absent; same-AI common-mode risk. | Verifier/references/import/source/environment pins and declared ownership; restore hashes; exact recomputation report. | C2/C5 algorithms partial; E002 full verifier missing. |
| M29 §3.8.2 check1 manifest hash/size/schema/inventory/strict parsing/ext anchor | Authentic evidence bytes; E/P | R, S9 timestamped external digest as authenticity anchor | Capture honesty/independent custody not proven. | External pin verified; all files/tamper/parser checks and retained original seal. | C3/C4 partial; real anchor and integrated contracts missing. |
| M30 §3.8.2 check2 commitments/seed/registry/amendments/eligibility | Coherent authorization chain; E/P | R scientific checks, S9 explicit Director approvals separated from external timestamp claims | Human self-authorization not external audit. | Exact protocol/source/plan/receipt subjects, complete chronology and separate authorization. | C4 strictR8 boundary cannot be relabeled; new evaluator/types later. |
| M31 §3.8.2 checks3–4 every total/geometry/success/statistic/label/control/failure | Correct reconstruction/results; S/E | R full mandatory checking; independent algorithms feasible and required, O3 human attestation | Human validation absent, shared primitive risks. | Exact reconstructed records/cluster moments/decisions and highprecision boundary failclosed evidence. | C2/C3/C5 components; E002 candidate verifier/integration missing. |
| M32 §3.8.2 check5 signed/independentlywitnessed report | Bind verifier findings; P/O | S9 signed or digest-pinned operator-declared verification report, external timestamp/retention, explicit no independent human audit | Independent reviewer signature/attestation. | Report identity/pins/scope/limitations/ownership plus external receipt; self-signature labeled self-signature. | C4 no real author/signature verifier; new report schema later. |
| M33 §3.9 allsuccess+seeded1% non-success audit;REC exact proposed format | Detect erroneous/omitted records; S/E/P | R workloads/independent algorithms/different SHA implementation; S9 solo verifier operation, nondiscretionary externally anchored audit seed procedure remains unresolved | Operator could manipulate pre-publication evidence or code; sampled audit no full completeness proof. | Approved format/vectors/seed provenance and actual audit report; freeze scope minimal vs separatelyauthorizedfull. | Missing E002 audit reader/sampler/verifier; no audit seed chosen. |
| M34 §3.9 optionalsecondmachine/full rerun;002-R anyREP | Stronger check/scientific replication; S/P/O | O3 external operator for audit optional; R genuine independent scientific replication before stronger deviation claim | Cannot call same person/same AI replay independent scientific replication. | Separately approved002-R new seed/machine/hash/source review; no execution here. | No runner; not a gate waived by solo wording. |
| M35 §3.8.3 archive steps1–2 original11files/bundle/env/outerinventory | Preserve immutable history; E/P | R | None | Exact originalhashes/size/inventory/tag/commit, separate archiveinventory and available dependencies. | Local C4/C5 checks support; archiveartifact absent. |
| M36 §3.8.3 steps3–4 twoindependent destinations/othercustodian/externalwitness | Independent custody/resilience; P/O | S9 two offmachine copies in distinct failure domains, at least one offline or retention/version protected; operator may own both. External retained digests mandatoryL2, O3 separatecustodian | Backups under sameoperator/account are not independent custody; corruption/rewrite of both possible. | Destination/version/retention logs, independent-tool perfile verification against prior external pins at both destinations. | No transfer/restoration evidence; external custody code absent. |
| M37 §3.8.3 step5 annualrestore/priorinventories | Recovery reliability; E/P | R separate-directory restore, annualchecks, preserve failures/source untouched; solo operator allowed | No secondhuman restore attestation. | Restore inventory/tool/env/results, priorreceipt validation. | Missing operational artifact; no transfer now. |
| M38 §3.13 G2 smoke/throughput/E-D audits/cleanrelease/QA2/S1–S5/writtenapproval | Actual execution readiness; S/E/P | R all checks, S9 Director approval and approvedtimestamp mechanism | Institutional release audit absent. | Versioned G1/QA2/G2 decision with component states and exact source/environment/plan. | No complete path/G1/QA2/G2, eligibility alwaysexecutiondisabled. |
| M39 §3.13 G3/G4 all outcomes and§3.14 risks | Keep science separate from permission/publicity; S/P | R classifications/failures, S9 Director final interpretation with advisory review, O3 independent human audit | Independent publication reviewer absent. | Final validattempt evidence, verification limitations/all attempts, explicit publication approval. | C2 rulesverified; operational reporting missing. |
| M40 E5 HIST v2 fourstates/final external acceptance record;READY/E6 ownership | Correct X3 plus authenticated audit status; E/P/O | S9 replace separatehuman finalauthority with explicit Director decision after algorithmic checks and externalouteranchor. Preserve fourstates as producer complete / algorithmically verified / externally anchored / Director accepted; O3 separatelyaudited. | External scientific acceptance/custody authority absent. | Newversioned solo auditrecord exact7M predicates/report/manifest/anchor/approval; never set fixturehistoricaltrue. | C5 fixturefinal permanentlyfalse; full provider/finalvalidator absent; new schemas/policy mandatory. |
| M41 READY/E6 platform/security/disk/RSS/runtime | Feasible trustworthy implementation; E/P | R real qualification, solo operator may perform; disclose absence of external human review | Independent resource/security attestation absent. | Actual Windows/SQLite/nativeRSS/disk reservation/durability evidence and limitations, protectedparent/no raceassumptions. | Partial tests; twoOSsymlinkskips, whole-process RSS/durability unresolved. |
| M42 R8§5 decisions D1–D15,ADD§8 blockers;REC audit format | No invented approvals | U preserve all unresolved technical/scientific/freezedecisions, alter only namedownership mechanisms | No retroactive pass | Explicit disposition per item; numerical/historical/QA2/encoding requirements unchanged. | Partial contracts do not resolve decisions. |
| M43 R8§3.10 entire evidence additions and§3.11 | Reconstructible evidence and interpretation; S/E/P | R all evidence content, ordering, read-only behavior, original sealing compatibility and no economic screen; S9 custody/approval only as M32/M36 | No additional loss beyond disclosed custody/attestation substitutions. | Full canonical artifact inventory, exact source/config/plan/seed/registry/environment binding, all prefix/cluster/success records, audit-seed provenance, archive hash list. | C3/C4 partial; actual integrated evidence writer/reader and registry binding missing. |

This matrix maps every G1 bullet, QA2 fixture/integration/verification/pass clause,
G2 constituent, commitment/registry/failure/custody/verification clause and the
later E5 acceptance boundary. The original scientific clauses remain normative
in full. No R8 failed/blocked gate or missing artifact is converted to a pass.

For completeness, accepted E4 `REQUIRED_ELIGIBILITY` kinds are
`e001-reconstruction`, `overlap-audits`, `g1`, `qa2-statistical`, `qa2-hashing`,
`g2`, `precommitment`, `witness-timing`, `beacon-verification`, `seed-record`,
`registry-history`, `release-approval`, `director-authorization`.
They map respectively to M10, M11, M02–M09, M12–M13, M14–M15, M38, M18,
M19, M20–M21, M20, M22–M23, M17/M38, M01/M38. E4 `retry-review` maps to
M24–M26. All are mandatory in existing R8 code; none is removed, weakened or
made to pass in this task. Future R9 migration must expressly distinguish
algorithmic verification, Director declaration and externally authenticated
timestamp/history evidence rather than reusing a proof kind with a new meaning.

## 5. Solo G1 / QA2 / G2 and decision states

Each gate record must include active protocol/governance/scientific-baseline
identities; source/config/environment/plan pins; checks and exact evidence;
algorithmic verification scope; external timestamp/custody status; unresolved
items; Director decision. No bool, local sentinel or advisory recommendation
substitutes for the record or authorizes dispatch.

**PASS:** all mandatory predicates for the stated gate and active revision are
supported by exact evidence. **CONDITIONAL:** only explicitly optional assurance
enhancements remain, with conditions and claim limits; cannot substitute for a
required scientific/engineering/external-time predicate. **BLOCKED:** required
evidence, implementation, approval or external service unavailable/unresolved.
**FAIL:** observed mismatch/invalid qualification/control/integrity/forbidden
retry. Preserve failures; root-cause remediation/review never erases them.
For Level2-target execution, CONDITIONAL/BLOCKED/FAIL never enables execution.

- **G1:** retain all R8§3.13 implementation predicates plus complete E/D/M audit
  capability, controls, blinded failure handling, evidence/registry integration,
  exact historical compatibility/exclusion and runtime findings. Director may
  accept engineering with AI advisory review under the adopted policy, but cannot
  waive correctness or turn bounded fixtures into complete historical results.
- **QA2:** requires separate written approval and G1, then exact R8§3.7.1 production
  path and budget on the identified release candidate. Independent algorithms,
  references, digest implementation and import isolation required; independent
  human authentication optional Level3. No parallel miniature harness, power
  simulation, fixture-only claim or discretionary retest. Preserve all Q entries.
- **G2:** requires G1 PASS, QA2 PASS, approved smoke/throughput evidence, complete
  plan/audits, clean frozen release/source/environment, validated Level2 timestamp and
  ≥24h prereveal lead, fixed beacon policy and S1–S5 evidence, retained/restorable
  evidence scheme, complete attempt history, approved audit seed/format policy
  and explicit Director execution approval. Missing Level2 services blocks; no
  automatic fallback to Level1. No evaluator returns an execution capability.

Code readiness, historical reconstruction, statistical qualification, external
anchoring, human approval, execution, post-execution verification and publication
remain separately recorded. None is inferred from another. Today's component
acceptances do not constitute G1/QA2/G2. G3 and G4 scientific outcomes unchanged.

## 6. Practical authorization, commitments, custody and retries

### Director approvals

Each material action needs its own written approval naming actor, permitted
action, exact scope/limits, protocol/governance revision, source identity,
input/evidence/config/plan references, prerequisites and prohibitions. A single
record may enumerate several actions explicitly; vague “ready” is insufficient.
Required actions: protocol adoption/freeze; implementation migration; QA2;
full E001 enumeration; release identity creation; commitment publication;
seed/beacon procedure; confirmatory execution; any retry/restart; final
interpretation/publication. This proposal grants none of them. AI may prepare,
review or recommend but never infer approval or execute merely from gate PASS.

### Commitment mechanisms and sequence

| Mechanism | Actual assurance | Insufficient claim |
|---|---|---|
| Git commit and retained bundle | Content-addressed source/history identity, reproducible byte binding | A sole-controlled repository proves neither public time nor honest capture; rewritten private history can be suppressed. |
| Signed Git tag/file (optional if practical) | A verifiable authorized-key assertion over exact bytes, subject to key policy | Selfsignature is not independent science/time/custody. No key/tag selected here. |
| Authenticated third-party timestamp (required Level2) | Specific digest existed by service-attested time under disclosed guarantees | No honest execution, complete recording or independent scientific supervision. Plain local timestamps/unsigned webpage dates insufficient. |
| Versioned/retention-controlled offmachine store | Availability/version history under the chosen policy; possibly external digest retention | Operator-controlled backup not independent custody or necessarily immutable time. |
| Published preregistration | Inspectable scope/history and public corrections; stronger chronology only with authenticated external time | Publication alone cannot prove source was executed or all attempts captured. |
| Fixed authenticated beacon record | Publicly checkable signature/round and nondiscretionary seed derivation | Unpredictability/chronology not proven by a relay's unsigned claim or signature hash alone. |

Future adopted sequence retains R8 S1–S6, with only S3 organizational substitution:
approve/freeze/G1/QA2/smoke and seedless plan; approve code release/tag; create
C_pre binding every existing required artifact and prior S/Q registry head;
publish/obtain authenticated externally retained timestamp of exact C_pre and
preregistration bundle SHA256 at least24h before fixed R* schedule; independently
verify receipt/time/policy before revealing/deriving seed; verify same fixed R*
signature/chain/round using approved pinned client; derive S4 exactly; commit
C_seed/full plan; approve specific execution; commit and externally checkpoint
startedA entry before attempt. No candidate/result exposure before commitment,
no known seed selection. All logs/results sealed then externally anchored.

No service/key/witness/round/client/release/master/commitment is chosen here.
Candidate services must later be assessed for authenticated time, digest/subject
binding, retention, trust roots, verification/expiry/revocation/outage behavior
and receipt reproducibility. External service supplies only its stated assurance.
Missed deadline→commitment ineligible/disclosed; wrongsignature/relaydisagreement
halts; samefixedround-only transports, wait/log24h, no replacementround/beacon.
No local clock or Director assertion replaces a required external timestamp.

### Retention and attempt history

Preserve all sealed originals and failed/interrupted bytes/locks/torn entries.
Canonical SHA256/size inventories bind source, dependencies, environment,
resolved config/plan, registry and evidence. Store new audit artifacts outside
E001. Copy exact bytes to two offmachine failure domains, one offline or
retention/version protected; retain receipts and prior inventories; restore to
a new directory and verify using a different tool/implementation against prior
external pins; perform annual read/restore checks. Operator may do all steps,
but call this solo retention, not independent custody. Never rewrite a source
manifest to incorporate new analyses or later approvals.

Local append-only, gap-free S/Q/A started/result entries plus Git commits remain
mandatory. Proposed Level2 substitute for a dedicated anti-rollback authority:
externally timestamp/retain each started head before its action and each result
head+manifest or partial-disclosure digest after sealing; include previous
external receipt digest and compare latest retained head at every transition.
If the external checkpoint cannot be verified, do not start the next action;
retain and disclose incomplete local evidence until anchoring is possible.
No lock stealing, journal repair, automatic resume/retry or head reset. This
binds published history; it cannot prove absence of private suppressed actions
before publication or defeat operator control over all local capture.

F1–F4/Valid semantics, same-seed rules, cap3 F1–F3, F4 defect/amendment exception,
post-amendment labels, validfinal/no pooling/no new seed all retained. Numerical
aborts get durable disclosure and no new seed. Every proposed retry needs explicit
Director scope/reason approval and pre-rerun external history checkpoint; advisory
review records the diff/root cause without primary-result selection. >3 escalation
requires separately documented exceptional Director decision, cannot waive
scientifically prohibited retries; new seed means new experiment with full history.
F1–F3 primary counters remain blinded; automatic digest checks only. F4's existing
full failed statistics disclosure rule is retained. Failureclassification is based
on harness/control criteria, never whether the primary outcome is attractive.

### E001 exact qualification and claim categories

Retain full 7000000 occurrence reconstruction/order/dedup/patterncontinuation,
exact0A1 and independently derived distinctX3 count/digest/ranks. Expected60721
is a comparison target, never an observed result inserted into a report.
Bounded PhaseA/B/E6 work cannot qualify it. Current fixture limits remain4096.

Separate report fields: (a) sealed-byte integrity; (b) historical source
correspondence; (c) synthetic bounded algorithm agreement; (d) authenticated
bounded original-runtime equivalence; (e) full candidate/exclusion reconstruction;
(f) exact historical numerical analysis reproduction; (g) human/organizational
authentication. Missing (d)/(f) cannot be claimed by passing (a)/(c).

Original CPython 3.11.0 executable provenance remains inaccessible/unauthenticated;
86 secondary floating discrepancies remain real. Do not change sealed evidence,
source/runtime or use tolerance/rounding to pass identity. If exact compatibility
is impossible, publish a precisely limited failed/blocked claim and escalate to
Director/Architect for a separate explicit scientific-compatibility disposition.
**This governance amendment does not waive R8 G1's exact reproduction prerequisite.**
If a later decision changes its scientific criterion, it is outside this task
and must be separately reviewed/versioned before G1 can pass. A solo review
ownership change alone cannot establish the correct excluded population.

For future full-audit acceptance, retain acyclic sequence: producer complete→
algorithmic report→completed outer manifest→externally authenticated outer receipt→
separate Director acceptance record. New solo report/acceptance schemas must
distinguish declaredDirector decision, algorithmic checks, external time/retention
and optional independent human attestation. No mutation of existing E5 fixture
finalrecords, no reuse of externally-audited receipt kinds for self-approvals.

## 7. Threat model and honest claim limits

| Threat | Mitigation | Residual risk / permissible assurance |
|---|---|---|
| Accidental implementation defect | Exact references/analogs, production-path QA2, independent algorithms, negative/tamper/boundary tests | Shared libs/specification errors remain; claim tested scope, not infallibility. |
| Incorrect historical reconstruction | Source/env pins, full exact independentalgorithm comparison, order/provenance/exclusiondigest | Inaccessible originalruntime blocks corresponding claim; expected count not evidence. |
| Selective reporting/unreported retries | Fixedseed/code, immutable started/results, external head checkpoints, retain all failures, no discretionary retry | Private suppressed actions remain possible; external chronology authenticates disclosed history only. |
| Premature seed/result exposure | Seedless freeze, futurefixedbeacon≥24h timestamplead, blinding/no interim access | Operator can bypass own tooling; disclose any exposure and block/review affected eligibility, never silently continue. |
| Local corruption | Streaming inventories/seals, offmachine copies, priorpins, restoretests | Undetected corruption before first trustedpin; not complete outcome truth. |
| Deliberate soleoperator manipulation | External time/digest publication, immutable releases/records, public reproducibility, separate algorithms | Cannot independently authenticate own honesty or noncapture/suppression; L2 not independent audit. |
| Thirdparty service failure/compromise | Preapproved trust/outagepolicy, retained receipts, verified signatures/round/pins, distinct backup domains | Timestamp/custody promises limited by service; requiredreceipt failure blocks, no opportunistic downgrade/round change. |
| AI-generated implementation/verification error | Shared-origin disclosure, source/import isolation, independently specified references, adversarial review, optional human audit | Different AI sessions not organizational independence; correlated hallucination/common-mode errors remain. |

A sampled1% audit remains probabilistic diagnostic coverage, not proof that no
success was omitted. Exact accounting/byte reconstruction is necessary but does
not prove execution honesty or all-outcome correctness. Full independent outcome
rehashing or a separately approved stronger scheme would add a different claim.

## 8. Publication and implementation migration

Publication must disclose solo operator/AI assistance, actual human-audit absence
and shared libraries/authorship; revision history/active identities/frozen science;
all attempts/failures/amendments/exclusions; exact raw/evidence/source/environment pins and
reproducibility instructions; statistical model/estimand/secondary limitations;
actual external commitment receipts and their guarantees or missing status;
runtime/reproduction86 discrepancies and other unresolved qualifications; audit
scope/sample limitations; self-controlled custody and potential suppression.
Report all arms/components/ratios, not selected attractive findings. Apply R8 G4
interpretation rules and require explicit Director interpretation/publication
approval. No independentaudit, cryptographicweakness or economicadvantage claim.

| Existing component | Compatibility under proposed revision | Required later work (none authorized now) |
|---|---|---|
| E1 encodings/samplers/AlgorithmD | Scientific logic and KATs unchanged; R8 config identity remains accepted | Version active protocol envelope forR9 while retaining scientific baseline and encoding identities; no sampler/seed law change. |
| E2 pure countstatistics | Reuse unchanged, same thresholds/labels/numerical safeguards | Explicit tests in latermigration that no governance result enters inference. |
| E3 Plan/accounting/secondary | R8 planv2/accountingv2 and SECv2 remain valid historical contracts | New plan/provenance identity version binds governance/assurance/activeR9/scienceR8; reject mixed identities. No statistical/accounting geometry change. |
| E4 Claim/VerifiedEvidence/Commitment/eligibility | Strict externallyverified R8 semantics unchanged; returns executiondisabled | New typed DirectorApproval, algorithmicreport, externally timestamped receipt and Level3 attestation policies; qualify real service verifier. Do not coerce self-approval into VerifiedEvidence or fake witness. |
| E4 journal/seal | Preserve canonical oldbytes/hashchain/retainedfailures | Reviewed newversion for external checkpoint policy and authorization roles; preserve all old receipts/results; no automaticrepair/dispatch. |
| E5 bounded adapters/core/fixturefinal | Accepted status/caps/fixturehistoricalfalse unchanged | Full provider, independentalgorithm qualifications and new solo fullacceptance validator separately authorized; no old fixture can become historicalpass. |
| QA2/verifier/controls/integration | Existing component tests accepted, actual pipeline stillmissing | Complete production paths, controls, independent verifier, bounded approved QA2 and reference provenance before gate passes. |
| E6 docs/READY | Preserve original ownership/provenance findings as historical R8 assessment | Append futureexplicit compatibility decision referencing which organizational prerequisites change; never rewrite oldblocked findings as passed. |
| Source/config/release/manifest/receipts | Existing R8 artifacts remain immutable | Bind activeR9+governance+scienceR8+SECv2 in new artifact schemas/source/config/manifest and receipts; no executionrelease created here. |

Migration needs a documented per-receipt compatibility decision: old scientific
component evidence may be referenced with its exact scope/pins, but old R8
eligibility/witness/custody/approval receipts cannot be combined with R9 gate
receipts by implication. Revalidate exact subjects/schema/policy, record accepted
reused evidence, rerun only separately authorized necessary qualification. Never
rewrite an executed experiment or existing audit receipt. Approval of R9 is not
approval of code migration, QA2, release, seed or execution.

## 9. Open Director decisions and present disposition

1. Adopt or reject this governance-only proposal and proposed identities/Level2
   target; confirm human Director authority and AI advisory role limitation.
2. Approve exact organizational substitutions M01/M13/M19/M24–M26/M28/M32/M36/M40
   and disclosed assurance losses; independent human audit remains optionalLevel3.
3. Approve future timestamp/receipt and latest head policy requirements, then
   separately select/qualify service/trust roots and operational archival policy.
4. Resolve freeze prerequisites already open: actual beacon/client live checks,
   audit format/seed provenance, minimal versus full outcome assurance, reproducible
   release environment/platform resources. No service/round/seed chosen here.
5. Resolve strict historical numerical/runtime compatibility by independent
   algorithmic qualification and explicit separately reviewed disposition;
   retain blocking status where exact scientific requirements are not met.
6. Authorize a separate narrowly scoped governance schema/migration proposal if
   adopted; no accepted implementation changes now. Scope later material actions
   individually; no blanket execution permission.

Present result: **Revision9 PROPOSED; G1 not passed, QA2 not qualified, G2 not
authorized.** All scientific and material engineering blockers remain. Stop for
Architecture Review042 with this proposal and the separate handoff.
