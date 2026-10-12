"""Algorithm D engineering checks, exact finite-law checks and numeric probes."""

from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import combinations
from math import comb
import random
import tracemalloc

import pytest

from hashlab.candidates import vitter as d
from hashlab.experiments.exp002 import sample_ranks, engineering_arm_stream, A1_SIZE


@pytest.mark.parametrize('N', range(1, 14))
def test_every_tiny_geometry(N):
    for n in range(N+1):
        for seed in range(10):
            ranks = list(d.vitter_ranks(N,n,seed=seed))
            assert len(ranks) == len(set(ranks)) == n
            assert ranks == sorted(ranks)
            assert all(0 <= r < N for r in ranks)


def exact_mass(N, n, skip):
    product = Fraction(n,N)
    for a,b in d._mass_factors(N,n,skip):
        product *= Fraction(a,b)
    return product


@pytest.mark.parametrize('N,n', [(N,n) for N in range(2,14) for n in range(2,N+1)] + [(27,2),(80,3)])
def test_exact_skip_mass_and_rejection_envelope(N,n):
    masses = []
    for s in range(N-n+1):
        expected = Fraction(comb(N-s-1,n-1),comb(N,n))
        actual = exact_mass(N,n,s)
        assert actual == expected
        masses.append(actual)
        if n < N:
            q = Fraction(N-n,N-1)
            cg = Fraction(n,N) * q**s
            h = Fraction(n,N) * Fraction(N-n-s+1,N-1)**s
            assert 0 <= h <= actual <= cg
            accept = actual/cg
            bounds = d._acceptance(d._Bounds(80),N,n,s)
            assert Fraction(bounds[0]) <= accept <= Fraction(bounds[1])
            squeeze = d._survival(d._Bounds(80),N-n-s+1,N-n,s)
            assert Fraction(squeeze[0]) <= h/cg <= Fraction(squeeze[1])
            # Production rejection kernel: proposal g, acceptance f/(c*g).
            g = Fraction(n-1,N-1) * q**s
            c = Fraction(n*(N-1),(n-1)*N)
            assert g * accept == actual/c
    assert sum(masses) == 1


@pytest.mark.parametrize('N', range(1,9))
def test_exact_combinatorial_subset_and_inclusion_probabilities(N):
    for n in range(N+1):
        probabilities = {}
        for subset in combinations(range(N),n):
            probability = Fraction(1)
            remaining, need, offset = N,n,0
            for rank in subset:
                skip = rank-offset
                probability *= exact_mass(remaining,need,skip)
                remaining -= skip+1
                need -= 1
                offset = rank+1
            probabilities[subset] = probability
        assert set(probabilities.values()) == {Fraction(1,comb(N,n))}
        for value in range(N):
            assert sum(p for subset,p in probabilities.items() if value in subset) == Fraction(n,N)
        for a,b in combinations(range(N),2):
            assert sum(p for subset,p in probabilities.items() if a in subset and b in subset) == Fraction(n*(n-1),N*(N-1))


def test_independent_algorithm_s_exact_path_enumeration(monkeypatch):
    # Enumerate the actual integer Algorithm S reference's random branches,
    # not a Monte Carlo frequency test. Keep the stage RNG deterministic here.
    class Branch(Exception):
        def __init__(self, upper):
            self.upper = upper

    class Select:
        def __init__(self, path):
            self.path = iter(path)
        def randrange(self, upper):
            try:
                return next(self.path)
            except StopIteration:
                raise Branch(upper)

    class Stage:
        def randrange(self, upper):
            return 0

    for N in range(1,6):
        for n in range(N+1):
            results = defaultdict(Fraction)
            pending = [((),Fraction(1))]
            while pending:
                path,weight = pending.pop()
                monkeypatch.setattr('hashlab.experiments.exp002.random.Random',
                                    lambda seed: Select(path) if seed==0 else Stage())
                try:
                    ranks = tuple(r for _,r in sample_ranks(N,n,0,selection_seed=0,stage_seed=1))
                    results[ranks] += weight
                except Branch as branch:
                    pending.extend((path+(v,),weight/branch.upper) for v in range(branch.upper))
            assert len(results) == comb(N,n)
            assert set(results.values()) == {Fraction(1,comb(N,n))}
            # D's independently derived sequential masses must give the same law.
            for ranks,p in results.items():
                remaining,need,offset,actual = N,n,0,Fraction(1)
                for rank in ranks:
                    actual *= exact_mass(remaining,need,rank-offset)
                    remaining,need,offset = remaining-(rank-offset)-1,need-1,rank+1
                assert actual == p


