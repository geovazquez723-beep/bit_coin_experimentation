"""Proof-of-work target arithmetic.

A 32-byte digest is read as a big-endian unsigned integer h in [0, 2**256).
A candidate succeeds iff h < target. All comparisons are exact integer
comparisons; no hex-string prefix shortcuts are used anywhere.

Requiring k leading zero bits is the same as target = 2**(256 - k):
h < 2**(256 - k) holds exactly when the top k bits of h are zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from hashlab import DIGEST_BITS, HASH_SPACE


def digest_to_int(digest: bytes) -> int:
    """Interpret a digest as a big-endian unsigned integer (leading zero bytes kept)."""
    if len(digest) * 8 != DIGEST_BITS:
        raise ValueError(f"expected a {DIGEST_BITS // 8}-byte digest, got {len(digest)} bytes")
    return int.from_bytes(digest, "big", signed=False)


def leading_zero_bits(value: int) -> int:
    """Number of leading zero bits of a 256-bit value (256 for value == 0)."""
    if not 0 <= value < HASH_SPACE:
        raise ValueError("value outside the 256-bit range")
    return DIGEST_BITS - value.bit_length()


def is_success(value: int, target: int) -> bool:
    """Exact success rule: hash_integer < target."""
    return value < target


@dataclass(frozen=True)
class Target:
    """A success threshold. `value` is the exclusive upper bound on the hash integer."""

    value: int

    def __post_init__(self) -> None:
        if not 1 <= self.value <= HASH_SPACE:
            raise ValueError("target must satisfy 1 <= target <= 2**256")

    @classmethod
    def from_leading_zero_bits(cls, bits: int) -> "Target":
        if not 0 <= bits <= DIGEST_BITS:
            raise ValueError("leading_zero_bits must be in [0, 256]")
        return cls(1 << (DIGEST_BITS - bits))

    @classmethod
    def from_hex(cls, text: str) -> "Target":
        cleaned = text.lower().removeprefix("0x")
        if not cleaned or len(cleaned) > 64 or any(c not in "0123456789abcdef" for c in cleaned):
            raise ValueError(f"invalid target hex {text!r}")
        return cls(int(cleaned, 16))

    @classmethod
    def from_config(cls, cfg: dict) -> "Target":
        keys = set(cfg)
        if keys == {"leading_zero_bits"}:
            return cls.from_leading_zero_bits(int(cfg["leading_zero_bits"]))
        if keys == {"target_hex"}:
            return cls.from_hex(str(cfg["target_hex"]))
        if keys == {"target_int"}:
            return cls(int(cfg["target_int"]))
        raise ValueError("target config needs exactly one of: leading_zero_bits, target_hex, target_int")

    @property
    def probability(self) -> Fraction:
        """Theoretical success probability for one uniformly random digest: target / 2**256 (exact)."""
        return Fraction(self.value, HASH_SPACE)

    @property
    def equivalent_leading_zero_bits(self) -> int | None:
        """k when target == 2**(256-k), else None."""
        if self.value & (self.value - 1) == 0:
            return DIGEST_BITS - (self.value.bit_length() - 1)
        return None

    def hit(self, value: int) -> bool:
        return value < self.value

    def to_dict(self) -> dict:
        p = self.probability
        return {
            "target_hex": f"{self.value:064x}" if self.value < HASH_SPACE else "1" + "0" * 64,
            "target_int": str(self.value),
            "equivalent_leading_zero_bits": self.equivalent_leading_zero_bits,
            "success_probability_exact": f"{p.numerator}/{p.denominator}",
            "success_probability_float": float(p),
        }
