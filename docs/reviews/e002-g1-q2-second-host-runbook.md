# E002 G1 Q-2 — second-host execution runbook

Status: **Q-2 is OPEN.** No independent second machine has run this procedure. The 2026-10-16 same-host replays (including a replay from the committed artifacts under CPython 3.13.0) report `q2_qualifying: false` by design and are **not** second-host qualification.

**What must stay distinct.** Original evidence producer revision `de27c0ee42cdf7129093080195a1671381c7d1bb` (`required_commit`; the verifier must run on this checkout). Verifier revision recorded in manifest v2 `c5cc9b84c17434d0ff68ebb164a67f6ad9e5f91a` (its `src/e002_verify` tree `936253244c68083a39090d7892d4d2ac9ae8086a` equals the tree at the producer revision). The replay tool comes from the *current* `main`; it only orchestrates and never rebinds the evidence to `main`. Do not regenerate or alter the evidence, and do not change the source-binding format.

## 1. Machine requirements
An independent, privately controlled Windows machine (not this development host; a different physical or virtual machine, so its `MachineGuid` and node name differ — the tool refuses to report `q2_qualifying: true` otherwise), Python 3.12 or newer (stdlib only; no pip packages are needed — verified with CPython 3.13.0 on a clean interpreter), Git, ~1 GB RAM free, ~1 GB disk plus the 202 MB inputs.

## 2. Private transfer (do not use the public repository, a public Actions artifact or a public runner)
Copy by an approved private method (encrypted USB drive, private network share, or other channel you control) these three items. All are hash-checked by the tool before anything is verified; you can also pre-check with `Get-FileHash -Algorithm SHA256`.
1. `docs/reviews/e002-g1-external-host-data/q2-package-v2.zip` — 82,259 B, SHA-256 `03f425c94d16217f9ab627ea61e7b54f6b4304f61fbca125fb00c5fb4e693745` (this one is already public in the repository).
2. The retained **S1.4 audit directory** `results\e001-s14-audit-20261012-01` (202 MB; protected, not in git):

| file (under the directory) | bytes | SHA-256 |
|---|---|---|
| `producer/accounting.sqlite` | 37,801,984 | `14bc1c75950284a1d514568207e7bbccea86706b44b118f95e42fa861e0b9803` |
| `producer/complete.json` | 2,104 | `c4fe9ba89f1c4390c5300a7a5512aaf20f2bc6fcbbfcbe2292b1af564f70ddc1` |
| `producer/exclusions.bin` | 971,536 | `39d09046325a41dd36d1bc0390e15a1d35a64f649d20f144b9025ccda4395268` |
| `producer/occurrences.bin` | 133,000,000 | `dc27fca46c57a8c02aaa50584af1783e1f4e6dbfedb48231847415c509d9695f` |
| `producer/plan.json` | 3,464 | `19d6396493fc9b8aa9559fd8ddab65f219b920a13b447bb9fb00c04da782054b` |
| `producer/ranks.bin` | 485,768 | `124d6722591d81c9739e63d2702d67dcc3f889fb297a55fd52d7c7c800ee320a` |
| `verifier/reference.sqlite` | 37,789,696 | `e024010e7585a019487fc47c1afcbc22ae1d7c7c497f1fc7e6a9cbf25f31970c` |
| `verifier/verified.json` | 1,881 | `3ed80c4d663614fb5245902f88037573776889dc3c3afc47e32018add11d42eb` |

3. The **11 sealed E001 files** `results\20261011T205056Z-exp001-fc1d75fc` (653 KB; protected, not in git):

| file | bytes | SHA-256 |
|---|---|---|
| `analysis.json` | 81,503 | `5e22b2fc5d0ce4ed9dca71f0499c7b1b35f0f40a43d34228d8daad455d38b252` |
| `batches.jsonl` | 254,047 | `65ecf72decf20c9e9a8db29b1526c5dd39eeb2ecfc3d29166100d92e339fbad8` |
| `config.resolved.json` | 2,875 | `d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b` |
| `config.source.yaml` | 4,268 | `f2c0de21f3eba4b6a5fff41c8729b10d5c389e09334bd218f133d55a0140f225` |
| `environment.json` | 843 | `34e5e3c11015405dd540b2541f54086824b066aa83ed94c5fb80e2c13aa467f3` |
| `manifest.json` | 1,482 | `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b` |
| `manifest.sha256` | 80 | `e7200d11952f130786c183dcce2318e817b0f54802e47f4f2d9170499bab227a` |
| `plan.json` | 37,502 | `ea38ed0150fae79d140b44691ad64dbda223163296b98671966d1b07456f3f36` |
| `report.md` | 11,305 | `e253f9ab9c40410e8f601a107716fbabd090782c75efa4dd47afb17cd64fb428` |
| `results.json` | 242,708 | `1ff1e2a3dc51c2860d7e5e5d69b8941c62e000c2e06f0f03b3d39331ee15818c` |
| `seeds.json` | 1,158 | `b04fa14409ff07606e81757908109427e4309615afd702a564f346b19b32d931` |

## 3. Commands on the second machine (PowerShell)
```
git clone <repo-url> hashlab-tools                       # current main: provides tools\second_host_replay.py only
git clone --no-checkout <repo-url> hashlab-q2            # verifier checkout at the ORIGINAL producer revision
git -C hashlab-q2 config core.autocrlf false
git -C hashlab-q2 checkout de27c0ee42cdf7129093080195a1671381c7d1bb
git -C hashlab-q2 rev-parse HEAD                         # must print de27c0ee42cdf7129093080195a1671381c7d1bb
Expand-Archive q2-package-v2.zip -DestinationPath q2-package
python -VV
python -B hashlab-tools\tools\second_host_replay.py replay q2-package --repository hashlab-q2 `
    --audit <path>\e001-s14-audit-20261012-01 --e001-sealed <path>\20261011T205056Z-exp001-fc1d75fc `
    --out q2-report.json
echo $LASTEXITCODE
```
The run takes about 10 seconds after the 133 MB history file is read. Add `--observe-hashing` **only** if this machine uses the producer's exact runtime files (`python.exe` `b847bb9f…09de8`, `python312.dll` `2b6fffde…49b1`, `libcrypto-3-x64.dll` `57df468e…7e8a`); with any other build that option fails closed on purpose. Different native runtime artifacts are expected: they are recorded in the report, not forced equal.

## 4. Acceptance (all required)
`$LASTEXITCODE` is `0`; `q2-report.json` has `q2_qualifying: true`, `matches_expected: true`, `package_problems: []`, `differences: []`, no `verifier_rejection`, `source_alignment.counts.no-match: 0`, and `result.independence.candidate_sha256.backend == "hacl"` with `known_answers: "passed"`. The report also records the replay host fingerprint (hashed), `python -VV`, executable hash and the sealed inputs; keep it with the loaded OS version (`winver`) and the SHA-256 of the three transferred items.
Exit code 1 = package/pin/inventory problem or verifier rejection (report it as a failure; never edit the evidence); exit code 2 = the machine has the same fingerprint as the producing host (not Q-2).
Then return `q2-report.json` for the Director's review; do not publish the protected inputs.

## 5. Source alignment (approved for this bounded evidence set)
The evidence binds raw working-tree bytes of 58 source files from the producing host (33 CRLF, 25 LF). The tool compares each file of the clean `de27c0e` checkout against the recorded size and SHA-256 and, in a scratch copy only, selects the LF or CRLF rendering **only if it matches the pin exactly**. Expected on this evidence: 25 as-checked-out, 33 CRLF, 0 no-match. Content is never altered; any non-match fails verification.
