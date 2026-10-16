# E002 G1-A — independent SHA-256 candidate verification — implementation handoff

2026-10-15, America/Los_Angeles. Branch `feat/e002-g1-independent-sha256`, created from updated `main` at exact base
**`8312e4518408b9b5df2aac96661eff8fb2bd273c`** (PR #5 confirmed `MERGED`, 2026-10-15T16:57:47Z). Work is **unstaged and uncommitted**
for Research Director review. Base inventory: `.tmp/e002-production-verification/g1a-base-inventory.json` (178 tracked files, 20 protected
`results/` files hashed). Final check: all 20 protected `results/` files are byte-identical and unrelated untracked work is untouched. Five tracked files from PR #5 are modified, all task-scoped: `src/e002_verify/production_evidence.py` (candidate hashing via the independent backend, `tally`, report identity), `src/hashlab/experiments/exp002_finalization.py` (report-identity gate only), `tools/qualify_e002_production_verification.py` (`--backend`), and tests `test_exp002_finalization.py` and `test_exp002_production_verification.py`. New: `sha256_independent.py`, `sha256_reference.py`, `tests/test_exp002_independent_sha256.py` and this handoff. No accepted scientific, statistical, generation or producer-hashing code changed.

**Result.** The independent verifier now evaluates every candidate digest with a SHA-256 implementation whose lineage is different from the
producer's, and the report says which one. **Algorithmic qualification: passed (bounded). Operational qualification for the full
180.2-million-candidate audit: open.** This is not G1 acceptance.

## 1. Backend selection and provenance

Runtime inspected: bundled CPython 3.12.14 on Windows 11 10.0.26200; `hashlib.sha256` is `_hashlib` over **OpenSSL 3.5.8** (the
producer's `SHA256Engine`, unchanged). No dependency was installed.

| Option | Lineage | Verdict |
|---|---|---|
| `hashlib` / `cryptography` 50.x | OpenSSL (the wheel bundles its own OpenSSL) | **Rejected** — same lineage as the producer |
| **`hacl`: CPython built-in `_sha2`** | HACL* (Project Everest) formally verified C, compiled into the interpreter | **Selected default.** Different codebase from OpenSSL, no new dependency, native speed, importable in the pinned interpreter |
| `cng`: Windows `bcrypt.dll` `BCryptHash` via ctypes | Microsoft CNG (`bcrypt.dll` 10.0.26100.1) | Accepted as a second independent native cross-check; Windows only |
| `reference`: pure-Python FIPS 180-4 (`sha256_reference.py`) | Written from the specification in this repository, no shared code | Accepted as the correctness oracle and for bounded replay; far too slow for the full audit |

Provenance statements and their strength: that CPython 3.12's `_sha2` is HACL*-based is the CPython source lineage (`Modules/_hacl`), not
something this run proves; the run proves instead that `_sha2` is a distinct built-in implementation object (`type(...).__module__ ==
'_sha2'`, not `_hashlib`), that it hashes correctly with the OpenSSL modules (`_hashlib`, `_ssl`, `ssl`) blocked in a subprocess, and that
it passes the published vectors. Identity recorded per run: `python.exe` SHA-256 `b847bb9f...09de8` and the SHA-256 of the binary that actually contains `_sha2`, `python312.dll`
(`2b6fffde96cf24a57fca642aaefd5788816ab5ef8624ea63b722cbceb94d49b1`); see §7 for why the second pin is required and for the interpreter-hash history.

**Limits of the independence claim.** It is independence of implementation lineage within one process, one machine and one CPU — not
independent hardware, operator or organization, and HACL*/OpenSSL/CNG may all use the same CPU SHA instructions. BLAKE2b (Feistel, N2,
A2 prefixes), MT19937 and the SHA-256 used for file pins and seed derivation remain on `hashlib`/OpenSSL; only research *candidate evaluation*
is moved. A reviewer wanting a second machine should run the verifier there with `--backend cng` or `reference`.

## 2. Interfaces

New (all in `src/e002_verify`, no `hashlab` imports):
* `sha256_independent.CandidateHasher(backend='hacl'|'cng'|'reference')`: `digest(candidate)` accepts only 8 or 80 raw `bytes` and returns
  the 32-byte big-endian digest; `evaluator()` is the hot-loop callable; `identity()` reports role `candidate-evaluation`, backend, lineage,
  known-answer status, interpreter pin, `independent_of_producer: true`. Construction runs the published known-answer vectors and fails closed
  with `BackendUnavailable` for an unknown/non-independent name (`hashlib`, `openssl`, …), a missing module, a non-Windows `cng`, or any wrong digest.
* `sha256_independent.file_integrity_backend()`: states that file/pin hashing stays on `hashlib` and is **not** used for candidates.
* `sha256_reference.sha256`: the pure-Python oracle.
* `production_evidence.verify_evidence(..., candidate_backend='hacl')`: constructs the hasher before reading any evidence; the candidate loop calls
  only that evaluator. The extracted `tally(row, effective, candidate, arm, cluster)` carries the unchanged success rule (strict
  `effective < 2**248`) and E3 counters. `production.transform` (P1/P2+/P2−), target, generation and accounting are untouched.
* Report: `independence.candidate_sha256` (identity above) and `independence.file_integrity_sha256`; the former `independence.sha256`
  (shared, non-independent) is removed.
* `tools/qualify_e002_production_verification.py verify --backend {hacl,cng,reference}`.
* Producer-side `exp002_finalization.parse_verification_report` (a new gate, not a change to any hashing): a production report is refused unless it
  identifies a candidate backend in `{hacl, cng, reference}` with `independent_of_producer: true`, `shared_with_producer: false` and known answers
  passed. No accepted scientific or statistical implementation, and not the producer's `SHA256Engine`, changed.

## 3. Qualification results

New tests: `tests/test_exp002_independent_sha256.py` (49 including parametrization over the three backends, two added at close-out; the rest of the 54 are updated report-identity cases in existing tests).
* **Known answers** (empty, `abc`, 448-bit, 896-bit and one-million-`a` vectors; the million-`a` vector for the reference is run once in the oracle test) pass for
  every backend.
* **Padding boundaries** 0, 1, 55, 56, 57, 63, 64, 65, 119, 120, 121, 127, 128, 129, 191, 192 and 1000 bytes, zero, `0xff`, mixed high-bit and random binary messages: all
  three backends equal the reference, the producer's `SHA256Engine` and OpenSSL, byte for byte.
* **Candidate encodings:** every 8- and 80-byte candidate of the bounded stream (≥ 78) agrees exactly with the producer and in big-endian integer value; digest byte order
  is pinned; repeated and interleaved calls and separate hasher instances share no state.
* **Strictness:** `str`, `bytearray`, `memoryview`, `None`, `int`, list and lengths 0/7/9/64/79/81 are rejected; `hashlib`, `openssl`, `sha256`, empty and `None` backends are refused;
  an absent `_sha2`, non-Windows `cng`, and backends returning wrong digests fail closed; the verifier refuses to start (even on a missing evidence path) without a valid backend.
* **Isolation:** with `_hashlib`/`_ssl`/`ssl` blocked the HACL* backend still works; a guard on the file-integrity hash proves no 8- or 80-byte candidate reaches it.
* **Target boundaries by injection (no hash search):** digests `T−1`, `T`, `T+1`, `0`, `2²⁵⁶−1` and `2²⁴⁷` classify as success/failure exactly under the unchanged strict rule, with first-byte and
  leading-zero counters correct; P1/P2+/P2− transformations at `T−1/T/T+1` and threshold-adjacent selector values match the specification.
* **Manipulation:** a backend that returns a flipped, zero, short, long or foreign digest at a chosen row is rejected; the 29 earlier resealed corruption tests still pass.

**Exact bounded replay** (real retained history, `g1a/`): one producer run (55.4 s, 856,698,880-byte peak working set, completion
`8562cf09b959cd831e1921ddf9fe74233520c9afec713c1d841c84f5e946e7da`), then three separate verifier runs on the same evidence, all passing with 78 candidates rehashed, 106 compression blocks,
identical accounting digest `47792c59…`, identical reports apart from the backend identity: `hacl` 6.1 s / 842,498,048 B, `cng` 6.0 s / 844,034,048 B, `reference` 6.3 s / 842,194,944 B.
Raw/effective digests, success classification and E3 accounting agree exactly. Evidence completeness/sealing, the capture gate and private-statistics checks (which use no candidate hashing) pass
unchanged in their existing tests; the bounded fixture is incomplete geometry, so the full-geometry statistics path is again exercised only with the artificial counts.

## 4. Test totals

| Run | Result |
|---|---|
| Focused (independent SHA-256 52 + components 81 + verification 112 + finalization 75 + kernel 92) | **414 passed**, 0 skipped, 36.04 s (412 before the close-out identity fix) |
| **Full offline regression** (`g1a-final/regression.txt`) | **1,890 passed, 2 failed, 2 skipped in 163.91 s** — *not green* (1,888 before the close-out fix) |

Baseline 1,836 + 54 new = 1,890; no new failures. The two failures are the inherited E001 snapshot tests (`.gitignore` size 367 vs 351) and the two skips are the Windows symlink-privilege
tests; neither is G1 acceptance and no test or E001 snapshot was weakened or changed.

## 5. Resource observations and feasibility (observations, not projections)

Bounded per-call observations, 200,000 calls each (reference: 4,000), microseconds per call: OpenSSL (producer) 0.61 (8 B) / 0.62 (80 B); **HACL\* 0.42 / 0.59**; CNG 1.16 / 1.16;
pure-Python reference 118 / 237. Whole-fixture overhead (78 candidates) is within noise (6.0–6.3 s, dominated by history loading).
* **HACL\* and CNG:** per-call cost is the same order as OpenSSL, so candidate evaluation is a small part of verifier cost (reconstruction dominates). A plausible full-scale strategy exists:
  the same single-threaded streaming verifier with `--backend hacl`, no extra dependency, memory unchanged. This is a plausibility statement, **not** a measured or guaranteed production runtime;
  no production-density benchmark was run and the earlier 40–50 min/26 GB figures remain projections.
* **Reference:** about 2×10² µs per call; applying that rate naively to 1.8×10⁸ candidates would be hours of added single-thread time, so it is retained **only as a bounded correctness oracle**.
* Operational risks to qualify: `_sha2` is a private CPython module name (present in 3.12+, must be pinned with the interpreter hash); `cng` exists only on Windows.

## 6. Status of Revision 8 §3.9 and remaining G1 obligations

* **§3.9 "different SHA-256 implementation" element:** *satisfied algorithmically and boundedly* — the verifier recomputes candidate digests with HACL* (or CNG, or the reference), not OpenSSL, and reports the backend.
* **§3.9 as a whole is not closed:** the always-on seeded 1 % audit (or authorized full audit), the final audit-policy decision, an approved audit format/seed provenance, and independent reproduction on a second machine remain open.
* **Operational qualification (full-scale feasibility): open.**

Remaining G1 obligations (unchanged by this task, none satisfied here): production-scale independent verification on the approved runtime/hardware and production-density producer qualification; blinding and resource
qualification; independent-verifier appointment, restored-copy run and signed/witnessed report; final audit-policy decision; external receipt, timestamp (C_pre and bundle), history-checkpoint, archive,
beacon (BLS) and authorization services; a production writer that satisfies the verifier's contract (including seeded-configuration/started-entry binding in `environment.json`); the strict E001 numerical/runtime disposition,
the two inherited snapshot failures and the symlink skips; then separately authorized QA2, G2 smoke, release/freeze, commitments/beacon procedure and exact-attempt execution approval.
The A1 rare refinement divergence (~10⁻²⁸ per full run, fail-closed) remains documented with no waiver. Production execution, capture issuance and receipt verification remain unavailable.

## 7. Close-out: runtime provenance review (G1-A final acceptance)

Inspected on the reviewed runtime, with no change to historical evidence.

| Item | Observed |
|---|---|
| Executable | `C:\Users\geova\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, 107,312 bytes, SHA-256 `b847bb9f4e48c19f585c8bf7d8b355f3f8c6d2125717ece9c9d7e16fb9f09de8` |
| Version / platform | CPython 3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit], Windows-11-10.0.26200-SP0 |
| Identity of `_sha2` | **Built-in** module (`'_sha2' in sys.builtin_module_names`, no `__file__`, spec origin `built-in`); `_hashlib` is *not* built-in |
| Container of `_sha2` | `python312.dll`, 6,985,520 bytes, SHA-256 `2b6fffde96cf24a57fca642aaefd5788816ab5ef8624ea63b722cbceb94d49b1`, confirmed as the loaded module via `GetModuleFileNameW` |
| OpenSSL | separate files `libcrypto-3-x64.dll`, `libssl-3-x64.dll`, `_hashlib.pyd`, `_ssl.pyd` in `DLLs/`; `python312.dll` does not import them (its imports are the system CRT and Windows libraries, including `bcrypt.dll`) |
| HACL* lineage evidence | CPython 3.12 source: SHA-2 module backed by HACL* (`Modules/_hacl`). Binary evidence: `python312.dll` embeds the build path `...\Python-3.12.14\Modules\_hacl\Hacl_Hash_SHA3.c`, so the HACL* source tree is compiled into this DLL. The embedded path names the SHA-3 file, not `Hacl_Hash_SHA2.c`, so this is **supporting** evidence of the HACL* tree, not proof of the SHA-2 code path; correctness rests on the known-answer and differential tests |
| Default backend | `hacl` (`CandidateHasher()` default; `--backend` optional) |
| Why `hashlib.sha256` stays for file integrity only | It is the same OpenSSL implementation the producer uses for candidates. That is fine for pins, manifests and inventories (any correct SHA-256 suffices) but would not be an independent check of candidate digests; the report states both roles separately |

**Discrepancy 1 — interpreter hash change (explained, not repaired).** Retained producer environments record `python.exe` SHA-256 `d41bad46...` up to
the 2026-10-13 21:27 run and `b847bb9f...` from the 2026-10-14 19:09 run onward; both report CPython 3.12.14 with the identical build timestamp. The runtime
files on disk were created about 2026-10-14 11:58 (directory created 2026-10-13 21:34), between those runs, so the bundled runtime directory was re-materialized by the environment
between sessions; nothing was installed or replaced by this work. The cause is inferred from file times and retained records, not proven. The earlier `python312.dll` hash was never recorded, so it cannot be
established whether the `_sha2` bytes changed. Historical evidence was not modified; any plan bound to `d41bad46...` would correctly fail `validate_local_inputs` on this runtime.

**Discrepancy 2 — material, fixed in this milestone.** On Windows `_sha2` lives in `python312.dll`, not in the 107 KB `python.exe` launcher, so the previously recorded interpreter hash
did **not** pin the code that evaluates candidates. The candidate-backend identity now also records the loaded `python312.dll` path and SHA-256 and whether it embeds the HACL* source-tree path
(`sha256_independent._sha2_container`; tests cover it and the actual verifier report carries it). The three bounded verifier re-runs (`g1a-final/`) pass on the same retained evidence with the new
field: `hacl` 6.1 s, `cng` 6.1 s, `reference` 6.2 s; 78 candidates, 106 blocks, identical accounting, bound to completion `8562cf09...`.

**Discrepancy 3 — open, producer side, not changed here.** The producer's `observe_runtime()` binds only `python.exe` and PyYAML; it does not pin `python312.dll` or the OpenSSL library
(`libcrypto-3-x64.dll`) that actually evaluates the producer's SHA-256. A production runtime binding for G1 should pin the interpreter DLL and the cryptographic libraries on both sides.

**Distinctions.** *Verified algorithmic correctness:* known-answer, padding-boundary, candidate-encoding and differential tests; exact bounded replay through the actual verifier with all three backends; fail-closed behavior.
*Supported implementation-lineage evidence:* CPython 3.12 source lineage and the embedded HACL* source-tree path; built-in module identity; operation with the OpenSSL modules blocked. *Runtime artifact identity:* `python.exe` and `python312.dll` hashes above (a re-materialized runtime whose executable hash differs from earlier milestones).
*Still unmeasured:* full-scale operational feasibility (no production-density run; per-call observations only), second-machine reproduction, and the seeded/full audit policy. Production activation remains disabled.
