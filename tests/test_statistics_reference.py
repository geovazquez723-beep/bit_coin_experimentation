"""Independent numerical reference cases for statistics/inference.py (Remediation E).

Every expected value here comes from a method that does NOT share code with
the implementation under test:

* binomial tails and test p-values: exact rational arithmetic (fractions.Fraction
  sums of the binomial pmf), evaluated at the exact binary value of the float p
  that is passed to the implementation, or closed forms evaluated with math.log1p
  / math.expm1;
* Clopper-Pearson: closed forms for k in {0, 1, n-1, n}, a published R value,
  and the defining tail equations re-checked in exact arithmetic;
* Holm: adjusted p-values computed by hand from the step-down definition, plus
  an independent sequential rejection procedure;
* planning: standard normal quantiles from published tables, and exact binomial
  power computed outside the code base by direct pmf summation (see
  docs/reviews/architecture-review-001-remediation.md).

Tolerances (documented in docs/methodology.md, section 7):

* rel 1e-9 where n <= 10,000;
* rel 1e-7 at n ~ 1e6, because log-gamma differences such as
  lgamma(n + 1) - lgamma(n) lose about 1e-9 absolute precision there
  (|lgamma(1e6)| ~ 1.3e7 has a float spacing of ~2e-9);
* abs 1e-300 floor: tails below about 1e-300 underflow to 0.
"""

from __future__ import annotations

import math
from fractions import Fraction

import pytest

from hashlab.statistics.inference import (
    binom_cdf,
    binom_sf,
    binom_test,
    bonferroni,
    clopper_pearson,
    exact_binomial_power,
    holm,
    minimum_detectable_effect,
    minimum_detectable_effect_unpooled,
    normal_power,
)

# Standard normal quantiles (published tables, 16 significant digits).
Z_0_80 = 0.8416212335729143
Z_0_975 = 1.959963984540054
Z_0_99 = 2.3263478740408408
Z_0_9995 = 3.2905267314919255

REL = 1e-9
REL_LARGE_N = 1e-7
ABS_FLOOR = 1e-300


# --------------------------------------------------------------------------- exact references


def exact_pmf(n: int, p: float) -> list[Fraction]:
    q = Fraction(p)  # exact binary value of the float handed to the implementation
    return [Fraction(math.comb(n, i)) * q**i * (1 - q) ** (n - i) for i in range(n + 1)]


def exact_cdf(n: int, p: float, k: int) -> Fraction:
    return sum(exact_pmf(n, p)[: k + 1], Fraction(0))


def exact_sf(n: int, p: float, k: int) -> Fraction:
    return sum(exact_pmf(n, p)[k:], Fraction(0))


SMALL_CASES = [
    (1, 0.5),
    (2, 0.25),
    (5, 1 / 3),
    (12, 1 / 256),
    (12, 1 - 2**-20),        # success probability extremely close to 1
    (12, 2**-40),            # extremely small success probability
    (60, 0.3),
    (60, 2**-30),
    (60, 1 - 2**-40),
]


# --------------------------------------------------------------------------- binomial tails


@pytest.mark.parametrize("n,p", SMALL_CASES)
def test_binomial_tails_match_exact_rational_sums(n: int, p: float) -> None:
    for k in range(n + 1):
        assert binom_cdf(k, n, p) == pytest.approx(float(exact_cdf(n, p, k)), rel=REL, abs=ABS_FLOOR)
        assert binom_sf(k, n, p) == pytest.approx(float(exact_sf(n, p, k)), rel=REL, abs=ABS_FLOOR)


@pytest.mark.parametrize("n,p", SMALL_CASES)
def test_two_sided_doubled_tail_matches_exact_definition(n: int, p: float) -> None:
    for k in range(n + 1):
        expected = min(Fraction(1), 2 * min(exact_cdf(n, p, k), exact_sf(n, p, k)))
        assert binom_test(k, n, p) == pytest.approx(float(expected), rel=REL, abs=ABS_FLOOR)
        assert binom_test(k, n, p, "greater") == pytest.approx(float(exact_sf(n, p, k)), rel=REL, abs=ABS_FLOOR)
        assert binom_test(k, n, p, "less") == pytest.approx(float(exact_cdf(n, p, k)), rel=REL, abs=ABS_FLOOR)


