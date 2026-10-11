# HASHLAB changelog and analysis contract

Every `plan.json`, `analysis.json` and `environment.json` records `hashlab_version`. Read evidence with
the contract of the version that produced it.

## 0.2.0: methodology hardening before Experiment 001

Architecture Review 001 (Engineering Assignments 002 and 003). Details and reasons:
[reviews/architecture-review-001-remediation.md](reviews/architecture-review-001-remediation.md).
No evidence was produced with 0.1.0, so no stored result is affected.

**Unchanged:** the primary hypotheses (H1) and secondary family (H2), engine, target difficulty
(8 leading zero bits), seeds, sample allocations, alpha, confidence level, Holm correction, the
discovery and replication rules, and both controls.

### Analysis contract (`analysis.json`)

| Area | 0.1.0 | 0.2.0 |
|---|---|---|
| Run-level gates | `HARNESS ALARM` if the null control was flagged | `HARNESS INTEGRITY FAILURE` for missing or inconsistent evidence (blocking); a flagged null control is a non-blocking diagnostic |
| New top-level keys | none | `experiment`, `integrity`, `diagnostics`, `economics`, `classification_legend`, `label_note` |
| `verdict` | `summary`, `classifications`, `unreplicated_discovery_signals` | adds `status` (stable code), `blocking`, `warnings`, `exploratory_screen_passed`, `confirmatory_economic_claim` (always `false`), `economic_evidence_level` |
| `null_control` | `{generator, passed, rule}` or `null` | adds `status`, `statistically_flagged`, `p_value`, `p_value_adjusted`, `replicated`, `blocking`, `interpretation`; a dict whenever a null control is designated. `passed` keeps its meaning (not flagged in discovery) |
| Economic reference | fastest observed generator | predeclared `economics.reference_generator`, identical domains only |
| `actionability` | `throughput_ratio_vs_fastest`, `actionable` could be `true` | `throughput_ratio_vs_fastest` removed; adds `throughput_ratio_vs_reference`, simultaneous bounds, `screen_status`, `exploratory_screen_passed`, `marginal_bound_alone_would_pass`, `evidence_level`, `confirmatory_status`; `actionable` is always `false`; lifts can be `null` |
| Strongest class | marginal bound × throughput vs fastest | simultaneous bound × throughput vs predeclared reference; exploratory only |
| Per generator | | adds `economics`, `classification_meaning` |
| Per phase `empirical` | unlabelled `rate_ci`, `rate_ratio_ci` | same values, plus `interval_type: marginal` and a `simultaneous` block |
| Per phase `throughput` | raw rates and timings | same, plus `candidate_overhead_seconds`, `candidate_overhead_fraction_of_wall`, `expected_valid_per_second`, `observed_valid_per_second` |
| Verdict wording | "NOT actionable", "consistent ... at the planned sensitivity" | "did not pass the exploratory economic screen"; null runs state that equivalence is not established |
| Report | | experiment header line, "How to read the labels", "Harness integrity", "Diagnostics", "Economics (EXPLORATORY)", labelled interval columns |

Class strings are unchanged: `consistent-with-null`, `unreplicated-discovery-signal`,
`replicated-anomaly-non-actionable`, `candidate-anomaly-requires-independent-replication`.

### Plan contract (`plan.json`)

New keys `economics` (reference, selection rule, comparability table) and `sensitivity`
(assumptions, directional MDEs, replication power). `decision_rules` adds
`exploratory_economic_screen`, `classification_legend`, `economic_reference`, `intervals`,
`integrity` and `null_control_rule`; `actionable` now says it is never declared. Each `power`
entry adds directional MDEs, `power_target` and `interpretation`. New plan warnings: no economic
reference, domains not comparable with the reference, identical domains not meaning independent
samples. **Every plan fingerprint changes** (content and version).

### Configuration contract

Optional top-level `economics: {reference_generator: <generator id> | null}` (default `null`, which
disables the economic screen with a plan warning). Older configs remain valid. `schema_version`
stays `1`.

### Compatibility for readers

- Tools that read `throughput_ratio_vs_fastest` must switch to `throughput_ratio_vs_reference`.
- Tools that matched verdict text should use `verdict.status`.
- Analyzing 0.1.0-style resolved configs with 0.2.0 works; with no `economics` section, no generator
  can pass the economic screen.
- `python -m pip install -e .` must be re-run so the installed metadata (`environment.json`,
  `packages.hashlab`) also says 0.2.0; `tests/test_config.py::test_package_version_is_consistent`
  fails until then.

### Also added

- `configs/smoke-evidence.yaml` and [smoke-test.md](smoke-test.md): evidence-pipeline smoke test
  (experiment id `smoke-evidence`, output `results-smoke/`), never Experiment 001 evidence.
- `statistics.inference`: `normal_power`, `minimum_detectable_effect_unpooled`, `exact_binomial_power`.

## 0.1.0

Initial research foundation (commit `c72f6e5`, integrated at `50e6a9b`).
