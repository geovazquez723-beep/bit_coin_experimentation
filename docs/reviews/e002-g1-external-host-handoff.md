# E002 G1 external-host qualification (Q-1 and Q-2) — handoff

2026-10-16, America/Los_Angeles. Branch `feat/e002-g1-external-host-qualification` from `main` at the PR #9 merge commit **`c5cc9b84c17434d0ff68ebb164a67f6ad9e5f91a`** (PR #9 `MERGED` 2026-10-16T17:27:46Z).
One commit is pushed on the branch, as authorized: the bounded workflow `.github/workflows/g1-q1-windows-symlink.yml` (`5f08293…`; push to this branch only, `permissions: contents: read`, no secrets, no deployment). **It is not merged.** Everything else is unstaged and uncommitted.
Data: `docs/reviews/e002-g1-external-host-data/`.

**Result.** **Q-1 is closed with real evidence**: all 11 previously skipped symlink tests ran and passed on a separate Windows host (GitHub-hosted `windows-2025`), 22 passed / 0 skipped / 0 failed.
**Q-2 remains OPEN** for two specific, evidenced reasons: (1) the verifier needs retained protected inputs (the 202 MB S1.4 audit and the 11 sealed E001 files) that cannot safely be published to a public repository or runner — the Director chose to keep Q-2 open rather than transfer them; (2) a newly demonstrated defect: the evidence's source binding is raw working-tree bytes, which no standard fresh checkout reproduces (§3.2). I built the tooling that works around (2) without changing evidence or verifier. G1 is **not** accepted; production remains disabled; no QA2, seed, beacon, real E002 hashing, full audit or large benchmark ran.

**Director disposition (2026-10-16):** the EOL-only source alignment (§3.2) is **accepted for this bounded evidence set**; Q-2 stays **open** until a second machine runs §3.4. The plan-format change to LF-normalized hashes is not commissioned.

## 1. Q-1 — real Windows symlink qualification: CLOSED (hosted runner)

| Item | Recorded value (`q1-windows-2025/host.txt`, `pytest.txt`, `junit.xml`) |
|---|---|
| Run | GitHub Actions run `38943859490`, job `117117935296`, workflow commit `5f0829363f412821db996927f4e8214c8e75950a` (only `.github/workflows/g1-q1-windows-symlink.yml` differs from `c5cc9b8`) |
| Host | Windows Server 2025 Datacenter 10.0.26100 (runner image `win25-vs2026` 20261007.264.1), AMD EPYC 7763, 2 cores; **a different OS edition/build, hardware and administrative domain from the local Windows 11 10.0.26200 development host** |
| Privilege context | process **elevated** (Administrator); `SeCreateSymbolicLinkPrivilege` listed (state `Disabled` in the token, as normally shown until used); Python `os.symlink` for a file and for a directory succeeded in the pre-test probe. Runner security configuration was **not** changed by me or the workflow |
| Runtime | CPython 3.12.10 (`hostedtoolcache`), pytest 9.1.1, PyYAML 6.0.3 (pinned installs); `ssl` OpenSSL 3.0.16 (not used for any evidence hashing here) |
| Tests | `tests/test_exp002_e4.py::test_symbolic_links_block_inventory_and_disclosure[False|True]` (the 2 original skipped tests), `tests/test_exp002_g1d_reparse_security.py` (14), `tests/test_exp002_symlink_simulation.py` (6) |
| Outcome | **22 passed, 0 failed, 0 skipped, 0 errors** — the 11 formerly skipped tests all executed and passed on the first run, unmodified (no test changed, none mocked to obtain green) |
| Real objects exercised | NTFS **file symlinks** (substituted for `chunk-00000000.bin`, `complete.json`, `plan.json`, `chunks.jsonl`, `environment.json`, each pointing at a byte-identical copy); NTFS **directory symlinks** (as evidence root, as parent of a new root, as an unexpected entry and in place of a chunk); real **junctions** (`mklink /J`) in the same positions; plain file/dir targets in disposable temp paths |
| Defenses confirmed | the independent verifier, producer chunk reader, `create_root`, `inspect_partial`, `classify_attempt_evidence` and `verify_restored_copy` raise `ValueError` on every linked root/parent/entry/substituted file; the original evidence stayed byte-identical and still verified afterwards; a linked *ancestor* is content-pinned (genuine bytes accepted, tampered bytes refused) as already documented in G1-D |

