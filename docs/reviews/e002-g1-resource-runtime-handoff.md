# E002 G1-B — production resource and runtime qualification — implementation handoff

2026-10-15, America/Los_Angeles. Branch `feat/e002-g1-resource-qualification`, created from updated `main` at exact base
**`9737010c1e1e125bbd6d5da22de4d70c58bc64e4`** (PR #6 confirmed `MERGED`, 2026-10-16T03:55:57Z; local `main` fast-forwarded from `origin/main`).
Work is **unstaged and uncommitted** for Research Director review. Base inventory (181 tracked files, 20 protected `results/` files, S1.4 audit files):
`docs/reviews/e002-g1-resource-runtime-data/base-inventory.json`. Raw probe results, host/runtime record, resource-model output and the bounded end-to-end
reports are in `docs/reviews/e002-g1-resource-runtime-data/`.

**Verdict.** On the intended hardware class (this host), the frozen E002 workload **is computationally practical**: a single-threaded producer is projected at
**≈ 2.2 – 5.8 h** (central ≈ 2.9 h), the preferred full independent audit at **≈ 0.7 – 2.1 h** (central ≈ 1.0 h), evidence is **25.94 GB** in 43,995 chunk files, and peak memory
is **≈ 0.86 GB** per process. SHA-256 is not a bottleneck (0.4–0.6 µs per candidate). Algorithm D (A1) is the single largest cost. **No optimization is needed for feasibility.**
These are *projections from bounded probes*, not a measured full run; the main residual uncertainties are the unprobed target media and the lack of any sustained-run
measurement (§7, §10). The producer runtime-binding gap (Discrepancy 3 of G1-A) is **closed** (§1). Production remains disabled. This is not G1 acceptance.

## 0. Research Director disposition (2026-10-16)

The Director accepted G1-B at **bounded engineering scope**. The frozen workload *appears* feasible on the measured host; this is a projection, **not** completed full-scale resource qualification and **not** G1 acceptance. Recorded decisions:

1. **Execution storage.** The active experiment prefers the qualified local NVMe volume (`C:`, measured). Unqualified USB storage (`D:`, `E:`) is **not** to be designated as the primary execution target. Archival destinations remain to be selected and qualified against Revision 9's two off-machine failure-domain copies, one offline or retention/version protected.
2. **Machine continuity.** Single uninterrupted-attempt model: no automatic resume, retry, new seed, journal repair or silent continuation after a restart; incomplete evidence is retained on failure; no new attempt lifecycle and no change to accepted E4/R9 requirements. (§10 item 5 is accordingly narrowed to operational qualification of keep-awake/Defender policy for that model.)
3. **Abort limits.** The *principle* of predeclared, outcome-blind resource abort thresholds is approved. The numerical values in §10 item 4 are **proposals only and not approved**; they stay here for explicit Director review before any production activation.
4. **Performance.** Accepted sampling and hashing implementations stay unchanged; the measurements do not justify optimization, and §6 is retained for information only.

**Measured vs projected (read this before citing any duration).** *Measured* (bounded single runs): A1 outputs 1–10,000 of 30,000,000 (≈ 105 µs producer / 51 µs verifier per output), five synthetic late-state A1 geometries, A3 up to 27,600 ranks, 100,000 control inversions, 10,000 artificial evidence rows, 10,000 hash evaluations per backend, and a 255 MiB NVMe chunk-shaped write probe. *Projected* (not measured): every full-workload figure — the 2.2–5.8 h producer, 0.7–2.1 h audit and archival times — including **A1 later-stream behaviour** (only 0.03 % of the stream and a few synthetic states were observed; the dense-tail Method A frequency is unsampled) and **sustained evidence I/O** (43,995 fsynced chunks were never written in one run; the disk probe was 454 files on NVMe with Defender on). Full integrated execution and the full independent audit have **not** run; USB and archival media are **unqualified**.

**Finalization checks (this review pass).** All 12 probe results have `status: completed` with external wall times of 0.19–2.79 s against caps of 30/60 s, within the stated record counts (no retries, no extended workloads). The recorded full regression (`regression.txt`, finished 21:23:33) postdates the last modification of every source, test and tool file (latest 21:18:02), so it corresponds to the final implementation; only this handoff text changed afterwards. The 20 protected `results/` files match the base inventory byte for byte, and no retained `.tmp` evidence outside `.tmp/e002-g1b/` has a modification time after G1-B work began.

## 1. Runtime-binding correction (producer + verifier)

**Problem (G1-A Discrepancy 3).** `observe_runtime()` pinned `python.exe` and PyYAML only. On this runtime `hashlib.sha256` is the `_hashlib.pyd` extension over
`libcrypto-3-x64.dll`, and the interpreter itself lives in `python312.dll`; none of those was pinned.

**Change (narrow, additive).**
* `src/hashlab/experiments/exp002_runtime_identity.py` (new): `observe_hashing_identity()` first exercises `hashlib.sha256` (known answer, and checks
  `type(hashlib.sha256()).__module__ == '_hashlib'` and `hashlib.sha256 is _hashlib.openssl_sha256`), then reads the **loaded-module list of the running process**
  (`EnumProcessModules`, not a guessed path) and records, per role, exact path, size and SHA-256 for: `interpreter`, `python_dll`, `hashlib_extension` (must equal `_hashlib.__file__`),
  `libcrypto` (exactly one loaded module), and `VCRUNTIME140.dll` as `crt`; plus the OpenSSL version asked of the **already loaded** library (`GetModuleHandle`, never `LoadLibrary`) and the Python version.
  Zero or ambiguous matches, a non-Windows platform, or a failed known answer raise `ValueError` (fail closed).
* `RuntimeBinding` gains an optional `hashing` field (omitted from `to_dict()` when `None`, so every legacy serialization is byte-identical); `observe_runtime()` always fills it;
  `ProductionPlan` **requires** it; the `hashing` interpreter row must equal `interpreter_sha256`. `validate_local_inputs` already compares the full observed binding, so a swapped DLL now fails there.
* `src/e002_verify/runtime_identity.py` (new, no `hashlab` imports, no shared code): validates the declared identity's shape and, with `--observe-hashing`, re-observes this process using a **different Windows API**
  (ToolHelp32 snapshot instead of `EnumProcessModules`) and compares role/size/SHA-256/versions. `production_evidence._runtime_shape` accepts the legacy 4-key runtime for bounded scopes and **requires `hashing` for production**.
  The report adds `independence.producer_hashing_identity` (declared hash; whether it was matched against the verifier's own loaded stack). Producer finalization refuses a report that does not carry it.
  The verifier's own candidate-hashing identity (`independence.candidate_sha256`, HACL\* in `python312.dll`) is unchanged and remains separate.
* `create_root(..., minimum_free_bytes=None)` (see §8) — optional, default behaviour unchanged.

**Observed identity on this host** (`environment.json`): `python.exe` `b847bb9f…09de8`; `python312.dll` `2b6fffde…49b1` (6,985,520 B); `_hashlib.pyd` `b9880771…330f` (70,448 B);
`libcrypto-3-x64.dll` `57df468e…7e8a` (8,003,376 B, **OpenSSL 3.5.8 25 Aug 2026**); `VCRUNTIME140.dll` `d5e4d9a3…9066`. The two independent observers return identical records.

**Integration finding fixed during qualification.** The first end-to-end bounded run failed closed (`declared producer hashing identity differs from the loaded stack: artifact bytes`) because my first draft also pinned
every `vcruntime140*`/`ucrtbase` module: `VCRUNTIME140_1.dll` is loaded by unrelated extensions in the producer process but not in the verifier. Only the hashing-relevant `VCRUNTIME140.dll` is now pinned, and a regression test compares identities across processes
with different imports. The failed attempt is retained unmodified under `.tmp/e002-g1b/bounded/attempt1-incidental-crt-mismatch/`.

**Evidence.** `tests/test_exp002_runtime_identity.py` (11 tests): both observers find the actual loaded `_hashlib`/`libcrypto`/`python312.dll`; guessed locations are ignored (missing or duplicate `libcrypto` modules are refused);
a **one-bit-altered copy** of `python312.dll`, `_hashlib.pyd` or `libcrypto` at the enumerated path changes the identity and the verifier comparison reports `artifact bytes`; an altered OpenSSL version is reported; shape rejections (missing/duplicate role, bad hex, unknown role,
wrong provider, extra key); interpreter row ≠ `interpreter_sha256`; production runtime without `hashing` refused. Bounded end-to-end (78 public-input candidates): producer `environment.json` carries the five-artifact identity;
the verifier with `--observe-hashing` passed (`locally_observed_and_matched: true`), 78 candidates / 106 blocks, accounting digest `47792c59…` **identical to G1-A**.

**Limits.** Windows only (other platforms refuse). It pins the *files that were loaded*, not CPU microcode or the OS (`bcrypt.dll`/`ucrtbase.dll` are system components and deliberately excluded because Windows servicing would churn them). Nothing in accepted evidence was rewritten;
any plan bound to the old source inventory or the pre-G1-A interpreter hash correctly no longer validates (the source inventory itself grew by the new modules).

## 2. Host, OS, Python and native identities (`environment.json`)

| Item | Value |
|---|---|
| Host | Lenovo 90YJ001KUS; AMD Ryzen 7 7800X3D, 8 cores / 16 threads (base 4.2 GHz); 33,947,426,816 B RAM (14.98 GB available at probe start) |
| OS | Windows 11 10.0.26200 (SP0); Microsoft Defender real-time protection **on** during all probes |
| Python | CPython 3.12.14 (main, Aug 25 2026) MSC v.1944 64-bit — bundled runtime `…\codex-primary-runtime\dependencies\python\` |
| Native | `python312.dll`, `_hashlib.pyd`, `libcrypto-3-x64.dll` (OpenSSL 3.5.8), `VCRUNTIME140.dll` — hashes above; verifier candidate backend HACL\* (`_sha2` inside `python312.dll`) |
| Volumes | `C:` WD PC SN740 1 TB NVMe, NTFS, 120.1 GB free (probe volume, repository volume); `D:` Avolusion PRO-5X 7.45 TB **USB HDD**, 1,040 GB free; `E:` LaCie d2 1.86 TB USB, 127 GB free |

## 3. Measurement method and exact limits

`tools/measure_e002_g1b.py` runs each probe in its **own child process** under an **external wall-clock cap** (hard kill by the parent) plus a soft in-process deadline; results are refused-overwrite JSON (no retries, no parameter changes after observation).
Fixed public engineering identities only: A1 sub-seeds 101/102, A3 201/202 (the retained I-series fixture seeds), control keys from `control_keys(0, 'experiment-002-kat')`, A2 prefix key `E002-I1!`. No production master seed, beacon, QA2 or E002 stream was used.
Memory is process peak working set (`GetProcessMemoryInfo`). Single run per probe (the brief forbids extending/retrying), so run-to-run variance is **not** measured; percentiles are within-run.

| Probe | Declared bound | Cap | Outcome |
|---|---|---|---|
| A1 producer / verifier, first 1,000 ranks | 1,000 outputs, no hashing | 30 s | completed 0.23 s / 0.19 s |
| A1 continuation (the single predeclared one, triggered because the first completed) | 10,000 outputs | 60 s | completed 1.20 s / 0.66 s |
| A1 synthetic late-state (producer / verifier) | 5 fixed remaining-population states, same N/n | 60 s | completed 0.37 s / 0.25 s |
| A3 | ≤ 100,000 ranks scanned, ≤ 10,000 emitted | 30 s | 10,000 emitted over 27,600 ranks; 1.07 s |
| N1/P/N2 | ≤ 100,000 inversions, ≤ 10,000 emitted per component | 30 s | 100,000 inversions, 10,000 per component; 2.79 s |
| Serialization | ≤ 10,000 artificial rows | 60 s | 10,000 rows, 3 chunks; 0.52 s |
| Hashing (producer, verifier) | ≤ 10,000 evaluations each | 60 s | 10,000 each; 0.35 s / 0.41 s |
| Disposable I/O | ≤ 256 MiB | 60 s | 454 files × 590,000 B = 255.4 MiB; 2.64 s |

No probe approached its cap. The disposable I/O probe was run once, on `C:` (the repository volume); the intended off-machine/archival media were **not** probed because no target volume has been designated.
A1 early-stream measurements are labelled as such: they cover outputs 1–10,000 of 30,000,000 at N/n = 143.13 and say nothing about the other 99.97 % beyond the synthetic probe below.

## 4. Measured results

### 4.1 A1 — exact Algorithm D (N = 4,293,918,720; 2 × 15,000,000 selections)
| | Producer (Decimal) | Independent verifier (interval arithmetic) |
|---|---|---|
| Latency, first 1,000 / first 10,000 (mean) | 105.4 µs / 104.9 µs | 51.5 µs / 51.4 µs |
| p50 / p90 / p99 / max (first 10,000) | 104.1 / 113.6 / 172.3 / 512.7 µs | 51.0 / 57.4 / 74.2 / 921 µs |
| Peak memory | 30.8 MB | 31.0 MB |
| Random 64-bit blocks (selection stream) | exactly 2.0 per output (20,000 for 10,000) — one for the geometric proposal, one for the squeeze test | identical |
| Stage-allocation draws | 11,197 per 10,000 outputs | identical |

Both implementations emitted **identical rank sequences** (SHA-256 of ranks `ce405f76…` for 1,000 and `93d58187…` for 10,000; last rank 1,388,795).
**Distribution of expensive operations:** every one of the 10,000 outputs had the same profile — 4 certified comparisons, 5 `Decimal` contexts at 40-digit precision (never escalated), 2 initial uniform draws and **zero** refinement beyond the first 64 bits,
1 geometric proposal (no D4 rejection, no binary-search fallback, no `_acceptance` product). The slowest outputs (e.g. 513 µs) have the same operation counts, so tail latency is OS/timer noise, not data-dependent arithmetic.
Exact-arithmetic cost is therefore a near-constant ≈ 100 µs/output of `Decimal` context construction and bounded division/multiplication; the refinement cap (4,096 bits) was never approached.

**Synthetic late-state probe** (clearly labelled; same N/n geometry, seed 7001; µs/output producer / verifier): N = 4,293,919, n = 30,000: 97.3 / 44.7 (2,000 outputs);
N = 42,939, n = 300: 149.0 / 91.1; N = 1,431, n = 10: 116 / 55.6; N = 130, n = 10 (13n ≥ N, **dense-tail Method A** engaged): 152.8 / 22.7; N = 26, n = 2: 18.1 / 7.7. Per-output cost stays within ≈ 1.5× the early stream; the last states have only tens of outputs, so they are
shape checks, not timing evidence. **Not established:** the actual 30-million-output runtime; the real probability and cost of the Method A dense tail near the end (it is fail-closed and bounded here, but its tail frequency was not sampled).

### 4.2 A3 — Algorithm S with exclusions, rank enumeration (population 82,128,984, 60,721 real exclusions)
Authenticated read-only load of the S1.4 exclusions: 0.50 s. Scan until 10,000 emitted (27,600 ranks scanned, 592 exclusions inside): **17.5 ms**, i.e. 1.75 µs per emitted and 0.633 µs per scanned rank (the two `randrange` streams alone are 0.19 and 0.17 µs; the remainder is generator/exclusion bookkeeping).
Producer `unrank` 3.9 µs for the early ranks (weights 1–3) and 4.97 µs for 10,000 **evenly spaced ranks across the whole population** (weights 5–6; labelled SYNTHETIC, not a scan); `rank` 4.7 µs; `to_bytes` 0.05 µs; `Attempt` construction 4.5 µs; kernel eligibility re-check (bisect + `rank(value)`) 4.5 µs.
Verifier: scan 2.21 µs/emitted with **identical ranks and values**; incremental Gosper step 0.18 µs/value (early) and 0.14 µs/value in the weight-6 region (SYNTHETIC position); independent colex decoders 1.9 µs (unrank) / 3.3 µs (rank). Peak 43.6 MB.
Caveat: the first 100,000 ranks cover only weights 1–3 (part of 4); unrank loop length depends on weight, hence the spaced synthetic measurement.

### 4.3 N1 / P / N2 and history
100,000 occurrences read from the authenticated retained file and inverted: Feistel inverse 6.83 µs producer / 5.79 µs verifier (**outputs agree**); forward 6.80 µs (N1), 6.79 µs (P) producer / 5.69 µs verifier (agree); single BLAKE2b round function 1.02 µs;
structural `C1/C3` check 1.15 µs producer / 0.12 µs verifier; membership in the 100k-element inverse set 0.03 µs. N2: 80-byte stream 1.49 µs producer / 0.93 µs verifier (byte-identical), A2 membership 0.08 µs.
Whole providers (row dictionaries included): N1 8.37, P 7.99, N2 3.73 µs per attempt; `Attempt.from_provider` encoding 4.95 µs. No rejection occurred in 10,000 N1 attempts (C1/C3/E001/A2 all zero), as expected for 64-bit values against a 7 M history.
Peak 90 MB. **Not representative:** the inverse set had 100k members, not 6.05 M distinct (cache-miss cost of lookups and the 0.84 GB set are taken from the existing I2/I3 resource evidence, not re-measured); history load at full scale is projected as 7.0 M × (inverse + 0.2 µs) ≈ 50 s, consistent with the 55–62 s bounded producer runs that load the real history.

### 4.4 Evidence rows, durability, verifier throughput
10,000 artificial public-input rows (13 stream/stage combinations, 8- and 80-byte candidates, 99 rejections, `source_index` up to 2⁶³+, `byte_offset` = 80 × 3·10⁷, ranks near 82,128,983; 9,901 hashed with OpenSSL and again with HACL\*):

| Quantity | Measured |
|---|---|
| Bytes per row | **120** (8-byte accepted), **192** (80-byte accepted), 56 / 128 (rejected); mean 141.5 |
| Chunk framing / index | 76 B per chunk + 157 B index line per chunk (3 chunks) |
| `encode_row` CPU | 1.32 µs/row |
| `Accumulator.add` incl. record validation | 3.99 µs/row; `ControlEngine.transform` 1.19 µs |
| `ChunkWriter` incl. fsync and per-chunk re-read inventory | 4.13 µs/row (41 ms for 3 chunks, n = 3: uncertain) |
| Producer `iter_chunks` replay incl. decode | 21.6 ms/chunk (5.3 µs/row) |
| Independent re-hash (HACL\*) | 0.45 µs/candidate (0.38 µs w8, 0.50 µs w80); OpenSSL producer 0.57 µs |
| Peak memory | 42 MB |

Disposable I/O probe on `C:` (NVMe, Defender on; 454 files shaped like real chunks, fsync each): **399 MB/s** sustained write, **1.48 ms per file** create+write+fsync (fsync 41 % of the time), directory listing 1.2 ms, first sequential read **166 MB/s**, hot re-read + SHA-256 inventory **1,630 MB/s**.
The read figure is for just-written files and is not a cold-read figure; the 3-chunk `ChunkWriter` figure (≈ 9–14 ms per chunk) is roughly an order of magnitude above the 1.5 ms/file I/O probe and is not understood (n = 3, includes encoding) — the resource model carries both.

## 5. Resource model

Counts are the frozen geometry: 180,200,000 evaluations (A1 30 M, A2 30 M, A3 30 M, N1 30 M, N2 30 M, P1 0.2 M, P2+ 15 M, P2− 15 M), ≈ 240.2 M compression blocks, a second 180.2 M for the audit.
`tools/model_e002_g1b_resources.py` (inputs: the retained probe JSON) prints stage tables. Each stage is **M** (measured rate), **D** (derived from measured components) or **A** (assumption). Ranges: CPU stages low = measured, central × 1.25, high × 2.5
(bounded probes of ≤ 10⁴ events cannot show sustained-run effects such as allocator growth, cache pressure, thermal or Defender behaviour); assumptions × 0.5 / × 1 / × 3–6. The 78-candidate fixture was **not** used for projection.

| Group (single-threaded) | Low | Central | High | Basis |
|---|---|---|---|---|
| A1 generation (30 M ranks) | 0:52 | 1:06 | 2:11 | M (early + synthetic late-state mean) |
| A2 generation | 0:02 | 0:03 | 0:09 | **A** — not individually probed |
| A3 enumeration (scan + unrank + encode) | 0:03 | 0:04 | 0:08 | D; full scan ≈ 52 s at 0.633 µs/rank × 82.1 M |
| N1 + P + N2 generation and history checks | 0:10 | 0:13 | 0:25 | M |
| Kernel eligibility re-check | 0:13 | 0:16 | 0:32 | D (second Feistel/rank per control or A3) |
| Attempt + accounting + transform | 0:29 | 0:36 | 1:13 | M |
| SHA-256 evaluation (180.2 M) | 0:02 | 0:02 | 0:04 | M |
| Serialization CPU | 0:04 | 0:05 | 0:10 | M |
| Durable chunk writes + fsync + inventory (43,995 files) | 0:01 | 0:06 | 0:15 | M, two conflicting estimates (§4.4) |
| History load + capture replay | 0:17 | 0:21 | 0:42 | D/M |
| **Producer total** | **2:13** | **2:51** | **5:50** | h:mm |
| **Independent audit total** (A1 regeneration 0:26/0:32/1:04 dominates; Feistel/N2/A3 0:07/0:09/0:18; re-hash 0:01/0:02/0:03; row comparison **A** 0:05/0:09/0:27; history 0:01; read 25.9 GB at 166 MB/s 0:03) | **0:43** | **0:57** | **2:03** | |
| Finalization/archival (inventory re-read, 2 copies, re-hash, restored-copy read) — copy rate **assumed 150 MB/s**, media unspecified | 0:11 | 0:18 | 1:22 | **A** |
| **Sequential end-to-end** (producer → audit → archival) | **3:07** | **4:06** | **9:15** | |

Full per-stage tables: `resource-model.md`. The stage ordering is stable under every multiplier: A1 (producer) ≈ 38 %, per-attempt Python accounting ≈ 22 %, eligibility + capture replay ≈ 20 %; A1 regeneration ≈ 56 % of the audit.

**Storage (derived exactly from the frozen layout; verified against measured row sizes).** Accepted rows 120.2 M × 120 B + 60 M × 192 B = **25,944,000,000 B**; plus framing 3.3 MB, index ≈ 6.9 MB (measured 157 B/line), plus ≤ 256 MB for the rejection allowance
(expected ≈ 0 rejections: 2⁻³² C1 probability per N1/P value). Evidence ≈ **25.95 GB (24.2 GiB)** in **43,995 chunk files**. `exp002_resource_preflight.required_free_bytes()` = **29.09 GiB** (+ 10 % + 2 GiB + 2 M-row rejection allowance).
Copies: local evidence + **two off-machine failure-domain copies, one offline or retention/version-protected** = 3 × 25.95 ≈ **77.9 GB**; a restored-copy verification adds a fourth working copy ≈ **103.8 GB** of capacity across media. The producer and verifier use **no temporary working space** (append-only writer; verifier streams one ≈ 0.6–0.8 MB chunk at a time).
`C:` has 120.1 GB free, `D:` 1,040 GB, `E:` 127 GB — capacity is adequate for one local copy but the two off-machine copies must be on separate media/machines (not designated).
**Memory:** producer 858 MB and verifier 846 MB peak working set on the bounded run that loads the **real** 7 M-occurrence history (the set dominates; accumulator, prefixes and exclusions add < 5 MB; A1/A3 state is O(1)). Both together ≈ 1.7 GB of 32 GB.

## 6. Bottlenecks and feasible optimizations (for separate review; none applied)

1. **A1 `Decimal` construction** (~100 µs/output; 5 contexts per output, all at 40 digits). Candidate optimizations: reuse per-precision contexts; a certified integer/`Fraction` fast path for the comparisons that currently decide at 64 bits. **Scientific implication:** must return the identical certified decision for every comparison (all 10,000 observed decisions resolve at 64 bits, but that is not a proof); requires differential testing against the frozen implementation over many states and proof that endpoints still enclose the true probability. Using the verifier's faster interval implementation in the producer would **destroy independence** — do not.
2. **Verifier A1 parallelism / arm parallelism.** Arms are seed-independent; the verifier could regenerate A1 and the controls in separate processes (wall-clock ≈ A1 alone, 0.4–1.1 h). No effect on correctness if the row-by-row comparison order and evidence ordering are preserved by a deterministic merge.
3. **Producer eligibility re-check** duplicates the provider's Feistel/rank (≈ 13–32 min). Memoizing provider output would weaken the self-check; it should be kept unless the Director accepts that trade.
4. **Per-attempt object validation** (`Attempt` + `CandidateRecord` + accumulator ≈ 10 µs, ≈ 29–73 min): can be batched only without changing the validation outcomes; low value.
5. **Chunk files:** 43,995 small files with an fsync each is the pattern most sensitive to the destination media (§7).

Bounded evidence says none of these is required to finish in a working day; they matter only if sustained-run or media measurements come in far above the central estimate.

## 7. What the measurements do **not** justify

* A full-workload runtime from any single rate: no integrated, sustained, production-density run exists. The model composes independently measured stages, ignores interaction effects and uses multipliers that are assumptions.
* A1 beyond the first 10,000 outputs (only the labelled synthetic states); the Method A dense-tail frequency near the end.
* Disk behaviour on the **intended** media. `C:` NVMe numbers (399 MB/s, 1.5 ms/file) say nothing about the USB HDDs, where 43,995 fsyncs of ≈ 0.6 MB files could add tens of minutes; the page cache inflates the read figures.
* Memory beyond the bounded real-history runs (accepted as representative because the history set dominates).
* A2 generation (assumption), verifier row comparison/tally (assumption anchored to 1.15 µs/row from G1-A), archival copy rates (assumption).
* Run-to-run variance: each probe ran once by instruction.

## 8. Failure-handling qualification (`tests/test_exp002_g1b_resource_failures.py`, 38 tests + 3 in `test_exp002_production_verification.py`)

Synthetic fault injection into the real `run_engineering` kernel (unit fixtures) and `ChunkWriter`. Every case asserts a sanitized `KernelFailure` with no chained exception text, **no `complete.json`**, evidence retained, `failure.json` equal to the sanitized `F1` report (or absent when the disk is full),
`authenticate_capture` refusing the directory, a rerun into the same directory refusing, and — via call counters — **one scheduling pass and ≤ 206 hash evaluations** (no silent retry, no seed substitution; the engineering plan has no seed or retry parameter).

| Mode | Injection | Result |
|---|---|---|
| Disk full | `ENOSPC` at chunk create, early/late chunk write, fsync, index write, `accounting.json`, `complete.json` | all fail closed, none completes |
| Insufficient free space before execution | `exp002_resource_preflight.check_free_space` via `create_root(minimum_free_bytes=…)` | refuses **before** the directory or `INCOMPLETE` marker exists; passes at exactly the requirement |
| Out-of-memory / interruption / I/O error | `MemoryError`, `KeyboardInterrupt`, `OSError(EIO)` in `Accumulator.add`, `encode_row`, SHA-256 | all fail closed, evidence retained |
| Interrupted writes | chunk truncated at header / mid-row / before trailer / trailer tail | both readers refuse, also after re-sealing the transport hashes |
| Corrupted inventory | truncated/dropped/duplicated/swapped lines, altered hash or size, garbage tail, empty file, missing chunk (4-chunk real `ChunkWriter` output); whole-run inventory damage vs the completion pin and reference verifier | all rejected |
| Runtime DLL/hash mismatch | altered `libcrypto` digest in the observed runtime → `ProductionPlan.validate_local_inputs`; altered artifacts in the verifier comparison | refused, nothing created |
| Verifier interruption | `KeyboardInterrupt`/`MemoryError`/`OSError` mid-rehash in the production verifier and the reference verifier | no report returned, evidence directory byte-identical, a fresh run passes |
| Incomplete finalization | `INCOMPLETE` beside `complete.json`; `complete.json` missing | no authentication; production inspection stays `withheld` |

**Observations, not defects:** (i) no free-space preflight existed; the optional `minimum_free_bytes` parameter is the only change to E4 code (default `None` = unchanged behaviour; the production writer remains disabled and must pass `required_free_bytes()`).
(ii) `complete.json` creation follows removal of the `INCOMPLETE` marker; a crash between the two leaves a directory with neither, which every reader rejects (it has no completion pin) and which gets `failure.json` — acceptable, but a finalization procedure should treat "neither marker" as failed. No E4/R9 semantics were modified.
The `ENOSPC` handling relies on the writer's existing poison-and-abandon design, which these tests confirm.

## 9. Qualification

| Run | Result |
|---|---|
| Focused (independent SHA-256, components, production verification, finalization, kernel, runtime identity, resource failures) | **466 passed**, 0 failed, 50.4 s |
| **Full offline regression** (`.tmp/e002-g1b/regression.txt`) | **1,942 passed, 2 failed, 2 skipped in 191.9 s** — *not green*; the same two inherited E001 snapshot failures (`.gitignore` size 367 vs 351) and two Windows symlink-privilege skips as the last reported baseline (1,890 passed). 52 tests added (11 runtime-identity, 38 resource-failure, 3 verifier-interruption) |
| Bounded end-to-end with the new binding | producer 61.9 s / 858 MB, verifier (`--observe-hashing`) 6.4 s / 846 MB; accounting `47792c59…` unchanged |

Preservation: all 20 protected `results/` files (and the 7 S1.4 audit files hashed) are byte-identical to the G1-A base inventory; the 564 retained files under `.tmp/` outside `e002-g1b/` (I1/I2/I3, kernel, production-verification evidence) are byte-identical to a pre-work snapshot (0 differences; final re-hash after all work).
E001/S1.4 sources are untouched; the two inherited failures are unchanged and are **not** treated as satisfying G1.

## 10. Remaining G1 blockers (specific)

1. **Target and archival media undecided/unprobed.** Designate the production volume and the two off-machine failure-domain copies (one offline or retention-protected), then run the ≤ 256 MiB chunk-shaped probe there (USB HDD behaviour with 43,995 fsyncs is the largest unmeasured resource risk), and measure copy/re-hash rates.
2. **No sustained, integrated run.** Authorize one *synthetic* integrated rehearsal (public `experiment-002-kat` identities, e.g. 1–5 % of the geometry, real writer + verifier) to replace the composed model with a measured integrated rate and variance; it should include the A1 dense tail if a state can be constructed without a production seed.
3. **Pinned production runtime.** The bundled runtime directory was re-materialized between sessions earlier (G1-A Discrepancy 1). The producer now pins the loaded stack, but a specific frozen interpreter must be chosen, its identity recorded before the plan and re-observed at start and end of the run (the observer exists; the disabled activation adapter does not yet call it).
4. **Operational abort limits are proposals, not code** (production is disabled): preflight free space ≥ 29.09 GiB (+ copy capacity); process working set > 4 GiB; A1 > 400 µs/output averaged over the first 1 % (4× measured); mean chunk commit > 100 ms over 100 chunks; any `ENOSPC`/`MemoryError`/I/O error; runtime identity differing between start and end. Each abort is a disclosed failure with no resume, retry or seed replacement and must be predeclared and outcome-blind. Needs Director approval.
5. **Machine continuity.** A 3–6 h producer run must survive sleep/updates/Defender activity; keep-awake and exclusion policy are undecided (Defender was on for every probe).
6. **Still open from G1-A:** second-machine/restored-copy verification, final audit policy, independent-verifier appointment, external receipt/timestamp/beacon services, the two inherited E001 snapshot failures and symlink skips, and the A1 rare-refinement divergence waiver decision. Production execution, capture issuance and receipt verification remain unavailable.

## 11. Files

New: `src/hashlab/experiments/exp002_runtime_identity.py`, `src/hashlab/experiments/exp002_resource_preflight.py`, `src/e002_verify/runtime_identity.py`, `tools/measure_e002_g1b.py`, `tools/model_e002_g1b_resources.py`,
`tests/hashing_fixture.py`, `tests/test_exp002_runtime_identity.py`, `tests/test_exp002_g1b_resource_failures.py`, `docs/reviews/e002-g1-resource-runtime-data/`, this handoff.
Modified (task-scoped): `exp002_kernel_plan.py` (optional `hashing`, production requirement), `exp002_kernel_evidence.py` (`create_root` optional preflight), `exp002_finalization.py` (report must bind producer hashing identity), `e002_verify/production_evidence.py` and `kernel.py` (accept/require `hashing`, `--observe-hashing`),
`tools/qualify_e002_production_verification.py` (`--observe-hashing`), and three existing test modules (synthetic hashing identity in unit plans; one added interruption test). No accepted scientific, statistical, generation or hashing-algorithm code changed; no candidate-selection law, source cursor or E4/R9 semantic was altered.
