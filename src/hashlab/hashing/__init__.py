"""Hash engines and proof-of-work target arithmetic."""

from hashlab.hashing.sha256 import SHA256Engine
from hashlab.hashing.sha256d import SHA256dEngine
from hashlab.hashing.target import (
    Target,
    digest_to_int,
    is_success,
    leading_zero_bits,
)

ENGINES = {
    SHA256Engine.name: SHA256Engine,
    SHA256dEngine.name: SHA256dEngine,
}


def get_engine(name: str):
    """Return an engine instance by name ("sha256" or "sha256d")."""
    try:
        return ENGINES[name]()
    except KeyError:
        raise ValueError(f"unknown engine {name!r}; expected one of {sorted(ENGINES)}") from None


__all__ = [
    "ENGINES",
    "SHA256Engine",
    "SHA256dEngine",
    "Target",
    "digest_to_int",
    "get_engine",
    "is_success",
    "leading_zero_bits",
]
