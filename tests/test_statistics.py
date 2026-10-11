from __future__ import annotations

import math
from fractions import Fraction

import pytest

from hashlab.statistics import (
    DigestAccumulator,
    binom_cdf,
    binom_sf,
    binom_test,
    bonferroni,
    chi2_sf,
    clopper_pearson,
    holm,
    leading_zero_gof,
    leading_zero_probability,
    minimum_detectable_effect,
    uniform_byte_gof,
)
from hashlab.statistics.inference import adjust, betainc


def exact_cdf(k: int, n: int, p: Fraction) -> float:
    return float(sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1)))


# ---- binomial tails


@pytest.mark.parametrize("n,p", [(20, Fraction(3, 10)), (50, Fraction(1, 256)), (100, Fraction(1, 2)), (7, Fraction(9, 10))])
def test_binom_cdf_matches_exact_sum(n: int, p: Fraction) -> None:
    for k in range(n + 1):
        assert binom_cdf(k, n, float(p)) == pytest.approx(exact_cdf(k, n, p), rel=1e-9, abs=1e-300)


def test_binom_sf_complements_cdf() -> None:
    for k in range(0, 31):
        assert binom_sf(k, 30, 0.2) + binom_cdf(k - 1, 30, 0.2) == pytest.approx(1.0, abs=1e-12)


def test_binom_small_tail_keeps_relative_accuracy() -> None:
    expected = 0.99**5000  # ~1.5e-22
    assert binom_cdf(0, 5000, 0.01) == pytest.approx(expected, rel=1e-9)


def test_binom_edge_cases() -> None:
    assert binom_cdf(-1, 10, 0.5) == 0.0
    assert binom_cdf(10, 10, 0.5) == 1.0
    assert binom_sf(0, 10, 0.5) == 1.0
    assert binom_sf(11, 10, 0.5) == 0.0
    with pytest.raises(ValueError):
        binom_test(11, 10, 0.5)


def test_binom_test_values() -> None:
    # Two-sided, doubled-tail definition.
    lower = exact_cdf(3, 20, Fraction(1, 2))
    assert binom_test(3, 20, 0.5) == pytest.approx(2 * lower, rel=1e-9)
    assert binom_test(10, 20, 0.5) == 1.0
    assert binom_test(15, 20, 0.5, "greater") == pytest.approx(1 - exact_cdf(14, 20, Fraction(1, 2)), rel=1e-9)
    assert binom_test(5, 20, 0.5, "less") == pytest.approx(exact_cdf(5, 20, Fraction(1, 2)), rel=1e-9)


def test_binom_test_large_n_at_expectation_is_not_significant() -> None:
    n = 500_000
    k = round(n / 256)
    assert binom_test(k, n, 1 / 256) > 0.9


def test_betainc_symmetry() -> None:
    for a, b, x in [(2.0, 3.0, 0.4), (10.0, 0.5, 0.9), (1000.0, 2000.0, 0.33)]:
        assert betainc(a, b, x) + betainc(b, a, 1 - x) == pytest.approx(1.0, abs=1e-12)


# ---- Clopper-Pearson


def test_clopper_pearson_closed_forms() -> None:
    lower, upper = clopper_pearson(0, 10, 0.95)
    assert lower == 0.0 and upper == pytest.approx(1 - 0.025 ** (1 / 10), rel=1e-9)
    lower, upper = clopper_pearson(10, 10, 0.95)
    assert upper == 1.0 and lower == pytest.approx(0.025 ** (1 / 10), rel=1e-9)


def test_clopper_pearson_reference_value() -> None:
    # R: binom.test(5, 20)$conf.int -> 0.08657147 0.49104587
    lower, upper = clopper_pearson(5, 20, 0.95)
    assert lower == pytest.approx(0.08657147, abs=1e-7)
    assert upper == pytest.approx(0.49104587, abs=1e-7)