**What this closes:** the real-symlink enforcement of the reparse-point guards (`require_plain`, the verifier's independent `_plain`) on Windows/NTFS, and evidence-path containment against symlink substitution — Q-1 as specified by the Director.
**Remaining target-host-specific item (not a Q-1 blocker):** the local Windows 11 development host still cannot create symlinks (no privilege, Developer Mode off). If the Director wants the same 11 tests to pass on the *target production host* as well, the host owner must enable Developer Mode or grant "Create symbolic links" and run `python -B -m pytest tests/test_exp002_g1d_reparse_security.py tests/test_exp002_e4.py tests/test_exp002_symlink_simulation.py -q -rs` (0 skips). I did not change any local security setting.
Note: the runner is an ephemeral VM; the hosted run was done in the public repository, so its log is public (it contains no protected evidence, only the test names and host facts above).

## 2. Repository preparation and revision identities
* Merge commit recorded: `c5cc9b84…`. The old `de27c0e` package (G1-D `q2-package.zip`) is **not** presented as bound to the merged release.
* **Original producer identity (preserved, unchanged):** evidence `producer/` from the G1-B run (78 evaluations, public engineering seed 0), completion pin `e2cd0fc8eaf2661414b98278fb940ae896aa2d68b712a563c43633a6a38f9a27`; producer sources = `de27c0ee42cdf7129093080195a1671381c7d1bb` (G1-B working copy equals that commit up to line endings, §3.2); producer runtime: `python.exe` `b847bb9f…09de8`, `python312.dll` `2b6fffde…49b1`, `_hashlib.pyd` `b9880771…330f`, `libcrypto-3-x64.dll` `57df468e…7e8a` (OpenSSL 3.5.8), `VCRUNTIME140.dll` `d5e4d9a3…9066`.
* **Current verifier revision:** `c5cc9b84…`. `src/e002_verify` is **byte-identical** between `de27c0e` and `c5cc9b8` (git tree `936253244c68083a39090d7892d4d2ac9ae8086a` at both). The only source difference is the two producer-side wrapper files fixed in G1-D (`exp002_kernel.py`, `exp002_kernel_disclosure.py`, +3 lines each).
* Demonstrated consequence: the **verifier at the merged revision refuses the original evidence** (`reference: bound source inventory differs from the checkout`) because the plan binds the exact producer source bytes. That is correct fail-closed behavior, not a verifier defect, and it fixes the Q-2 basis: the original evidence must be verified at its bound source revision (`de27c0e`), with the identical verifier tree. (Director choice recorded: *original evidence at de27c0e*.)

## 3. Q-2 — independent second-host replay: OPEN

### 3.1 Transfer package v2 (built, not transferred)
`q2-package-v2.zip` (82,259 B, SHA-256 `03f425c94d16217f9ab627ea61e7b54f6b4304f61fbca125fb00c5fb4e693745`): the original evidence byte for byte (`diff -r` identical to the retained directory), seed record, pin, the producer-side expected verifier report, and `MANIFEST.json` (schema `hashlab-e002-q2-package-v2`) separately recording `producer_revision`/`required_commit` = `de27c0e`, `verifier_revision` = `c5cc9b8`, the equal `e002_verify` trees, the 2 differing producer files, the producer runtime/hashing identity, a hashed host fingerprint, and SHA-256/size for every package file, the 8 S1.4 audit inputs and the 11 sealed E001 inputs.
**Content inspection before any transfer:** no tokens, keys, credentials, e-mail addresses or secret-like words in any package file; the only personal data is the producer's Windows profile name inside runtime artifact paths (`C:\Users\geova\…` in `environment.json`, the expected report and the manifest; already present in earlier committed data). No E002 outcome exists (public engineering seed, 78 artificial-geometry evaluations). **Not packaged, deliberately:** the S1.4 audit directory and the sealed E001 files (below).

### 3.2 Obstacles (specific)
1. **Required protected inputs cannot be published.** `verify_evidence` needs `results/e001-s14-audit-20261012-01` (8 files, 202 MB: `occurrences.bin` 133,000,000 B, `accounting.sqlite` 37.8 MB, `reference.sqlite` 37.8 MB, `exclusions.bin`, `ranks.bin`, plans/reports) — all pinned inside the verifier — **and** the 11 sealed E001 files (653 KB) under `results/<run>/`. They are retained, hash-pinned evidence outside git; the repository and runner are public, and a 133 MB file also exceeds the 100 MB git limit. Publishing them to make the workflow run is not permitted, and regenerating them on the runner would be the forbidden E001 reconstruction. **Director decision: keep Q-2 open** (alternatives were a temporary private repository, or the Director's own second machine).
2. **Newly demonstrated defect — source binding is not reproducible across checkouts.** The producer's plan binds the *raw working-tree bytes* (size + SHA-256) of 58 source files. The producer's working tree had mixed line endings (33 files CRLF, 25 LF; the result of Windows `core.autocrlf` conversion at different times). A fresh clone of `de27c0e` produces all-CRLF (`autocrlf=true`) or all-LF (`false`); **both fail** with `bound source inventory differs from the checkout` (verified on this host with both settings). So even with the inputs in place, no standard checkout on a second host can verify this evidence as-is.
   *Mitigation delivered (no evidence or verifier change):* `second_host_replay.py replay` builds a scratch copy of the clean pinned checkout and, for each bound file, accepts the LF or CRLF rendering **only if it matches the recorded size+SHA-256 exactly** (content is never altered; a non-match is left to fail the verifier). Result of a fresh pinned clone on this host: 25 files as checked out, 33 CRLF-aligned, 0 no-match, verifier report equal to the expected report on all compared sections.
   *Recommended permanent fix (Director decision; changes the plan format, not done here):* pin LF-normalized source hashes (precedent: E001 contract `source_sha256_lf`) and compare LF-normalized bytes, then regenerate the bounded fixture; or require `core.autocrlf=false` plus `.gitattributes eol=lf` for all sources before the production plan is built.

### 3.3 What was run, and why it is not Q-2
`q2-samehost-replay-v2.json`: replay of package v2 with a *fresh pinned clone* of `de27c0e` (`--no-checkout`, `autocrlf=false`), the independent verifier with the HACL\* backend (`known_answers: passed`) and `--observe-hashing`: `package_problems: []`, `differences: []`, `matches_expected: true`, **`q2_qualifying: false`** (same host fingerprint; exit code 2). This validates the package, manifest, EOL alignment and tool end to end, but a second process/checkout on the same machine is **not** Q-2.
Tests: `tests/test_exp002_q2_replay_tool.py` (4, updated for manifest v2 and the sealed-input check).

### 3.4 Smallest alternative second-host setup
One additional Windows machine (the Director's other PC, a private self-hosted runner, or a private repository/runner only if the Director explicitly authorizes sending the protected inputs there), with CPython 3.12 and no remote-orchestration infrastructure:
```
# transfer: q2-package-v2.zip (SHA-256 above), results\e001-s14-audit-20261012-01 (202 MB), results\20261011T205056Z-exp001-fc1d75fc (11 files); all hash-checked by the tool
git clone --no-checkout <repo> hashlab-q2
git -C hashlab-q2 config core.autocrlf false
git -C hashlab-q2 checkout de27c0ee42cdf7129093080195a1671381c7d1bb
powershell Expand-Archive q2-package-v2.zip -DestinationPath q2-package
python -B hashlab-q2\tools\second_host_replay.py replay q2-package --repository hashlab-q2 --audit <audit dir> --e001-sealed <sealed dir> --out q2-report.json [--observe-hashing]
```
(The manifest-v2 tool is the modified, still-unstaged `tools/second_host_replay.py` of this branch; the `de27c0e` checkout contains no tool, so run the tool file from this branch, or after it is committed and merged, with `--repository` pointing at the `de27c0e` checkout.) Acceptance: exit 0, `q2_qualifying: true`, `matches_expected: true`, `package_problems: []`, `candidate_sha256.backend == hacl`; record `python -VV`, executable and native-library hashes, OS version. `--observe-hashing` additionally requires the same pinned runtime files as the producer; on a different build the run fails closed (`artifact bytes`) — omit it then and record both identities. Any difference in candidates, raw/effective digests, accounting or completion binding is a failure to be reported, not adjusted.

## 4. Updated G1 matrix (bounded qualifications are not production acceptance)
| Requirement | Status | Basis / remaining |
|---|---|---|
| Q-1 real symlink/reparse-point and evidence-path containment tests | **PASS** (hosted Windows Server 2025; 22/22, 0 skipped) | §1; optional repeat on target host |
| Junction, parent/ancestor, entry-substitution containment | PASS | G1-D (local) and §1 (hosted) |
| Q-2 independent second-host replay | **OPEN** | §3: protected inputs undeployable on public runner (Director: keep open); source-binding EOL defect (needs Director decision); a second machine and a run are required |
| Source-binding reproducibility across checkouts | **OPEN — defect** | §3.2; tool mitigation only; permanent fix is a plan-format decision |
| Independent SHA-256, runtime binding, resource-failure behavior, blinding (ordinary interfaces), D-3 mismatch policy | PASS (bounded) | G1-A/B/D |
| E001 identity (D-1(a)), snapshot checks (D-2) | PASS / approved | G1-C |
| Sustained rehearsal, NVMe/archival media probes, two off-machine copies, frozen interpreter, abort-limit values, continuity | OPEN (final runtime/media) | G1-B §10 |
| Path-pinned reader containment; producer refinement logging; audit policy; verifier appointment; custodians | OPEN (Director decisions) | G1-D §6-D |
| QA2; G2 authorization; seed/beacon/commitment; production execution; external receipts | OPEN (later authorization) | not authorized |

## 5. Tests and preservation
| Run | Result |
|---|---|
| Hosted Q-1 (windows-2025) | **22 passed, 0 failed, 0 skipped** |
| Local focused (`test_exp002_q2_replay_tool.py`) | 4 passed |
| Local full offline regression (`regression.txt`, 175.6 s, CPython 3.12.14) | **2,000 passed, 0 failed, 11 skipped** — identical to the last baseline; the 11 skips are the symlink tests that cannot execute on the local Windows 11 host and are **not** passes there; they passed on the hosted host (§1) |
No source file changed on this branch. Retained evidence, protected `results/` files and snapshots were not modified. Scratch is under `.tmp/e002-g1e/`.

## 6. Files
Pushed (workflow only): `.github/workflows/g1-q1-windows-symlink.yml`. **Unstaged:** modified `tools/second_host_replay.py` (manifest v2, `--e001-sealed`, `--expected-report`, `--producer-commit`, `--verifier-revision`, EOL-only source alignment), modified `tests/test_exp002_q2_replay_tool.py`, new `docs/reviews/e002-g1-external-host-data/` (`q1-windows-2025/{host.txt,pytest.txt,junit.xml}`, `q2-package-v2.zip`, `q2-samehost-replay-v2.json`), this handoff.

## 7. Exact outstanding blockers and shortest route
1. **Q-2:** a second Windows machine (or an explicitly authorized private environment) holding the protected inputs; run §3.4. Prerequisite decision on the source-binding defect: either accept the delivered EOL-only alignment for this one bounded evidence set, or change the plan to pin LF-normalized hashes and regenerate the fixture.
2. Director decisions: path-pinned containment, producer refinement logging, archival custodians/targets, abort-limit values, final audit policy, independent-verifier appointment.
3. Final runtime and media qualification (frozen interpreter, sustained rehearsal on the NVMe, two off-machine copies with restore verification).
4. Then (separately authorized): QA2 → G2 authorization → seed/beacon/commitment. With Q-1 closed, **Q-2 plus items 2–3 are the shortest route to G1 acceptance**; QA2 needs G1 acceptance first.
