from __future__ import annotations

from pathlib import Path

import pytest

from hashlab.experiments.baseline import build_plan, describe_plan
from hashlab.experiments.config import ConfigError, load_config_file, resolve_config

BASELINE = Path(__file__).resolve().parents[1] / "configs" / "baseline.yaml"


def test_baseline_config_is_valid_and_feasible() -> None:
    pytest.importorskip("yaml")
    _, raw = load_config_file(BASELINE)
    resolved = resolve_config(raw)
    plan = build_plan(resolved)  # planning only: no hashing
    assert plan["errors"] == []
    types = {g["type"] for g in resolved["generators"]}
    assert types == {"sequential", "uniform", "patterned", "structured", "random_bytes"}
    assert resolved["controls"]["null_control_generator"] in {g["id"] for g in resolved["generators"]}


def test_defaults_are_applied(tiny_config) -> None:
    resolved = resolve_config(tiny_config)
    assert resolved["statistics"]["correction"] == "holm"
    assert resolved["execution"]["dedup"] == "auto"


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda c: c.update(extra=1), "unknown top-level key"),
        (lambda c: c["statistics"].update(alhpa=0.05), "unknown key 'alhpa'"),
        (lambda c: c.update(engine="md5"), "engine"),
        (lambda c: c.update(target={"leading_zero_bits": 4, "target_hex": "ff"}), "target"),
        (lambda c: c["phases"].pop("validation"), "phases"),
        (lambda c: c["statistics"].update(alpha=1.5), "statistics.alpha"),
        (lambda c: c["statistics"].update(correction="fdr"), "correction"),
        (lambda c: c["execution"].update(batch_size=10**7), "batch_size"),
        (lambda c: c["generators"].append(dict(c["generators"][0])), "duplicate id"),
        (lambda c: c["generators"].append({"id": "p", "type": "patterned", "width": 3, "max_period": 2}), "width"),
        (lambda c: c["controls"].update(null_control_generator="ghost"), "null_control_generator"),
        (lambda c: c.update(seeds={}), "seeds"),
        (lambda c: c.update(schema_version=2), "schema_version"),
        (lambda c: c.update(economics={"reference_generator": "ghost"}), "economics.reference_generator"),
        (lambda c: c.update(economics={"refrence_generator": "seq"}), "unknown key 'refrence_generator'"),
    ],
)
def test_invalid_configs_are_rejected(tiny_config, mutate, message) -> None:
    mutate(tiny_config)
    with pytest.raises(ConfigError) as excinfo:
        resolve_config(tiny_config)
    assert message in str(excinfo.value)


def test_positive_control_lift_must_fit_target(tiny_config) -> None:
    tiny_config["target"] = {"leading_zero_bits": 1}  # p0 = 1/2, so lift 1.0 would need q = 1 (allowed)
    resolve_config(tiny_config)
    tiny_config["controls"]["positive_control"]["relative_lift"] = 1.5
    with pytest.raises(ConfigError):
        resolve_config(tiny_config)


def test_economic_reference_defaults_to_none(tiny_config) -> None:
    resolved = resolve_config(tiny_config)
    assert resolved["economics"] == {"reference_generator": None}
    plan = build_plan(resolved)
    assert plan["economics"]["reference_generator"] is None
    assert any("no economic reference is predeclared" in w for w in plan["warnings"])


def test_baseline_predeclares_the_sequential_byte_reference() -> None:
    pytest.importorskip("yaml")
    _, raw = load_config_file(BASELINE)
    plan = build_plan(resolve_config(raw))
    assert plan["economics"]["reference_generator"] == "seq-be-w8"
    status = {gid: row["status"] for gid, row in plan["economics"]["comparability"].items()}
    assert status == {
        "seq-be-w8": "reference",
        "uniform-be-w8": "comparable",
        "struct-gray-w8": "comparable",
        "struct-stride-w8": "comparable",
        "struct-bitrev-w8": "comparable",
        "random-bytes-w8": "comparable",
        "seq-dec-w16": "not-comparable",
        "uniform-dec-w16": "not-comparable",
        "pattern-bytes-w8": "not-comparable",  # subset of the 8-byte space (different cardinality)
        "pattern-chars-w16": "not-comparable",
    }
    assert plan["economics"]["comparability"]["pattern-bytes-w8"]["domain_differences"] == ["cardinality"]


