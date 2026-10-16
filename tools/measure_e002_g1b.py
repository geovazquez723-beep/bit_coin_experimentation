"""G1-B bounded, non-confirmatory engineering probes for E002 resource qualification.

Every probe runs in its own child process under an external wall-clock cap and uses fixed public
engineering identities (no production seed, no real E002 stream, no beacon). Limits are predeclared
in ``PROBES`` and are never extended or retried based on observed values. Results are JSON files under
the output directory; nothing here changes a candidate-selection law.

    python tools/measure_e002_g1b.py run <probe> --out DIR [--audit DIR] [--io-dir DIR]
    python tools/measure_e002_g1b.py environment --out DIR
"""
import argparse
import json
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'src'), str(Path(__file__).resolve().parent)]

A1_N = 2**32 - 2**20                 # frozen A1 population 4,293,918,720
A1_SELECT = 15_000_000               # per stage; 30,000,000 total
A3_N = 82_128_984
A1_SEEDS = (101, 102)                # public engineering sub-seeds (as in the retained I-series fixtures)
A3_SEEDS = (201, 202)
N2_PREFIX_KEY = b'E002-I1!'

# name: (hard external cap seconds, soft in-process cap, work bound description)
PROBES = {
    'a1-producer-1k':     dict(cap=30, work='first 1,000 emitted A1 ranks (production Algorithm D)'),
    'a1-verifier-1k':     dict(cap=30, work='first 1,000 emitted A1 ranks (independent interval implementation)'),
    'a1-producer-10k':    dict(cap=60, work='first 10,000 emitted A1 ranks (single predeclared continuation)'),
    'a1-verifier-10k':    dict(cap=60, work='first 10,000 emitted A1 ranks (single predeclared continuation)'),
    'a1-late-producer':   dict(cap=60, work='synthetic remaining-population states, same N/n geometry'),
    'a1-late-verifier':   dict(cap=60, work='synthetic remaining-population states, same N/n geometry'),
    'a3':                 dict(cap=30, work='<=100,000 ranks scanned, <=10,000 emitted'),
    'controls':           dict(cap=30, work='<=100,000 inversions, <=10,000 emitted per component'),
    'serialize':          dict(cap=60, work='<=10,000 artificial evidence rows, <=10,000 hash evaluations'),
    'hash-producer':      dict(cap=60, work='<=10,000 public-input evaluations (OpenSSL)'),
    'hash-verifier':      dict(cap=60, work='<=10,000 public-input evaluations (independent backend)'),
    'disk-io':            dict(cap=60, work='<=256 MiB disposable files on the target volume'),
}


def peak_rss():
    from qualify_e002_i3 import peak_rss as probe
    return probe()


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(p * len(values)))] if values else None


def dist(values):
    if not values:
        return None
    return dict(n=len(values), mean=sum(values) / len(values), min=min(values), p50=pct(values, .5),
                p90=pct(values, .9), p99=pct(values, .99), max=max(values))


class Clock:
    """Soft in-process deadline (hard cap is enforced externally by the driver)."""
    def __init__(self, soft):
        self.start = time.perf_counter()
        self.soft = soft

    def elapsed(self):
        return time.perf_counter() - self.start

    def expired(self):
        return self.elapsed() >= self.soft


def timed(fn, *args):
    t = time.perf_counter()
    value = fn(*args)
    return value, time.perf_counter() - t


# ------------------------------------------------------------------------------------------ A1

class CountingRandom(random.Random):
    tally = {}

    def __init__(self, seed=None):
        super().__init__(seed)
        self.tag = seed

    def getrandbits(self, k):
        CountingRandom.tally[self.tag] = CountingRandom.tally.get(self.tag, 0) + 1
        return super().getrandbits(k)


def _instrument_producer():
    import types
    from hashlab.candidates import vitter as V
    counts = dict(compare=0, refine=0, bounds=0, geometric=0, method_a=0, hint=0, max_precision=0)
    V.random = types.SimpleNamespace(Random=CountingRandom)
    orig = dict(compare=V._Uniform.compare, refine=V._Uniform.refine, binit=V._Bounds.__init__,
                geometric=V._geometric_skip, method_a=V._method_a_skip, hint=V._geometric_hint)

    def compare(self, probability):
        counts['compare'] += 1
        return orig['compare'](self, probability)

    def refine(self):
        counts['refine'] += 1
        return orig['refine'](self)

    def binit(self, precision):
        counts['bounds'] += 1
        counts['max_precision'] = max(counts['max_precision'], precision)
        return orig['binit'](self, precision)

    def geometric(N, n, rng):
        counts['geometric'] += 1
        return orig['geometric'](N, n, rng)

    def method_a(N, n, rng):
        counts['method_a'] += 1
        return orig['method_a'](N, n, rng)

    def hint(N, n, uniform):
        counts['hint'] += 1
        return orig['hint'](N, n, uniform)

    V._Uniform.compare, V._Uniform.refine, V._Bounds.__init__ = compare, refine, binit
    V._geometric_skip, V._method_a_skip, V._geometric_hint = geometric, method_a, hint
    return V, counts


