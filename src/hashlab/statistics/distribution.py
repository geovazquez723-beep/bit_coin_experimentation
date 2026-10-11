"""Streaming digest-distribution summaries and goodness-of-fit tests.

Under the null hypothesis (uniform 256-bit digests):

* leading-zero-bit count L: P(L = j) = 2**-(j+1) for 0 <= j < 256, P(L = 256) = 2**-256
* first byte and last byte: each uniform on 0..255

Only these counts are kept, never the digests, so memory stays fixed
whatever the sample size.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hashlab import DIGEST_BITS
from hashlab.statistics.inference import chi2_sf

MIN_EXPECTED_PER_BIN = 5.0


@dataclass
class DigestAccumulator:
    """Fixed-size counters for digest-distribution diagnostics."""

    leading_zero_bits: list[int] = field(default_factory=lambda: [0] * (DIGEST_BITS + 1))
    first_byte: list[int] = field(default_factory=lambda: [0] * 256)
    last_byte: list[int] = field(default_factory=lambda: [0] * 256)

    def add(self, digest: bytes, value: int) -> None:
        self.leading_zero_bits[DIGEST_BITS - value.bit_length()] += 1
        self.first_byte[digest[0]] += 1
        self.last_byte[digest[-1]] += 1

    @property
    def total(self) -> int:
        return sum(self.leading_zero_bits)

    def to_dict(self) -> dict:
        last_nonzero = max((i for i, c in enumerate(self.leading_zero_bits) if c), default=0)
        return {
            "leading_zero_bits": self.leading_zero_bits[: last_nonzero + 1],
            "first_byte": list(self.first_byte),
            "last_byte": list(self.last_byte),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DigestAccumulator":
        acc = cls()
        for i, count in enumerate(data["leading_zero_bits"]):
            acc.leading_zero_bits[i] = int(count)
        acc.first_byte = [int(c) for c in data["first_byte"]]
        acc.last_byte = [int(c) for c in data["last_byte"]]
        if len(acc.first_byte) != 256 or len(acc.last_byte) != 256:
            raise ValueError("byte histograms must have 256 bins")
        return acc


def leading_zero_probability(j: int) -> float:
    """Null probability that a uniform 256-bit value has exactly j leading zero bits."""
    if not 0 <= j <= DIGEST_BITS:
        raise ValueError("j must be in [0, 256]")
    return 2.0 ** -(j + 1) if j < DIGEST_BITS else 2.0**-DIGEST_BITS


@dataclass(frozen=True)
class GoodnessOfFit:
    test: str
    statistic: float | None
    df: int | None
    p_value: float | None
    bins: int
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "test": self.test,
            "statistic": self.statistic,
            "df": self.df,
            "p_value": self.p_value,
            "bins": self.bins,
            "note": self.note,
        }


def chi_square_gof(observed: list[int], expected: list[float], test: str) -> GoodnessOfFit:
    """Pearson chi-square goodness of fit (all parameters fixed by H0, so df = bins - 1)."""
    if len(observed) != len(expected) or len(observed) < 2:
        raise ValueError("need matching observed/expected lists with at least 2 bins")
    if min(expected) < MIN_EXPECTED_PER_BIN:
        return GoodnessOfFit(test, None, None, None, len(observed), "not run: an expected bin count is below 5")
    statistic = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
    df = len(observed) - 1
    return GoodnessOfFit(test, statistic, df, chi2_sf(statistic, df), len(observed))


def leading_zero_gof(histogram: list[int]) -> GoodnessOfFit:
    """Leading-zero-bit counts against the geometric null.

    Bins j = 0..K-1 are kept separate and j >= K is pooled into one tail bin,
    with K the largest value that keeps every expected count >= 5.
    """
    n = sum(histogram)
    if n == 0:
        return GoodnessOfFit("leading_zero_bits", None, None, None, 0, "not run: no data")
    counts = list(histogram) + [0] * (DIGEST_BITS + 1 - len(histogram))
    k = 0
    # Tail expected count for j >= k is n * 2**-k, and bin k-1 has expected n * 2**-k too.
    while k < DIGEST_BITS and n * 2.0 ** -(k + 1) >= MIN_EXPECTED_PER_BIN:
        k += 1
    if k < 1:
        return GoodnessOfFit("leading_zero_bits", None, None, None, 0, "not run: sample too small")
    observed = counts[:k] + [sum(counts[k:])]
    expected = [n * leading_zero_probability(j) for j in range(k)] + [n * 2.0**-k]
    return chi_square_gof(observed, expected, "leading_zero_bits")


def uniform_byte_gof(histogram: list[int], test: str) -> GoodnessOfFit:
    n = sum(histogram)
    if n == 0:
        return GoodnessOfFit(test, None, None, None, 256, "not run: no data")
    return chi_square_gof(list(histogram), [n / 256.0] * 256, test)
