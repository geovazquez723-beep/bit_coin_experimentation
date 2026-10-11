"""HASHLAB: reproducible research harness for SHA-256 proof-of-work search.

Working assumption (the null hypothesis): for distinct inputs, SHA-256 outputs
behave like uniformly distributed pseudorandom 256-bit values. Nothing in this
package claims or assumes otherwise. It measures and tests that assumption.
"""

__version__ = "0.1.0"

DIGEST_BITS = 256
HASH_SPACE = 1 << DIGEST_BITS  # number of distinct 256-bit digests