def probe_a1(side, limit, soft):
    import hashlib
    clock = Clock(soft)
    rss0 = peak_rss()
    CountingRandom.tally.clear()
    if side == 'producer':
        V, counts = _instrument_producer()
        generator = V.a1_sample_ranks(A1_N, A1_SELECT, A1_SELECT, selection_seed=A1_SEEDS[0], stage_seed=A1_SEEDS[1])
    else:
        import types
        from e002_verify import production as P
        counts = {}
        P.random = types.SimpleNamespace(Random=CountingRandom)
        generator = P.a1_ranks(A1_N, A1_SELECT, A1_SELECT, A1_SEEDS[0], A1_SEEDS[1])
    per = []                      # (seconds, compare, bounds, refine, geometric)
    ranks, stages = [], []
    names = ('compare', 'bounds', 'refine', 'geometric')
    last = {k: counts.get(k, 0) for k in names}
    status = 'limit-reached'
    while len(ranks) < limit:
        if clock.expired():
            status = 'soft-cap-reached'
            break
        t = time.perf_counter()
        stage, rank = next(generator)
        dt = time.perf_counter() - t
        now = {k: counts.get(k, 0) for k in names}
        per.append((dt,) + tuple(now[k] - last[k] for k in names))
        last = now
        ranks.append(rank)
        stages.append(stage)
    seconds = [p[0] for p in per]
    blocks = dict(CountingRandom.tally)
    sel_blocks = blocks.get(A1_SEEDS[0], 0)
    out = dict(emitted=len(ranks), status=status, wall_seconds=clock.elapsed(),
               microseconds_per_output=dict(mean=1e6 * sum(seconds) / max(1, len(seconds)),
                                            distribution_us={k: v * 1e6 for k, v in dist(seconds).items() if k != 'n'} if seconds else None),
               selection_getrandbits64_calls=sel_blocks,
               selection_blocks_per_output=sel_blocks / max(1, len(ranks)),
               stage_getrandbits_calls=blocks.get(A1_SEEDS[1], 0),
               ranks_sha256=hashlib.sha256(b''.join(r.to_bytes(8, 'big') for r in ranks)).hexdigest(),
               first_ranks=ranks[:5], last_rank=ranks[-1] if ranks else None,
               stage_D_count=stages.count('D'), peak_rss_bytes=peak_rss(), rss_before_bytes=rss0,
               state=dict(note='early stream only: n=30,000,000 at start, remaining n decreases by one per output',
                          N_over_n_at_start=A1_N / (2 * A1_SELECT)))
    if side == 'producer' and per:
        for i, k in enumerate(names, 1):
            column = [p[i] for p in per]
            out['per_output_' + k] = dist(column)
            hist = {}
            for v in column:
                hist[v] = hist.get(v, 0) + 1
            out['histogram_' + k] = dict(sorted(hist.items())[:40])
        out['total_counts'] = {k: counts[k] for k in counts}
        order = sorted(range(len(per)), key=lambda i: -per[i][0])[:5]
        out['slowest_outputs'] = [dict(output=i, microseconds=per[i][0] * 1e6, compare=per[i][1], bounds=per[i][2],
                                       refine=per[i][3], geometric=per[i][4]) for i in order]
        # Expensive-operation breakdown, measured on the same instrumented run:
        out['max_precision_digits'] = counts['max_precision']
    return out


def probe_a1_late(side, soft):
    """Synthetic remaining-population states preserving N/n; clearly not the real stream."""
    clock = Clock(soft)
    states = [(4_293_919, 30_000, 2000), (42_939, 300, 300), (1_431, 10, 10), (130, 10, 10), (26, 2, 2)]
    result = []
    if side == 'producer':
        from hashlab.candidates.vitter import vitter_ranks as gen
    else:
        from e002_verify.production import vitter_ranks as gen
    for N, n, take in states:
        if clock.expired():
            result.append(dict(N=N, n=n, status='skipped-soft-cap'))
            continue
        if side == 'producer':
            it = gen(N, n, seed=7001)
        else:
            it = gen(N, n, 7001)
        times, got = [], 0
        t0 = time.perf_counter()
        for _ in range(take):
            if clock.expired():
                break
            t = time.perf_counter()
            try:
                next(it)
            except StopIteration:
                break
            times.append(time.perf_counter() - t)
            got += 1
        result.append(dict(N=N, n=n, ratio=N / n, requested=take, emitted=got, seconds=time.perf_counter() - t0,
                           microseconds_per_output=dist([x * 1e6 for x in times])))
    return dict(label='SYNTHETIC remaining-population probe; not a measurement of the real late stream',
                states=result, wall_seconds=clock.elapsed(), peak_rss_bytes=peak_rss())


