"""Candidate-generator interface and candidate-domain definitions.

Terminology used everywhere in HASHLAB:

* A **candidate** is always a Python ``bytes`` object. It is the exact input
  that gets hashed.
* A **byte-domain** generator produces arbitrary byte values (0x00-0xFF).
* A **character-domain** generator produces text and encodes it as ASCII.
  Every character maps to exactly one byte, so the candidate bytes are a strict
  subset of the byte space. For example, the 16-character decimal string
  "0000000000000042" is NOT the same input as the 8-byte integer 42.
* **Width** is always the candidate's length in bytes. Every candidate from a
  generator has exactly that length.

Comparisons between generators with different domains (different width,
alphabet or encoding) compare different sample spaces. The analysis report
records the domain of every generator so that limitation stays visible.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import ClassVar, Iterator

SEED_DERIVATION_VERSION = "hashlab-seed-v1"


@dataclass(frozen=True)
class Domain:
    """Precise description of the set a generator draws candidates from."""

    kind: str  # "bytes" or "ascii-chars"
    width_bytes: int
    alphabet: str  # human-readable alphabet description
    alphabet_size: int  # symbols per position
    cardinality: int  # exact number of distinct candidates the generator can emit
    description: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["cardinality"] = str(self.cardinality)  # can exceed JSON-safe integers
        return data


def derive_seed(master_seed: int, *labels: str) -> int:
    """Derive a 64-bit sub-seed from the master seed and labels (deterministic, documented).

    seed = first 8 bytes (big-endian) of SHA-256("hashlab-seed-v1|<master>|<label1>|<label2>...")
    """
    material = "|".join([SEED_DERIVATION_VERSION, str(int(master_seed)), *labels]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


class CandidateGenerator(ABC):
    """Base class. Subclasses produce a deterministic stream of fixed-width candidates."""

    type_name: ClassVar[str] = ""
    #: True if the stream never repeats a candidate (proved by construction and unit-tested).
    unique_by_construction: ClassVar[bool] = False
    #: True if the stream depends on a seed. Seedless streams resume from a start index instead.
    uses_seed: ClassVar[bool] = False

    def __init__(self, generator_id: str, width: int) -> None:
        if not generator_id or not isinstance(generator_id, str):
            raise ValueError("generator id must be a non-empty string")
        if not isinstance(width, int) or not 1 <= width <= 1024:
            raise ValueError(f"{generator_id}: width must be an integer in [1, 1024]")
        self.generator_id = generator_id
        self.width = width

    @abstractmethod
    def domain(self) -> Domain:
        """The exact candidate domain."""

    @abstractmethod
    def stream(self, seed: int | None, start_index: int = 0) -> Iterator[bytes]:
        """Yield candidates.

        Seeded generators use ``seed`` and ignore ``start_index``. Seedless
        generators ignore ``seed`` and begin at position ``start_index`` of
        their fixed enumeration. That lets a validation phase continue exactly
        where the discovery phase stopped, so the two phases never overlap.
        """

    def available(self, start_index: int = 0) -> int:
        """Max distinct candidates left from ``start_index`` (seeded: full domain)."""
        card = self.domain().cardinality
        if self.uses_seed:
            return card
        return max(0, card - start_index)

    def parameters(self) -> dict:
        return {"width": self.width}

    def describe(self) -> dict:
        return {
            "id": self.generator_id,
            "type": self.type_name,
            "parameters": self.parameters(),
            "unique_by_construction": self.unique_by_construction,
            "uses_seed": self.uses_seed,
            "domain": self.domain().to_dict(),
        }
