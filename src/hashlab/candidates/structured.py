"""Generator 4: structured, deterministic sequences.

Each mode is a bijection f on [0, 2**(8*width)), applied to the index
i = 0, 1, 2, ... The candidate is f(i) as ``width`` big-endian bytes, so the
domain is all byte strings of length ``width``. Because f is a bijection and
the index never wraps around, each mode is unique by construction.

* ``gray``: reflected binary Gray code, f(i) = i XOR (i >> 1). Consecutive
  candidates differ in exactly one bit.
* ``stride``: f(i) = (offset + stride * i) mod 2**(8*width). It needs an odd
  stride, because odd numbers are invertible modulo a power of two.
* ``bit-reversed``: f(i) = the 8*width bits of i in reverse order. Consecutive
  candidates differ mostly in their high bits.
"""

from __future__ import annotations

from typing import Iterator

from hashlab.candidates.base import CandidateGenerator, Domain

MODES = ("gray", "stride", "bit-reversed")


def gray_code(value: int) -> int:
    return value ^ (value >> 1)


def reverse_bits(value: int, bits: int) -> int:
    return int(format(value, f"0{bits}b")[::-1], 2)


class StructuredGenerator(CandidateGenerator):
    type_name = "structured"
    unique_by_construction = True
    uses_seed = False

    def __init__(
        self,
        generator_id: str,
        width: int,
        mode: str = "gray",
        stride: int | None = None,
        offset: int = 0,
    ) -> None:
        super().__init__(generator_id, width)
        if mode not in MODES:
            raise ValueError(f"{generator_id}: mode must be one of {MODES}")
        self.mode = mode
        self.modulus = 1 << (8 * width)
        if mode == "stride":
            if not isinstance(stride, int) or stride % 2 == 0 or stride <= 0:
                raise ValueError(f"{generator_id}: stride mode needs a positive odd integer stride")
            if not isinstance(offset, int) or not 0 <= offset < self.modulus:
                raise ValueError(f"{generator_id}: offset must be in [0, 2**(8*width))")
        elif stride is not None or offset != 0:
            raise ValueError(f"{generator_id}: stride/offset only apply to stride mode")
        self.stride = stride
        self.offset = offset

    def domain(self) -> Domain:
        return Domain(
            kind="bytes",
            width_bytes=self.width,
            alphabet="bytes 0x00-0xFF",
            alphabet_size=256,
            cardinality=self.modulus,
            description=f"{self.mode} bijection of the index, as {self.width}-byte big-endian values",
        )

    def parameters(self) -> dict:
        params: dict = {"width": self.width, "mode": self.mode}
        if self.mode == "stride":
            params.update(stride=self.stride, offset=self.offset)
        return params

    def map_index(self, index: int) -> int:
        if self.mode == "gray":
            return gray_code(index)
        if self.mode == "stride":
            assert self.stride is not None
            return (self.offset + self.stride * index) % self.modulus
        return reverse_bits(index, 8 * self.width)

    def stream(self, seed: int | None, start_index: int = 0) -> Iterator[bytes]:
        index = start_index
        while index < self.modulus:
            yield self.map_index(index).to_bytes(self.width, "big")
            index += 1
