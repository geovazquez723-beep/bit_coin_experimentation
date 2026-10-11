# Evidence-pipeline smoke test (NOT Experiment 001)

**Config:** [`configs/smoke-evidence.yaml`](../configs/smoke-evidence.yaml), experiment id `smoke-evidence`
**Output directory:** `results-smoke/` (git-ignored, separate from `results/`)

This test checks the plumbing only: an evidence directory is created and sealed, the manifest
verifies, the results, analysis and report are written, stored evidence can be re-analyzed, and
tampered or inconsistent evidence is refused. It uses 4 tiny generators (300 + 300 candidates
each), an easy target (2 leading zero bits), a different seed, and about 5,400 hashes in total.

**Its numbers have no scientific meaning.** Never report, pool or compare them with Experiment
001. A smoke run is easy to tell apart from Experiment 001:

| | Smoke test | Experiment 001 |
|---|---|---|
| Directory | `results-smoke\` | `results\` |
| Run id | `<UTC>-expsmoke-evidence-<hex>` | `<UTC>-exp001-<hex>` |
| Report header | `Experiment: **smoke-evidence** (SMOKE-TEST-evidence-pipeline-NOT-experiment-001)` | `Experiment: **001** (...)` |
| `analysis.json` | `"experiment": {"id": "smoke-evidence", ...}` | `"experiment": {"id": "001", ...}` |

## Commands (PowerShell, Director)

```powershell
cd C:\repo\hashlab
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"     # refreshes installed metadata to 0.2.0 (environment.json records it)

# 0. Start clean; record that results\ holds only .gitkeep
if (Test-Path results-smoke) { Remove-Item -Recurse -Force results-smoke }
Get-ChildItem -Force results

# 1. Validate and plan (dry runs, nothing written)
python -m hashlab.cli validate --config configs/smoke-evidence.yaml
python -m hashlab.cli plan --config configs/smoke-evidence.yaml

# 2. Run: creates and seals the evidence directory
python -m hashlab.cli run --config configs/smoke-evidence.yaml --results-dir results-smoke
$run = (Get-ChildItem results-smoke -Directory | Select-Object -First 1).Name
$dir = Join-Path results-smoke $run
$run                                   # expect ...-expsmoke-evidence-...

# 3. Evidence directory and manifest
Get-ChildItem $dir | Select-Object Name, Length, IsReadOnly
(Get-FileHash (Join-Path $dir manifest.json) -Algorithm SHA256).Hash.ToLower()
(Get-Content (Join-Path $dir manifest.sha256)).Split(' ')[0]          # must equal the line above
python -c "import json,sys; m=json.load(open(sys.argv[1])); print(m['schema'], m['run_id'], m['status']); print(sorted(m['files']))" (Join-Path $dir manifest.json)

# 4. Results and report
Get-Content (Join-Path $dir report.md) -TotalCount 30
python -c "import json,sys; a=json.load(open(sys.argv[1])); print(a['experiment']['id'], a['hashlab_version'], a['verdict']['status'], a['integrity'], a['verdict']['confirmatory_economic_claim'])" (Join-Path $dir analysis.json)

# 5. Re-analysis of stored evidence (writes only under <run>\analyses\<timestamp>\)
python -m hashlab.cli analyze --run-id $run --results-dir results-smoke
$LASTEXITCODE                          # expect 0
Get-ChildItem (Join-Path $dir analyses)
python -c "import sys; from pathlib import Path; from hashlab.evidence import verify_manifest; print(verify_manifest(Path(sys.argv[1])))" $dir   # expect []

# 6a. Integrity failure: a tampered COPY is refused (the original is not touched)
$bad = $run -replace '-[0-9a-f]{8}$', '-0badc0de'
Copy-Item -Recurse $dir (Join-Path results-smoke $bad)
$badResults = Join-Path results-smoke "$bad\results.json"
Set-ItemProperty $badResults -Name IsReadOnly -Value $false
(Get-Content $badResults -Raw).Replace('"complete"', '"completE"') | Set-Content $badResults -NoNewline -Encoding ascii
python -m hashlab.cli analyze --run-id $bad --results-dir results-smoke
$LASTEXITCODE                          # expect 3 (hash mismatch for results.json)
python -c "import sys; from pathlib import Path; from hashlab.evidence import verify_manifest; print(verify_manifest(Path(sys.argv[1])))" $dir   # original: expect []

# 6b. Analysis-level integrity failure: inconsistent counts, in memory only (nothing is written)
@'
import json, sys
from pathlib import Path
from hashlab.experiments.analysis import analyze_results
run = Path(sys.argv[1])
results = json.loads((run / "results.json").read_text(encoding="utf-8"))
resolved = json.loads((run / "config.resolved.json").read_text(encoding="utf-8"))
results["generators"]["smoke-seq"]["phases"]["discovery"]["successes"] += 1
analysis = analyze_results(results, resolved)
print(analysis["verdict"]["status"], analysis["verdict"]["blocking"])
for problem in analysis["integrity"]["problems"]:
    print(" -", problem)
'@ | python - $dir

# 7. Separation from Experiment 001
Get-ChildItem -Force results           # still only .gitkeep
git status --short --ignored results-smoke

# 8. Clean up when done (evidence files are read-only, hence -Force)
Remove-Item -Recurse -Force results-smoke
```

## Expected observations

| Step | Expected |
|---|---|
| 1 | `validate`: all self-checks `OK`, config valid (4 generators). `plan`: no errors; warnings about duplicate draws for `smoke-uniform`, differing domains, and identical domains not meaning independent samples |
| 2 | prints `run_id`, the evidence path and a verdict; exit code 0 |
| 3 | 11 files (`config.source.yaml`, `config.resolved.json`, `plan.json`, `environment.json`, `seeds.json`, `batches.jsonl`, `results.json`, `analysis.json`, `report.md`, `manifest.json`, `manifest.sha256`), all read-only; the two hashes match; schema `hashlab-manifest-v1`, status `complete` |
| 4 | experiment `smoke-evidence`, version `0.2.0`, integrity `passed: True`, `confirmatory_economic_claim: False`. The verdict itself is meaningless here |
| 5 | `[ OK ] evidence integrity verified`, one timestamped folder under `analyses\`, `verify_manifest` returns `[]` |
| 6a | `evidence integrity check FAILED: hash mismatch for results.json`, exit code 3; the original still verifies |
| 6b | `integrity-failure True`, with a problem saying the successes disagree with the leading-zero histogram |
| 7 | `results\` unchanged; `results-smoke/` shown as ignored (`!!`) |

The positive control (planted 2x lift, 3,000 candidates) should be detected. The null control
`smoke-rand` can be flagged by chance (probability at most 1%); that appears as a non-blocking
warning and is not a smoke-test failure.