@pytest.mark.parametrize('kwargs', [dict(size=0,count=0,seed=0), dict(size=10,count=11,seed=0),
    dict(size=10,count=-1,seed=0),dict(size=True,count=1,seed=0),dict(size=10,count=1.0,seed=0),
    dict(size=10,count=1,seed=True),dict(size=10,count=1,seed=-1),
    dict(size=A1_SIZE+1,count=1,seed=0),dict(size=10,count=1,seed=2**64)])
def test_invalid_arguments(kwargs):
    with pytest.raises(d.SamplingError):
        list(d.vitter_ranks(**kwargs))


def test_replay_and_stage_allocation():
    expected = [5,298,308,589,705,709,761,825,927,965]
    assert list(d.vitter_ranks(1000,10,seed=7)) == expected
    assert list(d.vitter_ranks(1000,10,seed=7)) == expected
    rows = list(d.a1_sample_ranks(100,2,2,selection_seed=7,stage_seed=8))
    assert rows == [('D',1),('V',11),('V',87),('D',89)]
    assert Counter(stage for stage,_ in rows) == {'D':2,'V':2}
    different_split = list(d.a1_sample_ranks(100,2,2,selection_seed=7,stage_seed=10))
    assert [r for _,r in rows] == [r for _,r in different_split]
    assert len(set(r for _,r in rows)) == 4
    candidates = list(engineering_arm_stream('A1',100,2,2,selection_seed=7,stage_seed=8))
    assert [(stage,int.from_bytes(candidate,'big')-2**20) for stage,candidate in candidates] == rows


def test_empty_full_singleton_and_exhaustion():
    assert list(d.vitter_ranks(10,0,seed=0)) == []
    assert list(d.vitter_ranks(10,10,seed=0)) == list(range(10))
    iterator = d.vitter_ranks(1,1,seed=0)
    assert next(iterator) == 0
    with pytest.raises(StopIteration):
        next(iterator)
    for D,V in [(0,7),(7,0),(3,4)]:
        rows = list(d.a1_sample_ranks(10,D,V,selection_seed=1,stage_seed=2))
        assert sum(s=='D' for s,_ in rows) == D
        assert sum(s=='V' for s,_ in rows) == V
    with pytest.raises(d.SamplingError):
        list(d.a1_sample_ranks(10,6,5,selection_seed=0,stage_seed=0))


def test_numeric_edges_and_ambient_decimal_context():
    class Bits:
        def __init__(self, blocks):
            self.blocks = iter(blocks)
        def getrandbits(self,n):
            return next(self.blocks)
    # U's first interval straddles the exact half boundary. Refinement must
    # keep its prefix, rather than discard/redraw it or decide via rounding.
    below = d._Uniform(Bits([2**63-1,0]))
    assert below.compare(lambda b: b.ratio(1,2))
    assert below.bits == 128
    above = d._Uniform(Bits([2**63,2**63]))
    assert not above.compare(lambda b: b.ratio(1,2))
    assert above.bits == 128
    baseline = list(d.vitter_ranks(1000,10,seed=7))
    with localcontext() as ctx:
        ctx.prec = 2
        assert list(d.vitter_ranks(1000,10,seed=7)) == baseline
    bounds = d._Bounds(40)
    with pytest.raises(d.SamplingError):
        bounds.ratio(1,0)


