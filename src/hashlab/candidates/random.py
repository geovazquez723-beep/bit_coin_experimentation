"""Generators 2 and 5: seeded random candidates.

Generator 2, ``uniform`` (uniformly sampled fixed-width integers):
    Uses Python's ``random.Random(seed)`` (Mersenne Twister; NOT a
    cryptographic generator, which this sampling doesn't need). It draws
    integers uniformly with replacement:

    * ``be-bytes``: x uniform on [0, 256**width), encoded as ``width``
      big-endian bytes.
    * ``ascii-decimal``: x uniform on [0, 10**width), encoded as a zero-padded
      decimal ASCII string.

Generator 5, ``random_bytes`` (random-looking fixed-width byte sequences):
    A seeded, deterministic byte stream: keyed BLAKE2b in counter mode,
    block_i = BLAKE2b(key=seed_bytes, msg=i as 16 big-endian bytes, 64-byte
    digest). It produces the concatenation block_0 || block_1 || ... and cuts
    it into ``width``-byte candidates. Domain: all byte strings of length
    ``width``.

    BLAKE2b is not SHA-256. That is deliberate: a candidate stream built from
    SHA-256 itself could create an artificial dependence with the hash being
    tested.

Neither generator is unique by construction. The experiment runner removes
duplicates exactly with a set of seen candidates, bounded by
``execution.max_tracked_candidates``, and reports how many duplicates it saw.
The expected number of within-stream duplicates for n uniform draws from N
values is about n*(n-1)/(2N) (``expected_duplicates``).
"""

from __future__ import annotations

import hashlib
import random as _stdlib_random
from typing import Iterator

from hashlab.candidates.base import CandidateGenerator, Domain

UNIFORM_ENCODINGS = ("be-bytes", "ascii-decimal")
_BLAKE_BLOCK = 64


def expected_duplicates(draws: int, domain_size: int) -> float:
    """Expected number of draws that repeat an earlier draw (sampling with replacement).

    E[duplicates] = n - E[distinct] = n - N*(1 - (1 - 1/N)**n).
    For N far larger than n this is about n*(n-1)/(2N).
    """
    if draws <= 1:
        return 0.0
    if domain_size > 10**15:
        return draws * (draws - 1) / (2.0 * domain_size)
    distinct = domain_size * (1.0 - (1.0 - 1.0 / domain_size) ** draws)
    return draws - distinct


class UniformIntegerGenerator(CandidateGenerator):
    type_name = "uniform"
    unique_by_construction = False
    uses_seed = True

    def __init__(self, generator_id: str, width: int, encoding: str = "be-bytes") -> None:
        super().__init__(generator_id, width)
        if encoding not in UNIFORM_ENCODINGS:
            raise ValueError(f"{generator_id}: encoding must be one of {UNIFORM_ENCODINGS}")
        self.encoding = encoding

    def domain(self) -> Domain:
        if self.encoding == "be-bytes":
            return Domain(
                kind="bytes",
                width_bytes=self.width,
                alphabet="bytes 0x00-0xFF",
                alphabet_size=256,
                cardinality=256**self.width,
                description=f"uniform integers on [0, 256**{self.width}) as big-endian bytes, with replacement",
            )
        return Domain(
            kind="ascii-chars",
            width_bytes=self.width,
            alphabet="ASCII digits '0'-'9'",
            alphabet_size=10,
            cardinality=10**self.width,
            description=f"uniform integers on [0, 10**{self.width}) as zero-padded ASCII decimal, with replacement",
        )

    def parameters(self) -> dict:
        return {"width": self.width, "encoding": self.encoding, "prng": "random.Random (MT19937)"}

    def stream(self, seed: int | None, start_index: int = 0) -> Iterator[bytes]:
        if seed is None:
            raise ValueError(f"{self.generator_id}: a seed is required")
        rng = _stdlib_random.Random(seed)
        if self.encoding == "be-bytes":
            bits = 8 * self.width
            while True:
                yield rng.getrandbits(bits).to_bytes(self.width, "big")
        else:
            upper = 10**self.width
            while True:
                yield f"{rng.randrange(upper):0{self.width}d}".encode("ascii")


class RandomBytesGenerator(CandidateGenerator):
    type_name = "random_bytes"
    unique_by_construction = False
    uses_seed = True

    def domain(self) -> Domain:
        return Domain(
            kind="bytes",
            width_bytes=self.width,
            alphabet="bytes 0x00-0xFF",
            alphabet_size=256,
            cardinality=256**self.width,
            description=f"{self.width}-byte slices of a keyed BLAKE2b counter-mode stream",
        )

    def parameters(self) -> dict:
        return {"width": self.width, "prng": "BLAKE2b-512 keyed counter mode"}

    def stream(self, seed: int | None, start_index: int = 0) -> Iterator[bytes]:
        if seed is None:
            raise ValueError(f"{self.generator_id}: a seed is required")
        key = int(seed).to_bytes(16, "big", signed=False)
        counter = 0
        buffer = b""
        while True:
            while len(buffer) < self.width:
                block = hashlib.blake2b(counter.to_bytes(16, "big"), key=key, digest_size=_BLAKE_BLOCK).digest()
                buffer += block
                counter += 1
            yield buffer[: self.width]
            buffer = buffer[self.width :]
