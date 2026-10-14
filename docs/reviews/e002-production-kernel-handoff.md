# E002 production execution kernel — implementation handoff

2026-10-13, America/Los_Angeles. Branch `feat/e002-production-readiness`.
Unchanged base **`16f8b30ae30a9ef3ffc0f2868e9508e70c8007cd`**.

**Implemented and boundedly qualified:** an inert production plan, full-geometry
stream scheduling and eligibility checks, shared evaluation/accounting kernel,
compact streaming capture, disclosure controls and guarded measured-inference
adapter. The fixed engineering adapter functions end to end with independent
regeneration/rehashing. **Production activation remains unconditionally disabled.**
This is not G1, QA2, a production audit or confirmatory scientific evidence.

## Files and interfaces

All kernel implementation files are new; accepted E1–E4/I1/I2/I3/science/test Git
blobs remain unchanged. Finalization adds only the two-path LF checkout rule
described below. The existing readiness assessment and source inventory remain
intact and are included as baseline assessment artifacts.

| New file | Interface / responsibility |
|---|---|
| `src/hashlab/experiments/exp002_kernel_plan.py` | `ProductionPlan`, `RuntimeBinding`, `Artifact`, `source_inventory`, `observe_runtime`, `master_material`, `derive_master`, fixed `EngineeringPlan`. |
| `src/hashlab/experiments/exp002_kernel.py` | `run_engineering`, disabled `run_production`; common lazy `_scheduled_attempts`, `_Eligibility`, `_coordinate`, opaque `VerifiedCapture`, bounded `authenticate_capture`. |
| `src/hashlab/experiments/exp002_kernel_evidence.py` | `Attempt`, binary row codec, `ChunkWriter`, `iter_chunks`, exclusive/incomplete output creation. |
| `src/hashlab/experiments/exp002_kernel_disclosure.py` | `private_processing`, sanitized `KernelFailure`, restricted public outcome/progress/failure/inspection interfaces, `RestrictedInference`. |
| `src/hashlab/experiments/exp002_kernel_inference.py` | `infer_measured`; `_calculate` calls unchanged primary/control/secondary inference. |
| `src/e002_verify/kernel.py` | Separately implemented binary decoder and `verify_engineering`; imports accepted independent I1/I2 references, no `hashlab` code. |
| `tests/test_exp002_kernel.py` | 92 bounded plan, scheduler, codec, reconstruction, corruption, interruption, inference and disclosure tests. |
| `tools/qualify_e002_kernel.py` | Only `produce`/`verify` for the fixed 206-evaluation engineering fixture. No production/QA2 role or quota/seed switch. |
| `docs/reviews/e002-production-kernel-handoff.md` | This handoff. |
| `.gitattributes` | Enforce `text eol=lf` only for the two accepted independent reference copies. |

The versioned production plan embeds the unchanged E3 seedless scientific plan,
canonical frozen configuration digest, R8/R9/governance/secondary identities,
approved derivation labels, control thresholds and source ranges, exact S1.4
history pins, runtime/dependency bindings, format/version, audit-scope decision
and restrictions. Missing/extra/altered frozen fields fail round-trip validation.
Local validation compares actual package bytes, interpreter/dependency identity,
Git HEAD and committed source correspondence, then authenticates retained history.
Uncommitted kernel files cannot qualify as a committed production release.

Source capture covers all 53 current HASHLAB Python/contract files, including
package initializers and transitive dependencies. Runtime observation binds the
actual interpreter hash/version/platform and installed PyYAML file inventory
digest/version. This is observed local identity, not production-runtime approval,
a complete reproducible OS/stdlib image, external authentication or honest-capture
assurance. No missing governance receipt is fabricated.

The approved master calculation is implemented as exact ASCII serialization,
SHA-256 first eight bytes and uint64 big-endian conversion. Two public synthetic
vectors check complete message/digest/conversion; malformed casing, lengths and
rounds are rejected. It performs no beacon retrieval/signature verification,
round selection, commitment creation or operational seed acceptance.

## Production capability and deliberate action limits

The scheduler has explicit full-geometry branches: A1 Algorithm D over
4,293,918,720 ranks with 15M/15M allocation; all A2 3,000×10,000 prefix/nonces;
A3 Algorithm S over the full 82,128,984 rank class with exact exclusions; default
production N1/N2/P geometry. Full-domain scheduler argument tests use empty spies,
not production-density sampling. No production performance is inferred.

