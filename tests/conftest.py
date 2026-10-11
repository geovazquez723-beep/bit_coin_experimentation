"""Shared fixtures. Every fixture is tiny: no test launches a real experiment."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:  # allow running tests without `pip install -e .`
    sys.path.insert(0, str(SRC))

TINY_CONFIG = {
    "schema_version": 1,
    "experiment": {"id": "test", "name": "tiny-fixture"},
    "engine": "sha256",
    "target": {"leading_zero_bits": 2},
    "seeds": {"master": 12345},
    "phases": {
        "discovery": {"candidates_per_generator": 300},
        "validation": {"candidates_per_generator": 300},
    },
    "statistics": {"alpha": 0.01, "confidence_level": 0.99},
    "execution": {"batch_size": 64, "progress_every_batches": 1000},
    "controls": {
        "null_control_generator": "rand",
        "positive_control": {"enabled": True, "width": 8, "candidates": 3000, "relative_lift": 1.0},
    },
    "generators": [
        {"id": "seq", "type": "sequential", "width": 4, "encoding": "be-bytes"},
        {"id": "uni", "type": "uniform", "width": 2},  # 65,536-value domain: a few duplicates expected
        {"id": "pat", "type": "patterned", "width": 8, "mode": "repeated-chars", "alphabet": "lowercase", "max_period": 2},
        {"id": "gray", "type": "structured", "width": 4, "mode": "gray"},
        {"id": "rand", "type": "random_bytes", "width": 8},
    ],
}


@pytest.fixture
def tiny_config() -> dict:
    return copy.deepcopy(TINY_CONFIG)


@pytest.fixture
def tiny_config_file(tmp_path: Path, tiny_config: dict) -> Path:
    import json

    path = tmp_path / "tiny.json"
    path.write_text(json.dumps(tiny_config), encoding="utf-8")
    return path
