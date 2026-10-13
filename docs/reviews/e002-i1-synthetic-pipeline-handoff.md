# E002-I1 — bounded synthetic pipeline qualification

Qualified on 2026-10-12 (America/Los_Angeles), on
`feat/e001-independent-qualification`, accepted HEAD
`be344c750302a8faeee48d321a6f4b99459b415f`. All changes remain uncommitted and
unstaged. This is engineering qualification only. It is not QA2, a research
execution, gate acceptance or confirmatory completion.

The pipeline connects accepted A1 Vitter sampling, A2 prefix/LE32 encoding and
exclusion-aware A3 Algorithm S to the existing SHA256Engine, strict `<2**248`
comparison, CandidateRecord and Accumulator. Selection and stage allocation use
separate public fixture RNG constants; A2 uses a fixed raw engineering key.
No experiment master, beacon or commitment was selected or derived.

| Arm | Explicit fixture population | Discovery | Validation |
|---|---|---:|---:|
| A1 | First 256 ranks of accepted eight-byte BE low integers; without replacement, then stage split | 32 | 32 |
| A2 | Clusters 0 and 1500; accepted 76-byte prefix plus nonce 0..31 in LE32 | 32 | 32 |
| A3 | True 64/32/6 weight/colex ranks `[0,4096)`; 218 historical exclusions, 3,878 eligible ranks | 32 | 32 |

Each producer run evaluates **192 unique candidate byte strings / 256 SHA-256
compression blocks**. Its separate verifier performs another 192 evaluations /
256 blocks. Three standalone producer/verifier pairs were executed for initial
qualification, measurement and final replay (1,152 candidate evaluations total,
excluding the bounded test-suite fixtures and fixed known-answer tests).
All three producer directories are byte-identical. A3 never scans the full
82,128,984-rank class. A1/A3 discovery and validation are disjoint random
partitions; A2 uses its accepted deterministic cluster stage assignment.

The read-only S1.4 adapter authenticates all eight retained files against accepted
pins, both completion reports and their agreement, the producer's recorded file
inventory, source/config/contract/manifest identities, original sealed files and
historical source bytes. It checks 60,721 distinct numeric-ordered eight-byte
values, their canonical digest, each accepted Hamming/colex rank and the separate
sorted `ranks.bin`. It never reconstructs E001. This set is only the A3 exclusion
intersection, not the complete E001 population.

Evidence contains canonical fixture/history metadata, every ordered candidate
with arm/stage/stream index/population rank/cluster, digest and success flag,
and the existing streamed accounting snapshot. Actual candidate bytes enforce
uniqueness. Exclusive creation, flush/fsync and a completion report written last
prevent an interrupted attempt from becoming complete; partial bytes remain for
inspection. There is no overwrite, resume or retry path. Durability is subject
to OS/filesystem fsync guarantees. The frozen accounting `complete` flag remains
false; only the separate `synthetic_complete` flag is true.

The reference package imports no HASHLAB production code. It independently
authenticates historical inputs, reconstructs the dense A1 fixture using exact
Fraction survival inversion, decodes A3 with binary-search colex unranking,
replays Algorithm S, constructs A2 from its byte specification and hashes with
stdlib `hashlib.sha256`. It compares every record and recomputes all accounting,
including successes, byte/leading-zero histograms, clusters and Hamming weights.
An externally retained completion pin is mandatory. Missing, extra, reordered,
duplicated, truncated, altered or resealed inconsistent evidence fails.

Producer and verifier agreed on all 192 records. Descriptive successes were zero
in five streams and one in A3 validation. No statistical or advantage claim is
made. The complete-report SHA-256 is:

```text
0a0c4e6d4a506af3b159ebd801b20baee8d611178a0f01322d30d865b3cb9c62
```

Final qualification: **1,334 passed, 2 skipped in 40.91 s**, including 99 I1
cases. The skips are existing E4 symlink tests: Windows privilege error 1314.
Coverage includes all arms/stages, sampling and byte uniqueness, RNG separation,
encoding and rank boundaries, fixed SHA-256 vectors, strict target equality,
accounting, producer/reference disagreement, interrupted writes, tampering even
after transport resealing, S1.4 identities/digest/rank checks and rejection of
confirmatory/QA2 claims. Unit-only mocked history is distinct from tests that
authenticate the actual retained evidence; those integration tests passed here.
They explicitly skip on installations lacking retained S1.4 data.

Final separate-process measurements on qualified CPython 3.13.0 / Windows 11:
producer 0.645 s, peak RSS 38,371,328 bytes; verifier 0.655 s, peak RSS 41,222,144
bytes. Times include imports and retained-file authentication. Whole-process
Windows PeakWorkingSetSize includes native memory. Each producer evidence
directory occupies 109,754 bytes. Historical evidence is read in bounded blocks
for integrity; only the fixed exclusion set and tiny fixture are held in memory.

New review inventory:

- `src/hashlab/experiments/exp002_s14.py` — authenticated read-only adapter.
- `src/hashlab/experiments/exp002_synthetic.py` — fixed producer pipeline.
- `src/e002_verify/__init__.py`, `src/e002_verify/core.py` — separate reference.
- `tools/qualify_e002_i1.py` — separate-process producer/verifier commands and measurements.
- `tests/test_exp002_i1.py` — deterministic qualification and fault injection.
- `docs/reviews/e002-i1-synthetic-pipeline-handoff.md` — this handoff.

Retained qualification artifacts are under
`results-smoke/e002-i1-qualification-20261012-01/`: `producer/`,
`measured-replay/`, `final-producer/`, `producer-pin.json`, `verified.json`,
final process measurements, source/qualification inventory and preservation
snapshots. These are ignored local engineering artifacts. Reproduce into a new
destination with the qualified interpreter and `tools/qualify_e002_i1.py produce
<new-directory>`, then `tools/qualify_e002_i1.py verify <new-directory> --pin
<printed-complete-sha256>`. Final regression used `python -m pytest -q -p
no:cacheprovider --basetemp results-smoke/e002-i1-qualification-20261012-01/pytest-final-regression`
with `PYTHONDONTWRITEBYTECODE=1`.

Preservation passed for all **149 baseline files** by SHA-256, size and observed
`mtime_ns`, including every accepted tracked source/design/test, all eleven
original sealed E001 files and all eight S1.4 files. The tracked diff and index
are empty. Git status consists of the seven new scoped files above plus the
unchanged pre-existing untracked `.venv313/`, `docs/plans/`, two R9 proposals and
Reviews 039/040. No commit, push, merge or tag occurred.

N1/N2/P controls remain the next integration milestone. Their existing accounting
slots are zero placeholders, not implemented controls. Frozen inference and
secondary-analysis code remains unchanged; tiny counts are not passed off as
frozen-geometry statistical results. Full experiment orchestration, production
durability/recovery, QA2 and governance/seed procedures remain unqualified.
Independent algorithmic agreement shares AI authorship, Python and generic
cryptographic libraries; no off-machine or independent human verification is
claimed. Work stops at this qualification handoff.