# ------------------------------------------------------------------------------------------ A3

def probe_a3(audit, soft):
    import bisect
    from math import comb
    from hashlab.experiments.exp002 import HammingPopulation, sample_ranks
    from hashlab.experiments.exp002_s14 import load_s14
    from hashlab.experiments.exp002_kernel_evidence import Attempt
    from e002_verify import production as P
    out = {}
    history, out['authenticate_and_load_exclusions_seconds'] = timed(load_s14, audit, REPO)
    excluded = history.exclusions.ranks
    population = history.exclusions.population
    clock = Clock(soft)
    scanned_limit, emit_limit = 100_000, 10_000
    # (a) producer Algorithm S scan with real exclusions
    ranks, stages = [], []
    t0 = time.perf_counter()
    for stage, rank in sample_ranks(A3_N, A1_SELECT, A1_SELECT, selection_seed=A3_SEEDS[0], stage_seed=A3_SEEDS[1],
                                    excluded=excluded):
        if rank >= scanned_limit or len(ranks) >= emit_limit or clock.expired():
            break
        ranks.append(rank)
        stages.append(stage)
    scan_seconds = time.perf_counter() - t0
    last = ranks[-1]
    ex_in_range = bisect.bisect_right(excluded, last)
    out['producer_scan'] = dict(emitted=len(ranks), ranks_scanned_through=last, exclusions_in_scanned_range=ex_in_range,
                                seconds=scan_seconds, microseconds_per_emitted=1e6 * scan_seconds / len(ranks),
                                microseconds_per_scanned_rank=1e6 * scan_seconds / (last + 1))
    # decomposition by replaying the identical two RNG streams without the generator body
    sel, stg = random.Random(A3_SEEDS[0]), random.Random(A3_SEEDS[1])
    remaining = A3_N - len(excluded)
    t = time.perf_counter()
    for _ in range(last + 1 - ex_in_range):
        sel.randrange(remaining)
    out['selection_randrange_only_microseconds_per_scanned_rank'] = 1e6 * (time.perf_counter() - t) / (last + 1 - ex_in_range)
    t = time.perf_counter()
    need = 2 * A1_SELECT
    for _ in ranks:
        stg.randrange(need)
    out['stage_randrange_only_microseconds_per_emitted'] = 1e6 * (time.perf_counter() - t) / len(ranks)
    # (b) producer unrank / encode / kernel-eligibility rank check on the emitted early ranks
    values, secs = timed(lambda: [population.unrank(r) for r in ranks])
    out['producer_unrank_early_ranks_us'] = 1e6 * secs / len(ranks)
    wsum = {}
    for v in values:
        wsum[v.bit_count()] = wsum.get(v.bit_count(), 0) + 1
    out['emitted_weight_histogram'] = dict(sorted(wsum.items()))
    encoded, secs = timed(lambda: [v.to_bytes(8, 'big') for v in values])
    out['encode_to_bytes_us'] = 1e6 * secs / len(ranks)
    attempts = []
    t = time.perf_counter()
    counters = {'D': 0, 'V': 0}
    for s, e, r in zip(stages, encoded, ranks):
        attempts.append(Attempt('A3', s, e, counters[s], population_rank=r))
        counters[s] += 1
    out['attempt_construction_us'] = 1e6 * (time.perf_counter() - t) / len(ranks)
    t = time.perf_counter()
    for a, r in zip(attempts, ranks):
        at = bisect.bisect_left(excluded, r)
        assert not (at < len(excluded) and excluded[at] == r) and population.rank(int.from_bytes(a.candidate, 'big')) == r
    out['kernel_eligibility_rank_check_us'] = 1e6 * (time.perf_counter() - t) / len(ranks)
    # (c) representativeness: 10,000 evenly spaced ranks across the full population (NOT a scan, no sampling)
    spaced = [i * (A3_N // emit_limit) for i in range(emit_limit)]
    spaced_values, secs = timed(lambda: [population.unrank(r) for r in spaced])
    out['SYNTHETIC_unrank_evenly_spaced_across_population_us'] = 1e6 * secs / len(spaced)
    _, secs = timed(lambda: [population.rank(v) for v in spaced_values])
    out['SYNTHETIC_rank_evenly_spaced_across_population_us'] = 1e6 * secs / len(spaced)
    w = {}
    for v in spaced_values:
        w[v.bit_count()] = w.get(v.bit_count(), 0) + 1
    out['SYNTHETIC_spaced_weight_histogram'] = dict(sorted(w.items()))
    # (d) verifier: Algorithm S with incremental Gosper enumeration, same bounds
    ver, t0 = [], time.perf_counter()
    for stage, rank, value in P.a3_ranks(A3_N, A1_SELECT, A1_SELECT, A3_SEEDS[0], A3_SEEDS[1], excluded):
        if rank >= scanned_limit or len(ver) >= emit_limit or clock.expired():
            break
        ver.append((stage, rank, value))
    vs = time.perf_counter() - t0
    out['verifier_scan'] = dict(emitted=len(ver), seconds=vs, microseconds_per_emitted=1e6 * vs / len(ver),
                                matches_producer_ranks=[r for _, r, _ in ver] == ranks[:len(ver)],
                                matches_producer_values=[v for _, _, v in ver] == values[:len(ver)])
    # Gosper stepping in isolation: early weights and (SYNTHETIC position) the weight-6 region
    it = P.colex_values()
    t = time.perf_counter()
    for _ in range(scanned_limit):
        next(it)
    out['verifier_gosper_early_us_per_value'] = 1e6 * (time.perf_counter() - t) / scanned_limit
    start6 = (1 << 32) | ((1 << 5) - 1)
    c = lambda v: v & -v
    value, t = start6, time.perf_counter()
    for _ in range(scanned_limit):
        cc = value & -value
        r_ = value + cc
        value = (((r_ ^ value) >> 2) // cc) | r_
    out['SYNTHETIC_verifier_gosper_weight6_us_per_value'] = 1e6 * (time.perf_counter() - t) / scanned_limit
    # verifier independent decoders (cross-check path)
    sub = ranks[:2000]
    _, secs = timed(lambda: [P._colex_unrank(r) for r in sub])
    out['verifier_colex_unrank_early_us'] = 1e6 * secs / len(sub)
    _, secs = timed(lambda: [P._colex_rank(v) for v in values[:2000]])
    out['verifier_colex_rank_early_us'] = 1e6 * secs / len(sub)
    out['wall_seconds_measured_sections'] = clock.elapsed()
    out['peak_rss_bytes'] = peak_rss()
    return out


# ------------------------------------------------------------------------------------------ controls

def probe_controls(audit, soft):
    import struct
    from hashlab.experiments.exp002_controls import (Feistel64, control_keys, PermutationControls, N2Controls,
                                                     ControlGeometry, ByteStream80, inverse_history, N1_STOP, P_START)
    from hashlab.experiments.exp002 import in_a1, in_a3, a2_prefix
    from hashlab.experiments.exp002_s14 import load_s14
    from hashlab.experiments.exp002_kernel_evidence import Attempt
    from e002_verify import production as P
    out = {}
    _, out['authenticate_history_seconds'] = timed(load_s14, audit, REPO)
    clock = Clock(soft)
    n1_key, n2_key = control_keys(0, 'experiment-002-kat')            # public engineering domain
    perm = Feistel64(n1_key)
    occ = struct.Struct('>BBII8sB')
    with open(Path(audit) / 'producer/occurrences.bin', 'rb') as handle:
        blob = handle.read(100_000 * occ.size)
    candidates = [occ.unpack_from(blob, i * occ.size)[4] for i in range(100_000)]
    out['occurrence_records_read'] = len(candidates)
    ints = [int.from_bytes(c, 'big') for c in candidates]
    inv, secs = timed(lambda: [perm.inverse(v) for v in ints])
    out['producer_feistel_inverse_us'] = 1e6 * secs / len(ints)
    vinv, secs = timed(lambda: [P.feistel(n1_key, v, inverse=True) for v in ints[:20_000]])
    out['verifier_feistel_inverse_us'] = 1e6 * secs / 20_000
    out['inverse_agreement_first_20000'] = vinv == inv[:20_000]
    index, secs = timed(lambda: set(inv))
    out['inverse_index_100k_build_seconds'] = secs
    fwd_n1, secs = timed(lambda: [perm.forward(i) for i in range(10_000)])
    out['producer_feistel_forward_n1_us'] = 1e6 * secs / 10_000
    fwd_p, secs = timed(lambda: [perm.forward(P_START + i) for i in range(10_000)])
    out['producer_feistel_forward_p_us'] = 1e6 * secs / 10_000
    vf, secs = timed(lambda: [P.feistel(n1_key, i) for i in range(10_000)])
    out['verifier_feistel_forward_us'] = 1e6 * secs / 10_000
    out['forward_agreement_n1'] = vf == fwd_n1
    _, secs = timed(lambda: [perm.round_function(0, i) for i in range(10_000)])
    out['producer_round_function_blake2b_us'] = 1e6 * secs / 10_000
    # rejection checks
    raws = [v.to_bytes(8, 'big') for v in fwd_n1]
    _, secs = timed(lambda: [(in_a1(r), in_a3(r)) for r in raws])
    out['producer_structural_rejection_check_us'] = 1e6 * secs / len(raws)
    _, secs = timed(lambda: [i in index for i in range(10_000)])
    out['inverse_index_membership_100k_set_us'] = 1e6 * secs / 10_000
    _, secs = timed(lambda: [P.structural_mask(v) for v in fwd_n1])
    out['verifier_structural_mask_us'] = 1e6 * secs / 10_000
    # N2 byte stream and A2 membership
    prefixes = tuple(a2_prefix(N2_PREFIX_KEY, j) for j in range(3000))
    prefix_set = frozenset(prefixes)
    stream = ByteStream80(n2_key)
    raws2, secs = timed(lambda: [stream.next() for _ in range(10_000)])
    out['producer_n2_stream_us_per_80_byte_candidate'] = 1e6 * secs / 10_000
    _, secs = timed(lambda: [(r[:76] in prefix_set and int.from_bytes(r[76:], 'little') < 10000) for r in raws2])
    out['producer_n2_a2_membership_us'] = 1e6 * secs / 10_000
    gen = P.n2_stream(n2_key)
    v2, secs = timed(lambda: [next(gen) for _ in range(10_000)])
    out['verifier_n2_stream_us'] = 1e6 * secs / 10_000
    out['n2_agreement'] = v2 == raws2
    # whole providers (generation + row dictionaries) with engineering geometry, then Attempt encoding
    history = inverse_history(perm, candidates)
    geometry = ControlGeometry('experiment-002-kat', per_stage=5_000, p1=2_000, p2=4_000)
    prp = PermutationControls(perm, history, geometry)
    rows, secs = timed(lambda: list(prp.n1()))
    out['producer_n1_provider_rows'] = len(rows)
    out['producer_n1_provider_us_per_attempt'] = 1e6 * secs / len(rows)
    out['n1_rejections'] = prp.counts['N1']
    rows_p, secs = timed(lambda: list(prp.positives()))
    out['producer_p_provider_rows'] = len(rows_p)
    out['producer_p_provider_us_per_attempt'] = 1e6 * secs / len(rows_p)
    n2 = N2Controls(n2_key, prefixes, geometry)
    rows_n2, secs = timed(lambda: list(n2.attempts()))
    out['producer_n2_provider_rows'] = len(rows_n2)
    out['producer_n2_provider_us_per_attempt'] = 1e6 * secs / len(rows_n2)
    sample = rows[:5000] + rows_p[:2500] + rows_n2[:2500]
    _, secs = timed(lambda: [Attempt.from_provider(r) for r in sample])
    out['attempt_from_provider_encoding_us'] = 1e6 * secs / len(sample)
    out['wall_seconds_measured_sections'] = clock.elapsed()
    out['peak_rss_bytes'] = peak_rss()
    return out


# ------------------------------------------------------------------------------------------ evidence

def artificial_rows(count):
    """Artificial, public-input evidence rows covering all eight streams, both widths, rejections and large indices.

    Never an E002 stream: candidates come from public engineering keys, never a master seed.
    Returns (rows, kinds) where rows are (Attempt, hash_input_or_None).
    """
    from hashlab.experiments.exp002_kernel_evidence import Attempt
    from hashlab.experiments.exp002_controls import Feistel64, control_keys, ByteStream80, P_START
    from hashlab.experiments.exp002 import HammingPopulation, a1_value, a2_prefix
    n1_key, n2_key = control_keys(0, 'experiment-002-kat')
    perm, stream, pop = Feistel64(n1_key), ByteStream80(n2_key), HammingPopulation()
    prefixes = [a2_prefix(N2_PREFIX_KEY, j) for j in range(3000)]
    order = [('A1', 'D'), ('A1', 'V'), ('A2', 'D'), ('A2', 'V'), ('A3', 'D'), ('A3', 'V'), ('N1', 'D'), ('N1', 'V'),
             ('N2', 'D'), ('N2', 'V'), ('P1', 'C'), ('P2+', 'C'), ('P2-', 'C')]
    idx = {k: 0 for k in order}
    rows, raw_index = [], 29_999_000
    for i in range(count):
        arm, stage = order[i % len(order)]
        k = (arm, stage)
        a = idx[k]
        reject = (i % 53 == 0) and arm in ('N1', 'N2', 'P1', 'P2+', 'P2-')
        if arm == 'A1':
            attempt = Attempt(arm, stage, a1_value(4_000_000_000 - i), a, population_rank=4_000_000_000 - i)
        elif arm == 'A2':
            c = (a // 10000) + (1500 if stage == 'V' else 0)
            attempt = Attempt(arm, stage, prefixes[c] + (a % 10000).to_bytes(4, 'little'), a,
                              source_index=c * 10000 + a % 10000, cluster=c)
        elif arm == 'A3':
            rank = A3_N - 1 - i
            attempt = Attempt(arm, stage, pop.unrank(rank).to_bytes(8, 'big'), a, population_rank=rank)
        elif arm in ('N1', 'P1', 'P2+', 'P2-'):
            source = (i if arm == 'N1' else P_START + i)
            raw = perm.forward(source).to_bytes(8, 'big')
            attempt = (Attempt(arm, stage, raw, None, source_index=source, reasons=('C1', 'E001')) if reject
                       else Attempt(arm, stage, raw, a, source_index=source))
        else:
            data = stream.next()
            c = (a // 10000) + (1500 if stage == 'V' else 0)
            raw_index += 1
            attempt = (Attempt(arm, stage, data, None, source_index=raw_index, byte_offset=80 * raw_index, reasons=('A2',))
                       if reject else Attempt(arm, stage, data, a, source_index=raw_index, byte_offset=80 * raw_index, cluster=c))
        if not attempt.reasons:
            idx[k] += 1
        rows.append(attempt)
    return rows


def probe_hash(side, soft):
    clock = Clock(soft)
    rows = artificial_rows(10_000)
    inputs = [r.candidate for r in rows]
    if side == 'producer':
        from hashlab.hashing.sha256 import SHA256Engine
        evaluate = SHA256Engine().digest
        identity = dict(backend='hashlib.sha256 (OpenSSL), producer SHA256Engine')
    else:
        from e002_verify.sha256_independent import CandidateHasher
        h = CandidateHasher('hacl')
        evaluate, identity = h.evaluator(), h.identity()
    t = time.perf_counter()
    digests = [evaluate(x) for x in inputs]
    secs = time.perf_counter() - t
    widths = [len(x) for x in inputs]
    out = dict(evaluations=len(inputs), seconds=secs, microseconds_per_evaluation=1e6 * secs / len(inputs),
               widths=dict(w8=widths.count(8), w80=widths.count(80)), identity=identity, wall_seconds=clock.elapsed(),
               peak_rss_bytes=peak_rss())
    for width in (8, 80):
        sel = [x for x in inputs if len(x) == width]
        t = time.perf_counter()
        for x in sel:
            evaluate(x)
        out['microseconds_per_evaluation_w%d' % width] = 1e6 * (time.perf_counter() - t) / len(sel)
    import hashlib
    out['digests_sha256_of_concatenation'] = hashlib.sha256(b''.join(digests)).hexdigest()
    return out


def probe_serialize(soft, io_dir):
    import hashlib
    import shutil
    import tempfile
    from hashlab.hashing.sha256 import SHA256Engine
    from hashlab.experiments.exp002_controls import ControlEngine
    from hashlab.experiments.exp002_foundation import Accumulator
    from hashlab.experiments.exp002_kernel_evidence import ChunkWriter, encode_row, iter_chunks, HEADER, TRAILER
    from e002_verify.sha256_independent import CandidateHasher
    clock = Clock(soft)
    out = {}
    rows, out['generate_artificial_rows_seconds'] = timed(artificial_rows, 10_000)
    engine = SHA256Engine()
    # one hash evaluation per accepted row (this probe's only hashing: <= 10,000)
    t = time.perf_counter()
    raws = [None if r.reasons else engine.digest(r.candidate) for r in rows]
    out['sha256_openssl_seconds'] = time.perf_counter() - t
    t = time.perf_counter()
    effs = []
    engines = {}
    for r, raw in zip(rows, raws):
        if raw is None:
            effs.append(None)
            continue
        mode = r.arm if r.arm[0] in 'NP' else 'N1'
        e = engines.setdefault(mode, ControlEngine(mode))
        effs.append(bytes.fromhex(e.transform(raw)['effective_digest_hex']))
    out['control_transform_seconds'] = time.perf_counter() - t
    # accounting: artificial rows already carry gapless per-stream accepted indices
    acc = Accumulator()
    t = time.perf_counter()
    n = 0
    for r, eff in zip(rows, effs):
        if eff is not None:
            acc.add(r.record(), eff)
            n += 1
    out['accumulator_add_us_incl_record_validation'] = 1e6 * (time.perf_counter() - t) / n
    out['accumulator_rows'] = n
    # pure serialization CPU (no I/O)
    t = time.perf_counter()
    blobs = [encode_row(i, r, raw, eff) for i, (r, raw, eff) in enumerate(zip(rows, raws, effs))]
    cpu = time.perf_counter() - t
    out['encode_row_us'] = 1e6 * cpu / len(rows)
    sizes = {}
    for r, b in zip(rows, blobs):
        key = (len(r.candidate), 'reject' if r.reasons else 'accepted')
        sizes[key] = (len(b), sizes.get(key, (0, 0))[1] + 1)
    out['bytes_per_row_by_type'] = {'w%d_%s' % k: dict(bytes=v[0], rows=v[1]) for k, v in sizes.items()}
    out['total_row_bytes'] = sum(len(b) for b in blobs)
    out['mean_bytes_per_row'] = out['total_row_bytes'] / len(blobs)
    # write through the real ChunkWriter on the target volume, with fsyncs
    base = Path(io_dir)
    base.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='g1b-serialize-', dir=base))
    try:
        writer = ChunkWriter(root)
        t = time.perf_counter()
        for r, raw, eff in zip(rows, raws, effs):
            writer.add(r, raw, eff)
        info = writer.finish()
        w = time.perf_counter() - t
        out['chunkwriter_total_seconds_including_fsync_and_inventory'] = w
        out['chunkwriter_us_per_row'] = 1e6 * w / len(rows)
        out['chunkwriter_chunks'] = info['chunks']
        files = sorted(root.iterdir())
        chunk_bytes = sum(f.stat().st_size for f in files if f.name.startswith('chunk-'))
        out['chunk_files'] = info['chunks']
        out['chunk_bytes_total'] = chunk_bytes
        out['index_bytes'] = (root / 'chunks.jsonl').stat().st_size
        out['index_bytes_per_chunk'] = out['index_bytes'] / info['chunks']
        out['chunk_framing_bytes_per_chunk'] = HEADER.size + TRAILER.size
        # sequential read + inventory (re-hash) throughput
        t = time.perf_counter()
        digest_total = 0
        for f in files:
            digest_total += len(f.read_bytes())
        out['sequential_read_mb_per_s'] = digest_total / 1e6 / (time.perf_counter() - t)
        t = time.perf_counter()
        for f in files:
            hashlib.sha256(f.read_bytes()).hexdigest()
        out['inventory_rehash_seconds'] = time.perf_counter() - t
        # producer-side reader / decode
        t = time.perf_counter()
        count = sum(1 for _ in iter_chunks(root, expected_chunks=info['chunks'], expected_attempts=info['attempts']))
        out['producer_iter_chunks_us_per_chunk_incl_decode'] = 1e6 * (time.perf_counter() - t) / info['chunks']
        out['producer_iter_chunks_rows'] = count
        # verifier-style rehash + compare on the same bytes with the independent backend
        hasher = CandidateHasher('hacl').evaluator()
        t = time.perf_counter()
        rehash = 0
        for r in rows:
            if not r.reasons:
                hasher(r.candidate)
                rehash += 1
        out['independent_rehash_us_per_candidate'] = 1e6 * (time.perf_counter() - t) / rehash
        out['independent_rehash_candidates'] = rehash
    finally:
        shutil.rmtree(root, ignore_errors=True)
    out['wall_seconds'] = clock.elapsed()
    out['peak_rss_bytes'] = peak_rss()
    out['label'] = 'artificial public-input rows; hashing=%d accepted rows with OpenSSL + %d with independent backend' % (
        sum(1 for r in rows if not r.reasons), rehash)
    return out


def probe_disk(io_dir, soft, total=256 * 1024 * 1024, file_size=590_000):
    """Disposable I/O probe shaped like the real chunk writer: many ~0.6 MB files, fsync each."""
    import hashlib
    import shutil
    import tempfile
    base = Path(io_dir)
    base.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='g1b-disk-', dir=base))
    block = os.urandom(1 << 20)
    count = total // file_size
    out = dict(label='DISPOSABLE I/O PROBE', volume=str(base), target_bytes=count * file_size, files=count)
    try:
        t = time.perf_counter()
        fsync_time = 0.0
        for i in range(count):
            data = (i.to_bytes(8, 'big') + block)[:file_size]
            with open(root / ('chunk-%08d.bin' % i), 'xb') as handle:
                handle.write(data)
                handle.flush()
                f0 = time.perf_counter()
                os.fsync(handle.fileno())
                fsync_time += time.perf_counter() - f0
            if time.perf_counter() - t > soft:
                out['stopped_early_at_file'] = i
                count = i + 1
                break
        w = time.perf_counter() - t
        written = count * file_size
        out.update(write_seconds=w, write_mb_per_s=written / 1e6 / w, fsync_seconds=fsync_time,
                   fsync_share=fsync_time / w, files_written=count, files_per_second=count / w,
                   ms_per_file_create_write_fsync=1e3 * w / count)
        t = time.perf_counter()
        names = sorted(p.name for p in root.iterdir())
        out['directory_listing_seconds'] = time.perf_counter() - t
        t = time.perf_counter()
        total_read = 0
        for name in names:
            total_read += len((root / name).read_bytes())
        r = time.perf_counter() - t
        out.update(sequential_read_seconds=r, sequential_read_mb_per_s=total_read / 1e6 / r,
                   read_note='files were just written; page cache likely serves most reads (not a cold-read figure)')
        t = time.perf_counter()
        for name in names:
            hashlib.sha256((root / name).read_bytes()).hexdigest()
        out['inventory_read_and_sha256_seconds'] = time.perf_counter() - t
        out['inventory_mb_per_s'] = total_read / 1e6 / out['inventory_read_and_sha256_seconds']
        usage = shutil.disk_usage(base)
        out['volume_free_bytes_after'] = usage.free
    finally:
        shutil.rmtree(root, ignore_errors=True)
    out['peak_rss_bytes'] = peak_rss()
    return out


# ------------------------------------------------------------------------------------------ driver

def environment_record():
    import ctypes
    from ctypes import wintypes
    from hashlab.experiments.exp002_runtime_identity import observe_hashing_identity
    from e002_verify.sha256_independent import CandidateHasher
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('dwLength', wintypes.DWORD), ('dwMemoryLoad', wintypes.DWORD), ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong), ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong), ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    ctypes.WinDLL('kernel32').GlobalMemoryStatusEx(ctypes.byref(status))
    return dict(platform=platform.platform(), machine=platform.machine(), processor=platform.processor(),
                logical_cpus=os.cpu_count(), physical_memory_bytes=status.ullTotalPhys,
                available_memory_bytes_at_start=status.ullAvailPhys, commit_limit_bytes=status.ullTotalPageFile,
                python=sys.version, producer_hashing_identity=observe_hashing_identity(),
                verifier_candidate_backend=CandidateHasher('hacl').identity())


