"""Statistical inference (exact binomial, chi-square, multiple testing) and digest summaries."""

from hashlab.statistics.distribution import (
    DigestAccumulator,
    GoodnessOfFit,
    leading_zero_gof,
    leading_zero_probability,
    uniform_byte_gof,
)
from hashlab.statistics.inference import (
    adjust,
    binom_cdf,
    binom_sf,
    binom_test,
    bonferroni,
    chi2_sf,
    clopper_pearson,
    holm,
    minimum_detectable_effect,
)

__all__ = [
    "DigestAccumulator",
    "GoodnessOfFit",
    "adjust",
    "binom_cdf",
    "binom_sf",
    "binom_test",
    "bonferroni",
    "chi2_sf",
    "clopper_pearson",
    "holm",
    "leading_zero_gof",
    "leading_zero_probability",
    "minimum_detectable_effect",
    "uniform_byte_gof",
]
