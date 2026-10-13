"""Independent synthetic binomial reference: Decimal finite-law recurrence.

No HASHLAB imports, incomplete beta, log-gamma or sampling. Normalize relative
mass at the mode. Omitted tails each have geometric upper bound below 1e-65.
"""
from decimal import Decimal, localcontext
from functools import lru_cache


@lru_cache(None)
def distribution(n, numerator=1, denominator=256):
    with localcontext() as ctx:
        ctx.prec=75
        p=Decimal(numerator)/denominator
        q=1-p
        mode=int((n+1)*p)
        masses={mode:Decimal(1)}
        term=Decimal(1)
        k=mode
        while k>0:
            ratio=Decimal(k)*q/(Decimal(n-k+1)*p)
            term*=ratio
            k-=1
            masses[k]=term
            if ratio<1 and term/(1-ratio)<Decimal('1e-65'):break
        term=Decimal(1)
        k=mode
        while k<n:
            ratio=Decimal(n-k)*p/(Decimal(k+1)*q)
            term*=ratio
            k+=1
            masses[k]=term
            if ratio<1 and term/(1-ratio)<Decimal('1e-65'):break
        total=sum(masses.values())
        keys=sorted(masses)
        cdf={}
        sf={}
        running=Decimal(0)
        for k in keys:
            running+=masses[k]/total
            cdf[k]=running
        running=Decimal(0)
        for k in reversed(keys):
            running+=masses[k]/total
            sf[k]=running
        return cdf,sf


def tails(k,n,numerator=1,denominator=256):
    cdf,sf=distribution(n,numerator,denominator)
    return (cdf.get(k,Decimal(0) if k<min(cdf) else Decimal(1)),
            sf.get(k,Decimal(1) if k<min(sf) else Decimal(0)))


def critical(n,alternative,family):
    cdf,sf=distribution(n)
    level=Decimal('0.005')/family
    if alternative=='less':
        return max(k for k,p in cdf.items() if p<level)
    return min(k for k,p in sf.items() if p<level)