@pytest.mark.parametrize("n", [1, 7, 100, 10_000])
def test_zero_and_all_successes_closed_forms(n: int) -> None:
    p = 0.3
    none = math.exp(n * math.log1p(-p))  # P(X = 0) = (1 - p)^n
    every = math.exp(n * math.log(p))  # P(X = n) = p^n
    assert binom_cdf(0, n, p) == pytest.approx(none, rel=REL, abs=ABS_FLOOR)
    assert binom_sf(n, n, p) == pytest.approx(every, rel=REL, abs=ABS_FLOOR)
    assert binom_cdf(n - 1, n, p) == pytest.approx(-math.expm1(n * math.log(p)), rel=REL)  # 1 - p^n
    assert binom_sf(1, n, p) == pytest.approx(-math.expm1(n * math.log1p(-p)), rel=REL)  # 1 - (1 - p)^n
    assert binom_test(0, n, p) == pytest.approx(min(1.0, 2 * none), rel=REL, abs=ABS_FLOOR)
    assert binom_test(n, n, p) == pytest.approx(min(1.0, 2 * every), rel=REL, abs=ABS_FLOOR)
    assert binom_test(0, n, p, "greater") == 1.0
    assert binom_test(n, n, p, "less") == 1.0


def test_boundary_counts_and_probabilities() -> None:
    assert binom_cdf(-1, 5, 0.4) == 0.0 and binom_cdf(5, 5, 0.4) == 1.0
    assert binom_sf(0, 5, 0.4) == 1.0 and binom_sf(6, 5, 0.4) == 0.0
    assert binom_cdf(2, 5, 0.0) == 1.0 and binom_sf(1, 5, 0.0) == 0.0
    assert binom_cdf(4, 5, 1.0) == 0.0 and binom_sf(5, 5, 1.0) == 1.0
    assert binom_cdf(0, 0, 0.5) == 1.0 and binom_test(0, 0, 0.5) == 1.0
    for bad in [(-1, 5), (6, 5)]:
        with pytest.raises(ValueError):
            binom_test(bad[0], bad[1], 0.5)
    with pytest.raises(ValueError):
        binom_cdf(1, 5, 1.5)


def test_extreme_target_probability_at_large_n() -> None:
    # p = 2^-64 (64 leading zero bits), n = 10^6: lambda = n p ~ 5.4e-14.
    n, p = 1_000_000, 2.0**-64
    none = math.exp(n * math.log1p(-p))
    assert binom_cdf(0, n, p) == pytest.approx(none, rel=REL_LARGE_N)
    assert binom_sf(1, n, p) == pytest.approx(-math.expm1(n * math.log1p(-p)), rel=REL_LARGE_N)
    # P(X >= 2) = C(n, 2) p^2 (1 - p)^(n - 2) * (1 + O(n p)); the O(n p) term is ~2e-14 here.
    two = float(Fraction(math.comb(n, 2)) * Fraction(p) ** 2) * math.exp((n - 2) * math.log1p(-p))
    assert binom_sf(2, n, p) == pytest.approx(two, rel=REL_LARGE_N)


# --------------------------------------------------------------------------- Clopper-Pearson


@pytest.mark.parametrize("n", [1, 2, 10, 100, 10_000, 1_000_000])
@pytest.mark.parametrize("confidence", [0.95, 0.99])
def test_clopper_pearson_closed_forms(n: int, confidence: float) -> None:
    half = (1.0 - confidence) / 2.0
    rel = REL if n <= 10_000 else REL_LARGE_N
    # k = 0: upper solves (1 - p)^n = half; k = n: lower solves p^n = half.
    lower, upper = clopper_pearson(0, n, confidence)
    assert lower == 0.0 and upper == pytest.approx(-math.expm1(math.log(half) / n), rel=rel)
    lower, upper = clopper_pearson(n, n, confidence)
    assert upper == 1.0 and lower == pytest.approx(math.exp(math.log(half) / n), rel=rel)
    if n >= 2:
        # k = 1: lower solves 1 - (1 - p)^n = half; k = n - 1: upper solves 1 - p^n = half.
        lower, _ = clopper_pearson(1, n, confidence)
        assert lower == pytest.approx(-math.expm1(math.log1p(-half) / n), rel=rel)
        _, upper = clopper_pearson(n - 1, n, confidence)
        assert upper == pytest.approx(math.exp(math.log1p(-half) / n), rel=rel)


def test_clopper_pearson_published_reference() -> None:
    # R: binom.test(5, 20)$conf.int -> 0.08657147 0.49104587 (printed to 8 decimals, so abs 1e-8)
    lower, upper = clopper_pearson(5, 20, 0.95)
    assert lower == pytest.approx(0.08657147, abs=1e-8)
    assert upper == pytest.approx(0.49104587, abs=1e-8)


