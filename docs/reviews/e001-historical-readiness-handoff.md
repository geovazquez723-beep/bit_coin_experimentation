# E001 historical reconstruction readiness — S1.3

2026-10-12. Branch `feat/e001-independent-qualification`; unchanged accepted HEAD
`5f62a47b4e1dc7d5350baa4a59cbb6c55c00c4f3`. Work is uncommitted and unstaged.

The complete producer/accountant/evidence/verifier path is implemented with
disk-backed state and qualified on explicitly bounded synthetic workloads.
Historical producer and verifier activation remain disabled in source. No new
historical window or full reconstruction was executed; the only historical-prefix
execution was the Director's explicit exception for unchanged accepted tests.

## Exact added-file inventory

- `src/hashlab/experiments/e001_historical.py` — authenticated historical metadata,
  disabled historical action, separate bounded synthetic geometry and shared
  streaming producer/accountant/evidence kernel.
- `src/e001_stream_verify/__init__.py` — independent streaming package boundary.
- `src/e001_stream_verify/streaming.py` — separately specified disk-backed replay,
  metadata, accounting, exclusion and completeness verification.
- `tests/test_e001_historical.py` — 58 deterministic qualification tests.
- `tools/qualify_e001_readiness.py` — opt-in fixed synthetic resource probes.
- `docs/reviews/e001-historical-readiness-handoff.md` — this handoff.

No accepted tracked source, test or document was modified. The original generators,
E1–E5, S1.1/S1.2, population definitions, R9 and M1A/M1B1 remain unchanged.

## Interfaces, activation and evidence

`e001_historical.historical_plan(sealed, source_root)` authenticates all historical
source/configuration/manifest/contract pins and returns inert S1.1-derived metadata:
seven eight-byte families, generator-major D/V order, 500,000 raw attempts per
stream, recorded phase seeds, seedless continuation and sealed accounting targets.
It constructs no candidate generator. Independent `streaming.historical_plan`
separately derives matching metadata from the hash-pinned contract.

`run_historical(sealed, source_root, output, limits=Limits())` and
`e001_stream_verify.streaming.verify_historical(root, work, contract_path, ...)`
are the two narrow future action interfaces. Each currently raises
`PermissionError` before generation, output creation or stream replay; internal
producer/verifier execution boundaries also reject historical plans. There is no
enable argument, historical window API, historical command, startup hook or job.
Activation requires a separately authorized, inspectable change of
`HISTORICAL_EXECUTION_ENABLED` and `HISTORICAL_VERIFICATION_ENABLED`, followed by
explicit API invocation. This assignment leaves both `False`.

`SyntheticGeometry`/`run_synthetic` and independent `verify_synthetic` exercise the
same streaming kernels with a separate synthetic scope, <=262,144 attempts and
fixed fixture keys 1/2 or 1/1. They neither increase nor bypass the accepted
4,096-attempt `FixturePlan` ceiling. Manual candidate injection is separately
labeled and remains <=4,096. Synthetic plans cannot use historical seeds, forge
source/configuration identity, or substitute the seven-million-attempt geometry.

Each attempt exclusively creates a new directory outside sealed evidence. Files
are write-once through these APIs; there is no reopen/retry/resume/repair path:

- `plan.json`: exact source/config/contract/manifest pins, stream identities,
  seeds, offsets, scope and reference mode.
- `occurrences.bin`: 19-byte `>BBII8sB` records (ordinal, phase, raw index,
  enumeration index, exact candidate, unique/within/cross code).
- `exclusions.bin`: numeric-ordered `>8sQ` pairs of distinct candidate and rank.
- `ranks.bin`: ascending weight/colex ranks as unsigned eight-byte values.
- `accounting.sqlite`: producer dedup/exclusion state and completion progress.
- `complete.json`: per-stream attempted/unique/duplicate counts, qualifying A1/A3
  evaluated counts, global distinct A3 count/digest, evidence sizes/hashes and
  observed resource sizes. Producer completion is separate from independent replay.

`INCOMPLETE` persists until final evidence is flushed/fsynced, database completion
commits, and the complete report is durably written. A leftover marker, missing
report/file, extra file, incorrect byte stream, incomplete database or false
accounting cannot verify. Output immutability is the exclusive write-once API and
integrity inventory; it is not an OS-level immutable-file attribute or external
timestamp assertion. Power-loss durability remains operationally unqualified.

