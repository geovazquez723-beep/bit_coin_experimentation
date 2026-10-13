# E002-I2 regression disposition and commit readiness

2026-10-13, America/Los_Angeles. Branch `feat/e002-i2-controls`; unchanged base
HEAD `3167c4ce66adabcc22743d99fc76e4f57316a711`.

**Decision recommendation:** accept the bounded I2 scientific/implementation
result subject to an explicit, narrowly scoped exception for the two pre-existing
session-snapshot failures below. Full regression cannot honestly be called green.
Leave all work unstaged and uncommitted until the Research Director accepts that
disposition. No test waiver or milestone acceptance is inferred by this report.

## Base-HEAD reproduction

Two unchanged tests fail independently of I2:

- `tests/test_e001_historical.py::test_original_sources_and_e001_preserved`
- `tests/test_e001_tooling.py::test_accepted_sources_and_sealed_evidence_unchanged`

Created an isolated copy under `.tmp/e002-i2-regression-disposition/base-head`.
Its code/tests came from the 137 tracked files at base HEAD, exported using
`git archive`. Every working-checkout file was compared with its archived HEAD
blob after CRLF normalization before copying its existing bytes/mtime into the
isolated copy. This preserves the current checkout environment while proving
the baseline content is HEAD, rather than the untracked I2 implementation.
Only copies of the eleven sealed E001 files and original S1.2/S1.3 session
snapshots were supplied as evidence. No original file was modified.

The isolated copy contains no I2 control module, independent control verifier,
I2 test file or synthetic runner. An import audit confirmed all 33 loaded
`hashlab` modules came from the isolated baseline's `src` directory; no I2
module was imported. Both tests reproduce the same first failure: `.gitignore`
is 367 bytes in the CRLF checkout, while the old snapshots require 351 bytes.
Their historical source and sealed-manifest checks pass before that assertion.

Evidence retained in `.tmp/e002-i2-regression-disposition/`:

| File | Evidence |
|---|---|
| `base-head.zip` | Exact Git archive of base HEAD; SHA-256 `708b9329a58c2c2fbb59fd810def3114e30c5a0f08fa3b72030c3930f22f1acf`. |
| `baseline-and-snapshot-inventory.json` | HEAD/branch, all tracked archive/checkout hashes, source mtimes, original snapshot hashes, and complete per-entry classification with expected/current bytes, hashes and mtimes. |
| `run_baseline.py`, `baseline-pytest.txt`, `baseline-imports.json` | Reproducible isolated test runner, two failures, and loaded-module isolation proof. |
| `snapshot-conflicts.json` | No contradictory expectations between common entries of the two old snapshots. The problem is their mismatch with accepted base HEAD. |
| `i2-and-retained-evidence-checks.json` | Reviewed source-inventory comparison and retained fixture transport/inventory checks. |
| `i2-focused.txt` | Fresh result: **76 passed**, no skips, 82.42 seconds. |
| `final-scope-inventory.json` | Final intended file scope and hashes; unrelated work excluded. |

## Exact snapshot classification

Categories below are mutually exclusive. Every non-exact entry also has an
mtime mismatch, recorded individually in the JSON inventory.

| Snapshot group | Exact bytes/stat | CRLF-only content difference | Identical bytes, timestamp-only difference | Other content difference | Total |
|---|---:|---:|---:|---:|---:|
| S1.2 protected | 2,454 | 46 | 14 | 12 | 2,526 |
| S1.3 protected | 2,454 | 50 | 14 | 12 | 2,530 |
| S1.2 sealed E001 | 11 | 0 | 0 | 0 | 11 |
| S1.3 sealed E001 | 11 | 0 | 0 | 0 | 11 |

For the CRLF category, replacing CRLF with LF reproduces the snapshot's exact
SHA-256; this is demonstrated per file, not assumed. `core.autocrlf=true` and
the unchanged HEAD blob explain the first `.gitignore` failure. The 14
timestamp-only entries have exactly the expected bytes and size; no content
correction is needed for them. Their earlier mtime drift's specific cause is
not established by these inventories.

The twelve other-content entries are the same in both snapshots. **All twelve
are tracked files whose current content is already present at accepted base
HEAD**, independent of I2. Their snapshot hashes cannot be recovered by CRLF
normalization:

```text
docs/proposals/e001-reconstruction-phase-b-proposal.md
docs/reviews/architecture-review-033-e4-foundation.md
docs/reviews/architecture-review-035-g1-gap-assessment.md
docs/reviews/architecture-review-036-e5-phase-a.md
docs/reviews/architecture-review-037-numerical-reproduction-decision.md
docs/reviews/architecture-review-038-e5-phase-b-bounded.md
docs/reviews/r9-m1b1-structural-policy-handoff.md
src/hashlab/experiments/exp002_r9_policy.py
tests/e001_reference.py
tests/test_e001_reconstruction.py
tests/test_exp002_e4.py
tests/test_exp002_r9_policy.py
```

This establishes stale baseline-content expectations, without claiming all
differences are environmental or attempting to reconstruct their full edit
history. The snapshots are local session preservation records, not the accepted
scientific source identity or sealed historical manifest.

## Correction assessment and regression status

**No safe local correction can satisfy both tests under this assignment.**
Restoring LF encodings and old mtimes would address two categories but leave
the twelve accepted base-content mismatches. Restoring old content would change
accepted implementation/tests/documentation. Rewriting snapshots, hiding them
from the tests, or removing their assertions would manufacture a passing result.
None was done; original snapshot bytes remain unchanged.

No environment correction, dependency change or test/source modification was
applied. Therefore the latest complete offline regression remains the retained
result in `.tmp/e002-i2-qualification/regression-final.txt`:
**1,408 passed, 2 failed, 2 skipped**. It is not presented as a new full-suite
run in this diagnosis. Both failures were freshly reproduced at isolated base
HEAD, and all 76 I2 tests were freshly rerun in the working checkout. A further
full run cannot be green while these unchanged failing assertions remain.

The two skips are the existing E4 Windows symlink tests (`WinError 1314`),
an environment privilege limitation. Runtime remains CPython 3.12.14 with
pytest 9.1.1; this is not qualification of the approved production interpreter.

## Preservation, scope and readiness

All seven previously reviewed I2 files match the exact hashes in the retained
I2 source inventory. All 137 pre-existing tracked files still match base HEAD
under its checkout line-ending convention; tracked and staged diffs are empty.
No protected existing test or scientific implementation changed because of I2.
All eleven sealed E001 files match both old snapshots in hash, size and mtime;
the original snapshots themselves also retain their pre-diagnosis hashes.

Both retained seven-file fixture directories remain byte-identical, and every
payload matches its completion inventory. Their unchanged completion hash is:

```text
94f31a1ed9adccedf6d71e31468c05fe0ba6a0c8d68bec35d95c943445b56f0b
```

The retained independent verifier report still binds that hash and verifies
14 candidate rehashes / 18 compression blocks. No retained producer/verifier
artifact was regenerated or modified for this disposition. The fresh test run
uses its own temporary fixture, never the retained result directory.

Final intended commit inventory, pending Director acceptance:

1. `docs/proposals/e002-i2-control-byte-specification.md`
2. `docs/reviews/e002-i2-controls-synthetic-handoff.md`
3. `docs/reviews/e002-i2-regression-disposition.md` — the only new deliverable in this assignment.
4. `src/hashlab/experiments/exp002_controls.py`
5. `src/hashlab/experiments/exp002_i2_synthetic.py`
6. `src/e002_verify/controls.py`
7. `tests/test_exp002_i2.py`
8. `tools/qualify_e002_i2.py`

The seven earlier deliverables are unchanged; the new report records diagnosis
only. Local `.tmp/` qualification/baseline copies are supporting evidence, not
part of the recommended source commit. Exclude `.venv313/`, `docs/plans/`, the
two unrelated R9 decision proposals, reviews 039/040, and the newly observed
unrelated `docs/run_all_tagging.ps1`. Nothing is staged.

No remaining I2 scientific blocker was found, consistent with the supplied
scientific-advisor assessment. The outstanding milestone issue is explicit
Director acceptance of the two pre-existing session-snapshot failures, not an
I2 control defect. This exception would apply only to those two node IDs at
this base HEAD and documented checkout state; it would not declare the suite
green, waive future failures, or grant production readiness or execution.

**Commit/PR recommendation:** the scoped implementation is ready for review,
but leave it uncommitted under the user's conditional instruction until the
Director accepts the specific baseline exception. After acceptance, a scoped
I2 commit and PR may report the actual regression result and link this
disposition. No PR was opened, commit created, push/merge performed, or I3 work
started. Rev8/Rev9, thresholds, control bytes, production seed behavior and
historical evidence remain unchanged; no reconstruction, QA2 or E002 research
execution occurred.
