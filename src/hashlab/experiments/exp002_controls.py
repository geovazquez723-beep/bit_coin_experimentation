"""Approved I2 deterministic controls. Providers only; no research dispatcher.

Production geometry is immutable. Small geometry requires the fixture domain.
Complete retained occurrences are read, never regenerated or candidate-hashed.
"""
from dataclasses import dataclass
from fractions import Fraction
from hashlib import blake2b
from pathlib import Path
import struct

from hashlab.candidates.base import derive_seed
from hashlab.hashing.sha256 import SHA256Engine
from .exp002 import integer, in_a1, in_a3, validate_prefixes
from .exp002_foundation import CandidateRecord
from .exp002_s14 import load_s14, S14_FILES

TARGET = 2**248
N1_STOP = 30_999_999  # exclusive, Director clarification
P_START = 2**63
ROUND_LABEL = b'hashlab-exp002-feistel-round-v1'
DOMAINS = ('experiment-002', 'experiment-002-kat')
OCCURRENCE = struct.Struct('>BBII8sB')


def control_keys(master, domain):
    integer(master, 0, 2**64-1)
    if domain not in DOMAINS:
        raise ValueError('control seed domain')
    n = derive_seed(master, domain, 'N1-feistel64-w8', 'permutation-key-v1')
    two = derive_seed(master, domain, 'N2-random-bytes-w80', 'stream-key-v1')
    return n.to_bytes(8, 'little'), two.to_bytes(16, 'big')


class Feistel64:
    def __init__(self, key):
        if type(key) is not bytes or len(key) != 8:
            raise ValueError('Feistel eight-byte key')
        self.key = key

    def round_function(self, round_number, right):
        integer(round_number, 0, 5)
        integer(right, 0, 2**32-1)
        msg = ROUND_LABEL + bytes([round_number]) + right.to_bytes(4, 'big')
        return int.from_bytes(blake2b(msg, key=self.key, digest_size=64).digest()[:4], 'big')

    def forward(self, source):
        integer(source, 0, 2**64-1)
        left, right = source >> 32, source & 0xffffffff
        for r in range(6):
            left, right = right, left ^ self.round_function(r, right)
        return (left << 32) | right

    def inverse(self, value):
        integer(value, 0, 2**64-1)
        left, right = value >> 32, value & 0xffffffff
        for r in range(5, -1, -1):
            left, right = right ^ self.round_function(r, left), left
        return (left << 32) | right


@dataclass(frozen=True)
class InverseHistory:
    indices: frozenset
    occurrences: int
    identity: dict
    permutation_key: bytes

    def summary(self):
        return dict(self.identity, historical_occurrences=self.occurrences,
                    distinct_inverse_skip_indices=len(self.indices),
                    complete_occurrence_evidence=True,
                    permutation_key_hex=self.permutation_key.hex())


def inverse_history(permutation, candidates, *, identity=None):
    """All supplied occurrences, including duplicates, map through the inverse.

    Intended for retained complete data or explicit unit fixtures. No A3 filter.
    In-memory index resource qualification at production scale remains separate.
    """
    indices, count = set(), 0
    for raw in candidates:
        if type(raw) is not bytes or len(raw) != 8:
            raise ValueError('historical eight-byte occurrence required')
        indices.add(permutation.inverse(int.from_bytes(raw, 'big')))
        count += 1
    return InverseHistory(frozenset(indices), count, dict(identity or {}), permutation.key)


def retained_candidates(path, plan):
    """Validate retained ordering/shape while reading; never call a generator."""
    with Path(path).open('rb') as source:
        for stream in plan['streams']:
            for i in range(stream['attempts']):
                raw = source.read(OCCURRENCE.size)
                if len(raw) != OCCURRENCE.size:
                    raise ValueError('truncated historical occurrences')
                ordinal, phase, attempted, enum, candidate, outcome = OCCURRENCE.unpack(raw)
                if ((ordinal, phase, attempted, enum) !=
                        (stream['ordinal'], stream['phase'], i, stream['start_index']+i)
                        or outcome != 0):
                    raise ValueError('retained historical occurrence semantics')
                yield candidate
        if source.read(1):
            raise ValueError('extra historical occurrences')


# Authentication is repeated before cache lookup; a changed retained file fails
# its accepted pin. Cache contains immutable fixture-key inverse indices only.
_FIXTURE_HISTORY_CACHE = {}


