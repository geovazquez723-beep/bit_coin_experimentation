# E001 full reconstruction tooling — S1.2 scientific handoff

2026-10-12. Branch `feat/e001-independent-qualification`, accepted parent and
unchanged HEAD `8d706c34d5e6708ac416344cbc312b32729e94c8`.
All assignment files are uncommitted and unstaged.

S1.2 qualifies bounded synthetic reconstruction, disk-backed exact duplicate
accounting, independent occurrence verification and exact exclusion reporting.
Full historical activation remains absent. These results do not establish the
historical A1 intersection, X3, original-runtime identity or historical completion.

## Exact assignment inventory

Four added files; no accepted tracked file changed:

- `src/hashlab/experiments/e001_tooling.py`: S1.1 provider adapter, SQLite
  accounting, wire observations and exclusion report.
- `src/e001_verify/occurrences.py`: independent algorithmic/manual fixture
  verification, including exact metadata, outcomes and final report.
- `tests/test_e001_tooling.py`: 58 synthetic qualification cases.
- `docs/reviews/e001-full-reconstruction-tooling-handoff.md`: this handoff.

Ignored local evidence is under `results-smoke/e001-s12-qualification/`:
`preserve.py`, `before.json`, `after.json`, `focused.txt`, `e001.txt`,
`regression.txt` and separate pytest temporary directories. These are diagnostic
fixtures outside sealed E001, not historical audit artifacts. The two earlier
test-fixture failures are described below; no accepted test was changed.

## Scientific source and activation boundary

Inspected S1.1 scheduling, E5 reconstruction/Phase B and their tests, independent
`e001_verify/core.py`, the Phase B verification bridge, accepted `exp002.py`
population definitions, original generator implementations, original
`baseline.py` semantics and the scientific recovery plan. Historical Git source
bytes were checked against all contract LF pins, as were loaded checkout files.
No source-semantic contradiction or rank-mapping ambiguity was found.

The inert production specification remains the accepted
`e001_scheduler.historical_schedule()`: seven generator-major pairs of streams,
500,000 raw attempts per phase, seven million in total. Ordinals/families are
0 sequential, 2 uniform MT19937, 4 patterned bytes, 6 Gray, 7 stride,
8 bit reversal and 9 keyed BLAKE2b. Historical phase seeds are metadata only for
the new provider. Seeded fixtures restart per phase with explicit synthetic
keys; seedless fixtures continue by raw attempted offset. Patterned offsets count
emitted primitive-pattern candidates, not raw motifs. No duplicate causes top-up.

New executable APIs accept only the unchanged `FixturePlan`, revalidated through
S1.1, with at most 4,096 total attempts. Passing historical descriptors is
rejected before generator construction or database creation. There is no full
history iterator, enable flag, CLI, dispatcher, historical seed selection or
derivation, automatic retry, resumption or repair in the new modules. Existing
accepted E5/S1.1 APIs and original generators remain unchanged.

The specification and database key/schema design cover the full geometry, but
**no executable full-scale implementation is enabled by S1.2**. Later activation
requires a separately reviewed provider accepting authenticated historical
descriptors, explicit larger disk reservations, independent streaming verifier
state, and reconciliation against sealed per-stream counts. Removing a fixture
cap alone would not qualify these operations. The current verifier retains at
most 4,096 fixture values; scalable independent state remains activation work.

## Public APIs and independence

- `fixture_occurrences(plan)` returns the accepted lazy S1.1 iterator. Records
  retain generator ID/family, phase, raw and enumeration indices, exact eight-byte
  candidate and source/config/contract/manifest identities.
- `occurrence_fields(row)` creates plain wire fields from a validated occurrence.
- `DiskAccounting(path, plan, batch_size=64)` exclusively creates a new store.
  It is a context manager; `observations(rows)` is one-use and yields wire records
  with `unique`, `within` or `cross` outcomes. `report()` requires complete
  exhaustion and the no-extra-row check. `close()` abandons any active iterator
  and rolls back its pending transaction before closing SQLite.
- `e001_verify.occurrences.verify_fixture(specs, discovery, validation, seeds,
  observations, report)` independently replays algorithms and verifies every wire
  field, exact type, duplicate classification, count, exclusion value, rank and
  digest. It returns `verification=independently-verified-synthetic` only after
  checking the supplied producer report exactly.
- `verify_manual_fixture(..., reference)` instead checks an explicitly supplied,
  immutable, bounded list of manually specified candidate bytes. Its returned
  `reference=manual` distinguishes collision/predicate qualification from
  `reference=algorithmic` generator qualification. Injected manual bytes fail
  algorithmic replay when they differ from the actual generator definition.

The independent module imports only its independently specified `core` reference
algorithms and no HASHLAB scheduler, generator, dedup, accounting or population
implementation. Family names/order, wire identities, offsets, dedup bypass and
phase precedence are separately specified. MT uses the accepted independent
624-word implementation; patterned reference uses the direct periodicity
definition rather than production KMP. Integer/bit formulas and independently
assembled BLAKE2b blocks supply the other streams. Existing MT known-answer
vectors were rerun as part of E001 qualification.