def test_fail_closed_bad_rng_and_refinement_cap():
    class Zero:
        def getrandbits(self,n):
            return 0
    class Bad:
        def getrandbits(self,n):
            return True
    with pytest.raises(d.SamplingError):
        d._Uniform(Bad())
    with pytest.raises(d.SamplingError,match='4096 bits'):
        d._Uniform(Zero()).compare(lambda b: b.ratio(0,1))


def test_fail_closed_rejection_cap(monkeypatch):
    monkeypatch.setattr(d,'_geometric_skip',lambda *args: None)
    with pytest.raises(d.SamplingError,match='rejection limit'):
        d._skip(100,2,random.Random(0))


def test_explicit_d2_d4_paths(monkeypatch):
    class Bits:
        def __init__(self, values):
            self.values = iter(values)
        def getrandbits(self,n):
            return next(self.values)
    # An exceptionally small proposal U lies in the forbidden tail: reject it,
    # never clamp it to the final eligible rank.
    assert d._geometric_skip(40,2,Bits([0])) is None
    original = d._acceptance
    calls = []
    def acceptance(*args):
        calls.append(args[3])
        return original(*args)
    monkeypatch.setattr(d,'_acceptance',acceptance)
    monkeypatch.setattr(d,'_geometric_skip',lambda *args: 30)
    assert d._skip(40,2,Bits([2**62])) == 30  # D3 fails, D4 accepts.
    assert calls == [30]
    calls.clear()
    proposals = iter([30,0])
    monkeypatch.setattr(d,'_geometric_skip',lambda *args: next(proposals))
    assert d._skip(40,2,Bits([3*2**62,2**63])) == 0  # D4 rejects, redraws D2.
    assert calls == [30]
    with pytest.raises(d.SamplingError,match='exhausted'):
        d._Uniform(Bits([]))


def test_singleton_exact_endpoints():
    class Endpoint:
        def __init__(self, last):
            self.last = last
        def randrange(self, upper):
            return upper-1 if self.last else 0
    assert d._skip(20,1,Endpoint(False)) == 0
    assert d._skip(20,1,Endpoint(True)) == 19


def test_search_hint_cannot_change_sample(monkeypatch):
    expected = list(d.vitter_ranks(1000,10,seed=7))
    monkeypatch.setattr(d,'_geometric_hint',lambda *args: -1)
    assert list(d.vitter_ranks(1000,10,seed=7)) == expected


def test_every_geometric_support_interval():
    class Bits:
        def __init__(self, value):
            self.value = value
        def getrandbits(self,n):
            return self.value
    q = Fraction(38,39)
    for skip in range(39):
        midpoint = (q**skip + q**(skip+1))/2
        block = int(midpoint * 2**64)
        assert d._geometric_skip(40,2,Bits(block)) == skip


@pytest.mark.parametrize('precision', [2,10,40])
def test_interval_power_enclosure(precision):
    b = d._Bounds(precision)
    for a,denominator in [(0,1),(1,3),(38,39),(999,1000)]:
        for exponent in [0,1,2,17,100]:
            low,high = d._survival(b,a,denominator,exponent)
            exact = Fraction(a,denominator)**exponent
            assert Fraction(low) <= exact <= Fraction(high)


def test_no_sample_retention():
    def peak(n):
        tracemalloc.start()
        for _ in d.vitter_ranks(20000,n,seed=7):
            pass
        value = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        return value
    small,large = peak(100),peak(1000)
    assert large < small + 32768
    assert large < 100000


def test_algorithm_s_and_d_empirical_comparison():
    counts_d,counts_s = Counter(),Counter()
    for seed in range(1000):
        counts_d.update(d.vitter_ranks(40,2,seed=seed))
        counts_s.update(r for _,r in sample_ranks(40,2,0,selection_seed=seed,stage_seed=0))
    assert all(25 <= counts_d[r] <= 80 for r in range(40))
    assert all(25 <= counts_s[r] <= 80 for r in range(40))
    # Supporting distributional check only; the exact-law tests are separate.
