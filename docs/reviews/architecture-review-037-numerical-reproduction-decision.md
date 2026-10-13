# Historical numerical reproduction decision memo — v1

Architecture Review 037 documentation for Review 038.
Memo identity: `hashlab-e001-original-runtime-reproduction-memo-v1`.
Status: decision requested; no runtime installation/replacement or reproduction
execution authorized or performed by this memo.

## Decision needed

E001 evidence integrity is established, but strict historical numerical identity
is unresolved. Decide whether to commission a separately provisioned original-
runtime, read-only analysis reproduction, and what exact identity claim it may
support. This is independent of the E5 Phase B occurrence/exclusion audit and
must not be a hidden prerequisite waiver or tolerance-based G1 pass.

Accepted E5 Phase A commit: `9d31eda5d7f20af00824ccdbe1452f8509567952`.
Historical source: `ef595f5c2f2166923fd277def39708409f564419`.
Sealed manifest SHA-256:
`546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
Evidence directory: `results/20261011T205056Z-exp001-fc1d75fc`.

## Observed discrepancy, retained without normalization into equality

[The accepted discrepancy ledger](../reviews/architecture-review-036-e001-numerical-differences.json)
retains 86 secondary floating-point field differences under current CPython
3.13.0 versus sealed output from CPython 3.11.0. Entries identify generator,
phase, test, field, original float, recomputed float and absolute difference.
They comprise statistic/p_value differences, with maximum absolute statistic
difference 2.2737367544323206e-13 and maximum p-value difference
3.4083846855992306e-14. All 86 remain actual discrepancies regardless of size.
No epsilon, rounding or tolerance converts them into an identity pass.

The ledger separately records the generated analysis timestamp and secondary
list ordering difference. These are additional representation/provenance
differences and must be reported, not overwritten or silently sorted away in
a purported byte-identity claim. Review 035's aligned comparison found all integer
counts/decisions and other aligned fields exactly equal; that narrower observation
does not establish complete analysis-file or numerical identity.

Evidence hashes/sizes/inventory/mtime_ns still match all eleven original files.
The historical source is preserved. Numerical drift is not evidence corruption,
and its cause has not been demonstrated. Runtime changes are a plausible cause,
not a proven diagnosis from observing the Python version alone.

## Known environment versus missing reproduction artifacts

The sealed environment records CPython 3.11.0, build string
`3.11.0 (main, Oct 24 2022, 18:26:48) [MSC v.1933 64 bit (AMD64)]`,
Windows AMD64/10.0.26200, OpenSSL 1.1.1q (5 Jul 2022), hashlab 0.2.0,
PyYAML 6.0.3 and pytest 9.1.1. The exact historical source and sealed resolved
configuration/results are available. Qualification environment now uses 3.13.0.

Recorded package versions and environment descriptions do not supply an
original interpreter binary hash, complete dependency artifact hashes, compiler/
C-runtime inventory, original installation image or a full reproducible build
recipe. A new installation labelled 3.11.0 might still differ in build/platform
behavior. Availability/provenance of the original executable and dependency
artifacts must be assessed before claiming exact environment recreation.
No download, installation, build, environment replacement or package resolution
was performed for this memo.

## Options and implications

| Option | What it can establish | Limits and required decision |
|---|---|---|
| A — isolated original-runtime analysis-only reproduction | Exact recomputation of numerical fields and decisions from immutable sealed counts using the original source/runtime, if original artifacts are authenticated | Requires separate provisioning and read-only execution approval; may still fail identity if build/dependencies or ordering differ. Timestamp/order and full-byte comparison must be separately disclosed. No promise of success. |
| B — independently authored numerical diagnosis | Which formulas, arithmetic order, math-library/runtime operations or serialization stages cause divergence, with original/recomputed values retained | Does not itself reproduce original runtime or prove strict identity. Must not substitute an independent tolerance result for an identity criterion. Scope only sealed count analysis, no candidate hashing. |
| C — retain unresolved strict reproduction while accepting narrower component findings | Accurately preserves the accepted integrity/count/decision findings and known limitations without additional runtime work | G1's strict historical reproduction item remains PARTIAL; Architect may clarify claim scope explicitly, but no implicit/tolerance identity pass is issued. |

Recommended decision: approve **planning/artifact provenance assessment for A**
first, with B available for diagnosis if explicitly scoped. Do not authorize
execution until runtime/source/dependency pins and comparison criteria have
been reviewed. Option C is the truthful status until a separate result is
accepted. No source or historical-result edits are an acceptable way to
eliminate differences.

## Proposed separately authorized A procedure

1. Appoint an independent reproduction owner and approve a trusted isolated
   location/VM. Obtain original interpreter artifacts if available, record
   publisher/original provenance and file hashes, and pin exact dependencies,
   historical source and all imported numerical/helper modules. If original
   binary provenance is unavailable, label the environment reconstruction as
   approximate, not identical, and return for decision before execution.
2. Keep current qualified Python and all accepted work intact. Use a separate
   immutable source export or read-only checkout at the historical commit;
   no edits to historical source, no regeneration of result counters and no
   candidate-generator/hash-engine invocation. Disable network access during
   reproduction and avoid dependencies selected from unpinned latest versions.
3. Verify the original eleven evidence files, then work from an authenticated
   read-only copy in the isolated location. Record exact hash/size/inventory/
   mtime_ns of originals before and after. Place all new artifacts outside E001.
4. Invoke only the pure historical analysis on sealed `results.json` and
   `config.resolved.json`. Do not invoke CLI analyze (it writes below the run
   directory), the runner, QA2 or any candidate regeneration. Record interpreter,
   dependencies, command/adapter revision, inputs, all outputs, stdout/stderr and
   any failure without replacing a previous result or retrying silently.
5. Independently compare every field. Emit original and recomputed values,
   exact JSON numeric representations and binary float representations (for
   float fields) as diagnostic evidence. Report counts/decisions separately
   from numerical fields, timestamps, array order and file bytes. Never round
   values, reorder the stored evidence or substitute sealed values into output.
6. Define the reviewed acceptance claim before execution: strict numerical field
   equality is exact, not tolerance based. A keyed secondary-row correspondence
   may identify a discrepancy but must also preserve/report original order and
   raw output; it cannot be described as full byte identity. A timestamp generated
   at analysis time will differ; this does not justify silently removing it from
   a broader claim. If the Architect requires identical complete serialized
   output, report failure unless all bytes actually agree; do not inject the
   original timestamp into source/runtime to manufacture that result.
7. Publish a separate independently authenticated report binding manifest/input
   pins, source/environment/artifact hashes, the exact comparisons, every
   discrepancy and limitations. Original analysis/report remain sealed. A mismatch
   blocks the requested identity claim and returns for review, with no tolerance
   waiver, automatic alternative runtime or source adjustment.

A narrowly approved diagnostic adapter may load inputs and capture output
outside E001; it must not change historical numerical code or decision rules.
Exact comparison/reporting code needs review before the proposed execution.
No historical full experiment regeneration is part of A or B.

## Relationship to MT19937 and G1 / QA2 / G2

Original-runtime numerical reproduction concerns analysis of sealed counts; it
need not generate any candidates. It therefore does not independently qualify
MT19937 integer seeding, getrandbits ordering or the complete seven-million
occurrence stream. Conversely an independent MT-compatible reconstruction can
validate candidate bytes without resolving numerical analysis drift.

The current Phase A MT reference shares stdlib random.Random with the producer.
It verifies bounded wiring/byte encoding and existing seeds, not independent RNG
compatibility across all historical outputs. The Phase B proposal explicitly
requires closing that gap with independently authored/pinned semantics and
reviewed original-source/runtime cross-checks. Neither procedure passes all G1,
performs QA2, grants G2 or selects an E002 release/seed/beacon/commitment.

## Approvals requested for a later task

Architect decisions required: desired identity claim, original-artifact provenance
standard, independent owner, permitted provisioning location/dependencies, exact
comparison/report schema, whether to authorize A execution after preparation,
and whether B diagnosis is separately allowed. Custodian/resource-owner approval
is needed for isolated artifacts and external report storage/authentication.
If an original artifact is unavailable, return that fact; do not substitute a
convenient patch version or introduce a tolerance-based pass.

This memo does not install/replace a runtime, regenerate historical results,
change the accepted source/evidence, execute candidate SHA-256, enumerate E001,
run QA2/E002 or issue a reproduction/G1 pass.
Stop for Architecture Review 038.

## Review 038 read-only artifact provenance assessment and exact comparison specification

No original runtime was downloaded, installed, invoked, replaced or regenerated.
No historical analysis was rerun for this assessment. Only static local metadata
and public artifact/source listings were read.

Local findings:

- `.venv/pyvenv.cfg` records CPython 3.11.0 and home/executable path
  `C:\Users\geova\AppData\Local\Programs\Python\Python311\python.exe`.
  PowerShell Test-Path currently reports that path exists. The qualified Python
  reader received PermissionError/WinError 5 when attempting static inspection;
  no original binary hash/build/provenance was established. Existence is not
  original-artifact authentication, and no attempt to execute it was made.
- `.venv/Lib/site-packages` retains `pytest-9.1.1.dist-info` and
  `pyyaml-6.0.3.dist-info`, matching sealed version labels. Readable metadata pins:
  pytest METADATA SHA-256 `c5d032518012789cabc870d46589aca3aeda36cf9fa4399ee88bda3d10438451`;
  pytest RECORD `94909053bd0ac30df5b77002b7edb8b487ed342cffaaf79e0c9bacc9b2ee0c39`;
  PyYAML METADATA `847a701020334386852b6e07bad1053cb0ce3da9ee1846e7e9d02b24e8bb3f8d`;
  PyYAML RECORD `5502bf031eeaa2a389656b0c0a6175c8a01a766a9328f53600e59229a662c0a4`.
  Both INSTALLER files have SHA-256
  `ceebae7b8927a3227e5303cf5e0f1f7b34bb542ad7250ac03fbcde36ec2f1508`.
  These are observed installed metadata, not authenticated original wheel hashes
  or proof that every installed payload matches the original run.
- A bounded filename inspection of Downloads found no matching original
  interpreter installer/PyYAML/pytest archives. This is not an exhaustive claim
  that no archival artifact exists anywhere. No caches were purged or modified.

Public availability checked read-only: the [official Python 3.11.0 release page](https://www.python.org/downloads/release/python-3110/)
lists a Windows 64-bit installer. This establishes a public listing, not that
it is the original installed binary or matches the recorded build.
[PyYAML 6.0.3](https://pypi.org/project/PyYAML/6.0.3/) and
[pytest 9.1.1](https://pypi.org/project/pytest/9.1.1/) have package-index pages.
No package archive was retrieved or authenticated. Missing original artifact
hashes, trust/custody evidence, build environment and dependency closure remain
unresolved. No newer patch version was substituted.

The [CPython v3.11.0 random module source](https://raw.githubusercontent.com/python/cpython/v3.11.0/Modules/_randommodule.c)
was inspected as text for seed/word semantics. The independent bounded verifier
specifies positive integer seeding as little-endian 32-bit limbs, array-based
initialization, high-bit extraction for short words and little-endian multiword
assembly. It never imports random.Random. Source inspection plus bounded current-
runtime comparison does not qualify the original executable or all historical
outputs. No original source/runtime qualification pass is claimed.

### Exact comparison specification (future separately approved execution)

Identity `hashlab-e001-numerical-exact-comparison-spec-v1`. Inputs must pin the
accepted sealed manifest, original source/runtime/dependency artifacts, original
analysis bytes and independently captured recomputation bytes. Output is outside
E001. This specification is documentation only; no reproduction runner is added.

1. Verify all original hashes/sizes/inventory before comparison. Preserve each
   raw JSON file and numeric token sequence. Reject duplicate keys/nonfinite
   numbers/missing fields; retain original array ordering and timestamps.
2. Match secondary records for diagnostic comparison by the exact unique tuple
   (generator,phase,test); detect duplicate/missing tuples. Preserve each side's
   original array index in the report; matching by tuple does not normalize a
   full-file or array-order identity claim into equality.
3. For every field, including all 86 ledger entries, report original/recomputed
   JSON tokens, exact parsed values and type. For floats also report hexadecimal
   float representation and IEEE-754 binary64 bits encoded as 16 BE hex digits.
   Signed zero and differing bit patterns remain discrepancies. Compare raw
   tokens, binary value and rendered bytes as separately named identity checks.
   No epsilon, ULP tolerance, rounding or substitution can grant a pass.
4. Compare all remaining secondary, primary/count/decision/provenance fields,
   not only the known 86. Retain new discrepancies. Compare full array order,
   complete serialized bytes and analysis timestamp independently; no removal of
   timestamp or sorting is permitted for a full-byte identity claim.
5. Report schema `hashlab-e001-numerical-exact-report-v1` with source/input/runtime
   pins, raw_output_sha256, original_order and recomputed_order, exact per-field
   observations (key, original_index, recomputed_index, field, original_token,
   recomputed_token, original_type, recomputed_type, original_bits/recomputed_bits
   where float), separate token/binary/order/timestamp/full_byte equality results,
   every mismatch and limitations. All reports are authenticated independently;
   no local boolean is G1 acceptance authority. No result is fabricated now.
6. If exact numerical identity fails, preserve all output and return for review.
   A matching narrower binary-value comparison cannot imply matching JSON tokens
   or complete-file identity. Changed timestamps/order are explicitly disclosed.
   Runtime/environment installation and this execution each require separate
   authorization after artifact provenance and comparison-code review.

Strict historical identity remains unresolved; the 86 accepted discrepancies
remain intact. No tolerance-based G1 pass, evidence edit, candidate hashing or
historical regeneration occurred. Stop for Architecture Review 039.