## Accounting, independent boundary and exact exclusions

Producer SQLite uses `first_seen(g,value,p)` with primary key `(g,value)` and
`excluded(value,rank)` with exact eight-byte BLOB primary key and unique rank.
`run(status,attempted)` records only diagnostic progress until completion.
The independent schema instead uses `membership(g,phase,candidate)` and
`x3(candidate,position)`, separately checking discovery membership before current
validation membership. Per-generator keys isolate populations. Unique-by-
construction families bypass dedup; raw budgets never top up after duplicates.

Only bounded RNG state, a single occurrence and <=14 counters stay in Python RAM.
All growing memberships/exclusion sets and sorted traversals use indexed SQLite
tables. No full-stream arrays or exclusion lists are retained in the verifier.
Defaults: 1,024 occurrences/transaction (configurable 1–4,096), 1 MiB page cache,
4 KiB pages, 128 MiB main DB cap, DELETE journal, FULL synchronous, zero busy
timeout. A separate journal allowance is twice the main DB cap. Main file growth
is bounded by `max_page_count`; journal/total sizes are checked at batch commits.
Indexed traversals avoid unbounded temporary sort files. Producer output reserves
worst-case files before directory creation and checks evidence/total limits while
writing. Default producer output reservation is 1 GiB.

Pending transactions roll back on ordinary interruption; committed partial batches
remain incomplete. An abrupt child exit after three synthetic occurrences (batch
size two) retained an unusable attempt and was rejected without reopening or
recovering its SQLite file. Injected commit failure retained zero committed rows;
actual SQLite page exhaustion also failed closed. Verifier interruptions retain
`INCOMPLETE` and no verified report. Existing attempt paths are never reused.

The new independent package imports only stdlib and accepted independent
`e001_verify.core` algorithms. It imports no HASHLAB generator, scheduler,
accountant, dedup or population implementation. The accepted pure-reference
package/import restrictions remain intact. An initial regression failure exposed
that boundary; relocating streaming I/O into its own package and adding an explicit
import allowlist resolved it without changing any accepted tests.

Replay checks every occurrence's bytes, ordering, indices, offsets and outcome;
derives accounting and predicates independently; compares numeric-sorted values
and separately rank-sorted evidence; and reconciles against pinned sealed counts
in the disabled historical path. The producer DB is opened only read-only with
`immutable=1` to inspect its completion marker, never to supply scientific counts
or dedup results. No SQLite recovery is attempted.

A1/A3 qualifying counts count evaluated candidates per generator, while A3
exclusions deduplicate globally. Canonical digest hashes numeric-sorted exact
eight-byte big-endian values, independently of rank ordering. The 16-occurrence
manual reference has 10 evaluated candidates, two A1, five A3, four distinct A3;
ranks `[0,31,32,82128983]` and digest
`d65c8c02efc910c357685ed6a2f1b3a23711458121c052624dbfbc9483891b49`.
Historical zero A1 / 60,721 A3 /
`7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`
are future expectations, not S1.3 observations; both kernels compute observed
values before comparing. Synthetic reports cannot claim historical completion.

## Resource qualification and provisional historical budget

Final measurements were isolated from test workloads in separate producer/verifier
processes. CPython 3.13.0 AMD64, SQLite 3.45.3, Windows 11 build 26200. Whole-process
peak RSS is Windows `GetProcessMemoryInfo.PeakWorkingSetSize`, including imports
and native SQLite allocations; throughput excludes interpreter/import startup but
includes evidence integrity hashing. Journal peaks are sampled before/after
commits, not continuously measured power-failure maxima.

| Fixed synthetic case | Attempts per component | Producer/s | Verifier/s | Peak RSS P/V (MiB) |
|---|---:|---:|---:|---:|
| Seven families, 4,096/phase | 57,344 | 154,842 | 171,470 | 28.5 / 21.3 |
| Seven families, 8,192/phase | 114,688 | 162,738 | 173,537 | 29.2 / 21.8 |
| Seven families, 16,384/phase | 229,376 | 164,006 | 177,720 | 29.3 / 22.0 |
| Patterned, 65,536/phase; enters period three | 131,072 | 198,739 | 260,455 | 28.6 / 21.2 |
| Two seeded families, 65,536/phase | 262,144 | 72,715 | 85,114 | 29.2 / 22.1 |

