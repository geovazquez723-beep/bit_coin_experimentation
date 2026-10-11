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
| Intervals | Clopper–Pearson, 99% |
| Replication | one-sided exact test, same direction, Holm across flagged generators |
| Actionability | throughput-adjusted lower bound of the success-rate ratio ≥ 1.01 |
| Null control | `random-bytes-w8` |
| Positive control | 200,000 candidates, planted +25% lift; must be detected |
| Planned sensitivity | minimum detectable relative effect ≈ 9.3% per generator (power 0.8) |

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
- success rate with a Clopper–Pearson interval, and the rate ratio with its
  interval;
- exact p-value, Holm-adjusted p-value and classification;
- leading-zero-bit histogram and first/last-byte histograms (for the
  secondary tests);
- generation, dedup, hashing and wall time, and the derived throughputs.

## Expected outcome under the null

Every generator is classified `consistent-with-null`. The null control passes,
the positive control is detected, and about 1% of the secondary tests would be
flagged by chance *before* correction (around 0 after correction).

## Execution

The Director runs it. See the README for the PowerShell commands. Change
nothing in this file or the config after a run without recording an
amendment below.

## Amendments

_None yet._
