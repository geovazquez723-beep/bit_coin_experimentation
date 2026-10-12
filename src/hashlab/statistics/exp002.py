"""Experiment 002 revision 8: pure count-only statistical contracts.

Difference rejects the strict independent Bernoulli(1/256) model null;
direction describes observations only. No result implies cryptographic weakness
or economic advantage. A2 margin concerns the model mean of evaluated inputs,
never a confirmatory bound on the prefix population.
"""
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
import math

from .inference import _beta_continued_fraction, holm

N = 15_000_000
P0 = 1 / 256
ALPHA = .005
CONFIDENCE = 1 - 2 * ALPHA / 3
T_CRITICAL = Decimal('2.9376')
LOW, HIGH = Fraction(49, 50), Fraction(51, 50)
# Discrete critical counts independently verified by Decimal finite-law sums.
DISCOVERY_CRITICAL = {1:(57916,59274), 2:(57864,59326), 3:(57835,59356)}
VALIDATION_CRITICAL = {1:(57971,59218), 2:(57916,59274), 3:(57885,59305)}


def _log_gamma_integer(n):
    """Stirling with exact Bernoulli coefficients, shifted to n >= 100.

    For positive integers the first omitted term bounds the error (< 2e-32).
    Used only in E2 to avoid cancellation in binary64 log-gamma differences.
    The constant log(2*pi)/2 cancels in the beta front except for one copy.
    """
    x = Decimal(max(n,100))
    result=(x-Decimal('.5'))*x.ln()-x
    result+=Decimal('0.91893853320467274178032973640561763986139747363778')
    for numerator,denominator,power in ((1,12,1),(-1,360,3),(1,1260,5),
        (-1,1680,7),(1,1188,9),(-691,360360,11),(1,156,13),(-3617,122400,15)):
        result+=Decimal(numerator)/(Decimal(denominator)*x**power)
    for j in range(n,100):
        result-=Decimal(j).ln()
    return result


def _beta(a,b,x):
    if x<=0:return 0.0
    if x>=1:return 1.0
    with localcontext() as ctx:
        ctx.prec=55
        dx=Decimal.from_float(x)
        front=(_log_gamma_integer(a+b)-_log_gamma_integer(a)-_log_gamma_integer(b)
               +Decimal(a)*dx.ln()+Decimal(b)*(1-dx).ln()).exp()
    if x<(a+1)/(a+b+2):
        return float(front)*_beta_continued_fraction(a,b,x)/a
    return 1-float(front)*_beta_continued_fraction(b,a,1-x)/b


def binom_test(k,n,p0=P0,alternative='two-sided'):
    """Doubled smaller exact binomial tail (not probability-ordering test)."""
    count(k,n)
    if not 0<p0<1 or alternative not in ('two-sided','greater','less'):
        raise ValueError('invalid binomial hypothesis')
    lower=1.0 if k==n else _beta(n-k,k+1,1-p0)
    upper=1.0 if k==0 else _beta(k,n-k+1,p0)
    return lower if alternative=='less' else upper if alternative=='greater' else min(1,2*min(lower,upper))


def clopper_pearson(k,n,confidence=CONFIDENCE):
    count(k,n)
    if not 0<confidence<1:raise ValueError('invalid confidence')
    def inverse(target,a,b):
        lo,hi=0.,1.
        for _ in range(200):
            mid=(lo+hi)/2
            if mid in (lo,hi):break
            if _beta(a,b,mid)<target:lo=mid
            else:hi=mid
        return (lo+hi)/2
    tail=(1-confidence)/2
    # Invert small tails for both endpoints, avoiding 1-small cancellation.
    lower=0. if k==0 else inverse(tail,k,n-k+1)
    upper=1. if k==n else 1-inverse(tail,n-k,k+1)
    return lower,upper


def count(k, n):
    if type(n) is not int or type(k) is not int or n <= 0 or not 0 <= k <= n:
        raise ValueError('require integer counts, n > 0 and 0 <= k <= n')


@dataclass(frozen=True)
class Stage:
    stage: str
    successes: int
    trials: int = N
    clusters: tuple[int, ...] | None = None

    def __post_init__(self):
        count(self.successes, self.trials)
        if self.stage not in ('D', 'V') or self.trials != N:
            raise ValueError('require D/V and frozen 15M stage size')
        if self.clusters is not None:
            if type(self.clusters) is not tuple or len(self.clusters) != 1500:
                raise ValueError('require ordered 1500-cluster tuple; position is cluster id')
            for k in self.clusters:
                count(k, 10000)
            if sum(self.clusters) != self.successes:
                raise ValueError('cluster total mismatch')


