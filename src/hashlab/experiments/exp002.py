"""Experiment 002 E1 foundations. No hashing, execution or seed selection.

Sampling uses Vitter Algorithm D for A1 and integer Algorithm S for A3,
followed by a hypergeometric stage split. Confirmatory orchestration is
deliberately unavailable in E1. Approved seed-derivation interfaces are pure;
sampling primitives also accept explicit engineering sub-seeds.
"""

from dataclasses import dataclass, asdict
from hashlib import blake2b, sha256
from math import comb
import random
import re
from datetime import datetime
from collections.abc import Iterator, Mapping, Sequence
from types import MappingProxyType

from hashlab.candidates.base import derive_seed
from hashlab.candidates.vitter import a1_sample_ranks

ENCODING = "hashlab-exp002-a2-encoding-v1"
ARM_SEED_ENCODING = "hashlab-exp002-a1-a3-subseed-encoding-v1"
PROTOCOL_IDENTITY = f"proposal-revision-8|{ENCODING}|{ARM_SEED_ENCODING}"
_ARM_SEED_LABELS = MappingProxyType({"A1": "A1-lowint-w8", "A3": "A3-lowhw-w8"})
_SEED_PURPOSE_LABELS = MappingProxyType({
    "selection": "selection-v1", "stage-allocation": "stage-allocation-v1",
})
A1_SIZE = 2**32 - 2**20
A3_CLASS_SIZE = 82_128_984
A3_SIZE = 82_068_263
EXCLUSION_DIGEST = "7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c"


def integer(value: int, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"expected integer in [{low}, {high}]")
    return value


def le32(value: int) -> bytes:
    return integer(value, 0, 2**32 - 1).to_bytes(4, "little")


@dataclass(frozen=True)
class Config:
    schema: str = "hashlab-exp002-config-v1"
    proposal_revision: int = 8
    a2_encoding: str = ENCODING
    a1_a3_seed_encoding: str = ARM_SEED_ENCODING
    protocol_identity: str = PROTOCOL_IDENTITY
    engine: str = "sha256"
    target: int = 2**248
    per_stage: int = 15_000_000
    prefixes: int = 3000
    nonces: int = 10_000
    a1_population: int = A1_SIZE
    a3_population: int = A3_SIZE
    a3_exclusion_sha256: str = EXCLUSION_DIGEST
    seed_derivation: str = "hashlab-seed-v1"
    alpha_difference: str = "0.005"
    alpha_margin: str = "0.005"
    relative_margin: str = "0.02"
    a2_t_df: int = 2999
    a2_t_critical: str = "2.9376"
    within_low_count: int = 115839
    within_high_count: int = 118519
    beyond_low_count: int = 113851
    beyond_high_count: int = 120546
    master: str = "derived-from-beacon"

    def __post_init__(self):
        # No geometry overrides or confirmatory seeds accepted in this seedless schema.
        for name, field in self.__dataclass_fields__.items():
            value = getattr(self, name)
            if type(value) is not type(field.default) or value != field.default:
                raise ValueError(f"frozen configuration field: {name}")

    @classmethod
    def from_mapping(cls, data: Mapping):
        if not isinstance(data, Mapping) or set(data) != set(cls.__dataclass_fields__):
            raise ValueError("configuration must contain exactly the versioned fields")
        return cls(**data)

    def to_dict(self):
        return asdict(self)


def a1_value(rank: int) -> bytes:
    return (2**20 + integer(rank, 0, A1_SIZE - 1)).to_bytes(8, "big")


def in_a1(candidate: bytes) -> bool:
    return type(candidate) is bytes and len(candidate) == 8 and 2**20 <= int.from_bytes(candidate, "big") < 2**32


def in_a3(candidate: bytes) -> bool:
    if type(candidate) is not bytes or len(candidate) != 8:
        return False
    value = int.from_bytes(candidate, "big")
    return value >> 32 != 0 and value.bit_count() <= 6


