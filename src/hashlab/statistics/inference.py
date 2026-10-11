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
    For planning only. The analysis itself uses exact tests.
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