Shared generic cryptographic dependencies and Codex/AI authorship remain
limitations. Python/.NET agreement on the synthetic exclusion digest provides an
additional calculation, not independent human authentication or qualification of
the original CPython 3.11.0 binary. This milestone did not install or execute that
runtime.

## SQLite schema, resources and failure semantics

The explicit schema is created only in a new exclusive file:

| Table | Fields and keys |
|---|---|
| `run` | `plan TEXT`, `status TEXT`; one initial row binds the fixture fingerprint and starts incomplete |
| `seen` | `generator INTEGER`, `candidate BLOB`, `phase TEXT`; primary key `(generator,candidate)`, WITHOUT ROWID; candidate type/length and phase CHECKs |
| `counts` | `stream INTEGER PRIMARY KEY`, `attempted`, `unique_count`, `within_count`, `cross_count`, `a1`, `a3` integer counters |
| `excluded` | `candidate BLOB PRIMARY KEY`, `rank INTEGER UNIQUE`, WITHOUT ROWID; exact eight-byte BLOB CHECK |

Dedup queries/inserts are deterministic and parameterized. Only uniform and keyed
random streams use `seen`; unique-by-construction families bypass it exactly as
the original auto mode. Generator keys prevent cross-generator dedup. First
discovery membership wins for every validation repetition; subsequent repetitions
of a discovery value stay cross-phase, never become within-phase duplicates.
No path reopens an existing file or mixes audit attempts.

Limits: 1–64 occurrences per transaction, 4,096 total attempts, 64 KiB SQLite
page cache, 4 KiB pages, 2,048-page/8 MiB main database cap, separate 8 MiB rollback
journal reservation, `temp_store=FILE`, `synchronous=FULL`, DELETE journal mode,
zero busy timeout. Disk checks occur before commits; main database growth is also
limited by SQLite. These limits bound fixture operation; filesystem allocation
overhead, whole-process RSS, power-loss durability and historical-scale throughput
were not qualified. Report arrays are bounded by the exclusion population within
the 4,096 fixture cap; input occurrences are not accumulated by disk accounting.

Only a final successful transaction after exhaustion persists `fixture-complete`.
Interrupted writes roll back the pending batch; previously committed batches can
remain with durable `incomplete` status. Partial rows never produce a report.
An exception or consumer close poisons the in-process attempt; retry/resumption is
rejected. A process interruption before the final commit likewise cannot have a
complete status. No existing database is opened for automatic recovery or repair.
Tests demonstrate injected commit failure, transaction rollback, abandonment and
partial committed batches; abrupt OS/power failure was not simulated.

Output creation rejects symlink/reparse ancestors and directories beneath a
`manifest.sha256` sealed-evidence marker. Qualification paths use dedicated smoke
directories. Session preservation checks provide the separate actual-E001 check.

## Exact exclusion reporting contract and observed fixture

`e001-s12-exclusions-v1` reports:

1. `raw_attempted`: every scheduled occurrence, including duplicates.
2. `unique_evaluated`: sum of original per-generator unique evaluations, respecting
   auto bypass; this is not global distinctness across generators.
3. `qualifying_a1` and `qualifying_a3`: evaluated candidates satisfying accepted
   predicates; repeated evaluated values in different generators count again.
4. `distinct_excluded_a3`: globally distinct eligible values.
5. `a3_values_numeric_hex`: exact 16-digit eight-byte encodings in unsigned
   numeric order, independent of population-rank order.
6. `a3_ranks`: distinct accepted weight/colex ranks in ascending rank order.
7. `exclusion_sha256`: SHA-256 of distinct candidates sorted unsigned numerically,
   concatenated as exact eight-byte big-endian values. SQLite's fixed-width BLOB
   order gives that numeric ordering. The digest is computed from observed bytes.
8. Per-stream attempted/unique/within/cross `accounting`, `status`, `verification`,
   `scope=synthetic-only`, `historical_complete=False`, `final_acceptance=False`.

An independent verifier never trusts producer completion/verification flags or
serialized counts. Missing/extra fields, altered types (including bool-as-int),
incomplete status, false historical claims and mismatched reports fail closed.
Production reports start `verification=not-independently-verified`.

The explicit 16-occurrence manual fixture has 10 unique evaluated candidates,
two qualifying A1 evaluations, five qualifying A3 evaluations and four distinct
excluded A3 values. It includes A1 lower/upper endpoints, nonqualifying values,
within/cross-phase duplicates, repeated cross-generator values, A3 weight 1/2/6
boundaries and rejected weight 7. Numeric exclusion order is:

```text
0000000100000000
0000000100000001
8000000000000000
fc00000000000000
```

