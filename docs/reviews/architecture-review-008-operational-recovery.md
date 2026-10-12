# Architecture Review 008: operational recovery

Documentation only, prepared for Architect review. Scientific baseline a28c563 is unchanged.
No recovery commands below have been executed. Director approval is required before installation,
builds, dependency downloads or regression execution. Preserve the original .venv and sealed evidence.
No Experiment 002 implementation, qualification, execution, seed or round selection is authorized.

## Workload correction

Proposal 3.12 now refers to QA2 3.7.1: <=4,200 candidate/known-answer hashes plus small integrity
hashes, with zero candidate hashes for synthetic fixtures. The cap includes 2,048 execution hashes,
2,048 independent re-hashes and <=104 probes. Confirmatory totals remain 180,200,000 hashes and
240,200,000 blocks. Including the separate QA2 cap gives <=180,204,200 hashes. The <=240,208,400 block estimate
is conditional on all QA2 probes also being <=80 B; 3.7.1 does not fix vector lengths. Itemize actual
probe blocks separately if longer vectors are used. Independent verification and integrity hashing
are excluded.
Earlier mentions of replacing 90M are historical, not an additional current workload. Proposal 3.9,
3.12, addendum sections 7/8 and remediation sections 10/11 retain the approved reduced QA2 design.

## Independent verifier: proposed deterministic audit format

The baseline requires all recorded successes and a seeded 1% sample of other inputs. A seed alone
cannot reconstruct the audit without frozen ordering and sampling semantics. The following proposed
engineering format needs approval/reference vectors before freeze; it changes no scientific rule.

1. Validate manifest/external anchor, config, registry and seed provenance first. Each recorded
   success needs a unique arm, stage and evaluated-input ordinal; require in-range ordinals and
   aggregate-count agreement. Missing or ambiguous provenance makes verification INCOMPLETE.
2. Independently enumerate accepted evaluated inputs in frozen production order, ordinals 0..N-1,
   after exclusions/rejections. Raw PRNG draw indices are different. A2 uses cluster then nonce;
   equally explicit ordering is required for every other arm/control. Reconstruct bytes and overlap.
3. Within each arm/stage let M=N-s be the count not recorded as successes, ordered by ordinal.
   Select k=floor(M/100) distinct failure ranks uniformly without replacement. For M<100, k=0;
   still check all successes. Total rounding loss is less than the number of strata.
4. Proposed XOF input is ASCII text, no BOM/quotes/newline/spaces:
   "hashlab-exp002-audit-v1|<arm-id>|<stage-id>|<64-lowercase-hex-audit-seed>".
   Freeze canonical delimiter-free ASCII IDs and stage names. Use SHAKE256, consuming sequential
   8-byte unsigned big-endian words. Uniform draw in [0,b): reject words >=floor(2^64/b)*b, then
   take word mod b. Consume one continuous XOF stream per stratum, without restarting per draw.
5. Floyd sampling: start empty set T; for j=M-k..M-1 draw t uniformly in [0,j], insert j if t is
   already in T, otherwise t. Sort T. Map failure rank r to the unique non-success ordinal i with
   i-count(success ordinals <=i)=r. Save ranks/ordinals and their canonical digest outside evidence.
6. Audit-seed timing/source remains a freeze prerequisite: require an independent nondiscretionary,
   witnessed procedure bound to the already sealed manifest, with no retries or discretionary
   sample choice. This is separate from the confirmatory seed. No audit seed or round is selected
   here. Merely recording a seed does not establish unbiased selection.

Independent reference vectors must cover XOF consumption, rejection, repeated draws, M=0, M<100,
rounding and failure-rank mapping. No HASHLAB sampler, aggregation or inference code may implement
the independent verifier; separately pinned generic cryptographic libraries are permissible.

| Activity | Workload and assurance |
|---|---|
| Statistical verification | Recompute counts, exact tests, Holm order, CP/t hull, labels and controls; zero candidate hashes. Correct calculations do not establish correctness of all recorded outcomes. |
| Candidate reconstruction | Reconstruct success provenance and sampled inputs independently. Sequential samplers/exclusion streams may require nearly all 180.2M evaluated inputs plus rejected draws/exclusion enumeration. A2 supports direct cluster/nonce access. Unsampled candidates need no SHA-256 merely for generator replay. |
| Probabilistic hashing audit | Hash all s successes plus sum floor((N-s)/100) other inputs across strata. At illustrative s=704,000: about 1,794,960 sampled non-successes and 2,498,960 total re-hashes, about 3.33M blocks if successes are proportional by width; <=2 blocks/input for <=80 B inputs. XOF, file-integrity hashes, replay and I/O are additional. |
| Optional full audit | 180.2M candidate hashes, 240.2M blocks, separately Director-approved; excluded from mandatory audit cost. |

