"""Experiment configuration: loading, defaults and strict validation.

Unknown keys are errors, so a typo cannot silently change an experiment.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from hashlab.candidates import build_generator
from hashlab.hashing import ENGINES, Target

SCHEMA_VERSION = 1
PHASES = ("discovery", "validation")

DEFAULTS: dict = {
    "statistics": {
        "alpha": 0.01,
        "confidence_level": 0.99,
        "correction": "holm",
        "power": 0.8,
        "min_actionable_relative_effect": 0.01,
    },
    "execution": {
        "batch_size": 10_000,
        "max_tracked_candidates": 2_000_000,
        "record_successes": False,
        "max_recorded_successes": 10_000,
        "dedup": "auto",
        "progress_every_batches": 50,
    },
    "controls": {
        "null_control_generator": None,
        "positive_control": {"enabled": False, "width": 8, "candidates": 200_000, "relative_lift": 0.25},
    },
    # Predeclared economic reference (experiments/economics.py). None disables the economic screen.
    "economics": {
        "reference_generator": None,
    },
}

ALLOWED_TOP = {
    "schema_version", "experiment", "engine", "target", "seeds", "phases",
    "statistics", "execution", "controls", "generators", "economics",
}


class ConfigError(ValueError):
    """Raised with every validation problem found, one per line."""


def load_config_file(path: Path) -> tuple[bytes, dict]:
    """Read a YAML (or JSON) config file. Returns (exact source bytes, parsed mapping)."""
    source = Path(path).read_bytes()
    text = source.decode("utf-8")
    if Path(path).suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise ConfigError("PyYAML is required for YAML configs (pip install -e .)") from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")
    return source, data


def _merge(defaults: dict, given: dict, section: str, errors: list[str]) -> dict:
    merged = copy.deepcopy(defaults)
    for key, value in (given or {}).items():
        if key not in defaults:
            errors.append(f"{section}: unknown key {key!r}")
        elif isinstance(defaults[key], dict):
            if not isinstance(value, dict):
                errors.append(f"{section}.{key}: expected a mapping")
            else:
                merged[key] = _merge(defaults[key], value, f"{section}.{key}", errors)
        else:
            merged[key] = value
    return merged


def _positive_int(value: object, name: str, errors: list[str], minimum: int = 1) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        errors.append(f"{name}: expected an integer >= {minimum}")


def _probability(value: object, name: str, errors: list[str]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 < float(value) < 1.0:
        errors.append(f"{name}: expected a number strictly between 0 and 1")


def resolve_config(raw: dict) -> dict:
    """Validate a parsed config and return the resolved (defaults-applied) config."""
    errors: list[str] = []
    for key in raw:
        if key not in ALLOWED_TOP:
            errors.append(f"unknown top-level key {key!r}")

    if raw.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    experiment = raw.get("experiment")
    if not isinstance(experiment, dict) or not experiment.get("id") or not experiment.get("name"):
        errors.append("experiment: needs 'id' and 'name'")
        experiment = {"id": "invalid", "name": "invalid"}
    else:
        for key in experiment:
            if key not in {"id", "name", "description", "specification"}:
                errors.append(f"experiment: unknown key {key!r}")
        experiment = {k: str(v) for k, v in experiment.items()}

    engine = raw.get("engine")
    if engine not in ENGINES:
        errors.append(f"engine: must be one of {sorted(ENGINES)}")

    target_cfg = raw.get("target")
    try:
        target = Target.from_config(target_cfg if isinstance(target_cfg, dict) else {})
    except (ValueError, TypeError) as exc:
        errors.append(f"target: {exc}")
        target = None

    seeds = raw.get("seeds")
    if not isinstance(seeds, dict) or set(seeds) != {"master"}:
        errors.append("seeds: expected exactly {master: <non-negative integer>}")
        seeds = {"master": 0}
    else:
        _positive_int(seeds["master"], "seeds.master", errors, minimum=0)

    phases_raw = raw.get("phases")
    phases: dict = {}
    if not isinstance(phases_raw, dict) or set(phases_raw) != set(PHASES):
        errors.append(f"phases: expected exactly {list(PHASES)}")
    else:
        for name in PHASES:
            entry = phases_raw[name]
            if not isinstance(entry, dict) or set(entry) != {"candidates_per_generator"}:
                errors.append(f"phases.{name}: expected exactly {{candidates_per_generator: N}}")
                continue
            _positive_int(entry["candidates_per_generator"], f"phases.{name}.candidates_per_generator", errors)
            phases[name] = {"candidates_per_generator": entry["candidates_per_generator"]}

    statistics = _merge(DEFAULTS["statistics"], raw.get("statistics", {}), "statistics", errors)
    _probability(statistics["alpha"], "statistics.alpha", errors)
    _probability(statistics["confidence_level"], "statistics.confidence_level", errors)
    _probability(statistics["power"], "statistics.power", errors)
    if statistics["correction"] not in ("holm", "bonferroni"):
        errors.append("statistics.correction: must be 'holm' or 'bonferroni'")
    mare = statistics["min_actionable_relative_effect"]
    if not isinstance(mare, (int, float)) or isinstance(mare, bool) or mare <= 0:
        errors.append("statistics.min_actionable_relative_effect: expected a positive number")

    execution = _merge(DEFAULTS["execution"], raw.get("execution", {}), "execution", errors)
    _positive_int(execution["batch_size"], "execution.batch_size", errors)
    if isinstance(execution["batch_size"], int) and execution["batch_size"] > 1_000_000:
        errors.append("execution.batch_size: must be <= 1,000,000 (bounded memory)")
    _positive_int(execution["max_tracked_candidates"], "execution.max_tracked_candidates", errors)
    _positive_int(execution["max_recorded_successes"], "execution.max_recorded_successes", errors, minimum=0)
    _positive_int(execution["progress_every_batches"], "execution.progress_every_batches", errors)
    if not isinstance(execution["record_successes"], bool):
        errors.append("execution.record_successes: expected true/false")
    if execution["dedup"] not in ("auto", "always"):
        errors.append("execution.dedup: must be 'auto' or 'always'")

    generators_raw = raw.get("generators")
    generators: list[dict] = []
    if not isinstance(generators_raw, list) or not generators_raw:
        errors.append("generators: expected a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, spec in enumerate(generators_raw):
            if not isinstance(spec, dict):
                errors.append(f"generators[{index}]: expected a mapping")
                continue
            gid = spec.get("id")
            if gid in seen_ids:
                errors.append(f"generators[{index}]: duplicate id {gid!r}")
            seen_ids.add(str(gid))
            try:
                build_generator(spec)
            except ValueError as exc:
                errors.append(f"generators[{index}]: {exc}")
                continue
            generators.append(dict(spec))

    controls = _merge(DEFAULTS["controls"], raw.get("controls", {}), "controls", errors)
    null_control = controls["null_control_generator"]
    if null_control is not None and null_control not in {g["id"] for g in generators}:
        errors.append("controls.null_control_generator: must name one of the generators")
    positive = controls["positive_control"]
    if not isinstance(positive["enabled"], bool):
        errors.append("controls.positive_control.enabled: expected true/false")
    _positive_int(positive["width"], "controls.positive_control.width", errors)
    _positive_int(positive["candidates"], "controls.positive_control.candidates", errors)
    lift = positive["relative_lift"]
    if not isinstance(lift, (int, float)) or isinstance(lift, bool) or lift <= 0:
        errors.append("controls.positive_control.relative_lift: expected a positive number")
    elif target is not None:
        p0 = float(target.probability)
        if p0 >= 1.0 or lift * p0 / (1.0 - p0) > 1.0:
            errors.append("controls.positive_control.relative_lift: too large for this target")

    economics = _merge(DEFAULTS["economics"], raw.get("economics", {}), "economics", errors)
    reference = economics["reference_generator"]
    if reference is not None and reference not in {g["id"] for g in generators}:
        errors.append("economics.reference_generator: must name one of the generators")

    if errors:
        raise ConfigError("\n".join(errors))

    assert target is not None
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment": experiment,
        "engine": engine,
        "target": target.to_dict(),
        "seeds": {"master": seeds["master"]},
        "phases": phases,
        "statistics": statistics,
        "execution": execution,
        "controls": controls,
        "generators": generators,
        "economics": economics,
    }


def target_from_resolved(resolved: dict) -> Target:
    return Target(int(resolved["target"]["target_int"]))
