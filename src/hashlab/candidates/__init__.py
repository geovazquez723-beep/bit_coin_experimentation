"""Candidate generators and the config factory."""

from __future__ import annotations

from hashlab.candidates.base import CandidateGenerator, Domain, derive_seed
from hashlab.candidates.patterned import PatternedGenerator
from hashlab.candidates.random import RandomBytesGenerator, UniformIntegerGenerator, expected_duplicates
from hashlab.candidates.sequential import SequentialGenerator
from hashlab.candidates.structured import StructuredGenerator

GENERATOR_TYPES: dict[str, type[CandidateGenerator]] = {
    cls.type_name: cls
    for cls in (
        SequentialGenerator,
        UniformIntegerGenerator,
        PatternedGenerator,
        StructuredGenerator,
        RandomBytesGenerator,
    )
}


def build_generator(spec: dict) -> CandidateGenerator:
    """Build a generator from a config entry: {id, type, width, ...type-specific params}."""
    params = dict(spec)
    try:
        generator_id = params.pop("id")
        type_name = params.pop("type")
    except KeyError as missing:
        raise ValueError(f"generator entry is missing {missing}") from None
    cls = GENERATOR_TYPES.get(type_name)
    if cls is None:
        raise ValueError(f"{generator_id}: unknown generator type {type_name!r}; expected {sorted(GENERATOR_TYPES)}")
    try:
        return cls(generator_id, **params)
    except TypeError as exc:
        raise ValueError(f"{generator_id}: invalid parameters for {type_name}: {exc}") from None


__all__ = [
    "GENERATOR_TYPES",
    "CandidateGenerator",
    "Domain",
    "PatternedGenerator",
    "RandomBytesGenerator",
    "SequentialGenerator",
    "StructuredGenerator",
    "UniformIntegerGenerator",
    "build_generator",
    "derive_seed",
    "expected_duplicates",
]
