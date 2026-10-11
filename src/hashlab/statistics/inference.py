"""Exact binomial inference and multiple-testing correction, in pure Python.

All tail probabilities come from the regularized incomplete beta function
I_x(a, b), evaluated with a continued fraction (Lentz's method, Numerical
Recipes 6.4):

    P(X <= k) = I_{1-p}(n - k, k + 1)        X ~ Binomial(n, p)
    P(X >= k) = I_p(k, n - k + 1)

Each tail is computed on the branch where it is small, so very small p-values
keep their relative accuracy and never come from 1 - (something close to 1).

Clopper-Pearson ("exact") interval at confidence 1 - alpha:

    lower = Beta^{-1}(alpha/2; k, n - k + 1)      (0 if k == 0)
    upper = Beta^{-1}(1 - alpha/2; k + 1, n - k)  (1 if k == n)

Two-sided exact binomial test (stated before collecting data): the doubled
smaller tail, p = min(1, 2 * min(P(X <= k), P(X >= k))). It is slightly
conservative compared with the "minimum likelihood" method.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

_EPS = 1e-15
_FPMIN = 1e-300
_MAX_ITER = 1_000_000
_BISECT_STEPS = 200


# --------------------------------------------------------------------------- incomplete beta


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, _MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            return h
    raise ArithmeticError(f"incomplete beta did not converge (a={a}, b={b}, x={x})")


def betainc(a: float, b: float, x: float, complement: float | None = None) -> float:
    """Regularized incomplete beta I_x(a, b) for a, b > 0.

    ``complement`` may pass 1 - x computed more accurately than ``1 - x`` in floating point.
    """
    if a <= 0 or b <= 0:
        raise ValueError("betainc requires a > 0 and b > 0")
    y = (1.0 - x) if complement is None else complement
    if x <= 0.0:
        return 0.0
    if y <= 0.0:
        return 1.0
    log_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(y)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _beta_continued_fraction(a, b, x) / a
    return 1.0 - math.exp(log_front) * _beta_continued_fraction(b, a, y) / b


# --------------------------------------------------------------------------- binomial


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    _check_binomial(n, p)
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p == 0.0:
        return 1.0
    if p == 1.0:
        return 0.0
    return betainc(n - k, k + 1, 1.0 - p, complement=p)


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    _check_binomial(n, p)
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if p == 0.0:
        return 0.0
    if p == 1.0:
        return 1.0
    return betainc(k, n - k + 1, p, complement=1.0 - p)


def binom_test(k: int, n: int, p0: float, alternative: str = "two-sided") -> float:
    """Exact binomial test p-value for H0: success probability == p0."""
    _check_count(k, n)
    lower = binom_cdf(k, n, p0)
    upper = binom_sf(k, n, p0)
    if alternative == "greater":
        return upper
    if alternative == "less":
        return lower
    if alternative == "two-sided":
        return min(1.0, 2.0 * min(lower, upper))
    raise ValueError("alternative must be 'two-sided', 'greater' or 'less'")


def _inverse_betainc(target: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(_BISECT_STEPS):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        if betainc(a, b, mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Exact (Clopper-Pearson) two-sided confidence interval for a binomial proportion."""
    _check_count(k, n)
    if n == 0:
        return (0.0, 1.0)
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    alpha = 1.0 - confidence
    lower = 0.0 if k == 0 else _inverse_betainc(alpha / 2.0, k, n - k + 1)
    upper = 1.0 if k == n else _inverse_betainc(1.0 - alpha / 2.0, k + 1, n - k)
    return (lower, upper)


def _check_binomial(n: int, p: float) -> None:
    if n < 0:
        raise ValueError("n must be non-negative")
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")


def _check_count(k: int, n: int) -> None:
    if n < 0 or not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n")


# --------------------------------------------------------------------------- chi-square


def _gamma_series(a: float, x: float) -> float:
    total = term = 1.0 / a
    ap = a
    for _ in range(_MAX_ITER):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * _EPS:
            return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    raise ArithmeticError("gamma series did not converge")


