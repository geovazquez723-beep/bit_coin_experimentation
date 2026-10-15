"""Independent full-domain reconstruction vs accepted producers. Bounded public vectors only.

No production-density stream, QA2, E001 reconstruction or real E002 hashing occurs here.
"""
from fractions import Fraction
from itertools import islice
from math import comb
import dataclasses
import random

import pytest

from hashlab.candidates.vitter import a1_sample_ranks
from hashlab.experiments import exp002 as e1
from hashlab.experiments.exp002 import A1_SIZE, HammingPopulation, a2_key, a2_prefix, arm_subseed, sample_ranks
from hashlab.experiments.exp002_controls import (ByteStream80, ControlEngine, Feistel64, control_keys)
from hashlab.experiments.exp002_foundation import LIMITS
from hashlab.experiments.exp002_kernel_plan import derive_master
from e002_verify import production as v
from e002_verify import core as ref_core


# ---------------------------------------------------------------- seeds/keys

@pytest.mark.parametrize('commit,round_number,randomness', [
    ('0'*40, 1, '0'*64), ('0123456789abcdef0123456789abcdef01234567', 42, 'ff'*32)])
def test_master_derivation_public_vectors_agree(commit, round_number, randomness):
    assert v.master_from_beacon(commit, round_number, randomness) == derive_master(commit, round_number, randomness)


@pytest.mark.parametrize('args', [('a'*39, 1, '0'*64), ('A'*40, 1, '0'*64), ('0'*40, True, '0'*64),
                                  ('0'*40, 0, '0'*64), ('0'*40, 2**64, '0'*64), ('0'*40, 1, 'F'*64), ('0'*40, 1, '0'*63)])
def test_master_derivation_rejects_malformed(args):
    with pytest.raises(ValueError):
        v.master_from_beacon(*args)


@pytest.mark.parametrize('master', [0, 1, 0x1becffc4219d959c, 2**64-1])
@pytest.mark.parametrize('domain', ['experiment-002', 'experiment-002-kat'])
def test_all_derived_keys_agree_for_production_and_engineering_domains(master, domain):
    s = v.seeds(master, domain)
    for arm, key in (('A1', 'a1'), ('A3', 'a3')):
        assert s[key] == (arm_subseed(master, arm, 'selection'), arm_subseed(master, arm, 'stage-allocation'))
    assert s['a2_key'] == a2_key(master, domain)
    assert (s['n1_key'], s['n2_key']) == control_keys(master, domain)


def test_domains_separate_keys_and_unknown_domain_rejected():
    assert v.seeds(0, 'experiment-002')['a2_key'] != v.seeds(0, 'experiment-002-kat')['a2_key']
    assert v.seeds(0, 'experiment-002')['a1'] == v.seeds(0, 'experiment-002-kat')['a1']   # approved A1/A3 label set
    with pytest.raises(ValueError):
        v.seeds(0, 'experiment-002-qa2')
    with pytest.raises(ValueError):
        v.derive(2**64, 'x')


# ------------------------------------------------------------------- A1

def test_frozen_geometry_constants_agree_with_producer():
    assert v.FROZEN.a1_size == A1_SIZE and v.A3_CLASS_SIZE == HammingPopulation().size
    assert v.FROZEN.quotas() == {(a, s): n for a, s, n in LIMITS}
    assert v.FROZEN.evaluations() == 180_200_000 and v.FROZEN.blocks() == 240_200_000
    assert v.class_size() == HammingPopulation().size == 82_128_984
    assert v.BOUNDED.evaluations() == 78 and v.BOUNDED.blocks() == 106


def test_dense_fixture_matches_accepted_independent_i1_reference():
    reference = list(ref_core.a1_ranks())
    # I1's reference draws 32+32 samples of 256 under seeds 101/102.
    assert [(s, r) for s, r in v.a1_ranks(256, 32, 32, 101, 102)] == reference


A1_CASES = [(256, 32, 32, 101, 102), (257, 3, 4, 1, 2), (1000, 40, 35, 9, 10),
            (100_000, 250, 250, 5, 6), (100_000, 3000, 3000, 5, 6), (572_000, 2000, 2000, 7, 8),
            (A1_SIZE, 4, 4, 11, 12), (A1_SIZE, 50, 50, 3, 4), (A1_SIZE, 1, 0, 3, 4), (A1_SIZE, 0, 1, 3, 4)]


