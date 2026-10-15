"""Independent full-domain E002 candidate reconstruction. No HASHLAB imports.

Separately specified from the producer samplers/control providers/accumulator:

* A1: Vitter Algorithm D over the full A1 population using exact-decision
  interval arithmetic (outward-rounded binary mantissa/exponent bounds), the
  producer-specified lazy 64-bit MT19937 uniform, and hypergeometric-style
  stage allocation. No ``decimal`` module and no producer code is used.
* A2: all derived prefixes and nonce blocks.
* A3: Algorithm S with exact exclusions; ranks are enumerated incrementally in
  weight/colex order (Gosper) instead of unranking each accepted rank.
* N1/P: six-round Feistel, shared ascending cursors, structural and historical
  exclusions by retained-value membership (the permutation is a bijection).
* N2: continuous 80-byte keyed stream with complete A2 rejection.

The only shared dependencies are CPython ``random`` (MT19937), ``hashlib`` and
the accepted independent S1.4/E001 loaders (``core``/``controls``). Interval
arithmetic certifies every comparison. Documented limitation: where the lazy
uniform's 2**-64 interval straddles a comparison boundary (probability about
2**-64 per comparison) the producer may refine along a different comparison
path; a verifier mismatch then fails closed and is never a false acceptance.
"""
from dataclasses import dataclass
from hashlib import blake2b, sha256
from math import comb, log, log1p
import random
import re
import struct

from .core import unrank as _colex_unrank
from e001_stream_verify.streaming import rank as _colex_rank