@dataclass(frozen=True)
class Arm:
    name: str
    discovery: Stage
    validation: Stage

    def __post_init__(self):
        if self.name not in ('A1', 'A2', 'A3', 'N1', 'N2'):
            raise ValueError('unknown arm')
        if not isinstance(self.discovery, Stage) or not isinstance(self.validation, Stage):
            raise ValueError('require Stage inputs')
        if (self.discovery.stage, self.validation.stage) != ('D', 'V'):
            raise ValueError('stage order must be D,V')
        clustered = self.name in ('A2', 'N2')
        if any((s.clusters is not None) != clustered for s in (self.discovery, self.validation)):
            raise ValueError('clusters required only for A2/N2')


def interval_outcome(lower, upper):
    """Strict rational comparisons; endpoint equality always yields UNDET."""
    lower, upper = Fraction(lower), Fraction(upper)
    if lower > upper:
        raise ValueError('reversed interval')
    if LOW < lower and upper < HIGH:
        return 'WITHIN'
    if upper < LOW or lower > HIGH:
        return 'BEYOND'
    return 'UNDET'


def cp_margin(k, n=2*N):
    count(k, n)
    cp = tuple(x * 256 for x in clopper_pearson(k, n, CONFIDENCE))
    # Approved discrete decision regions avoid float endpoint equality.
    if n == 2*N:
        outcome = ('WITHIN' if 115839 <= k <= 118519 else
                   'BEYOND' if k <= 113851 or k >= 120546 else 'UNDET')
    elif n == N:
        outcome = ('WITHIN' if 58126 <= k <= 59050 else
                   'BEYOND' if k <= 56720 or k >= 60484 else 'UNDET')
    else:
        outcome = interval_outcome(*cp)
    return cp, outcome


def cluster_interval(clusters):
    if type(clusters) is not tuple or len(clusters) != 3000:
        raise ValueError('require 3000 ordered pooled cluster counts')
    for k in clusters:
        count(k, 10000)
    total, squares = sum(clusters), sum(k*k for k in clusters)
    mean = Fraction(total * 256, 3000 * 10000)
    variance = Fraction((3000*squares-total*total)*256**2, 3000*2999*10000**2)
    # Compare squared distances exactly against the frozen decimal critical value.
    radius2 = Fraction(T_CRITICAL)**2 * variance / 3000
    within = mean > LOW and mean < HIGH and radius2 < min(mean-LOW, HIGH-mean)**2
    beyond = (mean < LOW and radius2 < (LOW-mean)**2 or
              mean > HIGH and radius2 < (mean-HIGH)**2)
    with localcontext() as ctx:
        ctx.prec = 60
        center = Decimal(mean.numerator)/Decimal(mean.denominator)
        radius = (Decimal(radius2.numerator)/Decimal(radius2.denominator)).sqrt()
        interval = (center-radius, center+radius)
    return interval, 'WITHIN' if within else 'BEYOND' if beyond else 'UNDET', mean, variance


MATRIX = {
    'NONE': ('equivalent-within-margin', 'inconclusive-at-margin', 'discordant-requires-investigation'),
    'UNREP': ('equivalent-within-margin', 'unreplicated-discovery-signal', 'discordant-requires-investigation'),
    'REP': ('replicated-deviation-within-margin', 'replicated-deviation-margin-undetermined', 'replicated-deviation-beyond-margin'),
}


def classify(difference, margin):
    if difference not in MATRIX or margin not in ('WITHIN', 'UNDET', 'BEYOND'):
        raise ValueError('invalid outcome')
    return MATRIX[difference][('WITHIN', 'UNDET', 'BEYOND').index(margin)]


def analyze(arms):
    """Exactly A1,A2,A3; deterministic name order; V tests only flagged arms."""
    arms = tuple(arms)
    if len(arms) != 3 or {a.name for a in arms} != {'A1','A2','A3'}:
        raise ValueError('require exactly A1,A2,A3')
    return _family(tuple(sorted(arms, key=lambda a:a.name)), True)