@pytest.mark.parametrize('N,d,vv,sel,stg', A1_CASES)
def test_algorithm_d_agrees_with_producer(N, d, vv, sel, stg):
    assert list(v.a1_ranks(N, d, vv, sel, stg)) == list(a1_sample_ranks(N, d, vv, selection_seed=sel, stage_seed=stg))


@pytest.mark.parametrize('master', [0, 0x1becffc4219d959c, 12345678901234567890])
def test_full_domain_a1_with_production_derived_seeds_agrees(master):
    s = v.seeds(master, 'experiment-002')
    expected = list(a1_sample_ranks(A1_SIZE, 12, 12, selection_seed=s['a1'][0], stage_seed=s['a1'][1]))
    observed = list(v.a1_ranks(A1_SIZE, 12, 12, *s['a1']))
    assert observed == expected
    ranks = [r for _, r in observed]
    assert ranks == sorted(set(ranks)) and ranks[-1] < A1_SIZE
    assert sorted(st for st, _ in observed) == ['D']*12 + ['V']*12
    assert [v.a1_ranks(A1_SIZE, 12, 12, *s['a1'])] != []   # lazily constructed repeatedly


def test_a1_boundary_populations_and_exhaustion():
    assert [r for _, r in v.a1_ranks(7, 3, 4, 1, 2)] == list(range(7))            # n == N
    assert len(list(v.a1_ranks(5, 0, 0, 1, 2))) == 0
    one = list(v.a1_ranks(A1_SIZE, 1, 0, 5, 6))
    assert len(one) == 1 and one[0][0] == 'D'


def _exact_f_over_density(N, n, s):
    """f(s)/(n/N) with f the exact hypergeometric skip law, from first principles."""
    return Fraction(comb(N-s-1, n-1), comb(N, n)) * Fraction(N, n)


@pytest.mark.parametrize('N,n', [(40, 3), (101, 6), (1000, 20), (5000, 17), (130, 9)])
def test_algorithm_d_proposals_and_acceptance_equal_the_exact_law(N, n):
    """Exact-law analog: certified enclosures contain the exact D3/D4 probabilities and the
    accepted-skip law g(s)*max(h(s), r(s)) is exactly proportional to the skip pmf."""
    q = Fraction(N-n, N-1)
    total = Fraction(0)
    rejected_by_cap = q ** (N-n+1)
    masses = []
    for s in range(0, N-n+1):
        h = Fraction(N-n-s+1, N-n) ** s
        r = _exact_f_over_density(N, n, s) / (q ** s)
        for make, exact in ((v._survival(N-n-s+1, N-n, s), h), (v._acceptance(N, n, s), r)):
            for precision in (v.P_MIN, 256):
                lo, hi = make(precision)
                lower, upper = Fraction(lo[0]) * Fraction(2) ** lo[1], Fraction(hi[0]) * Fraction(2) ** hi[1]
                assert lower <= exact <= upper
                assert upper - lower <= exact * Fraction(1, 2**(precision-24))
        assert h <= r                         # D3 squeeze never exceeds the D4 ratio
        g = q ** s * (1 - q)
        mass = g * min(Fraction(1), max(h, r))
        masses.append(mass)
        total += mass
    assert rejected_by_cap < 1
    for s, mass in enumerate(masses):
        assert mass / total == Fraction(comb(N-s-1, n-1), comb(N, n))   # exact skip pmf


def test_method_a_survival_matches_exact_survival():
    N, n = 30, 12
    sampler_hits = []
    exact = Fraction(1)
    for skip in range(N-n+1):
        exact *= Fraction(N-n-skip, N-skip)
        sampler_hits.append(exact)
    assert sampler_hits[-1] == 0
    # exact skip pmf from the survival recursion equals the combinatorial pmf
    previous = Fraction(1)
    for skip, surv in enumerate(sampler_hits):
        assert previous - surv == Fraction(comb(N-skip-1, n-1), comb(N, n))
        previous = surv