@dataclass(frozen=True)
class HammingPopulation:
    """Weight then colex enumeration, omitting subsets wholly below split.

    Alternate geometry is solely for small engineering fixtures.
    """
    bits: int = 64
    split: int = 32
    weight: int = 6

    def __post_init__(self):
        integer(self.bits, 2, 64)
        integer(self.split, 1, self.bits - 1)
        integer(self.weight, 1, self.bits)

    @property
    def size(self):
        return sum(comb(self.bits, w) - comb(self.split, w) for w in range(1, self.weight + 1))

    def unrank(self, rank: int) -> int:
        integer(rank, 0, self.size - 1)
        for w in range(1, self.weight + 1):
            count = comb(self.bits, w) - comb(self.split, w)
            if rank < count:
                break
            rank -= count
        # All-low subsets form the initial colex segment for each weight.
        rank += comb(self.split, w)
        value, upper = 0, self.bits - 1
        for k in range(w, 0, -1):
            while comb(upper, k) > rank:
                upper -= 1
            value |= 1 << upper
            rank -= comb(upper, k)
            upper -= 1
        return value

    def rank(self, value: int) -> int:
        integer(value, 0, 2**self.bits - 1)
        w = value.bit_count()
        if not 1 <= w <= self.weight or value >> self.split == 0:
            raise ValueError("outside Hamming population")
        positions = [i for i in range(self.bits) if value & (1 << i)]
        return (sum(comb(self.bits, k) - comb(self.split, k) for k in range(1, w))
                + sum(comb(p, k) for k, p in enumerate(positions, 1)) - comb(self.split, w))


@dataclass(frozen=True)
class Exclusions:
    """Validated immutable exclusion ranks; memory O(exclusion count), not sample size."""
    ranks: tuple[int, ...]
    population: HammingPopulation

    def __post_init__(self):
        if not isinstance(self.population, HammingPopulation):
            raise ValueError("exclusions require a Hamming population")
        if type(self.ranks) is not tuple:
            raise ValueError("exclusion ranks must be an immutable tuple")
        previous = -1
        for rank in self.ranks:
            integer(rank, 0, self.population.size - 1)
            if rank <= previous:
                raise ValueError("exclusions must be strictly increasing")
            previous = rank

    def verify_protocol(self):
        if self.population != HammingPopulation() or len(self.ranks) != 60_721:
            raise ValueError("wrong production exclusion geometry/count")
        digest = sha256()
        # Digest contract sorts values numerically, not by weight/colex rank.
        for value in sorted(self.population.unrank(r) for r in self.ranks):
            digest.update(value.to_bytes(8, "big"))
        if digest.hexdigest() != EXCLUSION_DIGEST:
            raise ValueError("wrong production exclusion digest")


def sample_ranks(size: int, discovery: int, validation: int, *,
                 selection_seed: int, stage_seed: int,
                 excluded: tuple[int, ...] = ()) -> Iterator[tuple[str, int]]:
    """Reference Algorithm S; O(size) time, O(1) extra memory.

    Each yielded rank is unique. Exclusions must already be sorted and exact.
    RNG instances are local; stage draws cannot perturb selection draws.
    """
    integer(size, 1, 2**64)
    integer(discovery, 0, size)
    integer(validation, 0, size)
    integer(selection_seed, 0, 2**64 - 1)
    integer(stage_seed, 0, 2**64 - 1)
    if type(excluded) is not tuple:
        raise ValueError("excluded must be an immutable sorted tuple")
    previous = -1
    for rank in excluded:
        integer(rank, 0, size - 1)
        if rank <= previous:
            raise ValueError("duplicate or unsorted exclusion")
        previous = rank
    remaining = size - len(excluded)
    need = discovery + validation
    if need > remaining:
        raise ValueError("sample exceeds eligible population")
    select, stages = random.Random(selection_seed), random.Random(stage_seed)
    exclusion_index = 0
    for rank in range(size):
        if not need:
            break
        if exclusion_index < len(excluded) and rank == excluded[exclusion_index]:
            exclusion_index += 1
            continue
        if select.randrange(remaining) < need:
            stage = "D" if stages.randrange(need) < discovery else "V"
            if stage == "D":
                discovery -= 1
            need -= 1
            yield stage, rank
        remaining -= 1


def a2_key(master: int, domain: str) -> bytes:
    integer(master, 0, 2**64 - 1)
    if domain not in ("experiment-002", "experiment-002-qa2", "experiment-002-kat"):
        raise ValueError("unknown A2 seed domain")
    return derive_seed(master, domain, "A2-prefix-nonce-w80", "prefix-key-v1").to_bytes(8, "little")


def arm_seed_labels(arm: str, purpose: str) -> tuple[str, str, str]:
    """Architecture Review 027's approved, immutable A1/A3 label contract."""
    if type(arm) is not str or arm not in _ARM_SEED_LABELS:
        raise ValueError("arm seed requires A1 or A3")
    if type(purpose) is not str or purpose not in _SEED_PURPOSE_LABELS:
        raise ValueError("seed purpose requires selection or stage-allocation")
    return "experiment-002", _ARM_SEED_LABELS[arm], _SEED_PURPOSE_LABELS[purpose]


