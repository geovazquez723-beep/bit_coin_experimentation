"""Positive control: a deliberately biased engine with a known effect size.

It answers: "If an effect of this size existed, would this run and this
analysis detect it?" A null result is only informative when the positive
control is detected at the same target and comparable sample size.

How the bias works: for each digest that is NOT already a success, its last
four bytes u (an integer in [0, 2**32)) decide whether it gets forced into a
success. When u / 2**32 < q, the digest value v is replaced by v mod target.
With q = lift * p0 / (1 - p0), the success probability becomes about
p0 * (1 + lift). The bias is deterministic given the candidate, so the control
reproduces exactly.

This engine is NEVER used for the primary hypotheses. Its results are written
under a separate "positive_control" key.
"""

from __future__ import annotations

from fractions import Fraction

from hashlab.hashing.target import Target

_U32 = 1 << 32


class BiasedControlEngine:
    name = "positive-control-biased"
    digest_size = 32

    def __init__(self, base_engine, target: Target, relative_lift: float) -> None:
        p0 = target.probability
        if p0 >= 1:
            raise ValueError("positive control needs a target below 2**256")
        q = Fraction(relative_lift).limit_denominator(10**12) * p0 / (1 - p0)
        if not 0 < q <= 1:
            raise ValueError("relative_lift is out of range for this target")
        self.base = base_engine
        self.target = target
        self.relative_lift = relative_lift
        self.threshold = int(q * _U32)  # force when u < threshold

    @property
    def expected_probability(self) -> float:
        p0 = float(self.target.probability)
        q = self.threshold / _U32
        return p0 + (1.0 - p0) * q

    def digest(self, data: bytes) -> bytes:
        digest = self.base.digest(data)
        value = int.from_bytes(digest, "big")
        if value >= self.target.value and int.from_bytes(digest[-4:], "big") < self.threshold:
            return (value % self.target.value).to_bytes(32, "big")
        return digest

    def describe(self) -> dict:
        return {
            "name": self.name,
            "base_engine": self.base.name,
            "relative_lift_requested": self.relative_lift,
            "force_threshold_u32": self.threshold,
            "expected_success_probability": self.expected_probability,
        }