def test_interval_arithmetic_encloses_exact_values():
    rnd = random.Random(20261014)
    for _ in range(300):
        a, b = rnd.randrange(0, 10**12), rnd.randrange(1, 10**12)
        s = rnd.randrange(0, 400)
        p = rnd.choice((v.P_MIN, 256, 512))
        lo, hi = v._power(v._ratio(a, b, p), s, p)
        exact = Fraction(a, b) ** s
        lower, upper = Fraction(lo[0]) * Fraction(2) ** lo[1], Fraction(hi[0]) * Fraction(2) ** hi[1]
        assert lower <= exact <= upper
        if exact:
            assert (upper - lower) / exact < Fraction(1, 2**(p-20))
    lo, hi = v._div(v._ratio(3, 7, 192), v._ratio(5, 11, 192), 192)
    assert Fraction(lo[0]) * Fraction(2) ** lo[1] <= Fraction(33, 35) <= Fraction(hi[0]) * Fraction(2) ** hi[1]


def test_uniform_certified_comparison_refines_only_on_a_boundary():
    class Fixed(random.Random):
        def __init__(self, blocks): self.blocks = list(blocks)
        def getrandbits(self, k): return self.blocks.pop(0)
    exact_half = Fixed([2**63, 5])      # U interval [1/2, 1/2 + 2**-64] straddles exactly 1/2
    u = v.Uniform(exact_half)
    assert u.less(lambda p: v._ratio(1, 2, p)) is False
    assert u.bits == 128                  # refined once; 64 bits could not certify
    clear = v.Uniform(Fixed([2**62]))
    assert clear.less(lambda p: v._ratio(1, 2, p)) is True and clear.bits == 64


def test_ambiguity_budget_fails_closed():
    class Constant(random.Random):
        def __init__(self): pass
        def getrandbits(self, k): return 0
    u = v.Uniform(Constant())
    with pytest.raises(v.Mismatch):
        u.less(lambda p: ((0, 0), (1, 0)))   # enclosure [0, 1] can never be certified


def test_inclusion_frequencies_are_uniform_for_fixed_public_seeds():
    N, n, seeds = 40, 3, 3000
    counts = [0]*N
    for seed in range(seeds):
        for _, r in v.a1_ranks(N, 2, 1, seed, seed+10**6):
            counts[r] += 1
    expected = seeds * n / N
    chi = sum((c-expected)**2/expected for c in counts)
    assert chi < 73.0          # chi-square, 39 d.f., upper 0.05% critical value is about 73; fixed seeds are deterministic


# ------------------------------------------------------------------- A3

def test_colex_enumerator_matches_accepted_unranking_exhaustively_on_small_geometries():
    for bits, split, weight in ((8, 3, 4), (10, 5, 4), (12, 6, 3), (6, 2, 6)):
        pop = HammingPopulation(bits, split, weight)
        values = list(v.colex_values(bits, split, weight))
        assert len(values) == pop.size == v.class_size(bits, split, weight)
        assert values == [pop.unrank(i) for i in range(pop.size)]
        assert all(pop.rank(x) == i for i, x in enumerate(values))


def test_colex_enumerator_production_prefix_and_class_boundaries():
    values = list(islice(v.colex_values(), 40_000))
    pop = HammingPopulation()
    assert all(values[i] == pop.unrank(i) == ref_core.unrank(i) for i in range(0, 40_000, 7))
    assert values[:3] == [2**32, 2**33, 2**34]
    boundaries, start = [], 0
    for w in range(1, 7):
        size = comb(64, w) - comb(32, w)
        first = 2**32 + 2**(w-1) - 1
        last = sum(2**(63-i) for i in range(w))
        assert ref_core.unrank(start) == pop.unrank(start) == first
        assert ref_core.unrank(start+size-1) == pop.unrank(start+size-1) == last
        boundaries.append(start)
        start += size
    assert start == v.A3_CLASS_SIZE
    gen = v.colex_values()
    assert next(islice(gen, 31, 32)) == 2**63           # last weight-1 value
    assert next(gen) == 2**32 + 1                       # first weight-2 value follows