def arm_seed_material(master: int, arm: str, purpose: str) -> bytes:
    """Exact approved ASCII derivation message; no master selection occurs."""
    integer(master, 0, 2**64-1)
    labels = arm_seed_labels(arm, purpose)
    return ("hashlab-seed-v1|" + str(master) + "|" + "|".join(labels)).encode("ascii")


def arm_subseed(master: int, arm: str, purpose: str) -> int:
    """Production derivation binding. Preserve the existing hashlab-seed-v1.

    Returns the integer passed to a local MT19937 instance, not an A2 LE key.
    Caller-supplied master must already satisfy the later commitment procedure.
    """
    integer(master, 0, 2**64-1)
    return derive_seed(master, *arm_seed_labels(arm, purpose))


def engineering_arm_stream(arm: str, size: int, discovery: int, validation: int, *,
                           selection_seed: int, stage_seed: int,
                           exclusions: Exclusions | None = None):
    """Small fixture adapter. Not a confirmatory plan or execution entry point.

    A3 exclusions are mandatory, including an explicitly empty fixture set.
    """
    if arm == "A1":
        integer(size, 1, A1_SIZE)
        if exclusions is not None:
            raise ValueError("A1 has no exclusions")
        excluded = ()
        encode = a1_value
    elif arm == "A3" and isinstance(exclusions, Exclusions):
        if size != exclusions.population.size:
            raise ValueError("wrong A3 population size")
        excluded = exclusions.ranks
        encode = lambda rank: exclusions.population.unrank(rank).to_bytes(8, "big")
    else:
        raise ValueError("unknown arm or missing A3 exclusions")
    if arm == "A1":
        rows = a1_sample_ranks(size, discovery, validation,
                              selection_seed=selection_seed, stage_seed=stage_seed)
    else:
        rows = sample_ranks(size, discovery, validation,
                           selection_seed=selection_seed, stage_seed=stage_seed, excluded=excluded)
    for stage, rank in rows:
        yield stage, encode(rank)


def a2_prefix(key: bytes, index: int) -> bytes:
    if type(key) is not bytes or len(key) != 8:
        raise ValueError("A2 key must be eight raw bytes")
    integer(index, 0, 2999)
    message = b"hashlab-exp002-prefix" + le32(index)
    return (blake2b(message + le32(0), key=key).digest()
            + blake2b(message + le32(1), key=key).digest()[:12])


def validate_prefixes(prefixes: Sequence[bytes], expected: int):
    integer(expected, 1, 3000)
    if len(prefixes) != expected or any(type(p) is not bytes or len(p) != 76 for p in prefixes):
        raise ValueError("wrong prefix geometry")
    if len(set(prefixes)) != expected:
        raise ValueError("prefix collision: halt; no redraw")


def a2_candidate(prefix: bytes, nonce: int) -> bytes:
    if type(prefix) is not bytes or len(prefix) != 76:
        raise ValueError("wrong prefix length")
    return prefix + le32(integer(nonce, 0, 9999))


def a2_stage(index: int) -> str:
    return "D" if integer(index, 0, 2999) < 1500 else "V"


def a2_stream(prefixes: tuple[bytes, ...]) -> Iterator[tuple[str, int, int, bytes]]:
    if type(prefixes) is not tuple:
        raise ValueError("prefixes must be immutable")
    validate_prefixes(prefixes, 3000)
    for index, prefix in enumerate(prefixes):
        for nonce in range(10_000):
            yield a2_stage(index), index, nonce, a2_candidate(prefix, nonce)


def audit_e001(candidates: Iterator[bytes], exclusions: Exclusions, expected_count: int):
    """Read-only plan audit interface; no E001 enumeration is performed by E1.

    Caller supplies reconstructed E001 candidates. Audit validates the exact
    distinct A3 intersection and fails on any A1 hit. No candidate hashing.
    """
    integer(expected_count, 0, 7_000_000)
    found, count = set(), 0
    for candidate in candidates:
        if type(candidate) is not bytes or len(candidate) != 8:
            raise ValueError("expected E001 eight-byte stream")
        count += 1
        if count > expected_count or in_a1(candidate):
            raise ValueError("E001 count or A1 overlap violation")
        if in_a3(candidate):
            found.add(exclusions.population.rank(int.from_bytes(candidate, "big")))
            if len(found) > len(exclusions.ranks):
                raise ValueError("unexpected A3 exclusion")
    if count != expected_count or found != set(exclusions.ranks):
        raise ValueError("incomplete E001 exclusion audit")


