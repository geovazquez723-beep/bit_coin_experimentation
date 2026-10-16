"""G1-C: A1 rare-refinement residual, exercised with the producer's REAL enclosure width.

The producer certifies each ``U < p`` comparison with 40-digit outward ``Decimal`` enclosures; the
independent verifier uses >= 192-bit enclosures.  If the exact probability lies just outside the
uniform's interval, closer to the edge than the producer's enclosure width, the producer refines
(consumes a further 64-bit block) while the verifier decides at once.  Both reach the SAME decision;
the consumed-block counts differ, so the replayed stream diverges and verification rejects (false
rejection, never false acceptance).  No sampler is modified; the deterministic blocks below are
scripted, not drawn.
"""
from fractions import Fraction
import random

import pytest

from hashlab.candidates import vitter as producer_sampler
from e002_verify import production as v

P2_64 = 2**64


class Quiet(random.Random):
    def __init__(self, blocks):
        self.blocks, self.calls = list(blocks), 0

    def getrandbits(self, k):
        assert k == 64
        self.calls += 1
        return self.blocks.pop(0)


def threshold_below_edge(shift, k=0x5555555555555555):
    """Exact probability just BELOW the interval's lower edge k/2**64 by 2**-shift."""
    return Fraction(k * 2 ** (shift - 64) - 1, 2**shift), k


@pytest.mark.parametrize('shift', [100, 120, 140, 150, 180])
def test_producer_refines_inside_its_width_but_decides_alike(shift):
    p, k = threshold_below_edge(shift)
    assert Fraction(k, P2_64) > p and Fraction(k, P2_64) - p == Fraction(1, 2**shift)
    num, den = p.numerator, p.denominator
    producer = producer_sampler._Uniform(Quiet([k, 2**62, 2**62]))
    verifier = v.Uniform(Quiet([k, 2**62, 2**62]))
    a = producer.compare(lambda b: b.ratio(num, den))
    b = verifier.less(lambda prec: v._ratio(num, den, prec))
    assert a == b is False                       # U >= low > p: not less; identical decision
    assert verifier.bits == 64                   # verifier's enclosure resolves the 2**-shift gap at once
    # gaps of 2**-100 / 2**-120 (~1e-30 / ~1e-36) exceed the producer's ~1e-39 width, so it decides with one block;
    # gaps of 2**-140 and below (<= ~1e-42) fall inside it, so it refines.
    assert producer.bits == (64 if shift <= 120 else 128)


def test_extra_consumed_block_changes_the_downstream_stream():
    """Why a width mismatch is detectable: one extra consumed block shifts every later draw."""
    stream = random.Random(2026)
    draws = [stream.getrandbits(64) for _ in range(8)]
    producer_view = draws[:2] + draws[3:]        # the producer consumed block 2 as a refinement
    verifier_view = draws[:2] + draws[2:]
    assert producer_view != verifier_view[:len(producer_view)]
    assert next(i for i, (x, y) in enumerate(zip(producer_view, verifier_view)) if x != y) == 2


def test_per_run_probability_bound_arithmetic():
    """Derivation of the documented ~1e-28 bound (bounded arithmetic, not a measurement)."""
    half_width = Fraction(3, 10**38)             # producer relative half-width ceiling after a 143-term product
    per_comparison = 4 * half_width              # two interval edges, two-sided window
    comparisons = 4 * 30_000_000                 # 4 certified comparisons/output (G1-B measurement) x 30 M selections
    bound = float(per_comparison * comparisons)
    assert bound < 1e-28
