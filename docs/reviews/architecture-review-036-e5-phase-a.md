# Architecture Review 036 — E5 Phase A handoff

Prepared for Architecture Review 037. Bounded historical fixtures only.
No full E audit, candidate SHA-256 evaluation, QA2 or E002 execution occurred.

## Branch, preserved assessment and exact inventory

Verified initial branch `feat/experiment-002-e4`, HEAD
`1a332d8c1ace2c36fa80bc8b808b3d72eba3e255`, empty index and no tracked changes.
Created `feat/experiment-002-e5` from that accepted E4 commit. The uncommitted
Review 035 assessment was preserved, not overwritten. Preexisting `.venv313/`
remains untouched and excluded.

Complete E5 work inventory (all untracked, uncommitted):

1. `docs/reviews/architecture-review-035-g1-gap-assessment.md` — preserved assessment.
2. `src/hashlab/experiments/e001_contract.json` — pinned historical metadata/source contract.
3. `src/hashlab/experiments/e001_reconstruction.py` — bounded provider and audit primitives.
4. `tests/e001_reference.py` — independent direct byte/rank fixture calculations.
5. `tests/test_e001_reconstruction.py` — E5 qualification tests.
6. `docs/reviews/architecture-review-036-e001-numerical-differences.json` — every one of the 86 numeric differences.
7. `docs/reviews/architecture-review-036-e5-phase-a.md` — this handoff.

No accepted E1–E4 source, test, protocol or original evidence file changed.
No commit, push, merge, tag or release creation.

## Historical source and artifact binding

Run: `20261011T205056Z-exp001-fc1d75fc`.
Manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
Recorded clean source commit: `ef595f5c2f2166923fd277def39708409f564419`.
Recorded branch: main, hashlab 0.2.0. Source identity is the immutable commit;
branch name alone is not used as authority.

The manifest pins nine payloads plus its own bytes and digest sidecar, for an
exact eleven-file inventory. `validate_history` rejects links/reparse/special
entries, altered inventory, unaccepted manifest/self-hash, noncomplete status,
changed payload bytes/sizes and malformed JSON (including duplicate/nonfinite
keys/numbers). It compares the entire sealed resolved configuration, seeds and
environment to the checked historical contract and checks result counts.

Important payload pins:

| Artifact | SHA-256 |
|---|---|
| config.resolved.json | d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b |
| seeds.json | b04fa14409ff07606e81757908109427e4309615afd702a564f346b19b32d931 |
| environment.json | 34e5e3c11015405dd540b2541f54086824b066aa83ed94c5fb80e2c13aa467f3 |
| results.json | 1ff1e2a3dc51c2860d7e5e5d69b8941c62e000c2e06f0f03b3d39331ee15818c |

Contract identity: `hashlab-e001-historical-contract-v1`.
Contract SHA-256 (LF bytes):
`008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04`.
The new JSON copies existing sealed values; it does not replace original inputs.
It also pins SHA-256 of LF source bytes obtained read-only with `git show` at the
historical commit for:

- `src/hashlab/candidates/{__init__,base,sequential,random,patterned,structured}.py`
- `src/hashlab/experiments/{baseline,config}.py`

Both supplied source checkout and loaded implementation checkout must match
those pins. CRLF-to-LF normalization applies to source/contract transport only,
never to sealed payload bytes or generated candidate bytes. Independent tests
re-read the original Git objects and verify these exact source pins. All eight
source files are unchanged from the historical revision. Runtime monkeypatching
or malicious in-process callers are outside this metadata trust boundary.

## Exact generator contract and counts

Runner source: `baseline.py:397` (`run_phase`) and `:534` (generator/phase loop).
Generator order is the resolved configuration list below, not the alphabetically
sorted order of `results.json`. Each generator runs discovery then validation.
Each phase attempted 500,000 occurrences and recorded 500,000 unique values,
zero within/cross-phase duplicates and no exhaustion. These are sealed historical
records, not recomputed full-population audit results.