@dataclass(frozen=True)
class SeedCommitment:
    """Seedless binding interface. Does not choose a round or derive a seed."""
    code_commit: str
    configuration_sha256: str
    seedless_plan_sha256: str
    exclusion_sha256: str = EXCLUSION_DIGEST

    def __post_init__(self):
        for value, length in ((self.code_commit, 40), (self.configuration_sha256, 64),
                              (self.seedless_plan_sha256, 64), (self.exclusion_sha256, 64)):
            if type(value) is not str or len(value) != length or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("invalid commitment digest")
        if self.exclusion_sha256 != EXCLUSION_DIGEST:
            raise ValueError("wrong exclusion commitment")


@dataclass(frozen=True)
class RegistryRecord:
    """Required started/result evidence binding; no registry file is written."""
    entry_id: str
    utc: str
    code_commit: str
    configuration_sha256: str
    plan_sha256: str
    command: str
    phase: str = "started"
    run_id: str | None = None
    status: str | None = None
    failure_class: str | None = None
    manifest_sha256: str | None = None

    def __post_init__(self):
        if type(self.entry_id) is not str or not re.fullmatch(r"[SQA][1-9][0-9]*", self.entry_id):
            raise ValueError("invalid entry id")
        if type(self.utc) is not str or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", self.utc):
            raise ValueError("timestamp must be UTC")
        try:
            datetime.fromisoformat(self.utc[:-1] + '+00:00')
        except ValueError as exc:
            raise ValueError("invalid timestamp") from exc
        SeedCommitment(self.code_commit, self.configuration_sha256, self.plan_sha256)
        if type(self.command) is not str or not self.command.strip():
            raise ValueError("exact command required")
        if self.phase == "started":
            if any(v is not None for v in (self.run_id, self.status, self.failure_class, self.manifest_sha256)):
                raise ValueError("started record cannot contain results")
        elif self.phase == "result":
            if type(self.run_id) is not str or not self.run_id or type(self.status) is not str or not self.status:
                raise ValueError("result requires run id and status")
            if self.failure_class not in ("valid", "F1", "F2", "F3", "F4"):
                raise ValueError("result requires failure class or valid")
            if self.failure_class == "valid" and self.status != "complete":
                raise ValueError("valid result must be complete")
            if self.failure_class == "F2" and self.status == "complete":
                raise ValueError("F2 result must be incomplete")
            if self.manifest_sha256 is None and self.failure_class == "F1":
                return  # Unsealed crash; absence is explicit, never a fabricated manifest.
            digest = self.manifest_sha256
            if type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise ValueError("sealed result requires manifest digest")
        else:
            raise ValueError("unknown registry record phase")


@dataclass(frozen=True)
class RegistryState:
    """Pure append-only transition interface; persistence/governance remain later gates."""
    entries: tuple[str, ...] = ()
    precommitted: bool = False
    seed_committed: bool = False
    final: bool = False

    def __post_init__(self):
        if type(self.entries) is not tuple or any(type(v) is not bool for v in
                (self.precommitted, self.seed_committed, self.final)):
            raise ValueError("invalid registry state")
        if self.seed_committed and not self.precommitted:
            raise ValueError("seed record requires precommitment")
        counters = dict(S=0, Q=0, A=0)
        for entry in self.entries:
            if type(entry) is not str or not entry or entry[0] not in counters:
                raise ValueError("invalid registry id")
            counters[entry[0]] += 1
            if entry != f"{entry[0]}{counters[entry[0]]}":
                raise ValueError("registry numbering gap/duplicate")
        if counters['A'] and not self.seed_committed:
            raise ValueError("attempt requires seed record")

    def append(self, kind: str, *, approved_amendment: bool = False):
        if type(approved_amendment) is not bool or kind not in ("S", "Q", "A") or self.final:
            raise ValueError("registry transition forbidden")
        if kind == "A" and not self.seed_committed:
            raise ValueError("attempt requires committed seed record")
        if self.precommitted and (kind == "S" or (kind == "Q" and not approved_amendment)):
            raise ValueError("post-commit qualification requires approved amendment")
        number = 1 + sum(e.startswith(kind) for e in self.entries)
        return RegistryState(self.entries + (f"{kind}{number}",), self.precommitted, self.seed_committed, self.final)
