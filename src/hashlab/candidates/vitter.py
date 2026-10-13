"""Vitter Algorithm D, geometric proposal (1984, section 4, equation 4-5).

See docs/reviews/architecture-review-026-algorithm-d.md for correspondence,
proof obligations and numeric policy. No candidate hashing or seed derivation.
"""

from decimal import Context, Decimal, DecimalException, ROUND_CEILING, ROUND_FLOOR, Underflow
import random
from collections.abc import Iterator


class SamplingError(ValueError):
    """Invalid input, uncertifiable arithmetic, or broken randomness source.

    Review 027: every failed attempt must be disclosed, including numerical
    resource aborts. No discretionary seed replacement or silent retry is
    authorized. Later orchestration must persist the attempt and failure.
    """


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise SamplingError(f"expected integer in [{low}, {high}]")
    return value


class _Bounds:
    """Positive rational arithmetic with enclosing Decimal endpoints.

    Integer powers use outward-rounded squaring, never Decimal fractional power.
    Each precision attempt owns its contexts; ambient Decimal state is irrelevant.
    """
    def __init__(self, precision):
        self.down = Context(prec=precision, rounding=ROUND_FLOOR, Emin=-999999999999, Emax=999999999999)
        self.up = Context(prec=precision, rounding=ROUND_CEILING, Emin=-999999999999, Emax=999999999999)
        self.down.traps[Underflow] = self.up.traps[Underflow] = True

    def ratio(self, numerator, denominator):
        if numerator < 0 or denominator <= 0:
            raise SamplingError("invalid probability ratio")
        a, b = Decimal(numerator), Decimal(denominator)
        return self.down.divide(a, b), self.up.divide(a, b)

    def multiply(self, a, b):
        return self.down.multiply(a[0], b[0]), self.up.multiply(a[1], b[1])

    def divide(self, a, b):
        if b[0] <= 0:
            raise SamplingError("uncertifiable positive denominator")
        return self.down.divide(a[0], b[1]), self.up.divide(a[1], b[0])

    def power(self, base, exponent):
        result = (Decimal(1), Decimal(1))
        while exponent:
            if exponent & 1:
                result = self.multiply(result, base)
            exponent >>= 1
            if exponent:
                base = self.multiply(base, base)
        return result


class _Uniform:
    """Lazy U in [prefix/2**bits, (prefix+1)/2**bits]. Never redraw on ties.

    Sixty-four-bit chunks represent independent fair bits under the ideal-RNG
    assumption. A refinement cap halts instead of guessing or reseeding.
    """
    def __init__(self, rng):
        self.rng, self.prefix, self.bits = rng, 0, 0
        self.refine()

    def refine(self):
        if self.bits >= 4096:
            raise SamplingError("random interval unresolved after 4096 bits")
        try:
            block = self.rng.getrandbits(64)
        except StopIteration as exc:
            raise SamplingError("random source exhausted") from exc
        _integer(block, 0, 2**64 - 1)
        self.prefix = (self.prefix << 64) | block
        self.bits += 64

    def compare(self, probability):
        """Return U < p only when certified; equality/ambiguity refines U."""
        precision = 40
        try:
            while True:
                bounds = _Bounds(precision)
                p_low, p_high = probability(bounds)
                if not (p_low.is_finite() and p_high.is_finite()) or p_low < 0 or p_low > p_high:
                    raise SamplingError("invalid probability interval")
                u_low = bounds.ratio(self.prefix, 1 << self.bits)[0]
                u_high = bounds.ratio(self.prefix + 1, 1 << self.bits)[1]
                if u_high < p_low:
                    return True
                if u_low > p_high:
                    return False
                self.refine()
                precision = min(1600, precision * 2)
        except DecimalException as exc:
            raise SamplingError("probability arithmetic failed") from exc


def _survival(bounds, numerator, denominator, exponent):
    return bounds.power(bounds.ratio(numerator, denominator), exponent)


def _mass_factors(N, n, skip):
    """f(skip)/(n/N), using the shorter of its two falling-product forms."""
    if skip < n - 1:
        for i in range(skip):
            yield N - n - i, N - 1 - i
    else:
        for i in range(n - 1):
            yield N - skip - 1 - i, N - 1 - i


def _acceptance(bounds, N, n, skip):
    # D4: f(skip)/(c*g(skip)); c*g = (n/N)*q**skip.
    product = (Decimal(1), Decimal(1))
    for numerator, denominator in _mass_factors(N, n, skip):
        product = bounds.multiply(product, bounds.ratio(numerator, denominator))
    return bounds.divide(product, _survival(bounds, N - n, N - 1, skip))


