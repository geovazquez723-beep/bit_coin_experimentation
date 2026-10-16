# E002 G1-D — platform and independent-host qualification — implementation handoff

2026-10-16, America/Los_Angeles. Branch `feat/e002-g1-platform-qualification`, created from updated `main` at **`de27c0ee42cdf7129093080195a1671381c7d1bb`** (PR #8 confirmed `MERGED` 2026-10-16T17:05:56Z).
Work is **unstaged and uncommitted** for Research Director review. Raw data: `docs/reviews/e002-g1-platform-qualification-data/`.

**Baseline identity.** Test/qualification runtime: bundled CPython 3.12.14 (`python.exe` `b847bb9f…09de8`, `python312.dll` `2b6fffde…49b1`, `_hashlib.pyd` `b9880771…330f`, `libcrypto-3-x64.dll` `57df468e…7e8a` OpenSSL 3.5.8; verifier candidate backend HACL\* in `python312.dll`), Windows 11 10.0.26200, AMD Ryzen 7 7800X3D, Defender on.
Source baseline = `de27c0e` plus the changes listed in §8. Protected `results/` files and retained evidence were not modified (§7).

**Outcome in one paragraph.** **Q-1 stays OPEN**: this host cannot create symlinks (no `SeCreateSymbolicLinkPrivilege`, Developer Mode off, non-elevated). Real-junction tests for every evidence reader now **pass**; the real-symlink tests are written and **skip** here with a Q-1 message; exact commands for a capable host are in §2.
**Q-2 stays OPEN**: no second host exists. A byte-exact transfer package, a replay tool that refuses a same-host run as non-qualifying, and exact commands are delivered (§3).
**Real-output blinding**: qualified for ordinary program interfaces over 7 failure paths, normal run, verifier rejection, numerical-inference failure and F1–F4; **one demonstrated defect found and fixed** (the private wrappers could be pickled/copied, exposing the private payload) (§4).
**D-3** policy verified against the existing verifier (§5). G1 matrix in §6. **G1 is not accepted.** Production remains disabled; no QA2, seed, beacon, real E002 hashing, full audit or large benchmark.

## 1. Correction to the G1-C record
`e002-g1-historical-platform-closure.md` §3/§5 (row 17) said the independent verifier has no read-side reparse-point check. **That was wrong**: `e002_verify` has its own independently written `_plain` guard (`e001_stream_verify/streaming.py:30`, re-exported by `e002_verify.core`) applied to the evidence root and to every directory entry (`production_evidence.py:425, 459–460`), mirroring the producer's `require_plain`. What *was* unvalidated was exercising it on real reparse points; that is now done for junctions (§2). Row 17 is therefore PASS for junctions, symlink-dependent for the rest. The G1-C document is a merged historical record and is not edited.

## 2. Q-1 — Windows symlink qualification

**Capability check (existing configuration only; nothing changed).** `whoami /priv`: no `SeCreateSymbolicLinkPrivilege`; `HKLM\…\AppModelUnlock\AllowDevelopmentWithoutDevLicense` absent (Developer Mode off); process not elevated; `New-Item -ItemType SymbolicLink` → "Administrator privilege required"; Python `symlink_to` → `WinError 1314`. I did not enable Developer Mode, request elevation, or alter policy.
**The two original E4 tests (`test_symbolic_links_block_inventory_and_disclosure[False|True]`) remain skipped — not passes.**

**New real-object tests** `tests/test_exp002_g1d_reparse_security.py` (14 cases; real files/directories/junctions; evidence is a real bounded-fixture run; assertions verify the *original evidence is byte-identical afterwards* and still verifies):
| Scenario | Readers exercised | Junction (runs here) | Dir/file symlink (needs host) |
|---|---|---|---|
| Evidence **root** is a link | independent verifier, producer `iter_chunks`, `classify_attempt_evidence`, `verify_restored_copy` | **PASS** (refused, ValueError) | written, SKIPPED |
| Output beneath a linked **parent** | `create_root` | **PASS** (refused before anything is created) | written, SKIPPED |
| An evidence **entry** is a link (replaces `chunk-00000000.bin`, or an unexpected extra entry) | verifier, `inspect_partial`, `classify_attempt_evidence` | **PASS** ×2 (nothing followed/deleted/repaired) | written, SKIPPED |
| A regular evidence file replaced by a **file symlink to a byte-identical copy** (chunk, complete, plan, index, environment) | verifier, `inspect_partial` | n/a (junctions cannot be files) | written, SKIPPED ×5 |
| Linked **ancestor** (characterisation) | verifier | **PASS**: evidence reached through a junctioned ancestor is verified by content pins only | n/a |
Results here: **5 passed, 9 skipped**. All skips carry "Q-1 open: symlink creation unavailable on this host".
**Observation for the Director (no code changed):** guards are leaf/entry-level (`lstat` on the directory and its entries) plus all-ancestor checks only in `create_root`. A *reader* given a path through a linked ancestor accepts it only if every byte matches the retained completion pin; a substituted directory fails the pin (tested). Path containment for readers is therefore **content-pinned, not path-pinned**. If path pinning is wanted, that is a separate change.
**Substituting a link for a regular file:** a file symlink/junction-as-file cannot be created here, so that case is **only qualified on a capable host**; hard links are regular files and are by design indistinguishable (content-pinned).

**Exact commands for a suitable host** (Windows 11, Developer Mode on or account granted *Create symbolic links*; Python 3.12+ with pytest; fresh checkout of this branch/commit):
```
python -c "import os,tempfile,pathlib; d=pathlib.Path(tempfile.mkdtemp()); (d/'t').write_text('x'); os.symlink(d/'t', d/'l'); print('symlink capable')"
set PYTHONPATH=src;tools;tests
python -B -m pytest tests/test_exp002_g1d_reparse_security.py tests/test_exp002_e4.py tests/test_exp002_symlink_simulation.py -q -rs -p no:cacheprovider
```
Acceptance for Q-1: **0 skipped** among the 9 + 2 symlink tests and 0 failures; report the host (`winver`, `python -VV`, hashes). If any new test fails there, that is a finding, not a test defect to be silenced (the symlink variants have never executed on this host).

## 3. Q-2 — independent second-host reproduction (OPEN)
**No authorized second host is available; no remote-execution infrastructure was built.** A second process on this machine is not Q-2 and is not claimed.
Delivered:
* `tools/second_host_replay.py` — `package` (byte-exact copy of the retained bounded evidence into a NEW directory + `MANIFEST.json` with every file's size/SHA-256, required commit, producer runtime/hashing identity, a hashed host fingerprint, and the hash-listed S1.4 audit inputs) and `replay` (verify manifest, audit inputs, clean checkout at the pinned commit; run the independent verifier with the **HACL\*** backend; compare `bindings`, `claims`, `coverage`, `mode`, `schema`, `scope`, `seed`, `verification` with the producer-side expected report; record host/runtime/native hashing identity). A replay on a host with the **same fingerprint** reports `q2_qualifying: false` and exits 2.
* `q2-package.zip` (80,393 B, SHA-256 `81e08da57cd0d26a3e8c7537e772695b9a6c9a06da5d664b6fbef95d20569f66`): the retained G1-B bounded production-format evidence (78 candidates, completion pin `e2cd0fc8…9a27`, public engineering seed 0), unchanged (`diff -r` against the original: identical), plus `expected-report.json`.
* Evidence of the tool working on this host: `q2-samehost-replay.json` (`matches_expected: true`, `q2_qualifying: false`, exit 2 — i.e. it reproduces the expected report *and refuses to call this Q-2*), and `samehost-reverify.json` (the verifier re-run reproduces G1-B's retained verifier report exactly).
* `tests/test_exp002_q2_replay_tool.py` (4 tests): same-host detection, altered package, wrong commit/missing audit inputs (verifier never runs), no report overwrite.
**Binding caveat.** The package's `environment.json` pins source bytes of the baseline commit, so the verifier must run at **`de27c0e`** (the package's `required_commit`), not at this branch (this branch edits two source files, §4). After G1-D merges a fresh package should be produced from the merged commit with the same tool.
**Second-host procedure:**
```
# 0. transfer (outside the repo): q2-package.zip (SHA-256 above) and the retained S1.4 audit directory results\e001-s14-audit-20261012-01 (≈ 202 MB; its 8 files are hash-listed in MANIFEST.json)
# 1. fresh pinned checkout and package
git clone <repo> hashlab-q2 && git -C hashlab-q2 checkout de27c0ee42cdf7129093080195a1671381c7d1bb
powershell Expand-Archive q2-package.zip -DestinationPath q2-package
# 2. replay (use the same pinned runtime files to include --observe-hashing; a different but known CPython 3.12 omits it)
python -B hashlab-q2\tools\second_host_replay.py replay q2-package --repository hashlab-q2 --audit <audit dir> --out q2-report.json [--observe-hashing]
```
Acceptance: exit 0 (`q2_qualifying: true`, `matches_expected: true`, no package problems), `candidate_sha256.backend == hacl`. With `--observe-hashing` on a host whose `python.exe`/`python312.dll`/`libcrypto` hashes differ from the producer's, the run **fails closed** by design (`artifact bytes`); that is a runtime-identity mismatch, not a reproduction failure — then run without the flag and record both host identities. The producer host's identities are in `MANIFEST.json`.

## 4. Real-output blinding qualification
**Scope:** ordinary program interfaces. **Not claimed:** protection from an operator with filesystem, debugger or deliberate-introspection access (name-mangled attributes, `object.__getstate__` called directly, memory inspection).
`tests/test_exp002_g1d_blinding.py` (24 cases) captures stdout/stderr at **file-descriptor level**, **all logging** (root handler, level 0, `logging.disable` reset), **warnings** (delivered to stderr), exception `str`/`repr`/`args`/full traceback and the whole `__cause__`/`__context__` chain, and return values. Sentinels: every raw and effective digest of every row of the real bounded run, plus numeric leaves of the private statistics payload, plus an injected marker emitted by `print`, stderr, `logging.critical` and `warnings.warn` from *inside* each failing path.
| Boundary | Cases | Result |
|---|---|---|
| Interrupted/failed hashing | `RuntimeError`, `KeyboardInterrupt`, `MemoryError` mid-run | sanitized `KernelFailure`, no chain, `failure.json` withheld fields only, no `complete.json` — **clean** |
| Generation failure | exception in the N1/P Feistel forward | clean |
| Evidence-write / serialization / finalization failure | `ENOSPC` at fsync, `MemoryError` in `encode_row`, `ENOSPC` creating `complete.json` | clean; evidence retained |
| Normal run | outcome `repr`/`str`/`to_dict`, `progress`, verifier report text | clean; public keys are exactly `status, scope, completion_sha256` |
| Verifier rejection | transport tamper; resealed semantic corruption of a raw and of an effective digest | message < 200 chars, contains no digest/outcome — clean |
| Numerical-inference failure | ambiguous secondary analysis in `infer_measured` and `commit_statistics` | sanitized, no statistics file written — clean |
| F1–F4 | `failure_report` F1–F3 withheld; F4 refused without authenticated inference; `disclose_f4` refused when the gate passed; `disclose_final` always refused; invalid `progress` refused | clean |
| Text forms / serialization of the private wrappers | `repr`, `str`, `format`, f-string, `%`; `pickle`, `copy`, `deepcopy`, `__reduce_ex__` | **defect found (below), now clean** |

**Demonstrated boundary defect (fixed).** `RestrictedInference` and `VerifiedCapture` hold the private statistics payload / accounting in `__slots__`. `pickle.dumps(...)`, `copy.copy/deepcopy` and `__reduce_ex__(2)` serialized or exposed the **complete payload** (verified: ≈ 13 KB pickle containing the primary/validation fields) although `repr` says "withheld". Any ordinary serializer (logging with `default=…`, multiprocessing, caching, a debug dump) could therefore leak primary/validation results.
Fix, 3 lines per class, no behaviour change otherwise: `__reduce__` raises `TypeError` and `__getstate__ = __reduce__` in `exp002_kernel_disclosure.RestrictedInference` and `exp002_kernel.VerifiedCapture`. 8 of the 24 tests failed before the change and pass after; the full regression below shows no other test depended on copying them. Source hash change consequence: §3 binding caveat.
**Residual (documented, unchanged):** the name-mangled attribute and `object.__getstate__(x)` remain reachable by deliberate introspection (same class as a debugger); `statistics.json` and the evidence directory are plaintext files (read-only bit is integrity, not access control); an embedding application that records warnings (`catch_warnings(record=True)`) sees warning text raised inside private processing (the kernel itself emits none); disclosure of per-arm results remains impossible through the ordinary API but not through file access.

## 5. A1 mismatch policy (D-3) — verified
`tests/test_exp002_g1d_mismatch_policy.py` (3 tests): `verify_evidence` has no waiver/retry/tolerance/ignore/resume/repair parameter and rejects non-`full` modes; with the verifier's A1 sampler made to consume one extra block, verification **fails** (ValueError < 200 chars, no report), evidence is **byte-identical** afterwards, a second call fails identically with **exactly the same number of sampler calls** (single pass, no hidden retry), genuine evidence still verifies, and neither the recorded seed nor a different supplied seed can turn a mismatch into success. **Producer refinement logging is not implemented and not commissioned.**

## 6. G1 requirement matrix (updated; bounded qualifications are not full-production acceptance)
**A. Direct qualification evidence (PASS at stated scope):** sampler exactness/unranking/M properties; margins, A2 hull, negative-lift control (E1–E3, I-series); E001 evidence verification, S1.4 audit, strict 3.11.0 re-analysis identity (D-1(a)); independent SHA-256 backend (G1-A); producer runtime-binding of the loaded hashing stack (G1-B); resource-failure fail-closed behaviour (G1-B); journal/evidence reparse-point and **junction** rejection at root, parent, entry and ancestor on real objects, for verifier, producer reader and finalization (G1-D); **real-output blinding over ordinary interfaces** incl. the serialization defect fix (G1-D); D-3 mismatch fail-closed behaviour (G1-D); present-baseline preservation checks (D-2).
**B. Requires a supported second host:** Q-2 reproduction (package/tool/commands ready; nothing run); the file/dir **symlink** tests are host-capability (Q-1), listed separately in C only because the environment need is a Windows host with symlink privilege, not a second *independent* host — a second host may supply both.
**C. Requires final runtime and media qualification:** Q-1 real symlink execution (9 + 2 skipped tests); sustained integrated rehearsal; NVMe/archival media probes and the two off-machine copies; frozen interpreter and start/end re-observation; abort-limit values; machine continuity.
**D. Requires separate Director decisions:** whether to adopt path-pinned (not only content-pinned) reader containment; whether to commission producer refinement logging; archival custodians/targets; second-host owner; abort-limit values; final audit policy; independent-verifier appointment.
**E. QA2 or later execution authorization:** QA2; G2 pre-execution authorization; seed/beacon/commitment issuance; production execution; external receipts.

## 7. Tests and preservation
| Run | Result |
|---|---|
| New files (`g1d_reparse_security`, `g1d_blinding`, `g1d_mismatch_policy`, `q2_replay_tool`) | 5 passed + 9 skipped (reparse), 24 passed (blinding), 3 passed (policy), 4 passed (tool); blinding had 8 failures before the §4 fix |
| **Full offline regression** (`regression.txt`, 185.2 s, CPython 3.12.14) | **2,000 passed, 0 failed, 11 skipped** (baseline 1,964 / 0 / 2) |

Accounting: +36 new passing tests. **Skips: 11, none are passes** — the 2 original E4 symlink tests (WinError 1314) plus the 9 new symlink variants of `test_exp002_g1d_reparse_security.py` (Q-1 message). The baseline's "2 skipped" grew by 9 because those real-symlink cases are new and cannot execute on this host; they are the Q-1 acceptance criterion.
Preservation: the 20 protected `results/` files re-hashed against the base inventory: **0 differences**; no retained `.tmp` evidence outside `.tmp/e002-g1b|c|d` has a later modification time; no snapshot, E001 artifact or historical output was touched. The only tracked files modified are the two source files in §8. Scratch outputs are in `.tmp/e002-g1d/` (new, unstaged).

## 8. Changed files
**Source (narrow, defect-justified):** `src/hashlab/experiments/exp002_kernel_disclosure.py` (+3), `src/hashlab/experiments/exp002_kernel.py` (+3): non-serializable private wrappers.
**New tests:** `tests/test_exp002_g1d_reparse_security.py`, `tests/test_exp002_g1d_blinding.py`, `tests/test_exp002_g1d_mismatch_policy.py`, `tests/test_exp002_q2_replay_tool.py`. **New tool:** `tools/second_host_replay.py`.
**Data:** `docs/reviews/e002-g1-platform-qualification-data/` (`q2-package.zip`, `q2-samehost-replay.json`, `samehost-reverify.json`, regression log). **This document.**
No accepted scientific, statistical, sampling or hashing code, E001 artifact, snapshot or retained evidence changed.

## 9. Remaining blockers (specific)
1. **Q-1:** a Windows host with symlink privilege to run §2's command (0 skips required).
2. **Q-2:** a designated independent second host and owner to run §3's procedure (use a fresh package from the merged commit).
3. Director decisions in §6-D (path-pinning, refinement logging, custodians, abort limits, audit policy, verifier appointment).
4. Final runtime/media qualification and all QA2/G2/production prerequisites (§6-C, §6-E).
