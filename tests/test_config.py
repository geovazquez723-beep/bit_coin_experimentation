from __future__ import annotations

from pathlib import Path

import pytest

from hashlab.experiments.baseline import build_plan
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
