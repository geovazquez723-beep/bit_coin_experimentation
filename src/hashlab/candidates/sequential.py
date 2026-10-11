"""Generator 1: sequential fixed-width integer encodings.

Enumerates the integers start, start+1, start+2, ... and encodes each one as a
fixed-width candidate:

* ``be-bytes``: the integer as ``width`` raw bytes, big-endian, zero-padded.
  Domain: all byte strings of length ``width`` (256**width elements).
* ``ascii-decimal``: the integer as a zero-padded decimal string of ``width``
  characters, ASCII-encoded. Domain: strings over "0"-"9" of length ``width``
  (10**width elements). This is a character domain, not a byte domain.

Unique by construction: the encoding is injective, and the enumeration stops
at the end of the domain instead of wrapping around.
"""

from __future__ import annotations

from typing import Iterator

from hashlab.candidates.base import CandidateGenerator, Domain

ENCODINGS = ("be-bytes", "ascii-decimal")


class SequentialGenerator(CandidateGenerator):
    type_name = "sequential"
    unique_by_construction = True
    uses_seed = False

    def __init__(self, generator_id: str, width: int, encoding: str = "be-bytes", start: int = 0) -> None:
        super().__init__(generator_id, width)
        if encoding not in ENCODINGS:
            raise ValueError(f"{generator_id}: encoding must be one of {ENCODINGS}")
        if not isinstance(start, int) or start < 0:
            raise ValueError(f"{generator_id}: start must be a non-negative integer")
        self.encoding = encoding
        self.start = start
        if start >= self.domain().cardinality:
            raise ValueError(f"{generator_id}: start is outside the domain")

    def domain(self) -> Domain:
        if self.encoding == "be-bytes":
            return Domain(
                kind="bytes",
                width_bytes=self.width,
                alphabet="bytes 0x00-0xFF",
                alphabet_size=256,
                cardinality=256**self.width,
                description=f"integers start..start+n-1 as {self.width}-byte big-endian unsigned values",
            )
        return Domain(
            kind="ascii-chars",
            width_bytes=self.width,
            alphabet="ASCII digits '0'-'9'",
            alphabet_size=10,
            cardinality=10**self.width,
            description=f"integers start..start+n-1 as zero-padded {self.width}-digit ASCII decimal strings",
        )

    def available(self, start_index: int = 0) -> int:
        return max(0, self.domain().cardinality - self.start - start_index)

    def parameters(self) -> dict:
        return {"width": self.width, "encoding": self.encoding, "start": self.start}

    def encode(self, value: int) -> bytes:
        if self.encoding == "be-bytes":
            return value.to_bytes(self.width, "big")
        return f"{value:0{self.width}d}".encode("ascii")

    def stream(self, seed: int | None, start_index: int = 0) -> Iterator[bytes]:
        limit = self.domain().cardinality
        value = self.start + start_index
        while value < limit:
            yield self.encode(value)
            value += 1