def run_child(name, args):
    cap = PROBES[name]['cap']
    soft = cap - 3
    if name.startswith('a1-producer') or name.startswith('a1-verifier'):
        side = name.split('-')[1]
        limit = 1000 if name.endswith('1k') else 10_000
        return probe_a1(side, limit, soft)
    if name.startswith('a1-late'):
        return probe_a1_late(name.split('-')[2], soft)
    if name == 'a3':
        return probe_a3(args.audit, soft)
    if name == 'controls':
        return probe_controls(args.audit, soft)
    if name == 'serialize':
        return probe_serialize(soft, args.io_dir)
    if name.startswith('hash-'):
        return probe_hash(name.split('-')[1], soft)
    if name == 'disk-io':
        return probe_disk(args.io_dir, soft)
    raise SystemExit('unknown probe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run', 'child', 'environment'))
    parser.add_argument('probe', nargs='?')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--audit', type=Path, default=REPO / 'results/e001-s14-audit-20261012-01')
    parser.add_argument('--io-dir', type=Path, default=REPO / '.tmp/e002-g1b/io')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.mode == 'environment':
        (args.out / 'environment.json').write_text(json.dumps(environment_record(), indent=2, sort_keys=True), encoding='utf-8')
        return
    if args.mode == 'child':
        result = run_child(args.probe, args)
        (args.out / (args.probe + '.child.json')).write_text(json.dumps(result, indent=2, sort_keys=True), encoding='utf-8')
        return
    cap = PROBES[args.probe]['cap']
    target = args.out / (args.probe + '.json')
    child_file = args.out / (args.probe + '.child.json')
    if target.exists():
        raise SystemExit('refusing to overwrite retained result (no retries with new parameters)')
    command = [sys.executable, '-B', str(Path(__file__).resolve()), 'child', args.probe, '--out', str(args.out),
               '--audit', str(args.audit), '--io-dir', str(args.io_dir)]
    started = time.time()
    t = time.perf_counter()
    status, code = 'completed', None
    try:
        completed = subprocess.run(command, timeout=cap, capture_output=True, text=True)
        code = completed.returncode
        stderr = completed.stderr[-2000:]
        if code != 0:
            status = 'child-failed'
    except subprocess.TimeoutExpired as exc:
        status, stderr = 'KILLED-AT-EXTERNAL-CAP', (exc.stderr or b'')[-2000:] if exc.stderr else ''
    record = dict(probe=args.probe, declared=PROBES[args.probe], status=status, returncode=code,
                  external_wall_seconds=time.perf_counter() - t, started_unix=started, stderr_tail=stderr)
    if child_file.exists():
        record['result'] = json.loads(child_file.read_text(encoding='utf-8'))
    target.write_text(json.dumps(record, indent=2, sort_keys=True), encoding='utf-8')
    print(args.probe, status, '%.2f s' % record['external_wall_seconds'])


if __name__ == '__main__':
    main()
