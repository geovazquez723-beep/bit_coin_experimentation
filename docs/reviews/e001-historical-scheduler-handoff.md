# E001 historical occurrence scheduler — S1.1 handoff

2026-10-12. Branch `feat/e001-independent-qualification`; accepted HEAD remains
`224506f344844fbc3a6e055d63e09b35f71ee297`. Uncommitted and unstaged for scientific review.

**New capability:** HASHLAB can describe all fourteen historical eight-byte
streams without constructing a candidate generator, and exercise the same
ordering, phase offsets, raw indices and duplicate precedence on bounded
synthetic occurrences. This supplies the scheduling layer for later E001
reconstruction. It does not reconstruct the historical population or qualify X3.

## Exact assignment inventory

Three new files; no accepted tracked files changed:

- `src/hashlab/experiments/e001_scheduler.py` — metadata, bounded synthetic
  iterator, observation/accounting and completion state.
- `tests/test_e001_scheduler.py` — 43 deterministic synthetic qualification cases.
- `docs/reviews/e001-historical-scheduler-handoff.md` — this handoff.

The pre-existing untracked scientific recovery plan, M1B decision proposal,
M1B2 decision brief, Review 039/040 documents and `.venv313/` were preserved.
Ignored diagnostic scratch is under
`results-smoke/e001-scheduler-qualification/`: before/after preservation JSON and
pytest temporary files. These are local qualification evidence, not sealed E001
artifacts or an accepted historical audit.

## Historical derivation and phase semantics

Inspected the recovery plan, E5 Phase A/B producer/verifier and tests,
`src/e001_verify/core.py`, E1 `exp002.py`, original source via `git show`, sealed
resolved configuration, seeds/results and E5 Review 036/038 records.
The original source and pinned metadata agree; no reconciliation was needed.

Normative source is commit `ef595f5c2f2166923fd277def39708409f564419`:
`src/hashlab/experiments/baseline.py::run_experiment` (generator-major phase loop),
`run_phase` (raw budget, offsets and prior-phase-first dedup), and
`needs_dedup_set` (auto bypass for unique-by-construction families).
Candidate behavior comes from original `candidates/{sequential,random,patterned,structured}.py`.
Current corresponding source bytes match the historical LF pins. In particular,
`patterned.py::stream` uses `islice(_enumerate(), start_index, None)`, not a
different motif-offset rule.

| Ordinal / identifier | Family | Discovery → validation |
|---|---|---|
| 0 / seq-be-w8 | Sequential | Index 0 → 500,000; 8-byte big-endian integer |
| 2 / uniform-be-w8 | Uniform MT19937 | Restart at recorded phase-specific sub-seed; index 0 in each phase |
| 4 / pattern-bytes-w8 | Patterned bytes | Emitted-candidate offset 0 → 500,000; retain lexicographic primitive-pattern enumeration |
| 6 / struct-gray-w8 | Gray | Index 0 → 500,000; `i XOR (i >> 1)` |
| 7 / struct-stride-w8 | Stride | Index 0 → 500,000; `11400714819323198485*i mod 2^64`, offset zero |
| 8 / struct-bitrev-w8 | Bit reversal | Index 0 → 500,000; reverse all 64 index bits |
| 9 / random-bytes-w8 | Keyed BLAKE2b | Restart counter stream at recorded phase-specific sub-seed; index 0 in each phase |

Each stream has exactly 500,000 **raw attempts**; fourteen streams describe seven
million attempts, not seven million unique evaluations. Seedless validation
continues after discovery's attempted count, not its unique count. The original
runner recreates a stream at that offset; the fixture iterator keeps a single
seedless stream moving to the identical position, avoiding duplicate prefix draws.
Historical seeds are copied from pinned records, never selected or derived.

Uniform D/V seeds are `11563638942429927757` / `17448145370022348540`;
keyed-BLAKE2b seeds are `710289665967761509` / `8231496708541735395`.
They appear only in historical metadata in this milestone's scheduler tests.
Actual synthetic iteration uses fixture keys 1/2.