@pytest.mark.parametrize('size,d,vv,excluded', [
    (4096, 16, 16, tuple(range(12, 40)) + (100, 101, 3000)),
    (4096, 6, 6, (0, 1, 2, 3, 32, 63, 127, 4095)),
    (200, 20, 20, ()), (200, 60, 60, tuple(range(0, 80))),
    (50, 48, 0, (0, 49)), (50, 12, 12, tuple(range(1, 50, 2))), (60, 0, 0, (5,))])
def test_exclusion_aware_algorithm_s_agrees_with_producer(size, d, vv, excluded):
    s = v.seeds(0x1becffc4219d959c, 'experiment-002')['a3']
    expected = list(sample_ranks(size, d, vv, selection_seed=s[0], stage_seed=s[1], excluded=excluded))
    observed = list(v.a3_ranks(size, d, vv, s[0], s[1], excluded))
    assert [(a, b) for a, b, _ in observed] == expected
    pop = HammingPopulation()
    assert all(pop.unrank(rank) == value for _, rank, value in observed)
    assert not {rank for _, rank, _ in observed} & set(excluded)


def test_algorithm_s_rejects_bad_exclusions_and_impossible_samples():
    with pytest.raises(v.Mismatch):
        list(v.a3_ranks(10, 1, 1, 1, 2, (3, 3)))
    with pytest.raises(v.Mismatch):
        list(v.a3_ranks(10, 1, 1, 1, 2, (11,)))
    with pytest.raises(v.Mismatch):
        list(v.a3_ranks(10, 5, 5, 1, 2, (1,)))


def test_real_s14_exclusion_shape_is_consistent_with_rank_enumeration():
    import struct
    from pathlib import Path
    path = Path(__file__).resolve().parents[1]/'results/e001-s14-audit-20261012-01/producer/ranks.bin'
    ranks = [x for x, in struct.iter_unpack('>Q', path.read_bytes())]
    assert len(ranks) == 60721 and ranks == sorted(set(ranks)) and ranks[-1] < v.A3_CLASS_SIZE
    below = tuple(r for r in ranks if r < 4096)
    assert len(below) == 218
    s = v.seeds(0, 'experiment-002')['a3']
    expected = list(sample_ranks(4096, 24, 24, selection_seed=s[0], stage_seed=s[1], excluded=below))
    assert [(a, b) for a, b, _ in v.a3_ranks(4096, 24, 24, s[0], s[1], below)] == expected


# ------------------------------------------------------------------- A2

@pytest.mark.parametrize('domain', ['experiment-002', 'experiment-002-kat'])
def test_a2_prefixes_and_nonce_blocks_agree(domain):
    key = v.seeds(0x1becffc4219d959c, domain)['a2_key']
    prefixes = [v.a2_prefix(key, j) for j in range(3000)]
    assert prefixes == [a2_prefix(key, j) for j in range(3000)] and len(set(prefixes)) == 3000
    assert all(len(p) == 76 for p in prefixes)
    for cluster in (0, 1, 1499, 1500, 2999):
        for nonce in (0, 1, 9999):
            assert e1.a2_candidate(prefixes[cluster], nonce) == prefixes[cluster] + nonce.to_bytes(4, 'little')


# ------------------------------------------------------------- N1 / N2 / P

@pytest.mark.parametrize('domain', ['experiment-002', 'experiment-002-kat'])
def test_feistel_forward_inverse_and_bijection_agree(domain):
    key, _ = control_keys(0x1becffc4219d959c, domain)
    producer = Feistel64(key)
    assert key == v.seeds(0x1becffc4219d959c, domain)['n1_key']
    sources = list(range(0, 24)) + [2**32-1, 2**32, 30_999_998, 2**63, 2**63+1, 2**64-1]
    for source in sources:
        value = v.feistel(key, source)
        assert value == producer.forward(source)
        assert v.feistel(key, value, inverse=True) == source == producer.inverse(value)
    assert len({v.feistel(key, i) for i in range(5000)}) == 5000


@pytest.mark.parametrize('domain', ['experiment-002', 'experiment-002-kat'])
def test_n2_stream_continuity_across_block_boundaries(domain):
    key = control_keys(7, domain)[1]
    stream = v.n2_stream(key)
    reference = ByteStream80(key)
    for index in range(70):          # crosses many 64-byte block / 80-byte record boundaries
        assert next(stream) == reference.next()
    assert reference.raw_index == 70
    resumed = ByteStream80(key, start_raw_index=33)
    assert resumed.next() == next(islice(v.n2_stream(key), 33, 34))


