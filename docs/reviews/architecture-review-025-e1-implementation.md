# Architecture Review 025 — E1 engineering foundation

Date: 2026-10-11 (America/Los_Angeles). Return for Architecture Review 026.

**Disposition: partial E1 implementation; E1 acceptance remains blocked by the
missing A1 Vitter Algorithm D accelerator.** No confirmatory execution is enabled.
The reference Algorithm S is distributionally correct but is not represented as
fulfilling the accepted A1 production algorithm/performance requirement.

## Repository and qualification

Starting branch: `docs/experiment-002-design`; HEAD/protocol baseline `c0a6d35`.
The pending `.gitignore` change excludes only `.venv-py313-review024/`; the other
qualification file records Python 3.13.0 and the prior 240-test regression.
The index was empty before staging. Only those two files were committed:
`8a27da2cc5e886f0094c67d8d000905959b187f2`, on the documentation branch.
Then `feat/experiment-002-e1` was created at that commit. E1 work is uncommitted
for review. Pre-existing untracked `.venv313/` is retained and unstaged.

The interpreter named in the request, `C:\repo\hashlab.venv-py313-review024\Scripts\python.exe`,
does not exist. Tests used the qualification record's existing interpreter:
`C:\repo\hashlab\.venv-py313-review024\Scripts\python.exe`.

## Files

- Changed and committed: `.gitignore`.
- Created and committed: `docs/reviews/architecture-review-024-python313-qualification.md`.
- Created, uncommitted: `src/hashlab/experiments/exp002.py`.
- Created, uncommitted: `tests/test_exp002_e1.py`.
- Created, uncommitted: this report.

## Implemented contracts

The versioned seedless configuration accepts an exact field set and frozen values,
rejecting unknown/missing fields, type coercion, boolean integers, geometry changes,
seed insertion and changes to represented scientific constants. It binds proposal
revision 8 and A2 encoding v1. It is an E1 library schema, not a runnable Experiment
002 configuration. The original runner and Experiment 001 implementation are unchanged.
Statistical procedures remain specification-only; E1 does not evaluate them.

A1 uses eight-byte big-endian values in `[2^20,2^32)`. A3 indexes by weight then
colex, omitting all-low-32-bit subsets. Full class size is 82,128,984. Rank/unrank
is checked against exhaustive independent small classes and full-domain boundary
probes. Immutable exclusions must be sorted, unique and in range. Production
exclusion verification requires 60,721 entries and the frozen sorted-value digest.
No production exclusions were reconstructed in this pass.

The reference sampler uses local MT19937 instances, integer Algorithm S and an
integer hypergeometric stage split, with separate supplied selection/stage seeds.
It consumes fixed exclusions before selection, emits increasing unique ranks,
and allocates exactly the requested D/V sizes. Additional memory is constant
apart from caller-owned exclusion data. SRS guarantees are conditional on the
protocol's ideal-RNG assumption. No SHA-256 is used per sampled candidate.

A2 implements the exact three approved derivation domains, uint64 master checks,
eight-byte LE key, keyed BLAKE2b-512 messages, 76-byte prefixes and LE32 nonces.
All three KAT prefixes and complete example candidates match exactly. Stage
indices 0–1499 are D and 1500–2999 are V. Candidate nonce range is 0–9999;
the serializer separately accepts the full uint32 range. Prefix collisions halt
without redraw. The production stream validates all 3,000 immutable prefixes
before yielding; tests generated only eight fixture prefixes plus KAT probes.

An E001 audit interface rejects A1 intersections and checks the exact A3
intersection supplied by the caller, with explicit stream count checks. It is
tested on tiny synthetic inputs, not represented as a fresh 7M-candidate audit.
A1/A3 disjointness follows from the high 32 bits; eight-/80-byte populations
cannot overlap. D/V disjointness follows from partitioning one unique sample;
A2 uniqueness follows from checked prefixes and unique nonces. Controls N1/N2/P
are not implemented in E1, so their future runtime overlap audits are not claimed.

SeedCommitment, RegistryRecord and RegistryState provide pure validation/binding
interfaces for digest fields, started/result records, gap-free ids, precommit/seed
ordering, amendment qualification and finality. They do not create a commitment,
select a round, derive a beacon master, write a registry, authorize a retry or
verify external governance. Unsealed F1 results can explicitly omit a manifest.

## Validation and small-fixture observations

Commands used the qualified interpreter with `PYTHONDONTWRITEBYTECODE=1`:

```text
python -m pytest tests/test_exp002_e1.py -q -p no:cacheprovider
54 passed in 0.27s

python -m pytest tests -q -ra -p no:cacheprovider --basetemp .venv-py313-review024/pytest-e1-temp --junitxml .venv-py313-review024/pytest-e1-results.xml
294 passed in 3.73s
```

The full result comprises all 240 existing tests and 54 E1 tests, with no failures
or skips. Replay matches a pinned small rank/stage vector. Three A2 KATs pass.
Small fixed-seed inclusion-frequency checks pass; these are engineering checks,
not confirmatory inference or production qualification QA2.

With tracemalloc enabled, reference Algorithm S over 20,000 ranks measured:

| Requested sample | Emitted | Wall seconds | Peak traced bytes |
|---|---:|---:|---:|
| 100 | 100 | 0.034973 | 6,600 |
| 18,000 | 18,000 | 0.066976 | 6,696 |

These are single small-fixture observations, not throughput forecasts. Tests
check sample-retention memory does not scale with sample size. A3 exclusion
storage is O(exclusions); digest verification additionally sorts exclusion values.
A2 plan prefix storage/checking is O(prefix count), never O(candidate count).

## Outstanding E1 matters for Review 026

1. Implement and independently review the accepted A1 Vitter Algorithm D skip
   sampler. The engineering adapter/reference must not substitute for it in a
   production plan. This is unfinished implementation, not a protocol amendment.
2. A1/A3 selection and split sub-seed label strings are not byte-frozen in the
   accepted text as A2's labels are. The current interface takes explicit
   engineering sub-seeds and does not invent confirmatory labels. Architect
   disposition is needed before binding those labels into production identity.
3. Registry persistence, commit/witness verification, full beacon commitment and
   retry authorization are later operational integration, not established by
   these pure interfaces. The supplied state flags are not governance evidence.
4. Production exclusion reconstruction/count verification and production sampler
   performance have not been run. No claim of completed G1 or QA2 is made.

## Experiment 001 and restrictions

Read-only integrity verification passed for all nine payload SHA-256 digests and
sizes, the exact 11-file inventory and manifest self-hash. Manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
No evidence files were modified. This establishes local integrity against the
existing pinned record, not independent historical authenticity or archival.

No E2/E3/E4 work, Experiment 002 execution, confirmatory subset, full-scale
generation, research candidate SHA-256 evaluation, execution seed, beacon round,
push, merge or tag occurred. Only seed-derivation, exclusion/file-integrity hashes
and small engineering tests ran. Git index remains empty. Untracked E1 files and
the pre-existing `.venv313/` remain for review.

## Review 026 continuation

The entries above are the preserved Review 025 historical result. The current
implementation, source correspondence, tests, proposed seed-label contract and
remaining approval gates are recorded in
[Architecture Review 026 E1 report](architecture-review-026-e1-implementation.md).
The earlier missing-Algorithm-D implementation blocker is addressed there;
the Architect still determines E1 acceptance.

The subsequent [Review 027 closeout](architecture-review-027-e1-closeout.md)
records the approved seed-contract binding and real-population bounded benchmarks.
