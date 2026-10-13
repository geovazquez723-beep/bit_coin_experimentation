# E001 historical exclusion audit — S1.4

**Result: Verified.** One producer attempt and one independent verifier attempt; no retries.

Accepted source: `a30636a4430d250ff00c1b472d393ee8b26701c3` on `feat/e001-independent-qualification`. This report remains uncommitted and unstaged. The temporary activation described below was retired during result closeout; see the final disabled state at the end.

## Runtime and preflight

Interpreter: `C:\repo\hashlab\.venv-py313-review024\Scripts\python.exe`. Exact version: `3.13.0 (tags/v3.13.0:60403a5, Oct  7 2024, 09:38:07) [MSC v.1941 64 bit (AMD64)]`. Platform: `Windows-11-10.0.26200-SP0`; SQLite `3.45.3`.

Installed distribution versions (the editable HASHLAB metadata appears twice): PyYAML 6.0.3, Pygments 2.21.0, colorama 0.4.6, hashlab 0.2.0, hashlab 0.2.0, iniconfig 2.3.1, packaging 26.3, pip 26.2.1, pluggy 1.6.0, pytest 9.1.1, setuptools 80.9.0, wheel 0.45.1.

The tracked tree and index were clean before activation. All original source/configuration/contract/manifest pins and eleven sealed files verified. Both destinations were absent; no Python process/full reconstruction was running. Preflight recorded 141,031,309,312 free disk bytes and 16,856,399,872 available physical memory bytes, exceeding 2 GiB disk and 256 MiB memory requirements. The accepted 15–30-minute planning allowance and unchanged resource limits were used.

[Exact runtime, binary/dependency hashes, initial preservation and plan](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/before.json); [preflight checks and host resources](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/preflight-passed.json).

## Exact activation delta

Both generic historical booleans remain `False`. A process-local audit capability permits only this fixed plan, accepted implementation plus the inspected activation delta, qualified runtime, original pins/seeds, fixed producer/verifier locations and accepted default limits. Historical plans must match the exact canonical plan hash and active plan object; producer rows must come from the accepted `_raw` generator. Historical entry points stay disabled for synthetic/default callers. Exclusive persistent role claims are consumed even on failure and prevent another attempt.

Plan SHA-256: `19d6396493fc9b8aa9559fd8ddab65f219b920a13b447bb9fb00c04da782054b`. Activation binding SHA-256: `0009b5de67e9a17da5ca9fb88a14736370c70424d06c65c3338ba3506c1bdb0a`.