@pytest.mark.parametrize('mode', ['N1', 'N2', 'P1', 'P2+', 'P2-'])
def test_effective_digest_transformations_agree_at_threshold_boundaries(mode):
    engine = ControlEngine(mode)
    assert v.THRESHOLDS[mode] == engine.threshold
    rnd = random.Random(99)
    cases = []
    for value in (0, 1, 2**248-1, 2**248, 2**248+1, 2**256-1, rnd.getrandbits(256)):
        for u in (0, engine.threshold-1 if engine.threshold else 0, engine.threshold, 2**32-1):
            cases.append(((value & ~(2**32-1)) | u).to_bytes(32, 'big'))
    cases += [rnd.getrandbits(256).to_bytes(32, 'big') for _ in range(300)]
    for raw in cases:
        assert v.transform(mode, raw) == bytes.fromhex(engine.transform(raw)['effective_digest_hex'])


def test_structural_reasons_and_historical_membership_logic():
    assert v.structural_mask(2**20) == v.C1 and v.structural_mask(2**32-1) == v.C1
    assert v.structural_mask(2**20-1) == 0 and v.structural_mask(2**32) == v.C3
    assert v.structural_mask(2**32 | 0b11111) == v.C3 and v.structural_mask(2**32 | 0b111111) == 0
    assert v.structural_mask((2**64-1) ^ 1) == 0 and v.structural_mask(0) == 0


# ------------------------------------------------- frozen schedule arguments

def test_frozen_geometry_schedule_arguments_without_production_sampling(monkeypatch):
    seen = {}
    monkeypatch.setattr(v, 'a1_ranks', lambda *a: seen.setdefault('A1', a) and iter(()))
    monkeypatch.setattr(v, 'a3_ranks', lambda *a: seen.setdefault('A3', a) and iter(()))
    tiny = dataclasses.replace(v.FROZEN, a1_stage=15_000_000, a2_clusters=(), control_stage=1, p1=1, p2=1)
    gen = v.attempts(tiny, 0x1becffc4219d959c, frozenset(), (12, 13, 14))
    rows = list(islice(gen, 40))      # drains the stubs, then bounded N1/N2/P rows (quota 1 each)
    s = v.seeds(0x1becffc4219d959c, 'experiment-002')
    assert seen['A1'] == (A1_SIZE, 15_000_000, 15_000_000, *s['a1'])
    assert seen['A3'][:3] == (82_128_984, 15_000_000, 15_000_000) and seen['A3'][3:5] == s['a3']
    assert seen['A3'][5] == (12, 13, 14)
    assert [r[0] for r in rows[:2]] == ['N1', 'N1'] and rows[0][1] == 'D' and rows[1][1] == 'V'
    assert [r[0] for r in rows if r[0] == 'N2'] == ['N2', 'N2']
    positives = [r for r in rows if r[0].startswith('P')]
    assert [r[0] for r in positives] == ['P1', 'P2+', 'P2-'] and [r[4] for r in positives] == [2**63, 2**63+1, 2**63+2]


def test_n1_stage_and_cursor_state_transition_on_injected_history():
    key = v.seeds(0, 'experiment-002-kat')['n1_key']
    banned = {v.feistel(key, 1), v.feistel(key, 3)}
    tiny = dataclasses.replace(v.BOUNDED, a1_stage=1, a2_clusters=(), a3_stage=1, a3_size=64,
                               control_stage=2, p1=1, p2=1)
    rows = [r for r in v.attempts(tiny, 0, frozenset(banned), ()) if r[0] == 'N1']
    assert [(r[1], r[4], r[2], r[5]) for r in rows] == [
        ('D', 0, 0, 0), ('D', 1, v.E001, None), ('D', 2, 0, 1), ('V', 3, v.E001, None), ('V', 4, 0, 0), ('V', 5, 0, 1)]


# ------------------------------- production-parameter public prefix vectors
# Only the first few hundred outputs of lazy generators at the frozen parameters.
# This is a deterministic interface vector, not a production-density stream or benchmark.

