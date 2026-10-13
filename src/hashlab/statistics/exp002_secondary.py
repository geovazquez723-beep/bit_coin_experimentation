"""Approved v2 exploratory count tests. No E2 decisions, gates or hashing.

Chi-square laws are approximate model references. All 36 slots are retained;
not-testable members use correction-only p=1. Numerical ambiguity at the Holm
cutoff fails qualification rather than rounding into a discovery.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
import math

from hashlab.experiments.exp002_foundation import (
    SECONDARY_ID, SECONDARY_SLOTS, validate_accounting,
)

ALPHA = Fraction(1, 100)
GROUP_POPULATIONS = (631413, 7407537, 74029313)


def _counts(values, length):
    if type(values) not in (list, tuple) or len(values) != length:
        raise ValueError('missing or extra count bins')
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError('require nonnegative integer counts')
    total=sum(values)
    if total>15000000:
        raise ValueError('counts exceed frozen stage capacity')
    return total


def chi_square_logsf(q: Fraction, df: int) -> float:
    """Log regularized upper gamma, evaluated without underflow of the tail."""
    if type(q) is not Fraction or q < 0 or type(df) is not int or df < 1:
        raise ValueError('invalid chi-square inputs')
    if not q:
        return 0.0
    x, a = float(q)/2, df/2
    if df == 2:
        return -x
    front = a*math.log(x)-x-math.lgamma(a)
    if x < a+1:
        term = total = 1/a
        for i in range(1, 100000):
            term *= x/(a+i)
            total += term
            if abs(term) < abs(total)*2e-16:
                lower = math.exp(front)*total
                if not 0 <= lower < 1:
                    raise ArithmeticError('invalid lower gamma probability')
                return math.log1p(-lower)
    else:
        # Lentz upper-gamma continued fraction; take logs before exponentiation.
        tiny = 1e-300
        b = x+1-a
        c, d = 1/tiny, 1/b
        h = d
        for i in range(1, 100000):
            an = -i*(i-a)
            b += 2
            d = an*d+b
            if abs(d) < tiny: d = tiny
            c = b+an/c
            if abs(c) < tiny: c = tiny
            d = 1/d
            delta = d*c
            h *= delta
            if abs(delta-1) < 2e-15:
                if h <= 0:
                    raise ArithmeticError('invalid gamma continued fraction')
                return min(0., front+math.log(h))
    raise ArithmeticError('chi-square reference did not converge')


@dataclass(frozen=True)
class Outcome:
    slot: str
    status: str
    statistic: Fraction | None
    df: int | None
    p_value: float | None
    log_p_value: float | None
    underflow: bool = False
    reason: str = ''
    adjusted_p: float | None = None
    adjusted_log_p: float | None = None
    flagged: bool = False
    role: str = 'exploratory-only'


def _nt(slot, reason):
    return Outcome(slot, 'not-testable', None, None, None, None, reason=reason)


def _tested(slot, q, df):
    logp = chi_square_logsf(q, df)
    p = math.exp(logp)
    return Outcome(slot, 'tested', q, df, p, logp, p == 0.)


def leading_zero(histogram, slot='reference'):
    n = _counts(histogram, 257)
    k = 0
    while k < 256 and n >= 5*2**(k+1):
        k += 1
    if k == 0:
        return _nt(slot, 'no qualifying leading-zero bins')
    observed = list(histogram[:k])+[sum(histogram[k:])]
    expected = [Fraction(n, 2**(j+1)) for j in range(k)]+[Fraction(n, 2**k)]
    q = sum(((o-e)**2/e for o,e in zip(observed, expected)), Fraction())
    return _tested(slot, q, k)


def uniform_byte(histogram, slot='reference'):
    n = _counts(histogram, 256)
    if n < 1280:
        return _nt(slot, 'expected byte count below five')
    e = Fraction(n, 256)
    q = sum(((o-e)**2/e for o in histogram), Fraction())
    return _tested(slot, q, 255)


def cluster_dispersion(counts, trials, slot='reference'):
    total = _counts(counts, 1500)
    _counts(trials, 1500)
    if any(n != 10000 for n in trials) or any(k > 10000 for k in counts):
        raise ValueError('require complete 1500 by 10000 cluster geometry')
    # Exact b*p_hat = total/1500, including equality at five.
    if total < 7500 or 15000000-total < 7500:
        return _nt(slot, 'zero fitted variance or expected cluster cell below five')
    mean = Fraction(total, 1500)
    variance = mean*(1-Fraction(total, 15000000))
    q = sum(((Fraction(k)-mean)**2/variance for k in counts), Fraction())
    return _tested(slot, q, 1499)


def a3_groups(raw_trials, raw_successes, slot='reference'):
    n = _counts(raw_trials, 6)
    total = _counts(raw_successes, 6)
    if n != 15000000 or raw_trials[0]>12 or any(k > t for k,t in zip(raw_successes, raw_trials)):
        raise ValueError('invalid A3 raw stage counts')
    trials = (sum(raw_trials[:4]), raw_trials[4], raw_trials[5])
    successes = (sum(raw_successes[:4]), raw_successes[4], raw_successes[5])
    if any(t > size for t,size in zip(trials, GROUP_POPULATIONS)):
        raise ValueError('A3 group exceeds eligible population')
    if any(t*total < 5*n or t*(n-total) < 5*n for t in trials):
        return _nt(slot, 'fixed group empty or expected grouped cell below five')
    p = Fraction(total, n)
    q = sum(((Fraction(k)-t*p)**2/(t*p*(1-p)) for t,k in zip(trials,successes)), Fraction())
    return _tested(slot, q, 2)


def holm_exact(probabilities):
    """36-member rational Holm contract; equality to .01 is not flagged."""
    if len(probabilities) != 36 or any(type(p) is not Fraction or not 0 <= p <= 1 for p in probabilities):
        raise ValueError('require exactly 36 rational probabilities')
    adjusted = [Fraction(1)]*36
    running = Fraction()
    for rank,i in enumerate(sorted(range(36), key=lambda i: probabilities[i])):
        running = max(running, min(Fraction(1), (36-rank)*probabilities[i]))
        adjusted[i] = running
    return tuple(adjusted), tuple(p < ALPHA for p in adjusted)


def correct_family(outcomes):
    outcomes = tuple(outcomes)
    if len(outcomes) != 36 or tuple(o.slot for o in outcomes) != SECONDARY_SLOTS:
        raise ValueError('incompatible exploratory family/order')
    logs = []
    for o in outcomes:
        if o.role!='exploratory-only':
            raise ValueError('exploratory result role mismatch')
        if o.status == 'not-testable':
            if any(v is not None for v in (o.statistic,o.df,o.p_value,o.log_p_value)) or o.underflow:
                raise ValueError('not-testable slot has a raw result')
            logs.append(0.)
        elif o.status == 'tested' and type(o.statistic) is Fraction and o.statistic >= 0 and type(o.df) is int and o.df > 0:
            if (type(o.p_value) is not float or type(o.log_p_value) is not float or not math.isfinite(o.log_p_value) or o.log_p_value > 0
                    or o.p_value != math.exp(o.log_p_value) or o.underflow != (o.p_value == 0.)):
                raise ValueError('invalid exploratory probability')
            logs.append(o.log_p_value)
        else:
            raise ValueError('invalid exploratory outcome')
    adjusted = [0.]*36
    running = -math.inf
    for rank,i in enumerate(sorted(range(36), key=lambda i: logs[i])):
        running = max(running, min(0., logs[i]+math.log(36-rank)))
        adjusted[i] = running
    cutoff = math.log(float(ALPHA))
    if any(abs(x-cutoff) <= 2e-12 for x in adjusted):
        raise ArithmeticError('exploratory Holm cutoff numerically ambiguous; higher precision required')
    return tuple(replace(o, adjusted_p=math.exp(x), adjusted_log_p=x,
                         flagged=o.status=='tested' and x < cutoff)
                 for o,x in zip(outcomes,adjusted))


def analyze_secondary(accounting):
    """Complete v2 accounting -> all 36 exploratory slots, never E2 or gates."""
    validate_accounting(accounting, require_complete=True)
    rows = {(r['arm'],r['stage']):r for r in accounting['streams']}
    outcomes = []
    for arm in ('A1','A2','A3','N1','N2'):
        for stage in ('D','V'):
            r = rows[arm,stage]
            for name,fn in (('leading_zero_bits',leading_zero),('first_byte',uniform_byte),('last_byte',uniform_byte)):
                outcomes.append(fn(r[name], f'{arm}:{stage}:{name}'))
    for arm in ('A2','N2'):
        for stage in ('D','V'):
            r = rows[arm,stage]
            outcomes.append(cluster_dispersion(r['cluster_successes'],r['cluster_trials'],f'{arm}:{stage}:dispersion'))
    for stage in ('D','V'):
        r = rows['A3',stage]
        outcomes.append(a3_groups(r['weight_trials'],r['weight_successes'],f'A3:{stage}:weight_groups'))
    return dict(schema='hashlab-exp002-exploratory-results-v1', secondary_identity=SECONDARY_ID,
                role='exploratory-only', family_size=36, alpha='0.01', correction='Holm',
                outcomes=correct_family(outcomes))
