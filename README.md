# HASHLAB

A reproducible research harness for SHA-256 proof-of-work search. It tests
whether structurally different candidate-generation strategies show
statistically meaningful differences in SHA-256 output distributions or
proof-of-work success rates.

The working assumption is the **cryptographic null hypothesis**: for distinct
inputs, SHA-256 outputs behave like uniform pseudorandom values. No advantage
is claimed without strong, replicated, independent evidence. See
[docs/research-charter.md](docs/research-charter.md).

| Document | Contents |
|---|---|
| [docs/research-charter.md](docs/research-charter.md) | purpose, governance, principles, scope |
| [docs/methodology.md](docs/methodology.md) | definitions, null hypotheses, decision rules, controls |
| [docs/experiment-001.md](docs/experiment-001.md) | Experiment 001 specification |
| [configs/baseline.yaml](configs/baseline.yaml) | Experiment 001 configuration |

## Layout

```text
configs/baseline.yaml           Experiment 001 configuration (pre-registered)
src/hashlab/
  cli.py                        validate | plan | run | analyze
  candidates/                   base (domains, seeds), sequential, random (uniform + random_bytes),
                                patterned, structured
  hashing/                      sha256, sha256d, target (exact integer target arithmetic)
  experiments/                  config (strict validation), baseline (plan + run), analysis (decision rules
                                + report), controls (positive-control engine), selfcheck (validate)
  statistics/                   inference (exact binomial, Clopper-Pearson, chi-square, Holm),
                                distribution (streaming histograms, goodness of fit)
  evidence/                     manifest (environment, file hashes, verification), storage (write-once runs)
tests/                          pytest suite (tiny fixtures only)
docs/                           charter, methodology, Experiment 001 spec
results/                        evidence directories, one per run
```

## Windows PowerShell: setup

```powershell
cd C:\repo\hashlab

# Optional but recommended: put the code under version control BEFORE running,
# so every run records an exact Git revision (otherwise environment.json says git is unavailable).
git init
git add -A
git status            # review, then commit yourself when satisfied

# Virtual environment (Python 3.10+; 3.11 is installed on this machine)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked by execution policy, for this window only:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"    # installs PyYAML and pytest
```

## Review, validate and test (no experiment is run)

```powershell
# 1. Built-in self-checks: hash test vectors, target math, statistical reference values
python -m hashlab.cli validate

# 2. Same, plus strict validation of the experiment config
python -m hashlab.cli validate --config configs/baseline.yaml

# 3. Unit tests (tiny fixtures; a few seconds)
python -m pytest

# 4. Pre-registered plan: hypotheses, domains, sample sizes, power, warnings (dry run, writes nothing)
python -m hashlab.cli plan --config configs/baseline.yaml
python -m hashlab.cli plan --config configs/baseline.yaml --json > plan-preview.json
```

## Execute Experiment 001 (Director only)

```powershell
# Runs about 10.2 million SHA-256 evaluations in pure Python. Not benchmarked yet: expect
# minutes, not hours, on a modern CPU. Peak memory is dominated by the exact dedup set
# (about 1M entries, roughly 100 MB). Ctrl+C seals a partial run marked "aborted".
python -m hashlab.cli run --config configs/baseline.yaml

# The command prints run_id, the evidence path and the verdict. List runs:
Get-ChildItem results -Directory

# Verify evidence integrity and re-analyze (writes results\<run_id>\analyses\<timestamp>\):
python -m hashlab.cli analyze --run-id <run_id>

# Read the report:
Get-Content results\<run_id>\report.md
```

Exit codes: `0` ok, `1` self-check failure, `2` config or plan error, `3`
evidence integrity failure, `130` interrupted.

## Evidence directory

`results/<UTC timestamp>-exp<id>-<random hex>/` is created exclusively (never
reused). Every file is made read-only after the run and listed with its
SHA-256 in `manifest.json`. `manifest.sha256` holds the hash of the manifest
itself.

| File | Contents |
|---|---|
| `config.source.yaml` | exact bytes of the config used |
| `config.resolved.json` | the config with defaults applied |
| `plan.json` | pre-registered plan and fingerprint |
| `environment.json` | Git revision and dirty flag, Python, OpenSSL, package versions, OS, CPU (no hostname or user name) |
| `seeds.json` | master seed, derivation rule, every sub-seed |
| `batches.jsonl` | streamed per-batch counters and timings |
| `successes.jsonl` | only if `record_successes: true` (capped) |
| `results.json` | final counters and histograms |
| `analysis.json`, `report.md` | statistical analysis and readable report |

## Assumptions

1. Python's `hashlib.sha256` (OpenSSL-backed) is a correct SHA-256 reference.
   This is checked against FIPS 180-2 vectors.
2. Digests are compared as **big-endian** integers for both engines. Bitcoin's
   byte-reversed little-endian convention is deliberately not used, because
   real block-header mining is out of scope.
3. `random.Random` (MT19937) is adequate for *sampling* the uniform
   generator. It is not used for anything security-related.
4. The keyed BLAKE2b counter stream is a reasonable "random-looking" null
   control that is algorithmically unrelated to SHA-256.
5. Exact deduplication in memory is affordable at the baseline scale. The
   plan refuses to run configs that exceed `max_tracked_candidates`.

## Limitations

- Generators use different domains (width, bytes vs ASCII), so each is
  compared only with the theoretical `p0`. Comparisons between generators
  would compare different sample spaces.
- There is no deduplication across generators. Generators may share some
  inputs.
- The secondary distribution tests reuse the primary digests, so they are not
  independent evidence.
- The baseline is sensitive to effects of about 9% relative or larger. It is
  silent about smaller effects.
- Throughput is measured in pure Python on one machine. It is relevant only to
  the actionability rule within a run, not to real mining economics.
- Manifest verification catches accidental changes, not deliberate tampering
  by someone who rewrites the manifest too.
- The patterned generators enumerate in lexicographic order, so a run samples
  the start of their domains, not a random subset.
- Statistics are implemented in pure Python, without SciPy. They are
  unit-tested against closed forms and published reference values, but
  extreme tails (p < about 1e-300) underflow to 0.
- The Engineer ran no experiment, benchmark or pytest session. The Engineer
  only compiled the sources and ran `validate`/`plan` and the reference
  arithmetic.

## Open architectural questions for the Architect and Director

1. **Evidence commitment:** should evidence directories be committed to Git,
   archived elsewhere, or have their manifest digests signed or timestamped
   externally? Today `results/` is untracked except for `.gitkeep`.
2. **Comparisons between generators:** should a later experiment add matched
   comparisons between generators that share a domain (for example
   `uniform-be-w8` vs `random-bytes-w8` vs `seq-be-w8`, all 8-byte), with
   two-sample tests?
3. **Two-sided binomial method:** keep the conservative doubled-tail p-value,
   or switch to the minimum-likelihood method?
4. **Secondary metrics:** add per-bit balance (256 positions) or serial
   correlation between consecutive digests? Both cost CPU per hash and need a
   correction design.
5. **Sample size:** what minimum detectable effect is the scientific target?
   Reaching 1% needs about 85× the baseline sample (about 870M hashes), which
   probably requires a compiled hashing path outside the current scope.
6. **Patterned sampling:** lexicographic prefix, or a seeded permutation of
   the motif space?
7. **`sha256d` run:** a separate Experiment 001b, or a second engine inside
   one pre-registered family (which changes the correction size)?