ARMS = ('A1', 'A2', 'A3', 'N1', 'N2', 'P1', 'P2+', 'P2-')
STAGES = ('D', 'V', 'C')
C1, C3, E001, A2R = 1, 2, 4, 8
TARGET = 1 << 248
A1_SIZE = 2**32 - 2**20
A3_CLASS_SIZE = 82_128_984
N1_STOP = 30_999_999
P_START = 1 << 63
THRESHOLDS = {'N1': 0, 'N2': 0, 'P1': 2**32 // 1020, 'P2+': 2**32 // 12750, 'P2-': 2**32 // 50}
DOMAINS = ('experiment-002', 'experiment-002-kat')
ROUND_LABEL = b'hashlab-exp002-feistel-round-v1'


class Mismatch(ValueError):
    """Independent reconstruction disagrees with, or cannot certify, evidence."""


# ----------------------------------------------------------------- geometry

@dataclass(frozen=True)
class Geometry:
    name: str
    domain: str
    a1_size: int
    a1_stage: int
    a2_nonces: int
    a2_clusters: tuple
    a3_size: int
    a3_stage: int
    control_stage: int
    p1: int
    p2: int

    def quotas(self):
        half = len([c for c in self.a2_clusters if c < 1500]) * self.a2_nonces
        other = len([c for c in self.a2_clusters if c >= 1500]) * self.a2_nonces
        q = {}
        for arm in ARMS:
            for stage in (('C',) if arm.startswith('P') else ('D', 'V')):
                q[arm, stage] = (
                    self.a1_stage if arm == 'A1' else half if arm == 'A2' and stage == 'D'
                    else other if arm == 'A2' else self.a3_stage if arm == 'A3'
                    else self.control_stage if arm in ('N1', 'N2')
                    else self.p1 if arm == 'P1' else self.p2)
        return q

    def evaluations(self):
        return sum(self.quotas().values())

    def blocks(self):
        return sum(n * (2 if a in ('A2', 'N2') else 1) for (a, _), n in self.quotas().items())


# Frozen production geometry, restated independently from the producer.
FROZEN = Geometry('production', 'experiment-002', A1_SIZE, 15_000_000, 10_000, tuple(range(3000)),
                  A3_CLASS_SIZE, 15_000_000, 15_000_000, 200_000, 15_000_000)
# Public engineering geometry. Never production evidence; production-domain
# keys are exercised separately by public vectors, not by this stream.
BOUNDED = Geometry('bounded-fixture', 'experiment-002-kat', A1_SIZE, 6, 8, (0, 1500),
                   4096, 6, 6, 2, 6)
GEOMETRIES = {g.name: g for g in (FROZEN, BOUNDED)}


# ------------------------------------------------------------ seed derivation

def master_from_beacon(precommit, round_number, randomness_hex):
    """Approved S4 conversion: ASCII message, SHA-256, first eight bytes, big-endian."""
    if (type(precommit) is not str or not re.fullmatch('[0-9a-f]{40}', precommit)
            or type(randomness_hex) is not str or not re.fullmatch('[0-9a-f]{64}', randomness_hex)
            or type(round_number) is not int or type(round_number) is bool
            or not 1 <= round_number < 2**64):
        raise ValueError('reference master inputs')
    message = f'hashlab-exp002-master-v1|{precommit}|{round_number}|{randomness_hex}'.encode('ascii')
    return int.from_bytes(sha256(message).digest()[:8], 'big')


def derive(master, *labels):
    if type(master) is not int or type(master) is bool or not 0 <= master < 2**64:
        raise ValueError('reference master range')
    material = '|'.join(['hashlab-seed-v1', str(master), *labels]).encode('utf-8')
    return int.from_bytes(sha256(material).digest()[:8], 'big')


def seeds(master, domain):
    """A1/A3 labels always use the approved 'experiment-002' label set; A2/N1/N2
    keys use the evidence domain (production or the engineering KAT domain)."""
    if domain not in DOMAINS:
        raise ValueError('reference seed domain')
    arm = 'experiment-002'
    return dict(
        a1=(derive(master, arm, 'A1-lowint-w8', 'selection-v1'),
            derive(master, arm, 'A1-lowint-w8', 'stage-allocation-v1')),
        a3=(derive(master, arm, 'A3-lowhw-w8', 'selection-v1'),
            derive(master, arm, 'A3-lowhw-w8', 'stage-allocation-v1')),
        a2_key=derive(master, domain, 'A2-prefix-nonce-w80', 'prefix-key-v1').to_bytes(8, 'little'),
        n1_key=derive(master, domain, 'N1-feistel64-w8', 'permutation-key-v1').to_bytes(8, 'little'),
        n2_key=derive(master, domain, 'N2-random-bytes-w80', 'stream-key-v1').to_bytes(16, 'big'))


# -------------------------------------------- certified interval arithmetic
# A value is (mantissa, exponent) meaning mantissa * 2**exponent. An interval
# is (lower, upper). All quantities are non-negative and all operations are
# monotone, so lower bounds use lower bounds and upper bounds use upper bounds.

P_MIN = 192


def _floor_to(m, e, p):
    s = m.bit_length() - p
    return (m >> s, e + s) if s > 0 else (m, e)


def _ceil_to(m, e, p):
    s = m.bit_length() - p
    return (-((-m) >> s), e + s) if s > 0 else (m, e)


def _ratio(a, b, p):
    if a == 0:
        return (0, 0), (0, 0)
    k = p + b.bit_length() - a.bit_length() + 1
    num, den = (a << k, b) if k >= 0 else (a, b << -k)
    q, r = divmod(num, den)
    return _floor_to(q, -k, p), _ceil_to(q + (r != 0), -k, p)


def _mul(x, y, p):
    return (_floor_to(x[0][0] * y[0][0], x[0][1] + y[0][1], p),
            _ceil_to(x[1][0] * y[1][0], x[1][1] + y[1][1], p))


def _quotient(n, d, p, up):
    if n[0] == 0:
        return (0, 0)
    if d[0] == 0:
        raise Mismatch('uncertifiable zero denominator')
    k = p + d[0].bit_length() - n[0].bit_length() + 1
    num, den = (n[0] << k, d[0]) if k >= 0 else (n[0], d[0] << -k)
    q, r = divmod(num, den)
    return (_ceil_to(q + (r != 0), n[1] - d[1] - k, p) if up
            else _floor_to(q, n[1] - d[1] - k, p))


def _div(x, y, p):
    return _quotient(x[0], y[1], p, False), _quotient(x[1], y[0], p, True)


def _power(x, s, p):
    result = ((1, 0), (1, 0))
    while s:
        if s & 1:
            result = _mul(result, x, p)
        s >>= 1
        if s:
            x = _mul(x, x, p)
    return result


def _compare(prefix, bits, m, e):
    """Sign of prefix/2**bits - m*2**e, without huge shifts."""
    if m == 0:
        return 1 if prefix else 0
    if prefix == 0:
        return -1
    lu, lp = prefix.bit_length() - bits, m.bit_length() + e
    if lu > lp + 1:
        return 1
    if lu < lp - 1:
        return -1
    t = e + bits
    left, right = (prefix, m << t) if t >= 0 else (prefix << -t, m)
    return (left > right) - (left < right)


class Uniform:
    """Lazy U in [prefix/2**bits, (prefix+1)/2**bits]; ties refine, never redraw."""

    def __init__(self, rng):
        self.rng, self.prefix, self.bits = rng, rng.getrandbits(64), 64

    def refine(self):
        if self.bits >= 4096:
            raise Mismatch('random interval unresolved after 4096 bits')
        self.prefix = (self.prefix << 64) | self.rng.getrandbits(64)
        self.bits += 64

    def less(self, make):
        """U < p, certified. ``make(precision)`` returns an enclosure of p."""
        while True:
            lower, upper = make(max(P_MIN, self.bits + 128))
            if _compare(self.prefix + 1, self.bits, *lower) < 0:
                return True
            if _compare(self.prefix, self.bits, *upper) > 0:
                return False
            self.refine()


def _survival(a, b, s):
    return lambda p: _power(_ratio(a, b, p), s, p)


def _acceptance(N, n, skip):
    def make(p):
        product = ((1, 0), (1, 0))
        if skip < n - 1:
            for i in range(skip):
                product = _mul(product, _ratio(N - n - i, N - 1 - i, p), p)
        else:
            for i in range(n - 1):
                product = _mul(product, _ratio(N - skip - 1 - i, N - 1 - i, p), p)
        return _div(product, _power(_ratio(N - n, N - 1, p), skip, p), p)
    return make


def _hint(N, n, uniform):
    try:
        shift = max(0, uniform.bits - 53)
        top = uniform.prefix >> shift
        midpoint = (2 * top + 1) / 2.0 ** (uniform.bits - shift + 1)
        return int(log(midpoint) / log1p(-(n - 1) / (N - 1)))
    except (ValueError, OverflowError, ZeroDivisionError):
        return -1


def _geometric_skip(N, n, rng):
    uniform = Uniform(rng)
    maximum = N - n

    def below(s):
        return uniform.less(lambda p: _power(_ratio(N - n, N - 1, p), s, p))

    if below(maximum + 1):
        return None
    hint = _hint(N, n, uniform)
    if 0 <= hint <= maximum and below(hint) and not below(hint + 1):
        return hint
    low, high = 0, maximum + 1
    while high - low > 1:
        middle = (low + high) // 2
        if below(middle):
            low = middle
        else:
            high = middle
    return low


def _method_a_skip(N, n, rng):
    uniform = Uniform(rng)
    state = [None, None]  # precision, running survival product

    def survival_at(skip):
        def make(p):
            if state[0] != p or state[1][0] != skip - 1:
                product = ((1, 0), (1, 0))
                for i in range(skip + 1):
                    product = _mul(product, _ratio(N - n - i, N - i, p), p)
            else:
                product = _mul(state[1][1], _ratio(N - n - skip, N - skip, p), p)
            state[0], state[1] = p, (skip, product)
            return product
        return make

    for skip in range(N - n + 1):
        if not uniform.less(survival_at(skip)):
            return skip
    raise Mismatch('Method A exhausted its legal support')


def _skip(N, n, rng):
    if n == N:
        return 0
    if n == 1:
        return rng.randrange(N)
    if 13 * n >= N:
        return _method_a_skip(N, n, rng)
    for _ in range(4096):
        skip = _geometric_skip(N, n, rng)
        if skip is None:
            continue
        uniform = Uniform(rng)
        if uniform.less(_survival(N - n - skip + 1, N - n, skip)):
            return skip
        if uniform.less(_acceptance(N, n, skip)):
            return skip
    raise Mismatch('Algorithm D rejection limit exceeded')


def vitter_ranks(size, count, seed):
    rng = random.Random(seed)
    N, n, offset = size, count, 0
    dense = False
    while n:
        dense = dense or 13 * n >= N
        skip = _method_a_skip(N, n, rng) if dense and 1 < n < N else _skip(N, n, rng)
        if not 0 <= skip <= N - n:
            raise Mismatch('skip outside legal support')
        rank = offset + skip
        yield rank
        offset = rank + 1
        N -= skip + 1
        n -= 1


def a1_ranks(size, discovery, validation, selection_seed, stage_seed):
    remaining = discovery + validation
    stages = random.Random(stage_seed)
    for rank in vitter_ranks(size, remaining, selection_seed):
        stage = 'D' if stages.randrange(remaining) < discovery else 'V'
        discovery -= stage == 'D'
        remaining -= 1
        yield stage, rank


# ------------------------------------------------------------------- A3 / A2

def colex_values(bits=64, split=32, weight=6):
    """Values ascending by weight then numeric order = colex rank order, with
    every subset wholly below ``split`` omitted (Gosper successor)."""
    for w in range(1, weight + 1):
        value = (1 << w) - 1 if (1 << w) - 1 >= 1 << split else (1 << split) | ((1 << (w - 1)) - 1)
        limit = 1 << bits
        while value < limit:
            yield value
            c = value & -value
            r = value + c
            value = (((r ^ value) >> 2) // c) | r


def class_size(bits=64, split=32, weight=6):
    return sum(comb(bits, w) - comb(split, w) for w in range(1, weight + 1))


def a3_ranks(size, discovery, validation, selection_seed, stage_seed, excluded):
    """Algorithm S with exclusions; yields (stage, rank, value)."""
    excluded = tuple(excluded)
    if list(excluded) != sorted(set(excluded)) or (excluded and (excluded[0] < 0 or excluded[-1] >= size)):
        raise Mismatch('exclusions must be strictly increasing ranks within the population')
    remaining, need = size - len(excluded), discovery + validation
    if need > remaining:
        raise Mismatch('sample exceeds eligible population')
    select, stages = random.Random(selection_seed), random.Random(stage_seed)
    values = colex_values()
    pointer = 0
    skipped = len(excluded)
    for rank in range(size):
        if not need:
            break
        value = next(values)
        if pointer < skipped and excluded[pointer] == rank:
            pointer += 1
            continue
        if select.randrange(remaining) < need:
            stage = 'D' if stages.randrange(need) < discovery else 'V'
            discovery -= stage == 'D'
            need -= 1
            yield stage, rank, value
        remaining -= 1


def a2_prefix(key, cluster):
    message = b'hashlab-exp002-prefix' + struct.pack('<I', cluster)
    return (blake2b(message + struct.pack('<I', 0), key=key).digest()
            + blake2b(message + struct.pack('<I', 1), key=key).digest()[:12])


# ------------------------------------------------------------------ controls

def _round(key, r, half):
    return int.from_bytes(blake2b(ROUND_LABEL + bytes([r]) + half.to_bytes(4, 'big'),
                                  key=key, digest_size=64).digest()[:4], 'big')


def feistel(key, value, *, inverse=False):
    left, right = value >> 32, value & 0xffffffff
    if inverse:
        for r in range(5, -1, -1):
            left, right = right ^ _round(key, r, left), left
    else:
        for r in range(6):
            left, right = right, left ^ _round(key, r, right)
    return (left << 32) | right


def n2_stream(key):
    counter, buffer = 0, b''
    while True:
        while len(buffer) < 80:
            buffer += blake2b(counter.to_bytes(16, 'big'), key=key, digest_size=64).digest()
            counter += 1
        yield buffer[:80]
        buffer = buffer[80:]


def structural_mask(value):
    return ((C1 if 2**20 <= value < 2**32 else 0)
            | (C3 if value >> 32 and value.bit_count() <= 6 else 0))


def transform(mode, raw):
    value, u = int.from_bytes(raw, 'big'), int.from_bytes(raw[28:], 'big')
    threshold = THRESHOLDS[mode]
    effective = value
    if mode == 'P2-':
        if value < TARGET and u < threshold:
            effective = value + TARGET
    elif mode in ('P1', 'P2+'):
        if value >= TARGET and u < threshold:
            effective = value % TARGET
    return effective.to_bytes(32, 'big')


# ---------------------------------------------------------------- the stream

def attempts(geometry, master, history_values, exclusion_ranks, *, cross_check=1):
    """Yield every expected attempt, including rejections, in producer order.

    Tuples are (arm, stage, mask, candidate, source, accepted, rank, offset,
    cluster); absent optional values are None. ``cross_check`` verifies every
    k-th accepted A3 value through two independent colex decoders.
    """
    g = geometry
    s = seeds(master, g.domain)
    index = {('A1', 'D'): 0, ('A1', 'V'): 0, ('A3', 'D'): 0, ('A3', 'V'): 0}
    for stage, rank in a1_ranks(g.a1_size, g.a1_stage, g.a1_stage, *s['a1']):
        yield 'A1', stage, 0, (2**20 + rank).to_bytes(8, 'big'), None, index['A1', stage], rank, None, None
        index['A1', stage] += 1
    prefixes = [a2_prefix(s['a2_key'], j) for j in range(3000)]
    if len(set(prefixes)) != 3000:
        raise Mismatch('A2 prefix collision')
    for cluster in g.a2_clusters:
        stage = 'D' if cluster < 1500 else 'V'
        for nonce in range(g.a2_nonces):
            yield ('A2', stage, 0, prefixes[cluster] + nonce.to_bytes(4, 'little'),
                   cluster * 10000 + nonce, (cluster % 1500) * 10000 + nonce, None, None, cluster)
    ex = tuple(sorted(r for r in exclusion_ranks if r < g.a3_size))
    checked = 0
    for stage, rank, value in a3_ranks(g.a3_size, g.a3_stage, g.a3_stage, *s['a3'], ex):
        if cross_check and checked % cross_check == 0:
            if _colex_unrank(rank) != value or _colex_rank(value) != rank:
                raise Mismatch('independent A3 colex decoders disagree')
        checked += 1
        yield 'A3', stage, 0, value.to_bytes(8, 'big'), None, index['A3', stage], rank, None, None
        index['A3', stage] += 1
    key, n2key = s['n1_key'], s['n2_key']
    prefix_set = frozenset(prefixes)
    cursor = 0
    for stage in ('D', 'V'):
        accepted = 0
        while accepted < g.control_stage:
            if cursor >= N1_STOP:
                raise Mismatch('N1 source index exhaustion')
            value = feistel(key, cursor)
            mask = structural_mask(value) | (E001 if value in history_values else 0)
            yield 'N1', stage, mask, value.to_bytes(8, 'big'), cursor, None if mask else accepted, None, None, None
            cursor += 1
            accepted += not mask
    raw_index = accepted_total = 0
    stream = n2_stream(n2key)
    q = g.control_stage
    while accepted_total < 2 * q:
        raw = next(stream)
        hit = raw[:76] in prefix_set and int.from_bytes(raw[76:], 'little') < 10000
        stage = 'D' if accepted_total < q else 'V'
        local = accepted_total % q
        cluster = local // 10000 + (1500 if stage == 'V' else 0)
        yield ('N2', stage, A2R if hit else 0, raw, raw_index, None if hit else local, None,
               80 * raw_index, None if hit else cluster)
        raw_index += 1
        accepted_total += not hit
    cursor = P_START
    for arm, quota in (('P1', g.p1), ('P2+', g.p2), ('P2-', g.p2)):
        accepted = 0
        while accepted < quota:
            value = feistel(key, cursor)
            mask = structural_mask(value) | (E001 if value in history_values else 0)
            yield arm, 'C', mask, value.to_bytes(8, 'big'), cursor, None if mask else accepted, None, None, None
            cursor += 1
            accepted += not mask