The engineering branch reuses I3's A1/A3 seeds and reduced rank populations,
I1 A2 key/clusters/nonces, and I2 engineering-domain controls. No constructor or
runner quota/seed override is provided. Eligibility enforces ordered arm/rank
progression, accepted indices, complete control source/raw continuity, exact
rejection reasons, A2 encoding and N2 accepted-order stage/cluster assignment.
N1 stops before 30,999,999; P streams share the ascending cursor from 2^63. N2
is not deduplicated. A1's historical disjointness uses the authenticated S1.4
zero-intersection result; A3 checks exact rank exclusions. Full N1/P history is
key-bound rather than replaced with the A3 subset.

Every accepted record receives exactly one base SHA-256 evaluation. The approved
transformation uses that digest; effective outcomes enter E3 accumulation and
success evidence. Rejected attempts receive no candidate SHA-256 evaluation.
Exact expected evaluation/block totals are derived from stream quotas. A growing
global candidate set is not used.

`run_production` rejects before any generation/I/O, including `enabled=True`,
unchecked masters, fixture domains and quota arguments. `_coordinate` has an
additional production guard; `_production_inputs` cannot accept an unchecked
master. There is no activation boolean, dispatch command, beacon client, approval
parser, resume or retry. Enabling production requires a reviewed source change
and authenticated seed/action integration; changing a scope string is insufficient.

## Evidence and verification semantics

Format **`hashlab-e002-kernel-chunks-v1`** writes one attempt per row, up to 4,096
rows per chunk, with a streaming canonical `chunks.jsonl` index. No array of
all chunks, candidates or digests is retained in the producer.

All binary integers are big-endian. A 28-byte `>8sIQQ` header binds magic
`E002KRN1`, version 1, chunk number and first global attempt number. A 48-byte
`>QBBBBQQQQI` row header contains global attempt number, arm/stage ids,
rejection bitmask, candidate length, source/raw index, accepted index,
population rank, byte offset and cluster. Arm ids follow
`A1,A2,A3,N1,N2,P1,P2+,P2-`; stages are `D,V,C`; reason bits are
`C1,C3,E001,A2`. Optional uint64 fields use all-one bits, and absent cluster uses
uint32 all-one bits. Candidate payload is 8 or 80 bytes. Accepted rows append
32-byte raw and 32-byte effective digests; rejected rows append no digest.
Effective success is derived by the frozen strict target comparison.

A 48-byte `>QQ32s` trailer binds row count, body length and SHA-256 of the row
bytes. Index entries additionally bind chunk name/number, first attempt, rows,
whole-file size and SHA-256. Row size is at most 192 bytes. Payloads include plan,
history, environment and accounting. A completion document is durably created
last, pins their inventories and the index, and reconciles exact trials,
evaluations, compression blocks, successes and rejections. Embedded accepted rows
provide complete effective success evidence without a duplicate success list.

Writes reuse E4 exclusive creation, plain-file checks, inventories and fsync.
Failures retain chunks/index/marker and a redacted failure sidecar where writing
is possible. Torn chunks, wrong inventory/sequence/counts, invalid transformations,
duplicates and missing evaluations cannot pass the required full bounded reader.
Existing paths are never reused. There is no automatic journal recovery or repair.
OS power-loss durability is not qualified by these tests.

`authenticate_capture` performs transport integrity and streaming accounting
replay against a caller-retained local pin. It does not independently regenerate
candidates or rehash digests. Its opaque engineering capability cannot enter
production inference. The independent engineering reader separately reconstructs
every expected candidate/rejection/source/stage and rehashes every accepted row;
resealed semantic corruption fails even against an updated local transport pin.

Production capture authentication is deliberately unavailable until independent
production finalization can bind resolved seeds/source/evidence. `infer_measured`
requires an opaque matching production capability and complete validated E3
geometry, then invokes unchanged three-arm Holm, A2/N2 cluster/hull procedures,
null/positive gates, nine-cell labels and all 36 secondary slots. Partial, synthetic,
raw or forged public inputs are rejected. Five artificial count families qualify
the calculation against accepted independent references; one private **unit-only**
capability injection tests adapter dispatch. No artificial artifact is issued as
an authenticated measured production result. Numerical failures remain failures.