def _geometric_hint(N, n, uniform):
    # Fixed Decimal context keeps the search hint independent of ambient
    # precision and platform libm. Its approximation never decides a skip.
    bits = min(uniform.bits, 53)
    top = uniform.prefix >> (uniform.bits-bits)
    bounds = _Bounds(40)
    midpoint = bounds.ratio(2*top+1, 1 << (bits+1))[0]
    q = bounds.ratio(N-n, N-1)[0]
    return int(bounds.down.divide(bounds.down.ln(midpoint), bounds.down.ln(q)))


def _geometric_skip(N, n, rng):
    """D2: geometric X, q=(N-n)/(N-1); reject X>N-n without truncating.

    A Decimal log is only a search hint. The actual skip and both of its
    endpoints must be certified using the same lazy U. Binary search is a
    deterministic recovery for inaccurate hints, not a different sampler.
    """
    uniform = _Uniform(rng)
    maximum = N - n
    below = lambda s: uniform.compare(lambda b: _survival(b, N-n, N-1, s))
    if below(maximum + 1):
        return None
    try:
        hint = _geometric_hint(N,n,uniform)
    except (ValueError, OverflowError, DecimalException):
        hint = -1
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
    """D1 dense tail: Method A's inverse survival product, certified exactly."""
    uniform = _Uniform(rng)
    for skip in range(N - n + 1):
        def survival(bounds):
            product = (Decimal(1), Decimal(1))
            for i in range(skip + 1):
                product = bounds.multiply(product, bounds.ratio(N-n-i, N-i))
            return product
        if not uniform.compare(survival):
            return skip
    raise SamplingError("Method A exhausted its legal support")


def _skip(N, n, rng):
    if n == N:
        return 0
    if n == 1:
        result = rng.randrange(N)
        return _integer(result, 0, N-1)
    if 13 * n >= N:  # D1, alpha=1/13, as in the 1987 appendix.
        return _method_a_skip(N, n, rng)
    # D2–D4. A cap is a fail-closed resource policy, never a forced acceptance.
    for _ in range(4096):
        skip = _geometric_skip(N, n, rng)
        if skip is None:
            continue
        uniform = _Uniform(rng)
        # D3: h/(c*g) = ((N-n-s+1)/(N-n))**s.
        if uniform.compare(lambda b: _survival(b, N-n-skip+1, N-n, skip)):
            return skip
        if uniform.compare(lambda b: _acceptance(b, N, n, skip)):
            return skip
    raise SamplingError("Algorithm D rejection limit exceeded")


def vitter_ranks(size: int, count: int, *, seed: int) -> Iterator[int]:
    """Fixed-size ordered sample from range(size); no full/sample collection.

    size is bounded by the accepted A1 population. Local MT19937; an exact
    bit-based interpretation of D, not the optimized float/Vprime appendix.
    """
    _integer(size, 1, 2**32 - 2**20)
    _integer(count, 0, size)
    _integer(seed, 0, 2**64-1)
    rng = random.Random(seed)
    N, n, offset = size, count, 0
    dense_tail = False
    while n:
        dense_tail = dense_tail or 13 * n >= N
        if dense_tail and 1 < n < N:
            skip = _method_a_skip(N, n, rng)
        else:
            skip = _skip(N, n, rng)
        _integer(skip, 0, N-n)
        rank = offset + skip
        if not 0 <= rank < size:
            raise SamplingError("rank outside population")
        yield rank  # D5; all subsequent ranks strictly exceed this rank.
        offset = rank + 1
        N -= skip + 1
        n -= 1
    if offset > size or N < 0:
        raise SamplingError("population accounting violation")


def a1_sample_ranks(size: int, discovery: int, validation: int, *,
                    selection_seed: int, stage_seed: int) -> Iterator[tuple[str, int]]:
    """A1 production sampling interface with explicit sub-seeds (no label binding)."""
    _integer(size, 1, 2**32 - 2**20)
    _integer(discovery, 0, size)
    _integer(validation, 0, size)
    _integer(selection_seed, 0, 2**64-1)
    _integer(stage_seed, 0, 2**64-1)
    remaining = discovery + validation
    _integer(remaining, 0, size)
    stages = random.Random(stage_seed)
    for rank in vitter_ranks(size, remaining, seed=selection_seed):
        stage = 'D' if stages.randrange(remaining) < discovery else 'V'
        if stage == 'D':
            discovery -= 1
        remaining -= 1
        yield stage, rank
    if remaining or discovery:
        raise SamplingError("stage accounting violation")
