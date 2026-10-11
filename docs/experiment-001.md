# Experiment 001: Candidate Structure vs Hash Success

**Status:** specified and implemented. **Not executed.** It waits for Director
approval.
**Config:** [`configs/baseline.yaml`](../configs/baseline.yaml)
**Implementation:** `src/hashlab/experiments/baseline.py`, `analysis.py`

## Question

Do structurally different candidate-generation strategies produce SHA-256
proof-of-work success rates, or digest distributions, that differ from the
uniform-random null?

## Fixed design (pre-registered)

| Item | Value |
|---|---|
| Engine | `sha256` (`sha256d` is available as a separate, later run) |
| Target | 8 leading zero bits: `T = 2^248`, `p0 = 1/256` |
| Master seed | `20261011` (sub-seeds derived by SHA-256; listed in `seeds.json`) |
| Discovery phase | 500,000 attempted candidates per generator |
| Validation phase | 500,000 attempted candidates per generator, disjoint from discovery |
| Primary test | exact two-sided binomial vs `p0`, Holm correction across 10 generators, alpha = 0.01 |
| Intervals | Clopper–Pearson, 99% **marginal** (descriptive), plus Bonferroni-**simultaneous** across the 10 generators (99.9% each) |
| Replication | one-sided exact test, same direction, Holm across flagged generators |
| Economic screen (exploratory) | predeclared reference `seq-be-w8`; identical domains only; simultaneous lower bound of the success-rate ratio × throughput ratio vs the reference ≥ 1.01. Never a confirmatory economic claim (amendment 1) |
| Null control | `random-bytes-w8`; a significant result is a non-blocking diagnostic, missing evidence is blocking (amendment 1) |
| Positive control | 200,000 candidates, planted +25% lift; must be detected |
| Planning sensitivity | 80%-power MDE ≈ 9.3% per generator for the discovery test (normal approximation, alpha' = 0.001 two-sided). A planning quantity, not an exclusion bound; see methodology section 8 |

## Generators and their domains

| id | type | domain kind | width (bytes) | domain size | construction |
|---|---|---|---:|---:|---|
| seq-be-w8 | sequential | bytes | 8 | 2^64 | integers 0,1,2,… as 8-byte big-endian |
| seq-dec-w16 | sequential | ascii-chars | 16 | 10^16 | zero-padded 16-digit decimal ASCII |
| uniform-be-w8 | uniform | bytes | 8 | 2^64 | MT19937 uniform integers, with replacement, then deduplicated |
| uniform-dec-w16 | uniform | ascii-chars | 16 | 10^16 | MT19937 uniform integers as decimal ASCII, then deduplicated |
| pattern-bytes-w8 | patterned | bytes | 8 | 16,842,496 | primitive byte motifs of period 1–3, repeated |
| pattern-chars-w16 | patterned | ascii-chars | 16 | 82,307,905 | primitive printable-ASCII motifs of period 1–4, repeated |
| struct-gray-w8 | structured | bytes | 8 | 2^64 | Gray code of the index |
| struct-stride-w8 | structured | bytes | 8 | 2^64 | `i × 0x9E3779B97F4A7C15 mod 2^64` |
| struct-bitrev-w8 | structured | bytes | 8 | 2^64 | bit reversal of the index |
| random-bytes-w8 | random_bytes | bytes | 8 | 2^64 | keyed BLAKE2b counter stream (null control) |

Generators use different domains (width 8 vs 16, bytes vs ASCII). **Each is
compared only with the theoretical `p0`, never with the others.** The plan
prints this limitation as a warning.

The patterned generators are enumerated in a fixed lexicographic order, so
their 1,000,000 candidates cover only the start of their domains (for
example, all of period 1–2 plus part of period 3). This is deliberate and
recorded.

## Metrics recorded

Per generator and phase:
- attempted, unique, within-phase duplicates, cross-phase duplicates;
- successes, with the theoretical expectation and standard deviation;
- success rate with a marginal Clopper–Pearson interval, and the rate ratio
  with its marginal and simultaneous intervals (each labelled);
- exact p-value, Holm-adjusted p-value and classification;
- leading-zero-bit histogram and first/last-byte histograms (for the
  secondary tests);
- generation, dedup, hashing and wall time; raw hashing throughput,
  candidate-generation overhead, end-to-end throughput, expected and observed
  valid hashes per second; and, for domains identical to `seq-be-w8`, the
  throughput ratio against that predeclared reference (exploratory).

Per run: harness-integrity problems (blocking) and non-blocking diagnostics,
both in `analysis.json` and `report.md`.

## Expected outcome under the null

Most likely every generator is classified `consistent-with-null`: Holm keeps
the chance of at least one false discovery flag (the null control included) at
or below 1%. The positive control is detected, and about 1% of the secondary
tests would be flagged by chance *before* correction (around 0 after
correction). A null outcome would not show that the generators are
equivalent; it only means no effect was detected at this sensitivity.

## Execution

The Director runs it. See the README for the PowerShell commands. Change
nothing in this file or the config after a run without recording an
amendment below.

## Amendments

### Amendment 1: Architecture Review 001 remediation (before any execution)

Recorded before Experiment 001 was run; no data had been collected. Details,
fingerprints and reasons are in
[docs/reviews/architecture-review-001-remediation.md](reviews/architecture-review-001-remediation.md).

- **Unchanged:** engine, target, seeds, sample allocations (500,000 + 500,000
  per generator, 200,000 positive-control candidates), the 10 generators,
  alpha, confidence level, Holm correction, the primary hypotheses H1 and the
  secondary family H2, and the discovery and replication rules.
- **Added to the config:** `economics.reference_generator: seq-be-w8`
  (predeclared economic reference). Config comments were reworded.
- **Changed decision rules:** the economic comparison uses the predeclared
  reference instead of the fastest observed generator, only for identical
  domains, and the Bonferroni-simultaneous lower bound instead of the marginal
  one. It is labelled exploratory and never declares a confirmatory
  advantage. A significant null control became a non-blocking diagnostic;
  missing or inconsistent evidence became a blocking integrity failure.
- **Documentation:** the MDE is described as a planning quantity, not an
  exclusion bound.
- Original plan fingerprint (commit `50e6a9b`):
  `c8dd07b28eb478da4e22e928e822760c45f35c610636440d138f565b6f36ca46`.
  The amended plan fingerprint is recorded in the remediation record.

### Amendment 2: final pre-experiment hardening, version 0.2.0 (before any execution)

- **Unchanged:** everything listed as unchanged in amendment 1. `configs/baseline.yaml` is byte-identical
  to amendment 1.
- Package version 0.2.0 (analysis contract in [CHANGELOG.md](CHANGELOG.md)).
- Labels clarified: a legend in every analysis and report, and
  `verdict.confirmatory_economic_claim: false`. No decision logic changed.
- Sample overlap documented (methodology section 5b): `seq-be-w8` and `struct-gray-w8` share 951,424 of
  their 1,000,000 candidates, so their primary results are not independent of each other.
- The plan fingerprint changed again (version string and plan text); the value is in the remediation
  record.
- A separate smoke-test config (`smoke-evidence`, output `results-smoke/`) was added. Smoke runs are
  never Experiment 001 evidence.