def load_control_history(audit_root, repository_root, permutation):
    verified = load_s14(audit_root, repository_root)
    from .e001_reconstruction import strict_json
    path = Path(audit_root)/'producer/occurrences.bin'
    plan = strict_json((Path(audit_root)/'producer/plan.json').read_bytes())
    identity = verified.identity() | dict(occurrences_sha256=S14_FILES['producer/occurrences.bin'][1])
    fixture_key = control_keys(0, 'experiment-002-kat')[0]
    cached = _FIXTURE_HISTORY_CACHE.get(permutation.key) if permutation.key == fixture_key else None
    if cached is not None:
        return cached
    result = inverse_history(permutation, retained_candidates(path, plan), identity=identity)
    if result.occurrences != 7_000_000:
        raise ValueError('complete historical occurrence count required')
    if permutation.key == fixture_key:
        _FIXTURE_HISTORY_CACHE[permutation.key] = result
    return result


@dataclass(frozen=True)
class ControlGeometry:
    domain: str = 'experiment-002'
    per_stage: int = 15_000_000
    p1: int = 200_000
    p2: int = 15_000_000

    def __post_init__(self):
        if self.domain not in DOMAINS:
            raise ValueError('control geometry domain')
        for value, maximum in ((self.per_stage, 15_000_000), (self.p1, 200_000), (self.p2, 15_000_000)):
            integer(value, 1, maximum)
        if self.domain == 'experiment-002' and (self.per_stage, self.p1, self.p2) != (15_000_000, 200_000, 15_000_000):
            raise ValueError('frozen production control geometry')
        if self.domain == 'experiment-002-kat' and max(self.per_stage, self.p1, self.p2) > 10_000:
            raise ValueError('engineering geometry cap')


def rejection_counts():
    return dict(attempted=0, rejected=0, accepted=0, reasons=dict(C1=0, C3=0, E001=0, A2=0))


class PermutationControls:
    """Single-use ascending N1 and shared P cursors; every attempt is auditable."""
    def __init__(self, permutation, history, geometry=ControlGeometry()):
        if type(permutation) is not Feistel64 or type(history) is not InverseHistory or type(geometry) is not ControlGeometry:
            raise ValueError('typed control inputs required')
        if history.permutation_key != permutation.key:
            raise ValueError('historical inverse index uses a different permutation')
        if geometry.domain == 'experiment-002' and (history.occurrences != 7_000_000 or
                history.identity.get('occurrences_sha256') != S14_FILES['producer/occurrences.bin'][1]):
            raise ValueError('production controls require complete authenticated history')
        self.permutation, self.history, self.geometry = permutation, history, geometry
        self.counts = {a: rejection_counts() for a in ('N1', 'P1', 'P2+', 'P2-')}
        self.n1_cursor, self.p_cursor = 0, P_START
        self._used = set()
        self.failed = False

    def _stream(self, specs, positive):
        kind = 'P' if positive else 'N1'
        if self.failed or kind in self._used:
            raise RuntimeError('control provider unavailable')
        self._used.add(kind)
        try:
            for arm, stage, quota in specs:
                accepted = 0
                while accepted < quota:
                    source = self.p_cursor if positive else self.n1_cursor
                    if source >= (2**64 if positive else N1_STOP):
                        raise ValueError('control source-index exhaustion')
                    if positive:
                        self.p_cursor += 1
                    else:
                        self.n1_cursor += 1
                    raw = self.permutation.forward(source).to_bytes(8, 'big')
                    reasons = [name for name, hit in (('C1', in_a1(raw)), ('C3', in_a3(raw)),
                                ('E001', source in self.history.indices)) if hit]
                    counts = self.counts[arm]
                    counts['attempted'] += 1
                    for reason in reasons:
                        counts['reasons'][reason] += 1
                    counts['rejected' if reasons else 'accepted'] += 1
                    row = dict(arm=arm, stage=stage, source_index=source, candidate_hex=raw.hex(),
                               accepted_index=None if reasons else accepted, reasons=reasons)
                    if not reasons:
                        accepted += 1
                    yield row
        except BaseException:
            self.failed = True
            raise

    def n1(self):
        return self._stream([('N1', s, self.geometry.per_stage) for s in ('D', 'V')], False)

    def positives(self):
        g = self.geometry
        return self._stream([('P1', 'C', g.p1), ('P2+', 'C', g.p2), ('P2-', 'C', g.p2)], True)