@pytest.mark.parametrize("k,n,confidence", [(7, 20, 0.95), (3, 40, 0.99), (1, 12, 0.9), (29, 30, 0.99)])
def test_clopper_pearson_defining_equations_in_exact_arithmetic(k: int, n: int, confidence: float) -> None:
    half = (1.0 - confidence) / 2.0
    lower, upper = clopper_pearson(k, n, confidence)
    assert float(exact_sf(n, lower, k)) == pytest.approx(half, rel=1e-9)  # P(X >= k | lower) = alpha/2
    assert float(exact_cdf(n, upper, k)) == pytest.approx(half, rel=1e-9)  # P(X <= k | upper) = alpha/2
    assert lower < k / n < upper


def test_clopper_pearson_nesting_across_confidence_levels() -> None:
    marginal = clopper_pearson(610, 100_000, 0.99)
    simultaneous = clopper_pearson(610, 100_000, 1 - 0.01 / 5)
    assert simultaneous[0] < marginal[0] < marginal[1] < simultaneous[1]


# --------------------------------------------------------------------------- Holm


@pytest.mark.parametrize(
    "p_values,expected",
    [
        # sorted p(i) times (m - i + 1), then a running maximum, then capped at 1:
        ([0.01, 0.02, 0.03, 0.04, 0.05], [0.05, 0.08, 0.09, 0.09, 0.09]),  # also R p.adjust(method = "holm")
        ([0.04, 0.01, 0.05, 0.03, 0.02], [0.09, 0.05, 0.09, 0.09, 0.08]),  # unsorted input keeps positions
        ([0.001, 0.01, 0.02, 0.04, 0.5], [0.005, 0.04, 0.06, 0.08, 0.5]),
        ([0.02, 0.02], [0.04, 0.04]),  # ties
        ([0.6, 0.7], [1.0, 1.0]),  # capped at 1
        ([0.03], [0.03]),  # a single test is unadjusted
        ([1.0, 0.0], [1.0, 0.0]),  # boundary p-values
        ([], []),
    ],
)
def test_holm_hand_computed_references(p_values: list[float], expected: list[float]) -> None:
    assert holm(p_values) == pytest.approx(expected, abs=1e-15)


def sequential_holm_rejections(p_values: list[float], alpha: float) -> set[int]:
    """Holm's step-down procedure as published (independent of holm())."""
    m = len(p_values)
    rejected: set[int] = set()
    for rank, index in enumerate(sorted(range(m), key=lambda i: p_values[i])):
        if p_values[index] < alpha / (m - rank):
            rejected.add(index)
        else:
            break
    return rejected


@pytest.mark.parametrize(
    "p_values",
    [[0.001, 0.2, 0.012, 0.04, 0.9], [0.0001, 0.0021, 0.0034, 0.3], [0.5, 0.6], [0.0009, 0.0011, 0.0013, 0.02]],
)
def test_holm_matches_the_step_down_procedure(p_values: list[float]) -> None:
    alpha = 0.01
    adjusted = holm(p_values)
    assert {i for i, p in enumerate(adjusted) if p < alpha} == sequential_holm_rejections(p_values, alpha)
    assert all(h <= b + 1e-15 for h, b in zip(adjusted, bonferroni(p_values)))


# --------------------------------------------------------------------------- planning sensitivity


def test_textbook_minimum_detectable_effect() -> None:
    # p0 = 0.5, n = 10,000, two-sided alpha = 0.05, power 0.8: (1.95996 + 0.84162) * 0.005 / 0.5
    plan = minimum_detectable_effect(10_000, 0.5, 0.05, 0.8, tests=1)
    assert plan.min_detectable_relative_effect == pytest.approx((Z_0_975 + Z_0_80) * 0.005 / 0.5, rel=1e-9)


def test_baseline_mde_reproduces_the_documented_figure() -> None:
    # n = 500,000, p0 = 1/256, family alpha 0.01 over 10 tests (Bonferroni 0.001 two-sided), power 0.8
    plan = minimum_detectable_effect(500_000, 1 / 256, 0.01, 0.8, tests=10)
    expected = (Z_0_9995 + Z_0_80) * math.sqrt((1 - 1 / 256) / (500_000 / 256))
    assert plan.min_detectable_relative_effect == pytest.approx(expected, rel=1e-9)
    assert round(plan.min_detectable_relative_effect, 3) == 0.093


