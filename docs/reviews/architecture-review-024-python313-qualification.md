# Architecture Review 024: Python 3.13 qualification

Date: 2026-10-11 (America/Los_Angeles). Scope: development environment qualification only.
Disposition: regression checks pass; awaiting Architect review. No E1 implementation authorized or started.

## Interpreter and environment

- Base: `C:\Program Files\Python313\python.exe`; `--version` returned `Python 3.13.0`, exit 0 in the normal sandbox.
- New isolated environment: `C:\repo\hashlab\.venv-py313-review024`.
- Created with the base interpreter's `-m venv`; creation and the new interpreter's `--version` both exited 0 in the normal sandbox.
- Exact runtime: `3.13.0 (tags/v3.13.0:60403a5, Oct 7 2024, 09:38:07) [MSC v.1941 64 bit (AMD64)]`.
- Host reported `Windows-11-10.0.26200-SP0`; runtime OpenSSL: `OpenSSL 3.0.15 3 Sep 2024`.
- Existing `.venv` and `.venv313` were retained without modification. Both configurations reference Python 3.11.0.

## Dependencies and installation

`pyproject.toml` specifies Python >=3.10, PyYAML >=6.0, development pytest >=8.0,
and build requirements setuptools >=68 and wheel. No dependency lockfile was found.
Existing environment metadata reported PyYAML 6.0.3, pytest 9.1.1, colorama 0.4.6,
iniconfig 2.3.1, packaging 26.3, pluggy 1.6.0, Pygments 2.21.0, HASHLAB 0.2.0,
and setuptools 65.5.0; pip was 22.3 in `.venv` and 26.2.1 in `.venv313`.
These were metadata observations, not execution results from the old environments.

New environment versions:

| Package | Version |
|---|---|
| HASHLAB (editable) | 0.2.0 |
| PyYAML | 6.0.3 |
| pytest | 9.1.1 |
| colorama | 0.4.6 |
| iniconfig | 2.3.1 |
| packaging | 26.3 |
| pluggy | 1.6.0 |
| Pygments | 2.21.0 |
| pip | 26.2.1 |
| setuptools | 80.9.0 |
| wheel | 0.45.1 |

Application and test versions were retained; build tooling satisfies the declared requirements.
The first dependency download attempt in the sandbox failed with `WinError 10013`:
`An attempt was made to access a socket in a way forbidden by its access permissions`.
The same pinned dependency installation succeeded with approved network escalation.
No permission changes were made. Subsequent installation and qualification ran in the normal sandbox.

Editable install command (exit 0), using the new environment's Python:

```powershell
python -m pip install --no-index --no-build-isolation -e '.[dev]'
```

## Regression qualification

- `python -m pip check`: exit 0, `No broken requirements found.`
- Complete offline suite: exit 0, **240 passed in 3.72s**, no failures or skips.
- Command: `python -m pytest tests -q -ra -p no:cacheprovider --basetemp .venv-py313-review024/pytest-temp --junitxml .venv-py313-review024/pytest-results.xml`.
- `PYTHONDONTWRITEBYTECODE=1` was set for tests. Test artifacts are inside the ignored new environment.
- Tests use tiny fixtures; no real experiment was launched.

## Evidence and repository preservation

Experiment 001 run `20261011T205056Z-exp001-fc1d75fc` passed read-only integrity checks:
all nine manifest payload SHA-256 digests and byte sizes match. Manifest SHA-256 matches
`manifest.sha256`: `546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b`.
All 11 evidence file names, sizes and last-write timestamps were unchanged across tests.
Only evidence-integrity hashing was performed; no experiment candidate hashing, seed generation,
beacon selection, re-analysis or scientific-protocol change was performed outside the offline tests.

The new environment is excluded through `.gitignore`; `git check-ignore` confirms this,
and `git ls-files .venv-py313-review024` returns no tracked files.
Starting branch was `docs/experiment-002-design`, with pre-existing untracked `.venv313/`.
Qualification changes are the one-line `.gitignore` addition and this review record;
the existing untracked environment remains. No files were deleted; no commit, push, merge or tag.

No remaining qualification blocker. Stop for Architect review.