class ByteStream80:
    def __init__(self, key, *, start_raw_index=0):
        if type(key) is not bytes or len(key) != 16:
            raise ValueError('N2 sixteen-byte key')
        integer(start_raw_index, 0, (64*2**128)//80-1)
        self.key, self.raw_index = key, start_raw_index
        self._counter, self._skip = divmod(80*start_raw_index, 64)
        self._buffer = b''

    def block(self, counter):
        integer(counter, 0, 2**128-1)
        return blake2b(counter.to_bytes(16, 'big'), key=self.key, digest_size=64).digest()

    def next(self):
        offset = 80*self.raw_index
        if offset+80 > 64*2**128:
            raise ValueError('N2 counter exhaustion')
        while len(self._buffer) < 80:
            block = self.block(self._counter)
            self._counter += 1
            self._buffer += block[self._skip:]
            self._skip = 0
        raw, self._buffer = self._buffer[:80], self._buffer[80:]
        self.raw_index += 1
        return raw


def n2_assignment(accepted, per_stage=15_000_000):
    integer(per_stage, 1, 15_000_000)
    integer(accepted, 0, 2*per_stage-1)
    stage = 'D' if accepted < per_stage else 'V'
    local = accepted % per_stage
    # Fixtures retain the accepted E3 stage-local cluster contract.
    return stage, local, local//10000 + (1500 if stage == 'V' else 0)


class N2Controls:
    def __init__(self, key, prefixes, geometry=ControlGeometry()):
        if type(geometry) is not ControlGeometry:
            raise ValueError('typed N2 geometry')
        validate_prefixes(prefixes, 3000)
        self.prefixes, self.geometry = frozenset(prefixes), geometry
        self.stream = ByteStream80(key)
        self.counts = rejection_counts()
        self._used = False
        self.failed = False

    def attempts(self):
        if self._used or self.failed:
            raise RuntimeError('N2 provider unavailable')
        self._used = True
        accepted = 0
        try:
            while accepted < 2*self.geometry.per_stage:
                raw_index = self.stream.raw_index
                raw = self.stream.next()
                hit = raw[:76] in self.prefixes and int.from_bytes(raw[76:], 'little') < 10000
                stage, local, cluster = n2_assignment(accepted, self.geometry.per_stage)
                self.counts['attempted'] += 1
                self.counts['rejected' if hit else 'accepted'] += 1
                self.counts['reasons']['A2'] += int(hit)
                row = dict(arm='N2', stage=stage, raw_index=raw_index, byte_offset=80*raw_index,
                           candidate_hex=raw.hex(), accepted_index=None if hit else local,
                           cluster=None if hit else cluster, reasons=['A2'] if hit else [])
                if not hit:
                    accepted += 1
                yield row
        except BaseException:
            self.failed = True
            raise


def accepted_record(attempt):
    if attempt['reasons'] or attempt['accepted_index'] is None:
        raise ValueError('rejected attempt has no candidate record')
    return CandidateRecord(attempt['arm'], attempt['stage'], attempt['accepted_index'],
                           attempt['candidate_hex'], attempt.get('cluster'))


class ControlEngine:
    """Exactly one base evaluation, retaining both raw and effective digests.

    Existing generic BiasedControlEngine and its public API stay unchanged.
    """
    def __init__(self, mode, base=None):
        if mode not in ('N1', 'N2', 'P1', 'P2+', 'P2-'):
            raise ValueError('control digest mode')
        self.mode = mode
        self.base = SHA256Engine() if base is None else base
        self.threshold = {'N1': 0, 'N2': 0, 'P1': (2**32)//1020,
                          'P2+': (2**32)//12750, 'P2-': (2**32)//50}[mode]

    @property
    def expected_probability(self):
        fraction = Fraction(self.threshold, 2**32)
        return (Fraction(1, 256)*(1-fraction) if self.mode == 'P2-' else
                Fraction(1, 256)+Fraction(255, 256)*fraction)

    def transform(self, raw):
        if type(raw) is not bytes or len(raw) != 32:
            raise ValueError('32-byte base digest required')
        value, selector = int.from_bytes(raw, 'big'), int.from_bytes(raw[-4:], 'big')
        transformed = False
        effective = value
        if self.mode == 'P2-' and value < TARGET and selector < self.threshold:
            effective, transformed = value+TARGET, True
        elif self.mode in ('P1', 'P2+') and value >= TARGET and selector < self.threshold:
            effective, transformed = value % TARGET, True
        return dict(mode=self.mode, threshold_u32=self.threshold, transformed=transformed,
                    raw_digest_hex=raw.hex(), effective_digest_hex=effective.to_bytes(32, 'big').hex(),
                    success=effective < TARGET)

    def evaluate(self, candidate):
        return self.transform(self.base.digest(candidate))
