"""Predeclared economic reference and domain comparability (pure; no hashing).

The economic reference generator is named in the configuration
(``economics.reference_generator``) BEFORE any data is collected. It is never
chosen from observed throughput. Comparability is decided from the configured
generator domains alone, so it is also fixed before execution and recorded in
the plan (and therefore in the plan fingerprint).

Two generators are *comparable* only if their candidate domains are identical:
same kind (bytes vs ASCII characters), same width in bytes (so the same hash
input length), same alphabet and the same exact cardinality. A subset domain
(for example repeated-byte patterns inside the 8-byte space) is NOT
comparable: it can be exhausted and does not describe the same search space.

Economic comparisons are exploratory in this harness. Throughput is a single
measurement of a Python implementation on one machine, with no uncertainty
model, so no economic comparison is confirmatory.
"""

from __future__ import annotations

from hashlab.candidates import build_generator

#: Domain fields that must all match for two generators to be economically comparable.
COMPARABILITY_FIELDS = ("kind", "width_bytes", "alphabet", "alphabet_size", "cardinality")

STATUS_REFERENCE = "reference"
STATUS_COMPARABLE = "comparable"
STATUS_NOT_COMPARABLE = "not-comparable"
STATUS_NO_REFERENCE = "no-reference"

EVIDENCE_LEVEL = "exploratory"


def reference_generator(resolved: dict) -> str | None:
    """The predeclared reference id, or None (old configs have no ``economics`` section)."""
    return (resolved.get("economics") or {}).get("reference_generator")


def comparability_table(resolved: dict) -> dict:
    """Per generator: comparability with the predeclared reference, from configured domains only."""
    reference = reference_generator(resolved)
    domains = {spec["id"]: build_generator(spec).domain().to_dict() for spec in resolved["generators"]}
    table: dict = {}
    for gid, domain in domains.items():
        if reference is None or reference not in domains:
            status, differences = STATUS_NO_REFERENCE, []
        elif gid == reference:
            status, differences = STATUS_REFERENCE, []
        else:
            differences = [f for f in COMPARABILITY_FIELDS if domain.get(f) != domains[reference].get(f)]
            status = STATUS_NOT_COMPARABLE if differences else STATUS_COMPARABLE
        table[gid] = {"status": status, "reference": reference, "domain_differences": differences}
    return table


def is_comparable(status: str) -> bool:
    return status in (STATUS_REFERENCE, STATUS_COMPARABLE)


__all__ = [
    "COMPARABILITY_FIELDS",
    "EVIDENCE_LEVEL",
    "STATUS_COMPARABLE",
    "STATUS_NOT_COMPARABLE",
    "STATUS_NO_REFERENCE",
    "STATUS_REFERENCE",
    "comparability_table",
    "is_comparable",
    "reference_generator",
]