def _family(arms, primary):
    dp = [binom_test(a.discovery.successes, N, P0) for a in arms]
    da = holm(dp) if primary else dp
    flagged = []
    for rank,i in enumerate(sorted(range(len(arms)),key=lambda i:dp[i])):
        lo,hi=DISCOVERY_CRITICAL[len(arms)-rank if primary else 3]
        k=arms[i].discovery.successes
        if lo<k<hi:
            if primary:break
        else:flagged.append(i)
    flagged.sort()
    directions = ['greater' if a.discovery.successes*256 > N else
                  'less' if a.discovery.successes*256 < N else None for a in arms]
    vp = {i:binom_test(arms[i].validation.successes,N,P0,directions[i]) for i in flagged}
    va = dict(zip(flagged, holm(list(vp.values())) if primary else list(vp.values())))
    replicated=set()
    for rank,i in enumerate(sorted(flagged,key=lambda i:vp[i])):
        lo,hi=VALIDATION_CRITICAL[len(flagged)-rank if primary else 1]
        k=arms[i].validation.successes
        rejected=k<=lo if directions[i]=='less' else k>=hi
        if not rejected:
            if primary:break
        else:replicated.add(i)
    results = []
    for i,a in enumerate(arms):
        k = a.discovery.successes+a.validation.successes
        cp, cm = cp_margin(k)
        ti = tm = variance = None
        margin, hull = cm, cp
        if a.name in ('A2','N2'):
            ti, tm, mean, variance = cluster_interval(a.discovery.clusters+a.validation.clusters)
            hull = (min(Decimal(str(cp[0])),ti[0]), max(Decimal(str(cp[1])),ti[1]))
            margin = 'WITHIN' if cm == tm == 'WITHIN' else 'UNDET'
            if cm == tm == 'BEYOND' and ((k<=113851 and mean<LOW) or
                                          (k>=120546 and mean>HIGH)):
                margin = 'BEYOND'
        diff = 'NONE' if i not in flagged else 'REP' if i in replicated else 'UNREP'
        results.append(dict(arm=a.name, discovery_p=dp[i], discovery_adjusted=da[i],
            direction=directions[i], validation_p=vp.get(i), validation_adjusted=va.get(i),
            difference=diff, cp_interval=cp, cp_outcome=cm, t_interval=ti, t_outcome=tm,
            cluster_variance=variance, hull=hull, margin=margin, classification=classify(diff,margin),
            notes=('unreplicated-discovery-signal',) if diff=='UNREP' else (),
            discovery_count=a.discovery.successes, validation_count=a.validation.successes,
            pooled_count=k, pooled_trials=2*N,
            cluster_sum_squares=sum(x*x for x in a.discovery.clusters+a.validation.clusters)
                if a.name in ('A2','N2') else None,
            observed_ratio=Fraction(k*256,2*N), discovery_ratio=Fraction(a.discovery.successes*256,N),
            validation_ratio=Fraction(a.validation.successes*256,N),
            estimand='model-mean-of-evaluated-inputs' if a.name in ('A2','N2') else 'finite-population-fraction-design-based',
            interpretation='strict model-null test; direction descriptive; no cryptographic or economic claim'))
    return tuple(results)


def controls(nulls, p1, pplus, pminus):
    """Statistical gates only; no operational validity or evidence integration."""
    nulls = tuple(nulls)
    if len(nulls)!=2 or {a.name for a in nulls}!={'N1','N2'}:
        raise ValueError('require N1,N2')
    outcomes = _family(tuple(sorted(nulls,key=lambda a:a.name)), False)
    positives=[]
    for k,n,direction in ((p1,200000,'greater'),(pplus,N,'greater'),(pminus,N,'less')):
        count(k,n)
        p = binom_test(k,n,P0,direction)
        ci, margin = cp_margin(k,n)
        detected=k>=870 if n==200000 else k>=59343 if direction=='greater' else k<=57848
        positives.append(dict(p=p,detected=detected,interval=ci,margin=margin,ratio=Fraction(k*256,n)))
    passed = (positives[0]['detected'] and any(p['detected'] for p in positives[1:])
              and all(p['margin']!='WITHIN' for p in positives[1:])
              and all(r['difference']!='REP' for r in outcomes))
    return dict(statistical_gate_passed=passed, nulls=outcomes, positives=tuple(positives))
