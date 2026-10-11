# HASHLAB Research Charter

## Purpose

HASHLAB studies whether the *structure* of candidate inputs to SHA-256 has any
measurable effect on proof-of-work outcomes. The question is whether a
strategy for choosing which inputs to try can make "digest below target" more
likely per hash than chance predicts.

## Default position: the cryptographic null hypothesis

For distinct inputs, SHA-256 outputs behave like uniformly distributed
pseudorandom 256-bit values. So the probability that any distinct candidate
succeeds against a target T is p0 = T / 2^256, whatever its structure.

This is a well-supported working model. It is **not** a mathematical theorem,
and HASHLAB does not claim it is one. Equally, HASHLAB does not claim any
deviation from it unless the evidence clears every bar in
[methodology.md](methodology.md). We expect every result to be consistent with
the null. The value of the lab is a rigorous, reproducible record of how
closely that holds and of the sensitivity at which we checked it.

## Governance

| Role | Holder | Responsibility |
|---|---|---|
| Director | Human operator | Approves all execution and research decisions; runs every experiment and benchmark locally |
| Architect | ChatGPT | Scientific methodology and acceptance criteria |
| Engineer | Claude Code | Implementation, static validation and documentation; never runs experiments |

## Principles

1. **Pre-registration.** Hypotheses, metrics, sample sizes, alpha, the
   correction method and decision rules are fixed in the config and in
   `plan.json` *before* any hashing. The plan fingerprint is stored with each
   run.
2. **Reproducibility.** Every run writes a uniquely identified evidence
   directory that is never reused. It holds the exact config, the resolved
   config, seeds, the Git revision, the software and machine environment, raw
   counters and the analysis, all sealed with a SHA-256 manifest.
3. **Separation of theory and measurement.** Reports keep theoretical
   expectations apart from empirical measurements.
4. **Controls.** Every run includes a null control (a generator expected to
   behave like the null) and a positive control (a planted effect of known size
   that must be detected).
5. **Replication before belief.** A discovery-phase signal means nothing until
   it replicates on a disjoint validation set. Even a replicated signal is only
   a *candidate anomaly* until reproduced independently (new seeds, another
   machine, code review).
6. **Economic relevance.** Effects that are statistically significant but
   useless for search (fewer successes, or a lift eaten up by slower candidate
   generation) are labeled non-actionable.
7. **No overreach.** No result in HASHLAB is reported as a "weakness of
   SHA-256". The strongest available label is
   `candidate-anomaly-requires-independent-replication`.

## Scope

In scope: SHA-256 and double SHA-256 over self-generated candidate inputs,
proof-of-work success at configurable targets, and digest-distribution
diagnostics.

Out of scope: real Bitcoin block-header mining, mining pools, wallets, cloud
execution, paid APIs, GPU/ASIC optimization and machine learning.