Full independent production regeneration/rehashing is supported by the format,
but is not implemented or run here. The plan preserves the approved cheaper
success-plus-sample option as an explicit unresolved freeze decision; that option
cannot prove absence of omitted successes. A local completion pin is not an E4
external seal or R9 timestamp/checkpoint/approval.

## Disclosure and failure behavior

The public boundary returns status/scope/pin only, validates fixed progress
fields, suppresses incidental Python stdout/stderr and logging during processing,
and raises a fresh sanitized exception outside the original exception handler.
F1–F3 reports and production inspection expose neither primary counts nor V
histograms/ratios/success lists. Measured inference is represented by a restricted
object with redacted repr/inspection. Final disclosure always rejects until an
authorization adapter is implemented. F4 disclosure requires completed restricted
inference with an actual control-gate failure; replicated null deviations produce
`BLOCKED`, other F4 cases `UNINFORMATIVE`, with required full failed statistics.

Adversarial tests inject secrets into print, pre-existing logging handlers,
custom log level 100, exception text and inference failures. Captured public output
and formatted tracebacks contain no secret, and public errors retain no original
exception context. Private evidence retains observations. This is a single-threaded
normal-interface boundary, not encryption, OS access control or a claim that a
solo operator cannot read raw files, attach a debugger, emit native writes or
deliberately bypass private APIs.

## Qualification evidence and remaining work

Local artifacts: `.tmp/e002-production-kernel-qualification/`. Original logs and
intermediate attempts are retained rather than overwritten.
Exact scoped hashes, preservation comparisons, retained evidence checks and final
reports are bound in `final-source-inventory.json` in that directory.

- Implementation-closeout focused suite: **92 passed**, no skips, **8.75s**.
- Implementation-closeout full offline suite: **1,567 passed, 3 failed, 2 skipped**, **135.53s**. It was
  **not green**. The two E001 session-snapshot failures remain
  `test_e001_historical.py::test_original_sources_and_e001_preserved` and
  `test_e001_tooling.py::test_accepted_sources_and_sealed_evidence_unchanged`;
  both first fail on `.gitignore` size 367 versus 351. Their I2/I3 exceptions do
  not establish G1 readiness. The two E4 symlink tests still skip for Windows
  privilege error 1314.
- The third failure at implementation closeout was
  `test_exp002_i3.py::test_reference_independence_and_reused_accepted_algorithms`:
  current-checkout reference copies contain CRLF but the accepted test requires
  raw LF. This is **not an accepted additional exception**. An isolated source
  copy from unchanged base HEAD, with no kernel files, reproduces the failure.
  Changing only its two reference copies to LF makes that one test pass. Every
  copied baseline source matches its Git blob after LF normalization. Original
  checkout bytes and tests were not altered. Diagnosis and both logs are
  `baseline-i3-checkout-diagnosis.json`, `baseline-i3-crlf.txt` and
  `baseline-i3-lf-copy.txt`. The Director-authorized finalization below corrects
  this checkout issue; the original failed result is retained, not reclassified.
- Final real-history producer: `producer-reviewed/`; independent separate-process
  reader: `verifier-reviewed-report.json`. Both agree on **206 evaluations / 274
  compression blocks**, 206 attempts. Unit history fixtures inject two historical
  rejections and verify the same 206 accepted evaluations from 208 attempts.
- Final completion SHA-256:
  `989692bb628126509157f432653b689033c4534d55a5293c0c32aeb17cd55b42`.
- Final evidence: **87,818 bytes**, seven files. Producer **56.126s /
  857,325,568-byte peak working set**; verifier **5.169s / 838,905,856 bytes**.
  Measurements include complete retained-history authentication/index work and
  overlap a regression run; they are resource observations, not throughput or
  production feasibility guarantees. Each separate producer/verifier performs
  only the fixed 206 candidate evaluations. Earlier separate-process evidence
  is retained under `producer-final/` and its reports as an intermediate revision.
- Deterministic unit replay compares every file byte-for-byte. Supplied-digest
  tests exercise positive lifting/negative suppression without extra candidate
  evaluation. 4,097/8,193-row codec tests cross chunk boundaries using supplied
  digests only, not new research hashing.