For d concealed wrong non-success outcomes in a stratum with genuinely independent uniform sample,
miss probability is choose(M-d,k)/choose(M,k), <=(1-k/M)^d for M>0. This assumes correct reconstruction
and seed provenance. SHAKE-based selection relies on a pseudorandom-stream assumption; the exact combinatorial bound
requires genuinely uniform sampling and is not an additional scientific error guarantee.
The sample does not prove absence of omitted successes. All recorded successes
being correct does not prove their set complete. No wall-time guarantee exists before measurements.

## Python target and approval prerequisites

Original .venv references missing CPython 3.11.0; its launcher exits 103 and py -0p reports no installed
Pythons. Project requirements: Python >=3.10, PyYAML >=6.0, pytest >=8.0, setuptools >=68, wheel.
Historical evidence used Python 3.11.0, PyYAML 6.0.3, pytest 9.1.1. Recovery is a new compatible
runtime, not identical historical reproduction.

As verified 2026-10-11, choose **CPython 3.11.17 Windows AMD64**, released 2026-10-01. It has
**no official Windows installer**; 3.11.9 was the last installer release. Use the official source build
below after approval, or obtain separate approval for a binary provider. Do not label 3.11.9 current.
Sources: [release/checksums](https://www.python.org/downloads/release/python-31117/),
[version-pinned Windows build instructions](https://raw.githubusercontent.com/python/cpython/v3.11.17/PCbuild/readme.txt),
[build script](https://raw.githubusercontent.com/python/cpython/v3.11.17/PCbuild/build.bat).

Before approval identify exact MSVC/Windows SDK, bootstrap Python/NuGet and external dependency
artifacts. PCbuild can download a latest bootstrap automatically; approve/record its exact version
and bytes rather than describing this as a locked toolchain. No implicit toolchain installation is
approved here. Retain the source-build directory permanently as the venv's base interpreter.

Proposed pins retain historical application/test versions and update build tools explicitly:
pip 25.1.1, setuptools 80.9.0, wheel 0.45.1, PyYAML 6.0.3, pytest 9.1.1, colorama 0.4.6,
iniconfig 2.3.1, packaging 26.3, pluggy 1.6.0, Pygments 2.21.0, HASHLAB 0.2.0 at reviewed commit.
[PyYAML](https://pypi.org/project/PyYAML/6.0.3/) and [pytest](https://pypi.org/project/pytest/9.1.1/)
advertise Python 3.11 compatibility. [setuptools](https://pypi.org/project/setuptools/80.9.0/) satisfies
>=68; [wheel](https://pypi.org/project/wheel/0.45.1/) and [pip](https://pypi.org/project/pip/25.1.1/)
are explicitly pinned. Actual compatibility remains conditional until downloads, imports, pip check
and regression tests pass. Missing/incompatible versions must fail; never silently upgrade.

## PowerShell recovery procedure — NOT EXECUTED

After Director approval, use a new session. Install the approved C++ toolchain first if absent and
record installer hash/component versions. Verify source release Sigstore/GPG provenance separately
before building. No activation, execution-policy/global-PATH change, overwrite or deletion is needed.
All new files go into a fresh LOCALAPPDATA directory. The repository and original .venv stay intact.

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'C:\repo\hashlab'
$recoveryRoot = Join-Path $env:LOCALAPPDATA 'HASHLAB\recovery-008'
if (Test-Path -LiteralPath $recoveryRoot) { throw 'Recovery directory exists; do not overwrite' }
New-Item -ItemType Directory -Path $recoveryRoot | Out-Null
Start-Transcript -Path (Join-Path $recoveryRoot 'recovery.log')
$sourceArchive = Join-Path $recoveryRoot 'Python-3.11.17.tar.xz'
Invoke-WebRequest 'https://www.python.org/ftp/python/3.11.17/Python-3.11.17.tar.xz' -OutFile $sourceArchive
$sourceDigest = 'bfb74ad39efae27cda510f134ab408e00f9992c56851cfc0b1cdb5646da11599'
if ((Get-FileHash -LiteralPath $sourceArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sourceDigest) {
    throw 'Source checksum mismatch'
}
# Independently verify release signature/provenance before proceeding.
& tar.exe -xf $sourceArchive -C $recoveryRoot
if ($LASTEXITCODE -ne 0) { throw 'Extraction failed' }
$pythonSource = Join-Path $recoveryRoot 'Python-3.11.17'
& (Join-Path $pythonSource 'PCbuild\build.bat') -p x64 -c Release
if ($LASTEXITCODE -ne 0) { throw 'CPython build failed' }
$basePython = Join-Path $pythonSource 'PCbuild\amd64\python.exe'
& $basePython -c 'import sys,struct,ssl,venv,ensurepip; print(sys.version); print(ssl.OPENSSL_VERSION); assert sys.version_info[:3] == (3,11,17); assert struct.calcsize("P") == 8'
if ($LASTEXITCODE -ne 0) { throw 'Runtime check failed' }
# Retain source, build logs, external artifact hashes, toolchain versions and binary inventory.
$venvDir = Join-Path $recoveryRoot 'venv'
& $basePython -m venv $venvDir
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
$recoveryPython = Join-Path $venvDir 'Scripts\python.exe'
function Invoke-RecoveryPython {
    param([string[]]$PythonArguments)
    & $recoveryPython @PythonArguments
    if ($LASTEXITCODE -ne 0) { throw "Python step failed: $PythonArguments" }
}
$reviewedCommit = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify revision' }
# Confirm this is the Architect-reviewed Review 008 documentation commit.
$reviewedCommit | Set-Content (Join-Path $recoveryRoot 'repository-commit.txt') -Encoding ASCII
$repoArchive = Join-Path $recoveryRoot 'repository.zip'
& git archive --format=zip --output=$repoArchive $reviewedCommit
if ($LASTEXITCODE -ne 0) { throw 'Repository export failed' }
$testWorkspace = Join-Path $recoveryRoot 'repository'
Expand-Archive -LiteralPath $repoArchive -DestinationPath $testWorkspace
$pins = @('pip==25.1.1','setuptools==80.9.0','wheel==0.45.1','PyYAML==6.0.3',
    'pytest==9.1.1','colorama==0.4.6','iniconfig==2.3.1','packaging==26.3',
    'pluggy==1.6.0','Pygments==2.21.0')
$pins | Set-Content (Join-Path $recoveryRoot 'requirements-pinned.txt') -Encoding ASCII
$wheelhouse = Join-Path $recoveryRoot 'wheelhouse'
New-Item -ItemType Directory -Path $wheelhouse | Out-Null
Invoke-RecoveryPython -PythonArguments (@('-m','pip','download','--index-url','https://pypi.org/simple',
    '--only-binary=:all:','--no-deps','--dest',$wheelhouse) + $pins)
Get-ChildItem -LiteralPath $wheelhouse -File | Sort-Object Name | ForEach-Object {
    '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $_.Name
} | Set-Content (Join-Path $recoveryRoot 'wheels.sha256') -Encoding ASCII
# Independently compare wheel digests with official PyPI release metadata before installation.
# --no-deps prevents unpinned resolver additions; pip check must pass.
Invoke-RecoveryPython -PythonArguments (@('-m','pip','install','--no-index','--find-links',$wheelhouse,
    '--no-deps') + $pins)
Invoke-RecoveryPython -PythonArguments @('-m','pip','check')
$projectWheelDir = Join-Path $recoveryRoot 'project-wheel'
Invoke-RecoveryPython -PythonArguments @('-m','pip','wheel','--no-index','--no-build-isolation',
    '--no-deps','--wheel-dir',$projectWheelDir,$testWorkspace)
$projectWheels = @(Get-ChildItem -LiteralPath $projectWheelDir -Filter '*.whl' -File)
if ($projectWheels.Count -ne 1) { throw 'Expected one project wheel' }
Invoke-RecoveryPython -PythonArguments @('-m','pip','install','--no-index','--no-deps',$projectWheels[0].FullName)
Get-FileHash -LiteralPath $projectWheels[0].FullName -Algorithm SHA256 |
    Format-List | Out-File (Join-Path $recoveryRoot 'project-wheel.sha256')
Invoke-RecoveryPython -PythonArguments @('-m','pip','check')
Invoke-RecoveryPython -PythonArguments @('-c',
    'import sys,ssl,yaml,pytest,hashlab; import importlib.metadata as m; assert sys.version_info[:3] == (3,11,17); assert m.version("hashlab") == "0.2.0"; assert m.version("PyYAML") == "6.0.3"; assert m.version("pytest") == "9.1.1"; print(sys.version); print(ssl.OPENSSL_VERSION); print(hashlab.__file__)')
& $recoveryPython -m pip freeze --all | Out-File (Join-Path $recoveryRoot 'installed-freeze.txt')
if ($LASTEXITCODE -ne 0) { throw 'Version recording failed' }
~~~

### Evidence integrity and full offline regressions

These checks hash evidence files only. Do not call analyze against original evidence, as it can write
an analyses directory. The complete existing tests/ suite uses tiny fixed fixtures, not Experiment 002.

~~~powershell
$sealedDir = 'C:\repo\hashlab\results\20261011T205056Z-exp001-fc1d75fc'
$expectedManifest = '546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b'
function Get-SealedSnapshot {
    $manifestPath = Join-Path $sealedDir 'manifest.json'
    if ((Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedManifest) {
        throw 'Pinned manifest mismatch'
    }
    $selfDigest = [IO.File]::ReadAllText((Join-Path $sealedDir 'manifest.sha256')).Trim()
    if ($selfDigest -ne "$expectedManifest  manifest.json") { throw 'Self-digest mismatch' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $names = @($manifest.files.PSObject.Properties.Name) + @('manifest.json','manifest.sha256')
    $entries = @(Get-ChildItem -LiteralPath $sealedDir -Force)
    if ($entries.Count -ne 11 -or $names.Count -ne 11) { throw 'Wrong inventory size' }
    if (@($entries | Where-Object { $_.PSIsContainer -or $_.Name -notin $names -or ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }).Count) {
        throw 'Unexpected file/directory/reparse point'
    }
    foreach ($entry in $manifest.files.PSObject.Properties) {
        $payload = Join-Path $sealedDir $entry.Name
        if ((Get-Item -LiteralPath $payload).Length -ne $entry.Value.bytes -or
            (Get-FileHash -LiteralPath $payload -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value.sha256) {
            throw "Payload integrity failure: $($entry.Name)"
        }
    }
    $entries | Sort-Object Name | ForEach-Object {
        '{0}  {1}' -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $_.Name
    }
}
$before = @(Get-SealedSnapshot)
$before | Set-Content (Join-Path $recoveryRoot 'evidence-before.sha256') -Encoding ASCII
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
try {
    Set-Location -LiteralPath $testWorkspace
    Invoke-RecoveryPython -PythonArguments @('-m','pytest','tests','-ra','-p','no:cacheprovider',
        '--basetemp',(Join-Path $recoveryRoot 'pytest-temp'),
        '--junitxml',(Join-Path $recoveryRoot 'pytest-results.xml'))
} finally {
    $after = @(Get-SealedSnapshot)
    $after | Set-Content (Join-Path $recoveryRoot 'evidence-after.sha256') -Encoding ASCII
    if (@(Compare-Object $before $after -CaseSensitive).Count) { throw 'Sealed evidence changed' }
    Stop-Transcript
}
~~~

Acceptance: all collected tests pass; no unexpected skips/deselections/xfails, no broken requirements,
imports/version/x64 checks pass, all 11 evidence files match pinned manifest and before/after snapshots.
Record test counts, exit status, full transcript/JUnit, source commit, Python/OpenSSL/toolchain versions,
source/wheel/binary hashes and installed freeze. Tiny runner/CLI fixture execution is not QA2 qualification.
Retain failures; diagnose before retrying. Use a fresh approved directory for any retry, never overwrite.

## Verification status and blockers

- PASS: documentation arithmetic 90M+60M+0.2M+30M=180.2M and 90M+120M+0.2M+30M=240.2M;
  QA2 workload/cross-references reviewed without changing science.
- PASS: local Experiment 001 eleven-file inventory, nine payload sizes/digests, pinned manifest and
  self-digest verified; unchanged across the documentation pass. No archival transfer.
- NOT RUN: Python regressions (missing original interpreter). PowerShell parse checks and Node
  arithmetic are not pytest results. No environment installation or qualification performed.
- BLOCKED: Director approval, source-build/toolchain/bootstrap/external provenance; actual package
  compatibility and full regression results.
- CONDITIONAL: audit-format/seed-provenance approval, independent verifier ownership/implementation
  and reference vectors; live quicknet/client/witness verification; off-machine archival custodians,
  destinations/retention, receipts and restoration tests. No seed or round was selected.