| Ordinal / ID | Exact sealed specification and encoding | Index semantics |
|---|---|---|
| 0 seq-be-w8 | sequential, width 8, encoding be-bytes, start 0; unsigned integer as 8 BE bytes | enumeration index i; D 0..499999, V 500000..999999 |
| 1 seq-dec-w16 | sequential, width 16, encoding ascii-decimal, start 0; zero-padded 16 ASCII digits | same continuing index |
| 2 uniform-be-w8 | uniform, width 8, encoding be-bytes; MT19937 getrandbits(64), 8 BE bytes | raw draw ordinal, independent seeded stream per phase, start_index 0 |
| 3 uniform-dec-w16 | uniform, width 16, encoding ascii-decimal; MT19937 randrange(10^16), 16 zero-padded ASCII digits | same per-phase draw semantics; no substitution of getrandbits for randrange |
| 4 pattern-bytes-w8 | patterned, width 8, mode repeated-bytes, max_period 3; alphabet bytes 0..255 | primitive motifs by period then lexicographic alphabet order; repeat/truncate to width; V continues at emitted index 500000 |
| 5 pattern-chars-w16 | patterned, width 16, mode repeated-chars, max_period 4, alphabet printable-ascii (0x20..0x7e) | same primitive-motif/continuation order, with 95 ASCII symbols |
| 6 struct-gray-w8 | structured, width 8, mode gray; i XOR (i>>1), 8 BE bytes | D/V continuing enumeration |
| 7 struct-stride-w8 | structured, width 8, mode stride, stride 11400714819323198485, offset 0; modulo 2^64, 8 BE bytes | same |
| 8 struct-bitrev-w8 | structured, width 8, mode bit-reversed; reverse exactly 64 bits, 8 BE bytes | same |
| 9 random-bytes-w8 | random_bytes, width 8; keyed BLAKE2b-512 counter stream | independent seed per phase, counter 0 upward encoded as 16 BE bytes; concatenate 64-byte blocks, slice into 8-byte candidates |

Parameters absent from the exact sealed specifications retain only the defaults
of the pinned historical constructors. No unsupported config is accepted and no
new convenient default is supplied. Seven 8-byte generators give 7,000,000 raw
occurrences; three 16-byte generators give 3,000,000. Cross-generator overlaps
are preserved as separate occurrences. The positive control's separate 200,000
inputs are not part of these populations and are not reconstructed by E5.

### Historical seeds and derivation

Master `20261011` is already sealed historical material, not a newly selected
E002 execution seed. For seeded generators the recorded derivation is first
8 bytes, BE integer, of SHA-256 of UTF-8
`hashlab-seed-v1|20261011|<generator_id>|<discovery-or-validation>`.
Independent tests verify this label-material derivation only; candidate bytes
are never input to SHA-256. The provider consumes the sealed subseeds directly.

| Generator | Discovery | Validation |
|---|---:|---:|
| uniform-be-w8 | 11563638942429927757 | 17448145370022348540 |
| uniform-dec-w16 | 4510579110814029430 | 7646975460325050960 |
| random-bytes-w8 | 710289665967761509 | 8231496708541735395 |

Seedless generators have explicit sealed seedless descriptions, not invented
numeric seeds. The separate positive-control seed is 15012741615826235588,
labels positive-control/control; it is documented but not used by this adapter.

### Deduplication and index meaning

`execution.dedup=auto`, max_tracked_candidates=2,000,000, batch_size=10,000.
Sequential, patterned and structured generators are unique by construction.
Uniform and random_bytes generators use an exact per-generator set. Discovery
values carry into validation's seen_previous set. Raw draws are attempted first;
repeats are counted and skipped for hashing, without topping up the 500,000 draw
budget. No cross-generator deduplication occurs. An occurrence index is therefore
not generally a unique-hashed-value ordinal, even though sealed duplicate counts
happen to be zero. Source reference: `baseline.py:425`–`:435`, `:534`–`:560`.

### Historical environment

CPython 3.11.0, Windows AMD64, MSC v.1933; OpenSSL 1.1.1q (5 Jul 2022);
PyYAML 6.0.3, pytest 9.1.1, hashlab 0.2.0; exact machine/environment metadata
is retained in the contract. Current qualification uses CPython 3.13.0.
MT19937 randrange/getrandbits compatibility and BLAKE2b behavior are checked on
bounded independent fixtures, not asserted as original-runtime full reproduction.
No environment replacement or historical regeneration was performed.

## Reconstruction APIs and authorization limits

`validate_history(root, source_root)` strictly authenticates the sealed collection
and source pins read-only. All metadata/source SHA-256 is separate from candidate
evaluation. `contract()` validates the pinned metadata copy before returning it.

`BoundedE001Reconstruction(root, source_root, prefix=8)` implements the
`E001Reconstruction.candidates(request)` shape but intentionally emits only
seven bounded discovery prefixes, default 56 raw eight-byte occurrences.
The method never emits the required seven million; feeding it to the existing
full `audit_e001` must fail its expected-count requirement. This phase must not
be substituted for a production provider or represented as a completed E audit.