def test_mde_scales_with_one_over_root_n() -> None:
    small = minimum_detectable_effect(125_000, 1 / 256, 0.01, 0.8, tests=10).min_detectable_relative_effect
    large = minimum_detectable_effect(500_000, 1 / 256, 0.01, 0.8, tests=10).min_detectable_relative_effect
    assert small == pytest.approx(2 * large, rel=1e-12)


@pytest.mark.parametrize("direction,sign", [("increase", 1), ("decrease", -1)])
def test_unpooled_mde_solves_its_defining_equation(direction: str, sign: int) -> None:
    n, p0 = 500_000, 1 / 256
    delta = minimum_detectable_effect_unpooled(n, p0, 0.01, 0.8, tests=10, direction=direction)
    p1 = p0 * (1 + sign * delta)
    rhs = Z_0_9995 * math.sqrt(p0 * (1 - p0) / n) + Z_0_80 * math.sqrt(p1 * (1 - p1) / n)
    assert delta * p0 == pytest.approx(rhs, rel=1e-9)


def test_unpooled_mde_reference_values_and_ordering() -> None:
    # Reference values from a fixed-point iteration of the same equation, run outside the code base.
    n, p0 = 500_000, 1 / 256
    increase = minimum_detectable_effect_unpooled(n, p0, 0.01, 0.8, tests=10, direction="increase")
    decrease = minimum_detectable_effect_unpooled(n, p0, 0.01, 0.8, tests=10, direction="decrease")
    pooled = minimum_detectable_effect(n, p0, 0.01, 0.8, tests=10).min_detectable_relative_effect
    assert increase == pytest.approx(0.09418832275217044, rel=1e-8)
    assert decrease == pytest.approx(0.09242073505393443, rel=1e-8)
    assert decrease < pooled < increase


def test_normal_power_size_and_consistency_with_the_mde() -> None:
    n, p0, alpha = 500_000, 1 / 256, 0.001
    assert normal_power(n, p0, 0.0, alpha) == pytest.approx(alpha, rel=1e-9)
    assert normal_power(n, p0, 0.0, alpha, "greater") == pytest.approx(alpha, rel=1e-9)
    delta = minimum_detectable_effect_unpooled(n, p0, 0.01, 0.8, tests=10, direction="increase")
    one_sided = normal_power(n, p0, delta, alpha / 2, "greater")  # same critical value as the MDE equation
    assert one_sided == pytest.approx(0.8, rel=1e-9)
    two_sided = normal_power(n, p0, delta, alpha)
    assert one_sided <= two_sided == pytest.approx(0.8, abs=1e-6)  # plus the negligible far tail


def exact_power_reference(n: int, p0: float, p1: float, level: float) -> tuple[Fraction, Fraction]:
    """Two-sided doubled-tail power and size in exact arithmetic; asserts no tail sits on the boundary."""
    null, alt = exact_pmf(n, p0), exact_pmf(n, p1)
    half = Fraction(level) / 2
    power = size = Fraction(0)
    for k in range(n + 1):
        lower, upper = sum(null[: k + 1], Fraction(0)), sum(null[k:], Fraction(0))
        assert abs(lower - half) > half * Fraction(1, 10**6) and abs(upper - half) > half * Fraction(1, 10**6)
        if lower < half or upper < half:
            power += alt[k]
            size += null[k]
    return power, size


@pytest.mark.parametrize("n,p0,p1,level", [(20, 0.5, 0.75, 0.05), (20, 0.5, 0.2, 0.05), (40, 0.3, 0.45, 0.01), (30, 0.1, 0.1, 0.05)])
def test_exact_binomial_power_matches_exact_rejection_region(n: int, p0: float, p1: float, level: float) -> None:
    power, size = exact_power_reference(n, p0, p1, level)
    assert exact_binomial_power(n, p0, p1, level) == pytest.approx(float(power), rel=1e-9)
    assert float(size) <= level  # the doubled-tail test is conservative


def test_exact_power_of_the_baseline_discovery_test_at_the_planning_mde() -> None:
    # Reference: direct pmf summation outside the code base. Rejection region k <= 1809 or k >= 2101
    # (P0 tails 4.948e-4 and 4.760e-4 against alpha'/2 = 5e-4). At the pooled MDE (+9.33%) the exact
    # power is about 0.775, not 0.80: the planning figure is a normal approximation.
    n, p0 = 500_000, 1 / 256
    mde = minimum_detectable_effect(n, p0, 0.01, 0.8, tests=10).min_detectable_relative_effect
    power = exact_binomial_power(n, p0, p0 * (1 + mde), 0.001)
    assert power == pytest.approx(0.7748769423030871, rel=1e-6)