Auto dedup applies to uniform and keyed-random families, separately for each
generator. Discovery membership wins over current validation membership:
repeating a discovery value twice in validation yields two cross-phase duplicates.
Unique-by-construction families bypass dedup sets, exactly as the original runner;
this bypass is not an independent check of generator correctness. Duplicate
occurrences remain in the schedule and never cause replacement draws. E001 has
no exclusion filter; a tested downstream consumer dropping a value also causes
no scheduler top-up.

## Public APIs and boundaries

- `historical_schedule()` returns fourteen frozen `Stream` descriptors, including
  family/identifier, phase, budget, starting index, historical seed, phase behavior
  and source/config/contract/manifest pins. It reads the hash-pinned contract;
  it does not build/advance generators or validate a live evidence directory.
  Session preservation checks separately called accepted `validate_history`.
- `fixture_schedule(FixturePlan)` returns descriptors for the existing bounded
  synthetic plan. Existing E5 plan limits and behavior are unchanged.
- `iter_fixture(plan, start=0, count=None)` returns a lazy iterator of frozen
  `Occurrence` records: stream, per-stream raw index, enumeration index and bytes.
  Windows use global fixture order; empty windows construct no generator.
  Historical descriptors cannot serve as its plan or occurrence stream.
- `FixtureAccounting(plan).observations(rows)` is one-use and yields frozen
  `Observation` values (`unique`, `within`, `cross`) while checking exact
  stream/index order, candidate width and geometry. It never requests replacement
  draws. `snapshot()` returns detached frozen per-stream `Counts` and a `Summary`.

Status is `incomplete` before/during consumption, `fixture-complete` only after
all expected rows and the no-extra-row check, `invalid` for malformed/truncated
input, or `interrupted` for external exceptions/explicit consumer close. Merely
receiving the last expected row leaves status incomplete until iteration finishes.
Early abandoned consumption cannot publish completion. No retry/resumption API
exists. Every summary has scope `synthetic-fixture-only`, `e_audit_passed=False`
and `final_acceptance=False`, including complete fixtures. No historical-audit
result, full provider, CLI or operational dispatcher was added.

## Qualification and independent expectations

Runtime: existing `.venv-py313-review024/Scripts/python.exe -B`, CPython 3.13.0,
MSC v.1941 AMD64. Pytest cache disabled; dedicated ignored temporary directories.

| Run | Passed | Failed | Skipped | Duration |
|---|---:|---:|---:|---:|
| Initial scheduler tests | 30 | 1 | 0 | 0.20 s |
| Scheduler before resource correction | 42 | 0 | 0 | 0.17 s |
| Existing E001 reconstruction + Phase B before correction | 136 | 0 | 0 | 11.86 s |
| Complete regression before correction | 1,118 | 0 | 2 | 28.11 s |
| Final scheduler tests | 43 | 0 | 0 | 0.18 s |
| Final existing E001 reconstruction + Phase B | 136 | 0 | 0 | 11.83 s |
| Final complete regression, including scheduler | 1,119 | 0 | 2 | 28.24 s |

Initial failure was an interruption-test closure referring to `rows` after it was
rebound to a generator (`TypeError`). Capturing the first row before rebinding
fixed the fixture. No production/scientific assertion was weakened. Additional
boundary/negative cases brought the scheduler suite to 42 tests. Final resource
review found that recreating seedless validation could replay discovery prefixes,
exceeding a 4,096 underlying-draw budget despite bounded emitted rows. Continuous
seedless iteration removes that replay without changing the candidate sequence;
a new instrumented 2,048+2,048 test proves exactly 4,096 draws, bringing the suite
to 43. All three required suites were rerun after this production correction.

Both regression skips are existing `tests/test_exp002_e4.py:259` symlink cases:
Windows `WinError 1314`, required privilege unavailable. They remain unqualified
on this host; skips are not passes or evidence of complete G1 qualification.

Commands used the qualified interpreter above:

```text
-m pytest tests/test_e001_scheduler.py -q -s -p no:cacheprovider --basetemp=results-smoke/e001-scheduler-qualification/focused-resource-temp
-m pytest tests/test_e001_reconstruction.py tests/test_e001_phase_b.py -q -p no:cacheprovider --basetemp=results-smoke/e001-scheduler-qualification/e001-resource-temp
-m pytest -q -p no:cacheprovider --basetemp=results-smoke/e001-scheduler-qualification/regression-resource-temp
```