Ascending rank order is `[0, 31, 32, 82128983]`, demonstrating that rank order is
not digest order. Explicit combinatorial calculations establish the first and
last population ranks. The observed canonical 32-byte exclusion-set digest is
`d65c8c02efc910c357685ed6a2f1b3a23711458121c052624dbfbc9483891b49`.
It was independently calculated by Python on the explicit serialization and by
.NET `SHA256.HashData` on a literal byte array. These are exclusion-set integrity
hashes, not research candidate SHA-256 evaluations.

Historical **expected, not observed here**: A1 intersection zero; A3 population
60,721; canonical digest
`7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c`.
No expected historical constant supplies any synthetic computed result.

## Synthetic matrix and actual qualification results

| Coverage | Evidence |
|---|---|
| All seven families, both phases, raw indices/offsets | Independent algorithmic replay and metadata comparison |
| Patterned continuation | Period-one/two boundary and lexicographic carry/primitive rejection |
| Seeded restart | Same synthetic phase seed yields validation cross-duplicates for uniform and keyed BLAKE2b |
| Lazy draw budget and disk resources | Instrumented 2,048+2,048 continuation; exactly 4,096 draws; cache/page caps checked |
| Duplicate semantics | Within/cross precedence, per-generator boundaries, auto bypass, no top-up, separate attempts |
| Transactions and interruption | Injected pre-commit failure rolls back seen/counts; partial committed batches remain incomplete; context/consumer close rolls back pending rows |
| Fail-closed occurrence verification | Missing/extra/extra-None/reordered/missing-generator records; wrong family/ID/phase/index/offset/seed/pins/bytes/outcome; actual corrupted producer rejected |
| Exclusions and report verification | Manual predicates/endpoints/counts, exact distinct bytes/ranks/digest; report corruption and false completion claims rejected |
| Safety and preservation | Historical plans rejected, no dispatcher, hash-engine/seed-derivation spies, sealed output rejection, source/evidence checks |

Runtime: existing `.venv-py313-review024/Scripts/python.exe -B`, CPython 3.13.0,
MSC v.1941 AMD64; pytest cache disabled. Final runs after the last code change:

| Suite | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|
| S1.2 focused | 58 | 0 | 0 | 1.86 s |
| Existing S1.1 + E001 reconstruction + Phase B | 179 | 0 | 0 | 12.89 s |
| Complete regression | 1,177 | 0 | 2 | 30.83 s |

Final 4,096-attempt disk-accounting Python traced peak was 179,904 bytes; native
SQLite allocation/RSS and historical performance are not measured by this value.
Both skips are existing `test_exp002_e4.py:259` symlink cases, Windows
`WinError 1314` (privilege unavailable). They remain unqualified on this host.
No tests were weakened. Earlier failures were an incorrect manually written
synthetic digest literal (corrected using independent explicit-byte calculation),
and a new tamper case that supplied the unchanged empty exclusion list (changed
to an actually false value). Neither required a scientific-code correction.

Commands used `-m pytest`, `-q`, `-p no:cacheprovider` and distinct `--basetemp`
paths under the smoke directory. Focused tests additionally used `-s` to record
memory. Full command/results text is retained in the local evidence logs.
The requested legacy E001 suites include their accepted bounded historical-prefix
reference checks; no new full-history operation was invoked or seed selected.
Regression hash tests exercise their existing synthetic/KAT fixtures.

## Preservation, Git status and remaining qualification

Before/after read-only inventories match exactly for all eleven sealed E001
files: names, SHA-256, sizes and observed `mtime_ns`. Both manifest verifications
returned `[]`; `validate_history` and original Git/loaded-source LF pin checks
passed before and after testing. Protected inventories also match for 2,526
tracked/unrelated-document/`.venv313` files. This is observed-session preservation,
not evidence establishing historical timestamp provenance.

Unchanged identities: original source
`ef595f5c2f2166923fd277def39708409f564419`; manifest
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`;
resolved config `d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b`;
contract LF `008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04`.
Accepted E1–E5, S1.1, R9 and M1A/M1B1 remain byte-identical. Tracked tree and index
were clean before work and retain empty `git diff` and `git diff --cached` after
work. HEAD and branch are unchanged.

Final short status consists of the four assignment additions above plus the
pre-existing untracked `.venv313/`, `docs/plans/`, the M1B decision proposal,
M1B2 decision brief and architecture Review 039/040 documents. No unrelated
document or environment file was changed. No commit/push/merge/tag was performed.

Remaining prerequisites: separate S1.3 authorization and historical activation;
independent scalable streaming state and disk/runtime qualification; authenticated
full fourteen-stream replay with sealed attempted/unique/duplicate reconciliation;
observed A1/X3 values, ranks/count/digest; original-runtime provenance and
compatibility qualification or explicit scientific disposition of the recorded
numerical differences. Period-three historical patterned offsets, million-draw
seeded streams and power-loss behavior remain unqualified. No research candidate
hashing, QA2, Experiment 002 run, beacon/commitment/release selection or new
governance infrastructure was introduced.