def test_clopper_pearson_defining_property() -> None:
    k, n, conf = 2000, 500_000, 0.99
    lower, upper = clopper_pearson(k, n, conf)
    alpha = 1 - conf
    assert binom_sf(k, n, lower) == pytest.approx(alpha / 2, rel=1e-6)
    assert binom_cdf(k, n, upper) == pytest.approx(alpha / 2, rel=1e-6)
    assert lower < k / n < upper


# ---- chi-square


def test_chi2_sf_reference_values() -> None:
    assert chi2_sf(3.0, 2) == pytest.approx(math.exp(-1.5), rel=1e-12)
    assert chi2_sf(3.841458820694124, 1) == pytest.approx(0.05, rel=1e-9)
    assert chi2_sf(0.0, 5) == 1.0
    # Even df has a closed form: Q = exp(-x/2) * sum_{i < df/2} (x/2)^i / i!
    closed = math.fsum(math.exp(i * math.log(200.0) - math.lgamma(i + 1) - 200.0) for i in range(128))
    assert chi2_sf(400.0, 256) == pytest.approx(closed, rel=1e-9)


def test_leading_zero_gof_on_exact_expectation_is_not_significant() -> None:
    n = 1 << 16
    histogram = [n >> (j + 1) for j in range(16)] + [1]  # geometric counts, exact up to the tail
    result = leading_zero_gof(histogram)
    assert result.p_value is not None and result.p_value > 0.99


def test_leading_zero_gof_detects_bias() -> None:
    histogram = [3000, 3000, 1000, 500, 250, 125, 62, 31, 16, 8, 4, 2]
    result = leading_zero_gof(histogram)
    assert result.p_value is not None and result.p_value < 1e-10


def test_uniform_byte_gof_needs_enough_data() -> None:
    assert uniform_byte_gof([1] * 256, "first").p_value is None
    assert uniform_byte_gof([100] * 256, "first").p_value == pytest.approx(1.0)


def test_leading_zero_probabilities_sum_to_one() -> None:
    total = sum(Fraction(1, 2 ** (j + 1)) for j in range(256)) + Fraction(1, 2**256)
    assert total == 1
    assert leading_zero_probability(0) == 0.5


def test_digest_accumulator_roundtrip() -> None:
    acc = DigestAccumulator()
    for digest in (bytes(32), b"\xff" * 32, b"\x01" + bytes(31)):
        acc.add(digest, int.from_bytes(digest, "big"))
    assert acc.total == 3
    assert acc.leading_zero_bits[256] == 1 and acc.leading_zero_bits[0] == 1 and acc.leading_zero_bits[7] == 1
    again = DigestAccumulator.from_dict(acc.to_dict())
    assert again == acc


# ---- multiple testing


def test_holm_reference() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5, 0.001]) == pytest.approx([0.5, 0.002])
    assert holm([]) == []


def test_holm_is_monotone_and_no_less_powerful_than_bonferroni() -> None:
    ps = [0.001, 0.2, 0.012, 0.04, 0.9]
    h, b = holm(ps), bonferroni(ps)
    assert all(hi <= bi + 1e-15 for hi, bi in zip(h, b))
    ordered = [h[i] for i in sorted(range(len(ps)), key=lambda i: ps[i])]
    assert ordered == sorted(ordered)
    with pytest.raises(ValueError):
        adjust(ps, "fdr")


# ---- planning


def test_minimum_detectable_effect_formula() -> None:
    plan = minimum_detectable_effect(500_000, 1 / 256, 0.01, 0.8, tests=10)
    assert plan.expected_successes == pytest.approx(1953.125)
    assert plan.alpha_per_test == pytest.approx(0.001)
    z = 3.2905267314919255 + 0.8416212335729143
    assert plan.min_detectable_relative_effect == pytest.approx(z * math.sqrt((1 - 1 / 256) / (500_000 / 256)), rel=1e-9)