@pytest.mark.parametrize('master', [0, 0x1becffc4219d959c])
def test_frozen_parameter_a1_prefix_agrees_with_producer(master):
    s = v.seeds(master, 'experiment-002')
    observed = list(islice(v.a1_ranks(A1_SIZE, 15_000_000, 15_000_000, *s['a1']), 300))
    expected = list(islice(a1_sample_ranks(A1_SIZE, 15_000_000, 15_000_000, selection_seed=s['a1'][0],
                                           stage_seed=s['a1'][1]), 300))
    assert observed == expected
    ranks = [r for _, r in observed]
    assert ranks == sorted(set(ranks)) and ranks[0] < 4000 and ranks[-1] < 300 * 4000


def test_frozen_parameter_a3_prefix_with_real_exclusions_agrees_with_producer():
    import struct
    from pathlib import Path
    path = Path(__file__).resolve().parents[1]/'results/e001-s14-audit-20261012-01/producer/ranks.bin'
    ranks = tuple(x for x, in struct.iter_unpack('>Q', path.read_bytes()))
    s = v.seeds(0x1becffc4219d959c, 'experiment-002')['a3']
    observed = list(islice(v.a3_ranks(v.A3_CLASS_SIZE, 15_000_000, 15_000_000, s[0], s[1], ranks), 500))
    expected = list(islice(sample_ranks(v.A3_CLASS_SIZE, 15_000_000, 15_000_000, selection_seed=s[0], stage_seed=s[1],
                                        excluded=ranks), 500))
    assert [(a, b) for a, b, _ in observed] == expected
    pop = HammingPopulation()
    assert all(pop.unrank(r) == value == ref_core.unrank(r) for _, r, value in observed)
    assert not {r for _, r, _ in observed} & set(ranks)
    assert any(r > 12 for _, r, _ in observed) and observed[0][1] < 100


# ------------------------------------------- injected uniform-boundary reproduction
# The 2**-64 uniform interval can contain a comparison threshold exactly. Scripted 64-bit blocks
# place the interval on the boundary (and on either side of it) so both branches run without
# production-scale generation. Producer and independent verifier must agree on the skip and on
# the number of random blocks consumed.

from hashlab.candidates import vitter as producer_sampler


class Scripted(random.Random):
    def __init__(self, blocks, tail=0x5555555555555555):
        self.blocks, self.calls, self.tail = list(blocks), 0, tail

    def getrandbits(self, k):
        assert k == 64
        self.calls += 1
        return self.blocks.pop(0) if self.blocks else (self.tail ^ (self.calls * 0x9E3779B97F4A7C15)) & (2**64 - 1)

    def randrange(self, n):
        raise AssertionError('not used on this path')


def _floor64(fraction):
    return (fraction.numerator << 64) // fraction.denominator


def _scenarios():
    for N, n in ((1000, 10), (21, 11), (500, 3), (2000, 7), (131, 9), (4000, 20)):
        if 13 * n >= N:
            continue
        q = Fraction(N - n, N - 1)
        for s in range(6):
            proposals = [_floor64(q**s) + d for d in (-1, 0, 1)] if s else [2**64 - 1, 2**64 - 2]
            h = Fraction(N - n - s + 1, N - n) ** s
            for g in proposals:
                for d3 in (_floor64(h) - 1, _floor64(h), _floor64(h) + 1, 0, 2**64 - 1):
                    for d4 in (0, 2**63, 2**64 - 1, 0x1234567890abcdef):
                        yield N, n, [g, d3, d4]


@pytest.mark.parametrize('tail', [1, 0xdeadbeefcafebabe])
def test_injected_boundary_blocks_give_identical_skip_and_random_consumption(tail):
    refined = clear = total = 0
    for N, n, blocks in _scenarios():
        if not all(0 <= b < 2**64 for b in blocks):
            continue
        a, b = Scripted(blocks, tail), Scripted(blocks, tail)
        outcome_a = producer_sampler._skip(N, n, a)
        outcome_b = v._skip(N, n, b)
        assert (outcome_a, a.calls) == (outcome_b, b.calls), (N, n, blocks)
        total += 1
        refined += a.calls > 3
        clear += a.calls <= 3
    assert total > 1000 and refined > 100 and clear > 100       # both branches are really exercised