Runtime: bundled **CPython 3.12.14**, pytest **9.1.1**, existing local site-packages;
no install or environment replacement. This does not qualify the approved
production runtime. Reproduce with that interpreter, `PYTHONDONTWRITEBYTECODE=1`
and `PYTHONPATH=C:\repo\hashlab\src;C:\repo\hashlab\.venv-py313-review024\Lib\site-packages`:
`python -B -m pytest tests/test_exp002_kernel.py -q -p no:cacheprovider`.
The same environment must reach child processes. The first regression bootstrap
omitted the inherited source path, causing five subprocess import failures in
addition to the inherited two snapshot failures; the original log is retained.
No tests were changed to bypass those failures.

## Director-authorized line-ending finalization

The Director accepted implementation and bounded qualification, with the existing
two E001 snapshot dispositions applying only to this engineering milestone, and
required correction of the third I3 failure without an exception. This is not G1
acceptance.

The new `.gitattributes` has exactly two anchored rules:

```gitattributes
/src/e002_verify/binomial_reference.py text eol=lf
/src/e002_verify/secondary_reference.py text eol=lf
```

Git now reports `i/lf w/lf attr/text eol=lf` for both files. Existing stat-matched
files were not rewritten by `checkout-index -f`; fresh copies were materialized
by Git into a new scratch prefix, checked, then copied to these two authorized
working paths. Their prior CRLF bytes remain in finalization scratch. Both Git
blobs are unchanged and the original I3 assertion is unchanged. The LF copies
match their accepted `tests/exp002_reference.py` and
`tests/exp002_secondary_reference.py` contents exactly after the source's specified
LF normalization. LF SHA-256 values are respectively
`71a9c12b5b79150042a580e46486f0bacc4f13f6450eb8fce1dc6a340a63edff` and
`4796cdb654bfe85d6511f87b8fc8444b89e60a13ad7ff687ef12078b9c60ba88`.
No cryptographic/statistical calculation or unrelated file ending changed.

Finalization logs are retained separately under
`.tmp/e002-production-kernel-finalization/`; the earlier qualification and
baseline-reproduction logs above remain historical evidence.
The affected I3 test passed **1/1 in 0.22s**, and the kernel focused suite passed
**92/92 in 8.76s**, with no skips.
The corrected complete offline regression reported **1,568 passed, 2 failed,
2 skipped in 135.80s**. The only failures are the two named E001 snapshot tests
above, retaining their existing milestone-only disposition. The two Windows
symlink privilege skips remain. There are no new failures, the I3 failure is
corrected, and the suite is **not green**. This remains **not G1 acceptance**.

At implementation closeout, preservation comparisons passed for all **181** inventoried pre-existing files
by hash, size and observed modification time, including both readiness artifacts,
the eleven original E001 files and eight retained S1.4 files. At that closeout,
the tracked tree and index were unchanged. Retained I1/I2/I3 completion/payload inventories are
checked against their prior pins in the qualification inventory; no historical
snapshot or evidence file was rewritten. Unrelated untracked files remain outside
the change scope.

Finalization preserves the other **179/181** baseline files by exact hash, size
and observed modification time. The only authorized working-byte changes among
those 181 are the two reference copies' CRLF-to-LF checkout conversions; their Git
blobs are unchanged and their original bytes are retained in finalization scratch.
Both readiness artifacts still match their accepted baseline hashes and are
included unchanged. Historical E001/S1.4 evidence and all seven pinned I1/I2/I3
producer/replay directories verify unchanged. Finalization preservation and scoped
hashes are recorded in
`.tmp/e002-production-kernel-finalization/finalization-inventory.json`.

Next increment: independent **production** sampling/seed/outcome verification and
evidence finalization, including resolved seed and committed source/runtime
authentication, streaming production capture capability issuance and real R9/E4
journal/seal/checkpoint/retention integration. Keep production activation disabled
until separately approved. G1 still needs production resources/runtime/blinding
qualification, required test/symlink closure and strict E001 numerical/runtime
reproduction disposition. Then separately authorized same-path QA2, G2 smoke,
release/freeze, external commitments/beacon procedure and exact-attempt execution
approval remain mandatory. No candidate-selection science needs redesign.

No production seed, round, beacon or commitment was selected; no QA2, A1
production-density benchmark, E001 reconstruction, full experiment, full outcome
audit, merge or tag occurred. The Director authorized the scoped milestone commit,
branch push and PR against main after final qualification; no automatic merge or
next production-verifier increment is authorized by this finalization.
