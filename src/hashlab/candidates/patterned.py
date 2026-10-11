"""Generator 3: repeated-character and repeated-byte patterns.

A candidate is a short motif repeated and cut to exactly ``width`` bytes:
candidate = (motif * ceil(width / m))[:width], for a motif of length m.

Modes:

* ``repeated-bytes``: motifs over all 256 byte values. This is a byte domain,
  for example b"\\x00\\x00..." or b"\\xab\\xcd\\xab\\xcd...".
* ``repeated-chars``: motifs over an ASCII character alphabet, encoded as ASCII.
  This is a character domain, for example "aaaa..." or "xyzxyz...".

Enumeration order: motif length m = 1, 2, ..., max_period, and within each
length the motifs in lexicographic order of the alphabet.

Uniqueness by construction: a motif is emitted only when the resulting
candidate's *minimal* period is exactly m, which happens exactly when the motif
is primitive (not a power of a shorter word). Each candidate has exactly one
minimal period, and two different motifs of the same length give different
prefixes, so no candidate is ever emitted twice. The config validator requires
width >= 2 * max_period. Under that condition the Fine-Wilf theorem makes the
domain size exactly

    sum over m = 1..max_period of  P(m),   P(m) = sum over d | m of mu(m/d) * A**d

where A is the alphabet size and P(m) counts primitive words (mu is the Mobius
function).
"""

from __future__ import annotations

import itertools
from typing import Iterator

from hashlab.candidates.base import CandidateGenerator, Domain

MODES = ("repeated-bytes", "repeated-chars")

ALPHABET_PRESETS: dict[str, str] = {
    "printable-ascii": "".join(chr(c) for c in range(0x20, 0x7F)),
    "alphanumeric": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "lowercase": "abcdefghijklmnopqrstuvwxyz",
    "digits": "0123456789",
}


def mobius(n: int) -> int:
    if n < 1:
        raise ValueError("mobius is defined for n >= 1")
    result = 1
    remaining = n
    factor = 2
    while factor * factor <= remaining:
        if remaining % factor == 0:
            remaining //= factor
            if remaining % factor == 0:
                return 0
            result = -result
        factor += 1
    if remaining > 1:
        result = -result
    return result


def primitive_word_count(alphabet_size: int, length: int) -> int:
    """Number of words of the given length that are not a power of a shorter word."""
    return sum(mobius(length // d) * alphabet_size**d for d in range(1, length + 1) if length % d == 0)


def minimal_period(data: bytes) -> int:
    """Smallest p >= 1 with data[i] == data[i + p] for every valid i (KMP prefix function)."""
    n = len(data)
    if n == 0:
        return 0
    border = [0] * n
    k = 0
    for i in range(1, n):
        while k and data[i] != data[k]:
            k = border[k - 1]
        if data[i] == data[k]:
            k += 1
        border[i] = k
    return n - border[-1]


class PatternedGenerator(CandidateGenerator):
    type_name = "patterned"
    unique_by_construction = True
    uses_seed = False

    def __init__(
        self,
        generator_id: str,
        width: int,
        mode: str = "repeated-bytes",
        max_period: int = 2,
        alphabet: str | None = None,
        alphabet_chars: str | None = None,
    ) -> None:
        super().__init__(generator_id, width)
        if mode not in MODES:
            raise ValueError(f"{generator_id}: mode must be one of {MODES}")
        if not isinstance(max_period, int) or max_period < 1:
            raise ValueError(f"{generator_id}: max_period must be a positive integer")
        if width < 2 * max_period:
            raise ValueError(
                f"{generator_id}: width ({width}) must be >= 2 * max_period ({max_period}) "
                "so that candidates are unique and the domain size is exact"
            )
        self.mode = mode
        self.max_period = max_period
        if mode == "repeated-bytes":
            if alphabet is not None or alphabet_chars is not None:
                raise ValueError(f"{generator_id}: repeated-bytes always uses all 256 byte values")
            self.alphabet_label = "bytes 0x00-0xFF"
            self.symbols = bytes(range(256))
        else:
            if (alphabet is None) == (alphabet_chars is None):
                raise ValueError(f"{generator_id}: repeated-chars needs exactly one of alphabet, alphabet_chars")
            if alphabet is not None:
                if alphabet not in ALPHABET_PRESETS:
                    raise ValueError(f"{generator_id}: alphabet must be one of {sorted(ALPHABET_PRESETS)}")
                chars = ALPHABET_PRESETS[alphabet]
                self.alphabet_label = f"preset {alphabet!r}"
            else:
                chars = str(alphabet_chars)
                self.alphabet_label = f"custom {chars!r}"
            if not chars or not chars.isascii() or len(set(chars)) != len(chars):
                raise ValueError(f"{generator_id}: alphabet must be non-empty, ASCII, with no repeated characters")
            self.symbols = chars.encode("ascii")

    def domain(self) -> Domain:
        size = len(self.symbols)
        cardinality = sum(primitive_word_count(size, m) for m in range(1, self.max_period + 1))
        return Domain(
            kind="bytes" if self.mode == "repeated-bytes" else "ascii-chars",
            width_bytes=self.width,
            alphabet=self.alphabet_label,
            alphabet_size=size,
            cardinality=cardinality,
            description=(
                f"{self.width}-byte strings whose minimal period is 1..{self.max_period} "
                f"(a primitive motif repeated and truncated)"
            ),
        )

    def parameters(self) -> dict:
        return {
            "width": self.width,
            "mode": self.mode,
            "max_period": self.max_period,
            "alphabet": self.alphabet_label,
        }

    def _enumerate(self) -> Iterator[bytes]:
        for period in range(1, self.max_period + 1):
            repeats = -(-self.width // period)
            for motif in itertools.product(self.symbols, repeat=period):
                candidate = (bytes(motif) * repeats)[: self.width]
                if minimal_period(candidate) == period:
                    yield candidate

    def stream(self, seed: int | None, start_index: int = 0) -> Iterator[bytes]:
        return itertools.islice(self._enumerate(), start_index, None)
