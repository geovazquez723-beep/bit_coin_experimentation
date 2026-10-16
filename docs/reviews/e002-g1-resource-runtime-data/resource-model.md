
### Producer

| Stage | Basis | Low | Central | High | Note |
|---|---|---|---|---|---|
| A1 Algorithm D (30M ranks) | M | 0:52:27 | 1:05:33 | 2:11:07 | max of early-stream mean and synthetic late-state means; 4 compares, 2 random blocks/output |
| A2 prefix+nonce stream | A | 0:01:30 | 0:03:00 | 0:09:00 | not individually probed; bounded by Attempt construction (4.5 us) + concatenation |
| A3 Algorithm S scan + unrank + encode | D | 0:03:22 | 0:04:13 | 0:08:26 | scan 1.7 us/emitted (early) + unrank at weight-6 mix 5.0 us; scan scales with ranks scanned (x2.74) |
| N1 forward + rejection checks | M | 0:04:10 | 0:05:13 | 0:10:27 | real provider incl. row dict; history set was 100k inversions, not 6.0M |
| P1/P2+/P2- forward + checks | M | 0:04:01 | 0:05:01 | 0:10:03 |  |
| N2 80-byte stream + A2 membership | M | 0:01:51 | 0:02:19 | 0:04:39 |  |
| Kernel eligibility re-check (second Feistel/rank per control/A3) | D | 0:12:59 | 0:16:14 | 0:32:28 |  |
| Attempt construction + Accumulator.add + ControlEngine.transform | M | 0:29:04 | 0:36:21 | 1:12:42 |  |
| SHA-256 evaluation (OpenSSL, 180.2M evals) | M | 0:01:42 | 0:02:07 | 0:04:15 | 568 ns/eval; hashing is not a bottleneck |
| Row serialization (encode_row) | M | 0:03:57 | 0:04:56 | 0:09:53 |  |
| Durable chunk writes + fsync + per-chunk inventory (43995 files) | M | 0:01:05 | 0:05:36 | 0:15:10 | disk probe 1.48 ms/file vs ChunkWriter in-situ ~13.8 ms/chunk; Defender real-time on; page-cache effects |
| History load: 7.0M occurrences inverted into index | D | 0:00:49 | 0:01:01 | 0:02:03 | consistent with the 55 s bounded producer runs (dominated by this load) |
| Producer-side capture replay / authentication (iter_chunks) | M | 0:15:52 | 0:19:50 | 0:39:40 |  |
| **Total (single-threaded sum)** | | **2:12:54** | **2:51:30** | **5:50:00** | |

### Independent verifier (full audit)

| Stage | Basis | Low | Central | High | Note |
|---|---|---|---|---|---|
| A1 regeneration (interval arithmetic) | M | 0:25:43 | 0:32:08 | 1:04:17 |  |
| A2 regeneration | A | 0:00:15 | 0:00:30 | 0:01:30 |  |
| A3 Algorithm S + Gosper | M | 0:01:06 | 0:01:22 | 0:02:45 |  |
| N1/P Feistel + masks | M | 0:05:55 | 0:07:24 | 0:14:49 |  |
| N2 regeneration | M | 0:00:30 | 0:00:38 | 0:01:17 |  |
| Independent SHA-256 rehash (HACL*) | M | 0:01:21 | 0:01:41 | 0:03:23 |  |
| Row pack/compare + transform + tally | A | 0:04:30 | 0:09:00 | 0:27:01 | earlier handoff measured 1.15 us/row for comparison alone; tally and transform added |
| History load (inverse index, 7.0M) | D | 0:00:41 | 0:00:52 | 0:01:44 |  |
| Sequential read of 25.9 GB (NVMe C:, 166 MB/s) | M | 0:02:36 | 0:03:15 | 0:06:31 | rate measured on just-written files; external USB HDD unmeasured; SHA-256 of chunks at 1.6 GB/s adds ~16 s |
| **Total (single-threaded sum)** | | **0:42:41** | **0:56:55** | **2:03:21** | |

### Finalization and archival (mostly unmeasured)

| Stage | Basis | Low | Central | High | Note |
|---|---|---|---|---|---|
| Manifest/inventory re-read of 43,995 chunk files | D | 0:02:36 | 0:03:15 | 0:06:31 |  |
| Copy to two off-machine copies (assumed 150 MB/s each) | A | 0:02:52 | 0:05:45 | 0:34:35 | target media/network not specified; throughput is an assumption |
| Re-hash both copies (assumed 150 MB/s) | A | 0:02:52 | 0:05:45 | 0:34:35 |  |
| Restored-copy verification pass (second full audit read) | D | 0:02:36 | 0:03:15 | 0:06:31 | read cost only; the regeneration cost is the verifier table |
| **Total (single-threaded sum)** | | **0:10:59** | **0:18:03** | **1:22:14** | |