The largest seeded stores reached 4,653,056 producer / 4,681,728 verifier main-file
bytes and sampled journals of 2,008,872 / 1,146,320 bytes. Balanced producer main
files grew 466,944 → 847,872 → 1,560,576 bytes while working sets stayed nearly
flat. Largest retained output was 9,636,001 producer and 4,682,684 verifier bytes.
These workloads exceed page-cache capacity and test period-three continuation;
they do not establish million-draw per-generator throughput.

At full geometry, occurrences are exactly 133,000,000 bytes. **If** the expected
60,721 exclusions hold, exclusion/rank files add 1,457,304 bytes. Linear seeded
state extrapolation suggests ~36 MB per DB before additional exclusion/index and
B-tree overhead; provision 40–100 MiB per DB provisionally, with a fail-closed
128 MiB cap. Worst-case producer reservation is 703,784,256 bytes under the default
limits; independent scratch reserves another 384 MiB main-plus-journal allowance.
Plan at least **2 GiB free space** and **256 MiB working-set headroom per process**
for a sequential producer/replay operation. Working-set headroom is an operational
planning allowance, not an implemented OS memory limit.

Simple balanced-to-seeded rate extrapolation gives approximately **83–179 seconds
combined** for producer plus verifier. This is not a runtime promise: larger
random B-trees, cache misses, fsync/device latency, background load and historical
family mix can change scaling. Reserve **15–30 minutes** provisionally, verify
actual host/free-space budgets immediately before any authorized run, and abort
on resource exhaustion rather than enlarging limits or retrying silently.

## Tests, preservation and operational prerequisites

Final results after the last code change:

| Suite | Passed | Failed | Skipped | Seconds |
|---|---:|---:|---:|---:|
| New S1.3 focused | 58 | 0 | 0 | 3.54 |
| Accepted E001 + S1.1/S1.2 | 237 | 0 | 0 | 14.82 |
| Complete regression | 1,235 | 0 | 2 | 34.47 |

Coverage includes all families, seeded restarts, seedless/period-three transitions,
exact manual predicates/ranks/digest, 262,144-draw lazy operation, real producer
disagreement, resealed byte/index/outcome/identity/report corruption, missing
generator/extra/truncated/reordered streams, SQLite rollback/full/interruption,
abrupt process exit, false completion, sealed output rejection and disabled
historical/internal entry points. Hash-engine and seed-derivation spies reject
research evaluation. Both skips are unchanged Windows symlink privilege failures
at `test_exp002_e4.py:259`, not passes. No accepted test was weakened or expanded.

Read-only before/after snapshots preserve all eleven sealed files' inventory,
SHA-256, sizes and observed `mtime_ns`; original manifest verification returned
`[]`, and original/loaded source/config/contract pins passed. All 2,530 protected
tracked/unrelated-document/`.venv313` files also match. This proves session
preservation, not historical timestamp provenance. Logs, inventories and all probe
attempts remain under ignored `results-smoke/e001-s13-qualification/`; final
resource evidence is `completion-resource-probes/measurements.json`.

Before enumeration: accept this code and resource scope; explicitly authorize
activation/execution; inspect the two source switches and pinned release/runtime;
allocate new evidence and independent scratch locations with verified budgets;
invoke the whole provider and then independent replay; reconcile every sealed
stream count and observed A1/X3 bytes/ranks/digest. No major streaming/accounting
implementation gap remains. Historical scale, crash/power durability and actual
execution budgets still need operational confirmation.

Original CPython 3.11.0 binary/dependency provenance and the previously recorded
86 numerical differences remain unresolved. Current-runtime byte agreement,
shared generic cryptographic libraries and shared AI authorship do not establish
independent human replication or original-runtime identity. No original-runtime
execution, research hashing, QA2/E002 run, seed/beacon/commitment selection or new
governance infrastructure occurred.

Git: tracked diff and index remain empty; only the six assignment additions above
and the pre-existing unrelated untracked inventory remain. Branch/HEAD are
unchanged. No commit, push, merge, tag or release was performed. Stop for scientific
review; historical activation remains disabled.