def _gamma_continued_fraction(a: float, x: float) -> float:
    b = x + 1.0 - a
    c = 1.0 / _FPMIN
    d = 1.0 / b
    h = d
    for i in range(1, _MAX_ITER + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = b + an / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    raise ArithmeticError("gamma continued fraction did not converge")


def gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x)."""
    if a <= 0:
        raise ValueError("a must be positive")
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_series(a, x)
    return _gamma_continued_fraction(a, x)


def chi2_sf(statistic: float, df: int) -> float:
    """Survival function of the chi-square distribution: P(X >= statistic)."""
    if df < 1:
        raise ValueError("df must be >= 1")
    return gammaincc(df / 2.0, statistic / 2.0)


# --------------------------------------------------------------------------- multiple testing


def bonferroni(p_values: list[float]) -> list[float]:
    m = len(p_values)
    return [min(1.0, p * m) for p in p_values]


def holm(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjusted p-values (controls family-wise error rate)."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[idx]))
        adjusted[idx] = running
    return adjusted


def adjust(p_values: list[float], method: str) -> list[float]:
    if method == "holm":
        return holm(p_values)
    if method == "bonferroni":
        return bonferroni(p_values)
    if method == "none":
        return list(p_values)
    raise ValueError("correction must be 'holm', 'bonferroni' or 'none'")


# --------------------------------------------------------------------------- planning


@dataclass(frozen=True)
class PowerPlan:
    expected_successes: float
    min_detectable_relative_effect: float
    alpha_per_test: float


def minimum_detectable_effect(n: int, p0: float, alpha: float, power: float, tests: int = 1) -> PowerPlan:
    """Normal-approximation minimum detectable relative change in success rate.

    Uses a two-sided test at Bonferroni level alpha/tests (conservative for Holm).
    MDE_rel = (z_{1 - alpha'/2} + z_{power}) * sqrt(p0 * (1 - p0) / n) / p0.
    The null variance is used in both terms (so the result is the same for an
    increase and a decrease) and the far rejection tail is ignored.

    For planning only. The analysis itself uses exact tests. An MDE is the
    effect a test would detect with probability ``power`` under these
    approximations. It is NOT an exclusion bound: a non-significant result does
    not show that effects of this size, or smaller, are absent.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    alpha_per_test = alpha / max(1, tests)
    z = NormalDist().inv_cdf(1.0 - alpha_per_test / 2.0) + NormalDist().inv_cdf(power)
    se = math.sqrt(p0 * (1.0 - p0) / n)
    return PowerPlan(
        expected_successes=n * p0,
        min_detectable_relative_effect=z * se / p0,
        alpha_per_test=alpha_per_test,
    )


def _check_planning(n: int, p0: float, level: float, name: str) -> None:
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0.0 < p0 < 1.0:
        raise ValueError("p0 must be strictly between 0 and 1")
    if not 0.0 < level < 1.0:
        raise ValueError(f"{name} must be strictly between 0 and 1")


def normal_power(n: int, p0: float, relative_effect: float, alpha_level: float, alternative: str = "two-sided") -> float:
    """Normal-approximation power of the test of H0: p = p0 when the true rate is p0 * (1 + relative_effect).

    Critical values use the null standard error sqrt(p0 (1 - p0) / n); the spread
    under the alternative uses sqrt(p1 (1 - p1) / n) ("unpooled"). Two-sided
    power counts both rejection tails. ``alpha_level`` is the level of this one
    test (already divided by any multiplicity correction). Planning only.
    """
    _check_planning(n, p0, alpha_level, "alpha_level")
    p1 = p0 * (1.0 + relative_effect)
    if not 0.0 <= p1 <= 1.0:
        raise ValueError("p0 * (1 + relative_effect) must be in [0, 1]")
    normal = NormalDist()
    se0 = math.sqrt(p0 * (1.0 - p0) / n)
    se1 = math.sqrt(p1 * (1.0 - p1) / n)
    shift = p1 - p0

    def tail(signed_shift: float, z: float) -> float:
        # P(estimate - p0 crosses z * se0 in the direction of signed_shift)
        if se1 == 0.0:
            return 1.0 if signed_shift >= z * se0 else 0.0
        return normal.cdf((signed_shift - z * se0) / se1)

    if alternative == "greater":
        return tail(shift, normal.inv_cdf(1.0 - alpha_level))
    if alternative == "less":
        return tail(-shift, normal.inv_cdf(1.0 - alpha_level))
    if alternative == "two-sided":
        z = normal.inv_cdf(1.0 - alpha_level / 2.0)
        return tail(shift, z) + tail(-shift, z)
    raise ValueError("alternative must be 'two-sided', 'greater' or 'less'")


def minimum_detectable_effect_unpooled(
    n: int, p0: float, alpha: float, power: float, tests: int = 1, direction: str = "increase"
) -> float:
    """Directional normal-approximation MDE that uses the alternative variance.

    Solves  delta * p0 = z_{1 - alpha'/2} * se0 + z_{power} * se1(delta)  for delta,
    with alpha' = alpha / tests (two-sided, like the discovery test),
    se0 = sqrt(p0 (1 - p0) / n), se1 = sqrt(p1 (1 - p1) / n), and
    p1 = p0 (1 + delta) for an increase or p0 (1 - delta) for a decrease.
    Returns delta > 0 (a relative effect size in either direction).

    Solved by bisection; the left side minus the right side increases with
    delta whenever n * p1 * (1 - p1) is not tiny. Planning only, NOT an
    exclusion bound (see ``minimum_detectable_effect``).
    """
    _check_planning(n, p0, alpha, "alpha")
    if not 0.0 < power < 1.0:
        raise ValueError("power must be strictly between 0 and 1")
    if direction not in ("increase", "decrease"):
        raise ValueError("direction must be 'increase' or 'decrease'")
    sign = 1.0 if direction == "increase" else -1.0
    alpha_per_test = alpha / max(1, tests)
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1.0 - alpha_per_test / 2.0)
    z_power = normal.inv_cdf(power)
    se0 = math.sqrt(p0 * (1.0 - p0) / n)

    def gap(delta: float) -> float:
        p1 = min(1.0, max(0.0, p0 * (1.0 + sign * delta)))
        return delta * p0 - z_alpha * se0 - z_power * math.sqrt(p1 * (1.0 - p1) / n)

    lo, hi = 0.0, ((1.0 - p0) / p0 if sign > 0 else 1.0)  # keeps p1 inside [0, 1]
    if gap(hi) < 0.0:
        raise ValueError("no relative effect in range reaches the requested power")
    for _ in range(_BISECT_STEPS):
        mid = 0.5 * (lo + hi)
        if mid in (lo, hi):
            break
        if gap(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return hi


def exact_binomial_power(n: int, p0: float, p1: float, alpha_level: float, alternative: str = "two-sided") -> float:
    """Exact power of ``binom_test`` at level ``alpha_level`` when the true rate is p1.

    Rejection uses the analysis rule (p-value strictly below the level): for
    the doubled-tail two-sided test, reject when P0(X >= k) < alpha_level / 2
    or P0(X <= k) < alpha_level / 2. Power is P1(X in the rejection region).
    Critical counts are found by bisection over k. For reproducing planning
    figures; not called by the plan, whose numbers stay normal approximations.
    """
    _check_count(0, n)
    _check_planning(max(n, 1), p0, alpha_level, "alpha_level")
    _check_binomial(n, p1)
    if alternative not in ("two-sided", "greater", "less"):
        raise ValueError("alternative must be 'two-sided', 'greater' or 'less'")
    level = alpha_level / 2.0 if alternative == "two-sided" else alpha_level
    power = 0.0
    if alternative in ("two-sided", "greater"):
        # smallest k in [0, n + 1] with P0(X >= k) < level (k = n + 1 means "never reject")
        lo, hi = 0, n + 1
        while lo < hi:
            mid = (lo + hi) // 2
            if binom_sf(mid, n, p0) < level:
                hi = mid
            else:
                lo = mid + 1
        power += binom_sf(lo, n, p1)
    if alternative in ("two-sided", "less"):
        # largest k in [-1, n] with P0(X <= k) < level (k = -1 means "never reject")
        lo, hi = -1, n
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if binom_cdf(mid, n, p0) < level:
                lo = mid
            else:
                hi = mid - 1
        power += binom_cdf(lo, n, p1)
    return power
