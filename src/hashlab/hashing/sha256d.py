"""Double SHA-256 engine: SHA256(SHA256(x)).

Note: Bitcoin displays block hashes byte-reversed and compares them as
little-endian integers. HASHLAB does NOT do that. Every engine's digest is read
as a big-endian unsigned integer, so success means the same thing for every
engine. Real block-header mining is out of scope.
"""

from __future__ import annotations

import hashlib


class SHA256dEngine:
    """Double SHA-256 of the raw candidate bytes: H(H(x))."""

    name = "sha256d"
    digest_size = 32

    def digest(self, data: bytes) -> bytes:
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()

    def describe(self) -> dict:
        return {
            "name": self.name,
            "definition": "hashlib.sha256(hashlib.sha256(candidate_bytes).digest()).digest()",
            "digest_bits": 256,
            "byte_order_for_comparison": "big-endian (NOT Bitcoin's reversed display order)",
        }
