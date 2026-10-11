"""Duplicate accounting, phase disjointness and the positive control, on tiny fixtures."""

from __future__ import annotations

import io
import json
from typing import Iterator

import pytest

from hashlab.candidates.base import CandidateGenerator, Domain
from hashlab.candidates.random import RandomBytesGenerator
from hashlab.experiments.baseline import SuccessRecorder, build_plan, run_phase
from hashlab.experiments.config import resolve_config
from hashlab.experiments.controls import BiasedControlEngine
from hashlab.hashing import SHA256Engine, Target


class ScriptedGenerator(CandidateGenerator):
    """Emits a fixed script of candidates (with deliberate repeats)."""

    type_name = "scripted"

    def __init__(self, script: list[bytes]) -> None:
        super().__init__("scripted", 1)
        self.script = script

    def domain(self) -> Domain:
        return Domain("bytes", 1, "bytes", 256, 256, "scripted")

    def stream(self, seed, start_index: int = 0) -> Iterator[bytes]:
        return iter(self.script[start_index:])


def run(gen, n, seen_prev, seen_cur, start=0, batch=2, engine=None, target=1 << 255):
    return run_phase(
        gen, engine or SHA256Engine(), target, "p", n, None, start, batch,
        seen_prev, seen_cur, io.StringIO(), SuccessRecorder(None, 0),
    )


def test_duplicates_within_phase_are_counted_and_not_hashed() -> None:
    gen = ScriptedGenerator([b"a", b"b", b"a", b"c", b"b", b"a"])
    counters = run(gen, 6, None, set())
    assert counters.attempted == 6
    assert counters.unique == 3
    assert counters.duplicates_within_phase == 3
    assert counters.digest.total == 3  # only unique candidates were hashed


def test_cross_phase_duplicates_are_removed_from_validation() -> None:
    gen = ScriptedGenerator([b"a", b"b", b"c", b"a", b"d", b"b"])
    discovery_seen: set[bytes] = set()
    discovery = run(gen, 3, None, discovery_seen)
    validation = run(gen, 3, discovery_seen, set(), start=3)
    assert discovery.unique == 3
    assert validation.unique == 1
    assert validation.duplicates_cross_phase == 2
    assert validation.duplicates_within_phase == 0


def test_exhaustion_is_reported() -> None:
    counters = run(ScriptedGenerator([b"a", b"b"]), 10, None, set())
    assert counters.exhausted and counters.attempted == 2


def test_success_counting_uses_exact_target() -> None:
    gen = ScriptedGenerator([bytes([i]) for i in range(256)])
    target = Target.from_leading_zero_bits(1).value
    counters = run(gen, 256, None, None, batch=50, target=target)
    expected = sum(1 for i in range(256) if int.from_bytes(SHA256Engine().digest(bytes([i])), "big") < target)
    assert counters.successes == expected
    assert counters.batches == 6


def test_batch_stream_records_every_batch() -> None:
    stream = io.StringIO()
    gen = ScriptedGenerator([bytes([i]) for i in range(10)])
    run_phase(gen, SHA256Engine(), 1 << 255, "p", 10, None, 0, 3, None, None, stream, SuccessRecorder(None, 0))
    rows = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [r["attempted"] for r in rows] == [3, 3, 3, 1]
    assert sum(r["unique"] for r in rows) == 10


def test_success_recorder_cap() -> None:
    out = io.StringIO()
    recorder = SuccessRecorder(out, 2)
    for i in range(5):
        recorder.record("g", "p", bytes([i]), bytes(32))
    assert recorder.recorded == 2 and recorder.dropped == 3
    assert len(out.getvalue().splitlines()) == 2


def test_positive_control_engine_has_detectable_planted_lift() -> None:
    target = Target.from_leading_zero_bits(2)
    engine = BiasedControlEngine(SHA256Engine(), target, relative_lift=1.0)
    assert engine.expected_probability == pytest.approx(0.5, abs=1e-6)
    counters = run_phase(
        RandomBytesGenerator("pc", 8), engine, target.value, "control", 4000, 1, 0, 500,
        None, set(), None, SuccessRecorder(None, 0),
    )
    rate = counters.successes / counters.unique
    assert 0.45 < rate < 0.55  # vs 0.25 under the null


def test_plan_reports_infeasible_requests(tiny_config) -> None:
    tiny_config["phases"]["discovery"]["candidates_per_generator"] = 200
    tiny_config["phases"]["validation"]["candidates_per_generator"] = 200
    tiny_config["generators"] = [{"id": "small", "type": "sequential", "width": 1}]
    tiny_config["controls"]["null_control_generator"] = None
    plan = build_plan(resolve_config(tiny_config))
    assert any("domain has only 256" in e for e in plan["errors"])


def test_plan_enforces_dedup_memory_cap(tiny_config) -> None:
    tiny_config["execution"]["max_tracked_candidates"] = 100
    plan = build_plan(resolve_config(tiny_config))
    assert any("max_tracked_candidates" in e for e in plan["errors"])


def test_plan_is_deterministic(tiny_config) -> None:
    resolved = resolve_config(tiny_config)
    assert build_plan(resolved)["plan_fingerprint"] == build_plan(resolved)["plan_fingerprint"]