Authenticated historical pins: source `ef595f5c2f2166923fd277def39708409f564419`; configuration `d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b`; contract (LF) `008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04`; manifest `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.

[Exact inspected activation diff, including the one-off runner](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/activation.diff), SHA-256 `46eff13b47b1ee0704d776c1ef062e97fc5bc731f97cf7dfdc3895e76f7b660f`. [Bound execution-file hashes](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/activation-binding.json). The delta changes only action guards/entry boundaries; all other scientific function/class ASTs are identical to S1.3. The 58 unchanged focused tests and 22 non-enumerating activation rejection checks passed.

## Observed result and reconciliation

| Quantity | Pinned expectation | Producer observation | Independent observation | Match |
|---|---:|---:|---:|---|
| raw_attempted | `7000000` | `7000000` | `7000000` | True |
| qualifying_a1 | `0` | `0` | `0` | True |
| distinct_excluded_a3 | `60721` | `60721` | `60721` | True |
| exclusion_sha256 | `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c` | `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c` | `7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c` | True |

Total unique evaluated: **7,000,000**; A3 qualifying evaluations across generators: **60,721** (global distinct exclusions are reported separately). Both are independently equal. All fourteen sealed stream reconciliations: **True**.

| Generator | Phase | Raw attempts | Unique | Within-phase duplicates | Cross-phase duplicates | Sealed / replay |
|---|---|---:|---:|---:|---:|---|
| seq-be-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| seq-be-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |
| uniform-be-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| uniform-be-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |
| pattern-bytes-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| pattern-bytes-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |
| struct-gray-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| struct-gray-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |
| struct-stride-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| struct-stride-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |
| struct-bitrev-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| struct-bitrev-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |
| random-bytes-w8 | discovery | 500,000 | 500,000 | 0 | 0 | Match |
| random-bytes-w8 | validation | 500,000 | 500,000 | 0 | 0 | Match |

Independent replay regenerated and compared all seven million occurrences, original seeded restarts/seedless continuation, family/phase order, raw indices, offsets, per-generator deduplication and discovery precedence. It independently derived membership, global distinct exclusions and population ranks, compared numeric-order values and separately sorted ranks, and checked the complete producer file inventory. Producer SQLite was read only for its completion marker, never used as independent accounting/classification input.

## Execution identities, actual resources and evidence

Producer directory: `C:\repo\hashlab\results\e001-s14-audit-20261012-01\producer`. Independent scratch: `C:\repo\hashlab\results\e001-s14-audit-20261012-01\verifier`.

| Component | PID | Pipeline seconds | Whole-process peak RSS bytes | Retained directory bytes | Peak DB bytes | Sampled peak journal bytes |
|---|---:|---:|---:|---:|---:|---:|
| producer | 36272 | 110.730 | 50233344 | 172264856 | 37801984 | 4341656 |
| verifier | 42648 | 90.812 | 49905664 | 37791577 | 37789696 | 3799936 |

Pipeline timing covers the invoked scientific/evidence operation; identity/resource preflight is additional. Peak RSS is Windows whole-process PeakWorkingSetSize, including imports/native SQLite. Journal peaks are sampled at commits, not continuous power-failure maxima. The two processes ran sequentially. No limits were increased.

[Producer execution claim](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/producer.claim.json), [producer measurement](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/producer.success.json), [verifier execution claim](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/verifier.claim.json), [verifier measurement](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/verifier.success.json).

| Evidence file | Bytes | SHA-256 |
|---|---:|---|
| `producer\accounting.sqlite` | 37801984 | `14bc1c75950284a1d514568207e7bbccea86706b44b118f95e42fa861e0b9803` |
| `producer\complete.json` | 2104 | `c4fe9ba89f1c4390c5300a7a5512aaf20f2bc6fcbbfcbe2292b1af564f70ddc1` |
| `producer\exclusions.bin` | 971536 | `39d09046325a41dd36d1bc0390e15a1d35a64f649d20f144b9025ccda4395268` |
| `producer\occurrences.bin` | 133000000 | `dc27fca46c57a8c02aaa50584af1783e1f4e6dbfedb48231847415c509d9695f` |
| `producer\plan.json` | 3464 | `19d6396493fc9b8aa9559fd8ddab65f219b920a13b447bb9fb00c04da782054b` |
| `producer\ranks.bin` | 485768 | `124d6722591d81c9739e63d2702d67dcc3f889fb297a55fd52d7c7c800ee320a` |
| `verifier\reference.sqlite` | 37789696 | `e024010e7585a019487fc47c1afcbc22ae1d7c7c497f1fc7e6a9cbf25f31970c` |
| `verifier\verified.json` | 1881 | `3ed80c4d663614fb5245902f88037573776889dc3c3afc47e32018add11d42eb` |

[Full evidence inventory with observed modification times](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/evidence-inventory.json). Complete producer and verified replay reports are retained in their respective evidence directories. No incomplete marker remains.

## Preservation, limitations and Git

Post-run checks passed for all eleven original sealed files (hashes, sizes and observed modification times), original manifest, historical source/configuration/contract pins, all accepted scientific algorithms/tests and 10,240 protected pre-existing files outside the two authorized activation edits. All 1,283 unrelated untracked files and earlier qualification evidence remain unchanged. [Post-run preservation record](C:/repo/hashlab/results-smoke/e001-s14-preflight-20261012-01/after.json). This establishes current-session preservation, not historical timestamp provenance.

This is current-runtime reconstruction and algorithmically independent replay, not original CPython 3.11.0 exact reproduction or independent human replication. Original-runtime/dependency provenance and the previously identified 86 numerical differences remain unresolved. Shared AI authorship and generic cryptographic libraries remain limitations. No research candidate SHA-256 target evaluation, new seed selection/derivation, QA2, E002, original-runtime execution or additional experiment occurred. SHA-256 was used only for integrity and the canonical exclusion set.

Execution-time Git snapshot, retained for historical context: HEAD was `a30636a4430d250ff00c1b472d393ee8b26701c3` and the index was empty. The two activation-boundary files were tracked modifications; the one-off runner and this result report were new untracked files. Pre-existing unrelated untracked inventory remained. No commit, push, merge, tag or release occurred.

```text
M src/e001_stream_verify/streaming.py
 M src/hashlab/experiments/e001_historical.py
?? .venv313/
?? docs/plans/
?? docs/proposals/experiment-002-r9-m1b-decision-proposal.md
?? docs/proposals/experiment-002-r9-m1b2-decision-brief.md
?? docs/reviews/architecture-review-039-external-readiness.md
?? docs/reviews/architecture-review-040-e6-preparation.md
?? docs/reviews/e001-historical-exclusion-audit-result.md
?? tools/run_e001_s14_audit.py
```

## Result closeout — final disabled state

Read-only inspection reconfirmed both report hashes, all eight retained audit files, the fourteen stream reconciliations and the canonical exclusion digest. No producer, independent replay or historical prefix was rerun. The complete audit and preflight directories, including the binding, activation diff, claims and evidence inventory, remain unchanged in bytes, sizes and observed modification times.

Only `src/hashlab/experiments/e001_historical.py` and `src/e001_stream_verify/streaming.py` were restored to the accepted S1.3 commit, after their changes matched the exact recorded S1.4 activation delta. Both historical switches are `False`, the temporary `_S14_AUDIT` hooks are absent, and five nonhistorical public/internal rejection checks passed before metadata or generator access. The tracked working tree and index are now clean; HEAD is unchanged.

The one-off runner was moved out of `tools` into [an archived text record](C:/repo/hashlab/results-smoke/e001-s14-closeout-20261012-01/records/run_e001_s14_audit.py.txt), preserving its bytes and observed modification time. Its original binding remains historical evidence, with its original execution-time path; it is not a current launch configuration. The [original result document](C:/repo/hashlab/results-smoke/e001-s14-closeout-20261012-01/records/original-result.md) was preserved before this closeout update.

[Exact closeout inventory and preservation record](C:/repo/hashlab/results-smoke/e001-s14-closeout-20261012-01/closeout.json). All eleven original sealed E001 files and their manifest remain intact. Unrelated untracked files and prior qualification evidence are preserved. This result document is the only new untracked development file from S1.4 after runner retirement. No commit, push, merge or tag was performed. E002 scientific integration is the next development priority; no E002 work was executed during closeout.