def test_exact_dyadic_threshold_refines_and_both_resolutions_agree():
    # q = 1023/1024 for N = 4097, n = 5; the geometric proposal compares U with q**s.
    N, n = 4097, 5
    q = Fraction(N - n, N - 1)
    assert q == Fraction(1023, 1024) and 13 * n < N
    for first in (_floor64(q), _floor64(q) - 1, _floor64(q) + 1):
        for second in (0, 2**64 - 1, 2**63):
            a, b = Scripted([first, 2**63, 2**63, second]), Scripted([first, 2**63, 2**63, second])
            assert (producer_sampler._geometric_skip(N, n, a), a.calls) == (v._geometric_skip(N, n, b), b.calls)
    straddle = Scripted([_floor64(q), 5]), Scripted([_floor64(q), 5])
    producer_sampler._geometric_skip(N, n, straddle[0])
    v._geometric_skip(N, n, straddle[1])
    assert straddle[0].calls == straddle[1].calls >= 2            # the exact-threshold interval forced a refinement


def test_enclosure_width_is_the_only_residual_difference_and_it_fails_closed():
    """Mechanism of the residual: the producer certifies with its own enclosure width. If an exact
    probability lies outside the uniform interval but within that width of an edge, the producer
    refines while the verifier (exact to >= 2**-128 relative) decides at once. The probability of
    this per comparison is about twice the enclosure width (< 1e-37). Here the width is injected."""
    from decimal import Decimal
    p = Fraction(1, 3)
    block = -(-(p.numerator << 64) // p.denominator)               # ceil: u_low is just above p
    assert Fraction(block, 2**64) > p
    class Quiet(random.Random):
        def __init__(self, blocks): self.blocks = list(blocks)
        def getrandbits(self, k): return self.blocks.pop(0)
    width = lambda b: Decimal(10) ** -(b.down.prec // 2 - 2)         # injected: ~1e-18 at the producer's first precision, far wider than its real ~1e-39
    exact = Decimal(1) / Decimal(3)
    wide = producer_sampler._Uniform(Quiet([block, 2**62]))
    tight = v.Uniform(Quiet([block, 2**62]))
    assert wide.compare(lambda b: (exact - width(b), exact + width(b))) is False and wide.bits == 128
    assert tight.less(lambda prec: v._ratio(1, 3, prec)) is False and tight.bits == 64
    # Same decision either way; only the consumed-block count differs, which makes the downstream stream
    # disagree and therefore fails closed (a false rejection), never a false acceptance.
    assert wide.bits != tight.bits


def test_uniform_straddle_counts_match_for_every_compare_boundary():
    class Quiet(random.Random):
        def __init__(self, blocks): self.blocks = list(blocks)
        def getrandbits(self, k): return self.blocks.pop(0)
    for numerator, denominator in ((1, 2), (1, 3), (110, 111), (1023, 1024), (5, 7)):
        p = Fraction(numerator, denominator)
        for delta in (-1, 0, 1):
            block = _floor64(p) + delta
            if not 0 <= block < 2**64:
                continue
            first, second = producer_sampler._Uniform(Quiet([block, 2**63])), v.Uniform(Quiet([block, 2**63]))
            bounds = lambda b: b.ratio(numerator, denominator)       # noqa: E731
            assert first.compare(bounds) == second.less(lambda prec: v._ratio(numerator, denominator, prec))
            assert (first.bits, first.prefix) == (second.bits, second.prefix)


def test_hint_agreement_with_producer_on_production_density_states():
    rnd = random.Random(7)
    checked = 0
    while checked < 3000:
        n = rnd.randrange(2, 30_000_000)
        N = min(A1_SIZE, n * rnd.randrange(14, 400))
        if 13 * n >= N:
            continue
        u = producer_sampler._Uniform(random.Random(rnd.getrandbits(64)))
        w = v.Uniform(random.Random())
        w.prefix, w.bits = u.prefix, u.bits
        assert producer_sampler._geometric_hint(N, n, u) == v._hint(N, n, w)
        checked += 1