def test_baseline_primary_design_is_unchanged_by_remediation() -> None:
    """Architecture Review 001 remediation must not touch hypotheses, target, sample sizes or alpha."""
    pytest.importorskip("yaml")
    _, raw = load_config_file(BASELINE)
    resolved = resolve_config(raw)
    assert resolved["engine"] == "sha256"
    assert resolved["target"]["equivalent_leading_zero_bits"] == 8
    assert resolved["seeds"] == {"master": 20261011}
    assert resolved["phases"] == {
        "discovery": {"candidates_per_generator": 500_000},
        "validation": {"candidates_per_generator": 500_000},
    }
    assert resolved["statistics"] == {
        "alpha": 0.01,
        "confidence_level": 0.99,
        "correction": "holm",
        "power": 0.8,
        "min_actionable_relative_effect": 0.01,
    }
    assert len(resolved["generators"]) == 10
    assert resolved["controls"]["null_control_generator"] == "random-bytes-w8"
    assert resolved["controls"]["positive_control"] == {
        "enabled": True, "width": 8, "candidates": 200_000, "relative_lift": 0.25,
    }


def test_baseline_plan_documents_sensitivity_assumptions() -> None:
    pytest.importorskip("yaml")
    _, raw = load_config_file(BASELINE)
    plan = build_plan(resolve_config(raw))  # planning only: no hashing
    sens = plan["sensitivity"]
    assert sens["assumptions"]["tests"] == 10
    assert sens["assumptions"]["alpha_per_test"] == pytest.approx(0.001)
    assert sens["assumptions"]["n_discovery"] == 500_000
    assert sens["discovery_mde_pooled"] == pytest.approx(0.09331703955144872, rel=1e-9)  # the documented ~9.3%
    assert sens["discovery_mde_increase_unpooled"] == pytest.approx(0.09418832275217044, rel=1e-8)
    assert sens["discovery_mde_decrease_unpooled"] == pytest.approx(0.09242073505393443, rel=1e-8)
    replication = sens["replication_power_at_discovery_increase_mde"]
    assert 0.5 < replication["all_generators_flagged"] < replication["one_generator_flagged"] < 1.0
    power = plan["generators"][0]["power"]["discovery"]
    assert power["min_detectable_relative_effect"] == pytest.approx(sens["discovery_mde_pooled"])
    assert "not an exclusion bound" in power["interpretation"]
    assert "not an exclusion bound" in describe_plan(plan)


SMOKE = Path(__file__).resolve().parents[1] / "configs" / "smoke-evidence.yaml"


def test_smoke_config_is_valid_feasible_and_distinct_from_experiment_001() -> None:
    pytest.importorskip("yaml")
    _, raw = load_config_file(SMOKE)
    resolved = resolve_config(raw)
    plan = build_plan(resolved)  # planning only: no hashing
    assert plan["errors"] == []
    _, baseline_raw = load_config_file(BASELINE)
    baseline = resolve_config(baseline_raw)
    assert resolved["experiment"]["id"] == "smoke-evidence" != baseline["experiment"]["id"]
    assert "NOT-experiment-001" in resolved["experiment"]["name"]
    assert resolved["seeds"] != baseline["seeds"]
    assert resolved["controls"]["null_control_generator"] is not None
    assert resolved["controls"]["positive_control"]["enabled"] is True
    assert plan["total_hashes_planned"] <= 10_000  # tiny: a smoke test, not a workload


def test_package_version_is_consistent() -> None:
    import re
    from importlib import metadata

    from hashlab import __version__

    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert declared is not None and declared.group(1) == __version__ == "0.2.0"
    try:
        installed = metadata.version("hashlab")
    except metadata.PackageNotFoundError:
        return  # running from source without installation
    assert installed == __version__, "reinstall with: python -m pip install -e .[dev]"
