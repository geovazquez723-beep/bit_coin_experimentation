# E002 G1-C — historical reproducibility and platform closure — implementation handoff

2026-10-16, America/Los_Angeles. Branch `feat/e002-g1-historical-platform-closure`, created from updated `main` at **`b96b4828a6d5417c99052aa7f64fd5363f48c128`**
(PR #7 confirmed `MERGED` 2026-10-16T16:41:01Z; local `main` fast-forwarded). Work is **unstaged and uncommitted** for Research Director review.
Raw data: `docs/reviews/e002-g1-historical-platform-data/`. Scratch runs (full analysis outputs, regression log): `.tmp/e002-g1c/` (retained, not staged).

**Bottom line.** (1) The 86 E001 differences are **fully explained and reproduced bit for bit**: they are the CPython ≥ 3.12 change to builtin `sum()` of floats (compensated summation) acting on the chi-square statistic;
the local CPython 3.11.0 interpreter whose build string matches the sealed environment reproduces **every float of the sealed analysis exactly**, and so does 3.12/3.13 when `sum` is replaced by a strict left fold.
No decision, flag, verdict or control result changes. Strict identity under the *current* 3.12/3.13 runtime still **fails**, by design, and one Director compatibility decision is required (§1.6).
(2) The two inherited E001 test failures were an **obsolete working-checkout expectation** (a `.gitignore` CRLF checkout conversion, plus later legitimate edits to 12 post-E001 files); a pinned present-baseline check replaces them without touching the snapshots (§2).
(3) The two skipped symlink tests **cannot run on this host** (no `SeCreateSymbolicLinkPrivilege`, Developer Mode off); they stay skipped. I added labelled *simulated* tests and cite the real junction test (§3).
(4) The A1 refinement residual is a **fail-closed false-rejection** mechanism with a bounded probability ≈ 1.4 × 10⁻²⁹ per full run; deterministic tests now use the producer's real enclosure width (§4).
(5) G1 evidence matrix in §5. **G1 is not accepted.** Production execution remains disabled; no QA2, production seed, full audit, large benchmark or E001 reconstruction was performed.

## 0. Director dispositions (recorded 2026-10-16)
The Director approved **D-1(a), D-2 and D-3 as recommended** in §6.
* **D-1(a):** the CPython 3.11.0 bit-identical reproduction is accepted as satisfying strict historical E001 re-analysis identity, with the stated provenance limit (no original binary hash) and the timestamp/input-order differences recorded as non-numerical. The 86 current-runtime (3.12/3.13) differences are recorded as an understood, decision-neutral runtime-compatibility finding (`sum` algorithm). Future E001 re-analysis that claims strict identity must run on 3.11.0 or with the left-fold diagnostic.
* **D-2:** the pinned present-baseline check replaces the protected-inventory half of the two snapshot assertions; the original snapshots are preserved.
* **D-3:** the policy "a verifier stream mismatch is a disclosed failure that is investigated, never waived or silently retried" is adopted. The producer-side private refinement log is **unimplemented and not commissioned** (open item; it is only needed to attribute a mismatch, may be proposed later). Remaining open: blinding at the real output boundary and verifier-side reparse-point checks (§5.1 rows 16–17).
Still open: Q-1 (symlink-capable Windows environment), Q-2 (second host), matrix rows 12, 15–17 and all §5.2 items. G1 is **not** accepted. Work remains unstaged and uncommitted.

## 1. The 86 historical E001 numerical differences

### 1.1 Method (read-only, bounded, no E001 enumeration)
`tools/diagnose_e001_numerics.py` loads the sealed `results.json` and `config.resolved.json` (never written), runs the pure historical `analyze_results` **in memory**, serializes with the repository's own `storage.dumps`,
and compares every float with the sealed `analysis.json` by **IEEE-754 bit pattern** — no tolerance, rounding or epsilon. Output is refused inside `results/` and never overwritten. No candidate generation or hashing occurs
(chi-square on stored counters only). The historical source was exported with `git archive ef595f5 src` to scratch and used unmodified; `analysis.py` and `statistics/{distribution,inference}.py` are identical between `ef595f5` and HEAD (only new files were added).
Seven runs, one per configuration, no retries (`e001-numeric-runs.json`, `e001-numeric-comparison-summary.json`):

| Interpreter (identity) | `sum` | generator order | float bit differences | serialized analysis vs sealed |
|---|---|---|---|---|
| CPython **3.11.0** `python.exe` sha256 `bf1b0302…1c73` (`python311.dll` `a0cf640e…bffbf`) | builtin | config order | **0** | identical **except** the `analyzed_at_utc` line |
| same | builtin | stored (sorted) order | 0 | differs in secondary-row order **and** timestamp |
| CPython 3.12.14 (`b847bb9f…09de8`) | builtin | config order | **86** | differs |
| same | strict left fold | config order | **0** | identical except timestamp line |
| CPython 3.13.0 (`62ebc90a…bb05`) | builtin | config order | **86** | differs |
| same | strict left fold | config order | **0** | identical except timestamp line |
| 3.13.0 with HEAD source (not the historical export) | builtin | config order | 86 | same 86 |

The "strict left fold" is a module-level shadow of `sum` inside `hashlab.statistics.distribution` in the diagnostic process only (the CPython ≤ 3.11 algorithm); no repository source is changed.

### 1.2 Which 86 outputs differ (`e001-numeric-classification.json`, one row per field with sealed / 3.11.0 / 3.13 values and binary64 bits)
43 secondary goodness-of-fit tests × 2 fields (`statistic`, `p_value`): `first_byte_uniform` 16 tests, `last_byte_uniform` 18, `leading_zero_bits` 9; 10 generators, 38 discovery and 48 validation fields.
Maximum |Δstatistic| = 2.2737367544323206e-13 (≈ 8 × 10⁻¹⁶ relative, a few ulp of ≈ 273); maximum |Δp| = 3.4083846855992306e-14 (up to 710 ulp for small p, amplified by the incomplete-gamma tail).
Everything else in the 1,736 compared analysis paths (counts, rates, intervals, primary/null/positive control results, classifications, verdict) is **bit-identical** on 3.12/3.13.

### 1.3 Cause classification
| Hypothesis | Verdict | Evidence |
|---|---|---|
| Interpreter/library behaviour | **Demonstrated cause.** CPython 3.12 changed `sum()` of floats to compensated (Neumaier) summation. `distribution.py:92` computes `statistic = sum((o-e)**2/e …)` over 256 float terms (byte tests) or the pooled leading-zero bins; the sealed value is the naive left-fold rounding (e.g. 273.5482879999998), 3.12+ returns the better-rounded 273.548288. | 3.11.0 binary → 0 differences; 3.12.14 and 3.13.0 → exactly 86; either with a left fold → 0. The p-value differences follow from the changed statistic (the same `gammaincc` code is bit-stable: 0 differences once the statistic agrees). |
| Algorithm implementation | Excluded | Identical source, identical formulas, identical results on 3.11.0. |
| Serialization | Not a numerical cause. | Float tokens are produced by `json.dumps` of the identical doubles. Serialization **does** account for two *representational* differences (§1.4). |
| Scientific calculation | Excluded | Same inputs and code yield the sealed bits on the original build. |
| libm/CRT/OS | Not implicated | `math.lgamma/exp/log` results are bit-identical across all three interpreters once `sum` is fixed. |

### 1.4 Representational differences that are not numerical
* **`analyzed_at_utc`** differs by construction (generated at analysis time). Not injected or masked in any identity claim; the "except timestamp line" results above state the exclusion explicitly. **Complete-file byte identity is therefore not achievable and is not claimed.**
* **Secondary-row order.** `results.json` is stored with sorted keys, so reloading it iterates generators alphabetically, whereas the original in-memory run followed configuration order (`seq-be-w8` first). This is a property of the *input representation*; feeding the generators in configuration order reproduces the sealed order and bytes on 3.11.0. Review 036's "secondary_order_identical: False" was this.

### 1.5 Impact on statistics and conclusions
Sealed and 3.13 outputs agree on `verdict`, all `generators`, `null_control`, `positive_control` and on the `flagged` flag of all 60 tested secondary rows (0 flagged in both). Smallest raw secondary p-value 0.0346; every adjusted p-value is 1.0. A relative statistic change of 10⁻¹⁵ cannot move any of these. **No statistical decision, reported result or scientific conclusion changes.**
Secondary tests are exploratory and not part of the primary decision.

### 1.6 Authenticated runtime identity and remaining strict-G1 position
* **Sealed record** (`environment.json`): CPython `3.11.0 (main, Oct 24 2022, 18:26:48) [MSC v.1933 64 bit (AMD64)]`, OpenSSL 1.1.1q, PyYAML 6.0.3, pytest 9.1.1, Windows 10.0.26200. It contains **no binary hash**.
* **Candidate original binary**: `C:\Users\geova\AppData\Local\Programs\Python\Python311\python.exe` (101,760 B, file date 2022-10-24, sha256 above) is what `.venv/pyvenv.cfg` (`version = 3.11.0`, `executable = …\Python311\python.exe`, `command = … -m venv C:\repo\hashlab\.venv`) points to; its self-reported build string and OpenSSL match the sealed record exactly, and it reproduces every sealed float. Review 038 could not read it (`WinError 5`); it is readable and executable now.
  This is **corroborative, not hash-authenticated**: no original hash exists, so I record it as "consistent with, not proven to be, the executable of the original run". PyYAML/pytest metadata hashes from Review 038 are unchanged and not re-pinned.
* **Authenticated identities available:** sealed manifest and all eleven files (verified, unchanged); historical source `ef595f5` (blob-pinned in `e001_contract.json`); the 3.11.0 interpreter/DLL hashes above (observation); current 3.12.14/3.13.0 hashes.
* **Strict G1 requirement status** ("E001 evidence verifies and re-analyses identically"): evidence verification **PASS**; re-analysis with the 3.11.0 build **identical to the bit** in all numerical fields (timestamp/order caveats §1.4); re-analysis under the **current qualified 3.12/3.13 runtime FAILS** strict identity (86 fields) for a now-known, decision-neutral reason.
  I did **not** add any tolerance, did not change `sum`, did not edit E001 or accepted analysis code.

**Director scientific-compatibility decision requested (D-1).** Choose one:
 (a) *Accept* the 3.11.0 reproduction as satisfying strict historical re-analysis identity, with the stated provenance limit (no original hash) and with the timestamp and input-order differences recorded as non-numerical; **and** record the 86 current-runtime differences as an understood runtime-compatibility finding (`sum` algorithm), decision-neutral — future E001 re-analysis must be run on 3.11.0 or with the left-fold diagnostic when strict identity is claimed; or
 (b) require hash-level authentication of the original interpreter first (e.g. an independently preserved installer/hash from the original machine), leaving the item OPEN; or
 (c) retain the item as PARTIAL (Review 037 Option C). Not recommended; the evidence above removes the stated uncertainty about cause.
Recommendation: (a). Regression coverage for the finding: `tests/test_e001_numeric_classification.py` (left fold → 0 bit differences; builtin `sum` on ≥ 3.12 → exactly the 86 ledger fields, all `statistic`/`p_value`).

## 2. The two inherited E001 snapshot failures

**What the assertions tested.** `test_original_sources_and_e001_preserved` and `test_accepted_sources_and_sealed_evidence_unchanged` each (i) call `validate_history` + `verify_manifest` (historical source/evidence integrity — these always passed) and then (ii) compare **2,526/2,530 working-tree files** (`protected`) and the 11 sealed files (`sealed`) with a local point-in-time inventory
(`results-smoke/e001-s12-qualification/before.json`, taken 2026-10-12 15:16; `…s13…` 15:49; gitignored qualification scratch, "not historical provenance" per the test's own comment) on **size, mtime_ns and SHA-256**. Part (ii) failed first on `.gitignore`.
**Measured disposition of the 2,526/2,530 protected entries** (both snapshots, identical classification):
2,454 byte- and mtime-identical; 14 byte-identical, mtime differs; **46–50 differ only by CRLF↔LF** (committed LF blob equals the snapshot hash; the working copy is CRLF under `core.autocrlf=true`, `.gitignore` 351 B → 367 B = its 16 line endings; the tree was rewritten 2026-10-12 21:02:56);
**12 post-E001 files** whose content matches no committed revision (each has one commit; the snapshot predates their final content): seven review/proposal documents (reviews 033, 035–038, the R9 M1b1 handoff, the E001 Phase B proposal), `tests/e001_reference.py`, `tests/test_e001_reconstruction.py`, `tests/test_exp002_e4.py`, `src/hashlab/experiments/exp002_r9_policy.py`, `tests/test_exp002_r9_policy.py`.
**The 11 sealed E001 files: all three attributes unchanged in both snapshots.** None of the 12 is E001 evidence or historical E001 source (that is pinned separately and verified).
Conclusion: the failing portion was an **obsolete working-checkout expectation**, not a historical source-integrity check.

**Change (no snapshot touched).** `tests/e001_snapshot.py` + `tests/fixtures/e001-present-baseline-v1.json` (built by `tools/build_e001_present_baseline.py` from the s13 snapshot). The two tests now call `check_snapshot_file`: sealed files must match **exactly** (size, mtime, SHA-256); each protected file must be unchanged, EOL-only different (the same LF normalization `validate_history` already uses for historical source pins),
or listed in the baseline with its **exact current LF-normalised SHA-256** (13 entries: the 12 above plus `tests/test_e001_tooling.py`, which this task edited); anything else fails. Protected-file mtime is no longer asserted (it changes on every checkout). New `tests/test_e001_present_baseline.py` (5 tests: both real snapshots, the fixture's pinned hashes; positive and negative synthetic cases — sealed edit, unlisted edit, missing file, pinned-vs-different content, CRLF-only).
**What this establishes:** historical source and sealed evidence unchanged (strictly); the rest of the working tree equals the snapshot except for explainable EOL conversion and 12 pinned, reviewed supersessions. **It does not establish** what the 12 files contained at snapshot time (only their hashes survive).
Limitation: the pinned files are now frozen by hash — editing `test_exp002_e4.py`, `exp002_r9_policy.py` etc. requires regenerating the fixture with the builder. `tests/test_e001_tooling.py` is itself in the snapshot; I edited it, so the fixture pins its edited hash.
**Director approval (D-2, approved):** replacing the two assertions' protected-inventory half with this present-baseline check. If not approved, an explicit G1 exception for the original assertions remains the alternative; the original snapshots and the old assertions' logic are preserved in git history.

## 3. Windows symlink qualification

Host: Windows 11 10.0.26200, non-elevated; `SeCreateSymbolicLinkPrivilege` absent; Developer Mode not enabled (`AllowDevelopmentWithoutDevLicense` = 0/absent); `New-Item -ItemType SymbolicLink` fails ("Administrator privilege required"). I did **not** enable Developer Mode, elevate, or change any system setting.
The two `test_symbolic_links_block_inventory_and_disclosure[False|True]` tests therefore **remain skipped (WinError 1314); they are not passes.**
**Security behaviour they enforce:** `require_plain` (`exp002_journal.py:21`) rejects any entry whose `lstat` carries `FILE_ATTRIBUTE_REPARSE_POINT` or is not a regular file/directory; `AttemptJournal.read`/`inspect_partial` also reject `is_symlink`. It is the single guard used by journal inventory/disclosure, `exp002_kernel_evidence.create_root/authenticate` (root and parent) and `exp002_finalization` (three sites).
**Evidence on this host:**
* real reparse point: `test_windows_junction_rejected` **passes** (a real junction hits the same `REPARSE_POINT` branch a Windows symlink hits; the code does not discriminate the reparse tag).
* new `tests/test_exp002_symlink_simulation.py` (**simulated** — a regular file made to *appear* to `pathlib` as a symlink/reparse point; labelled as not replacing the skipped tests): `require_plain` refuses (reparse+symlink, reparse+regular, symlink without attribute); inventory and partial inspection refuse; a plain file is accepted. 6 tests pass.
**Not covered:** the independent verifier (`e002_verify`) does not call a reparse-point check on its read side (it is content-pinned by the completion inventory, so a swapped link would change hashes, but path aliasing is unvalidated); a real file-symlink creation/rejection run.
**Required qualification environment (Q-1):** a Windows host with Developer Mode enabled (or a test account granted *Create symbolic links*) running the unchanged two tests with 0 skips; that is an environment action for the Director/host owner, not administrative access for this task. Until then they stay skipped.

## 4. A1 rare-refinement discrepancy — disposition

Unchanged facts (production-verification handoff §3A): no disagreement of law; when the uniform interval straddles an exact threshold both samplers refine identically and consume identical blocks (2,800 scripted scenarios per tail). The **only** residual: the producer certifies with 40-digit outward enclosures, the verifier with ≥ 192-bit; if an exact threshold lies *outside* the interval but within the producer's width of an edge, the producer refines and the verifier decides at once.
**New deterministic confirmation with the producer's real enclosure** (`tests/test_exp002_a1_refinement_disposition.py`, 7 tests, scripted blocks, no sampler changed): exact thresholds `k/2⁶⁴ − 2⁻ˢʰⁱᶠᵗ`. For gaps 2⁻¹⁰⁰ and 2⁻¹²⁰ both decide with one block; for 2⁻¹⁴⁰, 2⁻¹⁵⁰, 2⁻¹⁸⁰ **the producer consumes a second block (128 bits) while the verifier stays at 64** — *same decision, different consumption* —
and an extra consumed block provably shifts every later draw (first difference at the next block). The previous test injected an artificially wide enclosure; this one uses `Uniform.compare(b.ratio(...))` as shipped.
**Probability bound:** per certified comparison ≤ 4 × 3 × 10⁻³⁸ = 1.2 × 10⁻³⁷ (two edges, relative half-width ceiling 3 × 10⁻³⁸); 4 certified comparisons per output (G1-B measured, constant over the first 10,000 outputs) × 30,000,000 selections = 1.2 × 10⁸ comparisons ⇒ **≈ 1.4 × 10⁻²⁹ per full run** (documented 10⁻²⁸ is a safe upper figure; the later-stream distribution of comparison count was not measured, see G1-B §4.1).
**Fail-closed behaviour (already tested and unchanged):** a block-count difference desynchronises the replay, the independent verifier's row-by-row comparison rejects; the outcome is a false rejection, never a false acceptance, and nothing is waived or retried automatically.
**Disposition:** *no scientific defect; accepted fail-closed false-rejection probability ≈ 10⁻²⁹.* The approved sampler is **not** changed and the implementations stay independent.
**Director decisions requested (D-3):** (a) adopt the policy "a verifier stream mismatch is a disclosed failure that is investigated, never waived or silently retried" (already how F-classes behave); (b) decide whether to authorize a *separate narrow* producer-side private log of comparisons that refined (needed only to **attribute** a mismatch; not implemented here because it changes accepted producer code and is not needed for correctness). Without (b) the residual remains documented, probability-bounded and fail-closed.

## 5. G1 evidence matrix

PASS = directly supported by accepted evidence (at the scope stated); OPEN = needs implementation, execution, environment qualification or Director disposition; FAIL = contradicted by existing evidence.
Operational prerequisites for *full production* are kept in the second table.

### 5.1 Bounded scientific / platform qualifications
| # | Requirement | Status | Basis / what remains |
|---|---|---|---|
| 1 | Sampler exactness (small analogs), unranking bijection, M properties | PASS | E1, I1/I2 tests; G1-B A1/A3/controls probes agree with the independent verifier (identical rank sequences, bounded scale) |
| 2 | Margins, A2 hull, 2,999 df, cluster aggregation, negative-lift control vs independent references | PASS | E2/E3 references; I2/I3 |
| 3 | E001 evidence (11 files, manifest, source pins) verifies | PASS | unchanged; re-verified here (protected inventory 0 differences) |
| 4 | E001 full occurrence/exclusion audit (zero A1 overlap, 60,721 A3 exclusions) | PASS | retained S1.4 evidence, authenticated read-only in G1-B |
| 5 | E001 re-analysis identical — **3.11.0 build** | PASS (D-1(a) approved; provenance limit and timestamp/order caveats recorded) | bit-identical numerics; binary hash not authenticated; timestamp/order caveats |
| 6 | E001 re-analysis identical — **current 3.12/3.13 runtime** | FAIL (understood, accepted as decision-neutral finding) | 86 fields differ; cause demonstrated; D-1(a) approved; use 3.11.0/left fold for strict claims |
| 7 | Independent SHA-256 implementation (not shared with producer) | PASS (bounded) | G1-A; HACL\* in `python312.dll` vs OpenSSL, KATs |
| 8 | Producer runtime binding of the actual hashing stack | PASS | G1-B; verifier re-observes by separate API; altered-artifact tests |
| 9 | Resource feasibility (single producer + audit + storage) | PASS (projection) | G1-B bounded probes; not a sustained run |
| 10 | Resource-failure behaviour (ENOSPC, OOM, interruption, corrupted inventory, DLL mismatch) fails closed | PASS | G1-B, 38 tests |
| 11 | Journal filesystem hardening: reparse points/junctions rejected | PASS (junction real; symlink simulated) | §3 |
| 12 | Real file-symlink rejection tests execute | OPEN (Q-1) | 2 tests skipped, host lacks privilege |
| 13 | A1 producer/verifier refinement residual | PASS (fail-closed, bounded; D-3 policy adopted; refinement log not commissioned) | §4 |
| 14 | "All existing tests pass" | OPEN | full suite below; two E001 snapshot tests now use the present baseline (**D-2 approved**); 2 symlink skips remain |
| 15 | Second independently configured host reproduces results | **OPEN** | nothing has run on a second host; see §5.3 |
| 16 | Blinding of operator-visible progress/failure output at the real boundary | OPEN | scope metadata and sanitized `KernelFailure` only (G1-B); output renderer not qualified |
| 17 | Verifier read-side reparse-point check | OPEN | §3 "Not covered" |

### 5.2 Full-production operational prerequisites (not scientific qualifications)
| Requirement | Status | Remaining |
|---|---|---|
| Sustained integrated rehearsal (writer + verifier, public identities) and target-media probe | OPEN | G1-B §10.1–2: NVMe selected as primary by Director; archival media not designated/qualified |
| Two off-machine failure-domain copies, one offline/retention-protected; restored-copy verification | OPEN | custodians/targets undecided |
| Frozen interpreter selection and start/end runtime re-observation | OPEN | observer exists; production adapter disabled |
| Numerical abort limits; machine-continuity policy (keep-awake, Defender) | OPEN | principle approved; values await Director |
| Final audit policy, independent-verifier appointment, external receipts/timestamp/beacon | OPEN | R9 operational items |
| QA2; G2 pre-execution authorization; production execution | OPEN / not authorized | |

### 5.3 What can already be reproduced on an independently configured second host, and what still requires one
Reproducible by anyone from the repository plus the **untracked** sealed `results/` directory (copy required), each read-only and bounded: `diagnose_e001_numerics.py` (seconds; needs CPython 3.11.0 *and* any ≥ 3.12 to see both sides), the focused test files added in G1-A/B/C, the bounded probes (`tools/measure_e002_g1b.py`, ≤ 1 minute each).
**None of this has been run on a second host.** Two processes on this machine (producer/verifier, three interpreters) are **not** second-machine qualification and are not claimed as such. A second host must, at minimum: install the pinned interpreters with recorded hashes, restore the sealed evidence and a repository bundle from an archive copy, re-run the E001 numeric diagnostic and verifier probes,
and compare outputs with the records in this repository. Differing CPU/OS build/CRT is exactly what it would test. Requirement: a designated second host and owner.

## 6. Decisions requiring Research Director approval
| ID | Decision | Recommendation |
|---|---|---|
| D-1 | E001 strict-identity claim (§1.6): accept 3.11.0 bit-identical reproduction with stated provenance limit and timestamp/order caveats; record 3.12/3.13 drift as understood and decision-neutral | (a) accept |
| D-2 | Replace the protected-inventory half of the two inherited snapshot assertions with the pinned present-baseline check (§2) | approve |
| D-3 | A1 refinement: adopt investigate-never-waive mismatch policy; decide whether to commission a separate producer-side refinement log | adopt policy; log optional, later |
| Q-1 | Designate a Windows environment with symlink privilege (Developer Mode) to run the two skipped tests | designate |
| Q-2 | Designate second host/owner for independent reproduction (§5.3) | designate |
Remaining blockers outside this assignment: see §5.2 and the G1-B handoff §10.

## 7. Tests

| Run | Result |
|---|---|
| New/changed focused files (`test_e001_present_baseline`, `test_e001_numeric_classification`, `test_exp002_symlink_simulation`, `test_exp002_a1_refinement_disposition`, `test_e001_historical`, `test_e001_tooling`, `test_exp002_e4`, `test_exp002_production_components`) | all passed (20 new tests; 123 in the E001 group, 85 in the A1 group, 50 + 2 skips in E4/simulation) |
| **Full offline regression** (`regression.txt`, 170.2 s, CPython 3.12.14 bundled runtime) | **1,964 passed, 0 failed, 2 skipped** (previous: 1,942 passed, 2 failed, 2 skipped) |

Accounting: +20 new tests, and the two previously failing E001 snapshot tests now pass (+2). **The two skips are unchanged and are not passes**: `test_exp002_e4.py::test_symbolic_links_block_inventory_and_disclosure[False|True]` (WinError 1314). The "0 failed" rests on **D-2** (approved) (the present-baseline replacement of the snapshot assertions); it is not an assertion that the *original* snapshot comparison passes — it does not (§2).
G1's "all existing tests pass" is therefore **not** fully satisfied until the symlink tests run (Q-1).

## 8. Preservation
Protected `results/` files (20) re-hashed against the G1-B base inventory: **0 differences of 20**. The 11 sealed E001 files pass `validate_history`/`verify_manifest` inside the regression. No file under `results/`, `results-smoke/` snapshots, or retained `.tmp` evidence was modified; diagnostic outputs live under `.tmp/e002-g1c/` (new).
CPython 3.11.0 was **run** (not installed or modified) only to execute the read-only analysis described in §1; it was not used to generate candidates, hashes or any E001/E002 evidence.

## 9. Files
New: `tools/diagnose_e001_numerics.py`, `tools/build_e001_present_baseline.py`, `tests/e001_snapshot.py`, `tests/fixtures/e001-present-baseline-v1.json`, `tests/test_e001_present_baseline.py`, `tests/test_e001_numeric_classification.py`, `tests/test_exp002_symlink_simulation.py`, `tests/test_exp002_a1_refinement_disposition.py`,
`docs/reviews/e002-g1-historical-platform-data/` (`e001-numeric-classification.json`, `e001-numeric-comparison-summary.json`, `e001-numeric-runs.json`, regression log), this document.
Modified: `tests/test_e001_historical.py`, `tests/test_e001_tooling.py` (protected-inventory half only). No `src/` file, accepted scientific/statistical/sampling/hashing code, E001 evidence or snapshot changed.