Specific evidence in `test_e001_scheduler.py`:

- `test_historical_metadata_without_generators` forbids generator construction
  while checking all fourteen streams, budgets, historical seeds, identifiers,
  offsets and bindings. A conflict-injection test rejects mismatching phase metadata.
- `test_independent_phase_outputs_and_indices` covers every family/both phases.
  Expectations use direct integer/bit formulas, accepted independently implemented
  `e001_verify.MT19937`, and independently assembled BLAKE2b blocks; no production
  candidate helper generates expected outputs.
- Patterned expectations explicitly cross the 256 period-one outputs into
  period-two motifs and the `00/ff → 01/00 → 01/02` carry (skipping `01/01`).
  This tests exact candidate-offset continuation, not motif-index continuation.
- Deliberately repeated inputs demonstrate within/cross precedence, separate
  generator sets, bypass semantics and attempted-versus-unique counts. Draw spies
  prove laziness and no top-up, including a downstream exclusion example.
- Missing/extra rows (including an extra `None`), wrong stream/order, premature
  generator exhaustion, external interruption, partial/last-row consumption,
  invalid metadata/candidates/windows and fixture-cap rejection fail closed.
- Hash-engine and seed-derivation spies reject calls during synthetic replay.

Independent algorithms still share Codex authorship and generic cryptographic
dependencies. The MT reference already has pinned current-runtime vectors;
agreement does not qualify the historical CPython 3.11.0 binary. No independent
human authentication or full historical generator compatibility is asserted.

## Resource bounds

Historical representation allocates fourteen descriptors, not seven million rows.
Occurrence iteration retains only stream/generator state and one current record.
Prefix skips plus returned synthetic occurrences stay within the accepted
4,096-attempt fixture geometry. Synthetic dedup retains at most 4,096 eight-byte
keys for the current seeded generator; it clears at generator boundaries.
No full candidate arrays are allocated by the scheduler/accounting implementation.

Final memory test used **1,932 total attempts** (32 + 1,900) without row lists:
Python traced peaks **49,113 / 176,037 bytes**. Earlier runs measured
48,709 / 175,856 and 48,667 / 175,633 bytes. This demonstrates bounded fixture behavior; native
allocations, RSS, disk, historical-scale dedup and production performance are not
qualified. No benchmark or large historical-offset replay was performed.

## Preservation and remaining gaps

Before/after snapshots show exact equality for all eleven sealed E001 filenames,
SHA-256 digests, sizes and observed `mtime_ns`. Both accepted manifest verification
calls returned `[]`; accepted `validate_history` passed before and after. Original
Git source LF hashes match every contract pin, and current accepted source bytes
also match. The snapshots additionally preserve **121 tracked/unrelated document
files** byte-for-byte with identical sizes and observed modification times.

Key unchanged pins:

- Historical source: `ef595f5c2f2166923fd277def39708409f564419`.
- Manifest: `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
- Resolved config: `d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b`.
- Historical contract LF: `008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04`.

Observed-session modification-time equality is preservation evidence, not
historical timestamp provenance. Accepted E1–E5, R9, M1A/M1B1 source and existing
tests are unchanged. No original-runtime installation/execution or historical
analysis recomputation occurred; the 86 numerical discrepancies remain unresolved.

Remaining: full historical provider and scalable dedup/accounting; complete
seven-million-occurrence audit and exact X3 count/rank/digest verification;
independent full-stream replay with suitable resource bounds; original-runtime
provenance/compatibility and exact numerical disposition. Patterned period-three
historical offsets and million-draw seeded streams were not executed here.
Full historical dedup remains unqualified; only bounded semantics were demonstrated.

Final Git inventory adds the three assignment files to the pre-existing untracked
inventory above. `git diff` and `git diff --cached` are empty; HEAD/branch unchanged.
No commit, push, merge, tag, release, historical enumeration, research candidate
SHA-256 hashing, QA2/E002 execution, real execution-seed/beacon/commitment selection,
automatic recovery or governance expansion occurred. Existing regression hashes
are synthetic test/KAT workloads, not research execution.

Stop for scientific review. Next work can build the separately authorized full
historical provider on these scheduling semantics without changing the accepted
generator algorithms or treating fixture completion as an exclusion-audit pass.
