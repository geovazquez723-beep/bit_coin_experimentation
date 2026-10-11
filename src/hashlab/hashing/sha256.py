"""Baseline single SHA-256 engine (hashlib)."""

from __future__ import annotations

import hashlib


class SHA256Engine:
    """SHA-256 of the raw candidate bytes: H(x)."""

    name = "sha256"
    digest_size = 32

    def digest(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def describe(self) -> dict:
        return {
            "name": self.name,
            "definition": "hashlib.sha256(candidate_bytes).digest()",
            "digest_bits": 256,
            "byte_order_for_comparison": "big-endian",
        }