`records(generator, phase, start=0, count=prefix)` emits immutable `Occurrence`
records: generator ID, config ordinal, phase, raw occurrence index, historical
enumeration index, exact candidate bytes, scope, source commit and manifest pin.
It revalidates the original artifacts/source before each window. Per-window output
and replay are capped at 4,096. Constructor prefixes are capped at 409 (at most
2,863 occurrences from the seven discovery streams in candidates()).

Direct-index sequential and structured windows can address final historical
indices without replay. Seeded streams replay at most 4,096 raw occurrences per
window. Patterned streams also obey the replay cap; patterned validation requires
500,000 prior emitted values under the historical implementation, so it is
rejected in Phase A. No hidden large islice is allowed. Seeded validation raw
occurrences are reconstructible, but their accepted/deduplicated status versus
all discovery values is unresolved without the prohibited discovery enumeration.
The API makes no accepted-unique status claim. All output remains bounded fixture
provenance, not an authentication of full population completeness.

Auxiliary memory is bounded by generator state, the small contract and fixture
caps. The provider does not retain emitted candidates. Audit/exclusion primitives
use O(min(n,4096)) sets and lists, with explicit hard rejection beyond the cap.
This is a trusted source-checkout interface; JSON package-data distribution has
not been release-qualified. No runnable dispatcher or CLI entry point exists.

## Exact exclusion-audit primitives

A1/A3 membership and A3 rank mapping reuse accepted pure E1 functions without
modification: `in_a1`, `in_a3`, `HammingPopulation.rank/unrank`. Independent
reference tests use direct combinatorial counting, not these implementations.

`exclusion_representation(values)` validates every input as an eight-byte A3
member, counts distinct values and produces increasing unique weight/colex ranks.
Its SHA-256 contract sorts DISTINCT NUMERICAL VALUES and concatenates exact
8-byte BE encodings; it does not hash rank numbers or weight-order encodings.
Duplicate occurrences collapse only in that exclusion-set representation.
`validate_exclusion_representation` rejects unsorted/duplicate/invalid ranks,
false counts or altered digests. It never assumes 60,721 merely from a constant.
The 4,096 cap deliberately prevents a production X3 assertion in Phase A.

`fixture_audit(records, expected)` requires an exact bounded immutable provenance
schedule, sorted by config ordinal/phase/raw index. Repeated, excess, out-of-order
or malformed provenance fails. Candidate values may repeat under distinct
occurrences; these duplicates are reported separately from unique exclusions.
A1 hits produce fixture-a1-hit; early exhaustion produces incomplete.
An enumeration exception produces `InterruptedAudit` with the partial incomplete
summary and original cause. Malformed inputs propagate as rejection.

All summaries use `hashlab-e001-fixture-audit-v1`, include source/manifest,
expected/checked occurrences, duplicate occurrences, A1 hits and exact exclusion
representation. They always state scope bounded-fixture-only and
`e_audit_passed=False`, including complete fixtures. No full count or E claim is
inferred from configuration or fixture agreement.

## Independent qualification and preservation

`tests/e001_reference.py` imports no HASHLAB module. It independently implements
integer/Gray/stride/bit-reversal formulas, literal historical subseeds and direct
BLAKE2b counter slicing; patterned references use the direct periodicity definition,
not production KMP/Mobius logic. Uniform fixtures use the same explicitly stated
stdlib primitive, so they independently check adapter wiring/encoding rather than
independently implement MT19937. A3 references count lower-weight and numerically
preceding eligible values using binomial coefficients. This is independent fixture
calculation, not yet appointment of a separately authored operational verifier.

Tests compare exact byte sequences for all ten discovery streams and supported
validation streams, offsets, final direct-index boundaries, patterned primitive
boundaries, historical seeds, source Git objects and sealed contract payloads.
Negative cases include changed/missing manifest/config/seed/environment/result
provenance, source changes, post-construction tampering, invalid windows, wrong
record identity/index/width, A1 hits, duplicate record keys, duplicate values,
non-A3 exclusions, altered count/digest, short streams and interruptions.

Memory qualification streams 32 and 4,096 BLAKE2b candidate occurrences without
retaining outputs: peak traced Python memory stays below 4 MiB with growth below
1 MiB. No full-population throughput or RSS claim is made. Guarded read-only open
tests and eleven-file before/after snapshots verify no writes. Metadata-only SHA
checks reject candidate-sized input on the adapter's metadata hashing path;
exclusion digests are separately allowed by the approved set-encoding contract.

Focused/full final results and final integrity/status appear below.

## Historical numerical reproducibility — unresolved

