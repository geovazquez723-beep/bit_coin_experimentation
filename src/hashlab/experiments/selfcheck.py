"""Cheap correctness checks behind ``hashlab validate``.

They hash only a handful of fixed test vectors and tiny generator samples.
No experiment runs and nothing is written to disk.
"""

from __future__ import annotations

import itertools
import math
from typing import Callable

from hashlab.candidates import (
    PatternedGenerator,
    RandomBytesGenerator,
    SequentialGenerator,
    StructuredGenerator,
    UniformIntegerGenerator,
)
from hashlab.hashing import SHA256dEngine, SHA256Engine, Target, digest_to_int, leading_zero_bits
from hashlab.statistics.inference import binom_cdf, chi2_sf, clopper_pearson, holm

# FIPS 180-2 SHA-256 vectors, plus double-SHA-256 of the same messages.
SHA256_VECTORS = {
    b"": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    b"abc": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq": (
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
    ),
}
SHA256D_VECTORS = {
    b"": "5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456",
    b"abc": "4f8b42c22dd3729b519ba6f68d2da7cc5b2d606d05daed5ad5128cc03e6c6358",
}


def _check_hash_vectors() -> None:
    for message, expected in SHA256_VECTORS.items():
        assert SHA256Engine().digest(message).hex() == expected, f"sha256 vector failed for {message!r}"
    for message, expected in SHA256D_VECTORS.items():
        assert SHA256dEngine().digest(message).hex() == expected, f"sha256d vector failed for {message!r}"


def _check_target_math() -> None:
    target = Target.from_leading_zero_bits(8)
    assert target.value == 1 << 248
    assert target.hit((1 << 248) - 1) and not target.hit(1 << 248)
    digest = bytes([0x00, 0xFF]) + bytes(30)
    assert digest_to_int(digest) == 0xFF << 240
    assert leading_zero_bits(digest_to_int(digest)) == 8
    assert target.probability == 1 / 256


def _check_statistics() -> None:
    _, upper = clopper_pearson(0, 10, 0.95)
    assert math.isclose(upper, 1 - 0.025 ** (1 / 10), rel_tol=1e-9)
    exact = sum(math.comb(20, i) * 0.3**i * 0.7 ** (20 - i) for i in range(7))
    assert math.isclose(binom_cdf(6, 20, 0.3), exact, rel_tol=1e-10)
    assert math.isclose(chi2_sf(3.0, 2), math.exp(-1.5), rel_tol=1e-10)
    assert holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


def _check_generators() -> None:
    gens = [
        (SequentialGenerator("s", 4), None),
        (UniformIntegerGenerator("u", 8), 7),
        (PatternedGenerator("p", 8, max_period=2), None),
        (StructuredGenerator("g", 4, mode="gray"), None),
        (RandomBytesGenerator("r", 8), 7),
    ]
    for gen, seed in gens:
        first = list(itertools.islice(gen.stream(seed, 0), 50))
        second = list(itertools.islice(gen.stream(seed, 0), 50))
        assert first == second, f"{gen.generator_id} is not deterministic"
        assert all(len(c) == gen.width for c in first), f"{gen.generator_id} broke its fixed width"


CHECKS: list[tuple[str, Callable[[], None]]] = [
    ("hash test vectors (sha256, sha256d)", _check_hash_vectors),
    ("target and leading-zero arithmetic", _check_target_math),
    ("statistical reference values", _check_statistics),
    ("generator determinism and width", _check_generators),
]


def run_selfchecks() -> list[tuple[str, str | None]]:
    """Run every check. Returns (name, error message or None)."""
    outcomes = []
    for name, check in CHECKS:
        try:
            check()
            outcomes.append((name, None))
        except Exception as exc:  # noqa: BLE001 - report every failure, keep going
            outcomes.append((name, f"{type(exc).__name__}: {exc}"))
    return outcomes