The separate numerical-differences JSON retains all 86 mismatching secondary
fields by generator/phase/test/field, original sealed float, recomputed float and
absolute difference, without rounding them into equality. It also records the
analysis timestamp discrepancy and secondary-list ordering difference. Maximum
statistic difference remains 2.2737367544323206e-13 and maximum p-value difference
3.4083846855992306e-14. Counts, decisions and other aligned fields were unchanged
in Review 035's comparison. No tolerance-based G1 pass is introduced.

Strict historical numerical identity remains unresolved. A future separate
proposal may reproduce with the original pinned CPython 3.11.0/dependencies and
compare outside E001, but no installation/replacement/regeneration is authorized
or performed. The original analysis/report/evidence bytes remain untouched.

## Estimated full-enumeration cost and next authorization

These are estimates from the historical algorithm/count structure, not measured
production timings. The seven-million eight-byte audit needs seven million raw
occurrence evaluations plus duplicate accounting; random-bytes contributes
125,000 BLAKE2b-512 blocks across its two phase keys (eight candidates per block),
uniform-be contributes one million getrandbits draws; the remaining five million
are deterministic encodings/pattern/structured mappings. Membership checks are
O(7M), exclusion sorting/ranking is O(x log x) plus bounded combinatorial rank
work, where x is the ACTUALLY OBSERVED distinct A3 intersection, not an assumed
60,721. All 10M historical inputs would additionally include three million
16-byte occurrences, unnecessary for the seven-million eight-byte intersection.

Exact historical seeded dedup verification may retain about one million eight-byte
values at a time per generator: rough Python set/value overhead estimate
80–160 MiB plus exclusions and interpreter overhead, implementation/platform
dependent. Streams processed one generator at a time avoid seven simultaneous
sets. External sorting/disk-backed dedup is a possible future reviewed alternative,
not implemented here. Wall time is unqualified; plan minutes-to-hours as a broad
resource reservation only, not a throughput or completion guarantee. Phase A's
4096-record cap and source/metadata validations must not be naively extrapolated
as a production implementation. No candidate SHA-256 is needed for this E audit.

**An unconditional independent full enumeration is not yet defensible using this
adapter.** Phase A can be reviewed and accepted next; before Phase B authorization:

1. Appoint/pin an independent reconstruction implementation and runtime/environment.
2. Review a separate full-stream provider covering patterned continuation and exact
   seeded discovery/validation dedup, all count/order/provenance bindings and bounded
   resource/failure disclosure. Do not silently lift this adapter's fixture cap.
3. Approve a fixed seven-million-occurrence scope, no candidate hashing, no seed
   substitution/retries, explicit memory/storage reservation and interruption report.
4. Pin independent exclusion-vector/source contracts, require exact observed count/
   digest comparison, and retain separately witnessed audit artifacts outside E001.

Only then could a specifically scoped read-only full E001 enumeration be safely
authorized, conditional on those reviewed resources/contracts. It still would not
pass all G1, qualify QA2 or authorize E002/G2. No full enumeration is recommended
for immediate execution under the current request.

Stop for Architecture Review 037.

## Final qualification and Git status

Qualified interpreter `.venv-py313-review024/Scripts/python.exe`, Python 3.13.0;
PYTHONDONTWRITEBYTECODE=1 and pytest cache disabled. Ignored temporary fixture
copies only; no original evidence writes.

- Focused E5: **79 passed in 3.79s**, no skips.
- Complete regression: **832 passed, 2 skipped in 19.66s**.
- Both skips remain E4 file/directory symlink creation fixtures (WinError 1314,
  missing Windows privilege). Coverage retained; actual junction test passed.
- Final existing manifest verifier: no errors. All eleven E001 hashes, sizes,
  exact file inventory and nanosecond modification times match the retained
  pre-E4 snapshot (`review033-e001-before.json` in ignored qualification storage).
- All accepted tracked E1–E4 files have zero diff against HEAD; no changes to
  statistical decisions or protocol. Review 035 assessment retained unchanged.
- HEAD remains `1a332d8c1ace2c36fa80bc8b808b3d72eba3e255` on
  `feat/experiment-002-e5`; Git index empty.
- Git status: seven untracked E5 inventory files listed above plus preexisting
  excluded `.venv313/`; no tracked modifications.
- No full E001 enumeration, candidate SHA-256 evaluation/rehashing, E002 sampling,
  QA2 hashing, new execution seed/beacon/commitment choice or operational dispatch.
- No E5 commit, push, merge or tag.

Stop for Architecture Review 037.
