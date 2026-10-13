"""Rebuild synthetic reference pins, never import HASHLAB or hash candidates.

Run with the qualified Python from the repository root. The committed JSON
contains explicit inputs plus exact rational statistics and Decimal tail pins.
"""
from pathlib import Path
import json
import sys
from fractions import Fraction

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from exp002_secondary_reference import chi_reference, pearson, cluster_q, grouped_q


def complete_accounting():
    """Explicit synthetic sufficient statistics, no production imports."""
    streams=[]
    def balanced(n,m):
        q,r=divmod(n,m)
        return [q+1]*r+[q]*(m-r)
    for arm in ('A1','A2','A3','N1','N2','P1','P2+','P2-'):
        for stage in (('C',) if arm.startswith('P') else ('D','V')):
            n=200000 if arm=='P1' else 15000000
            k=0 if arm.startswith('P') else 58594
            first=[k]+balanced(n-k,255) if k else [0]*255+[n]
            leading=[sum(first[2**(7-j):2**(8-j)]) for j in range(8)]+[0]*249
            remaining=k
            for j in range(8,256):
                leading[j]=remaining//2
                remaining-=leading[j]
            leading[256]=remaining
            streams.append(dict(arm=arm,stage=stage,trials=n,successes=k,first_byte=first,
                last_byte=balanced(n,256),leading_zero_bits=leading,
                cluster_trials=[10000]*1500 if arm in ('A2','N2') else None,
                cluster_successes=balanced(k,1500) if arm in ('A2','N2') else None,
                weight_trials=[2,100,3000,112302,1353892,13530704] if arm=='A3' else None,
                weight_successes=[0,0,12,439,5289,52854] if arm=='A3' else None))
    return dict(schema='hashlab-exp002-accounting-v2',secondary_identity='hashlab-exp002-secondary-statistics-proposal-v2',
                complete=True,streams=streams)


def full_reference(accounting):
    results=[]
    rows={(r['arm'],r['stage']):r for r in accounting['streams']}
    def append(slot,q,df):
        p,logp=chi_reference(q,df)
        results.append(dict(slot=slot,statistic=[q.numerator,q.denominator],df=df,p=str(p),log_p=str(logp)))
    for arm in ('A1','A2','A3','N1','N2'):
        for stage in ('D','V'):
            row=rows[arm,stage];n=row['trials']
            k=min(256,(n//5).bit_length()-1)
            append(f'{arm}:{stage}:leading_zero_bits',pearson(row['leading_zero_bits'][:k]+[sum(row['leading_zero_bits'][k:])],
                [Fraction(n,2**(j+1)) for j in range(k)]+[Fraction(n,2**k)]),k)
            for key in ('first_byte','last_byte'):
                append(f'{arm}:{stage}:{key}',pearson(row[key],[Fraction(n,256)]*256),255)
    for arm in ('A2','N2'):
        for stage in ('D','V'):
            append(f'{arm}:{stage}:dispersion',cluster_q(rows[arm,stage]['cluster_successes']),1499)
    for stage in ('D','V'):
        r=rows['A3',stage]
        append(f'A3:{stage}:weight_groups',grouped_q(r['weight_trials'],r['weight_successes']),2)
    # Independent Decimal Holm step-down with all 36 fixed slots.
    from decimal import Decimal,localcontext
    with localcontext() as ctx:
        ctx.prec=100
        running=Decimal(0)
        for rank,i in enumerate(sorted(range(36),key=lambda i:Decimal(results[i]['p']))):
            running=max(running,min(Decimal(1),(36-rank)*Decimal(results[i]['p'])))
            results[i]['adjusted_p']=str(running)
            results[i]['flagged']=running<Decimal('.01')
    return results


def build():
    rows=[]
    def add(name, kind, inputs, q=None, df=None):
        reference=dict(status='not-testable',statistic=None,df=None,p=None,log_p=None)
        if q is not None:
            p,logp=chi_reference(q,df)
            reference=dict(status='tested',statistic=[q.numerator,q.denominator],df=df,p=str(p),log_p=str(logp))
        rows.append(dict(name=name,kind=kind,inputs=inputs,reference=reference))
    hist=[640,320,160,80,40,20,10,5,5]+[0]*248
    add('lz-null','leading',hist,Fraction(),8)
    alt=hist.copy();alt[0]+=8;alt[1]-=8
    add('lz-perturbed','leading',alt,Fraction(3,10),8)
    add('lz-small','leading',[9]+[0]*256)
    add('byte-null','byte',[10]*256,Fraction(),255)
    add('byte-perturbed','byte',[11,9]+[10]*254,Fraction(1,5),255)
    add('byte-underflow','byte',[2560]+[0]*255,Fraction(652800),255)
    add('byte-small','byte',[1279]+[0]*255)
    q,r=divmod(58594,1500)
    balanced=[q+1]*r+[q]*(1500-r)
    q,r=divmod(58594,375)
    concentrated=[0]*1125+[q+1]*r+[q]*(375-r)
    for name,counts in [('constant',[39]*1500),('alternating',[38,40]*750),
                        ('balanced',balanced),('concentrated',concentrated),
                        ('moderate',[33,45]*400+[32,46]*350),
                        ('threshold',[5]*1500)]:
        add('cluster-'+name,'cluster',counts,cluster_q(counts),1499)
    for name,counts in [('zero',[0]*1500),('all',[10000]*1500),('below',[4]+[5]*1499)]:
        add('cluster-'+name,'cluster',counts)
    n=[2,100,3000,112302,1353892,13530704]
    for name,k in [('near',[0,0,12,439,5289,52854]),('shift',[0,0,12,539,5289,52754])]:
        add('a3-'+name,'a3',dict(trials=n,successes=k),grouped_q(n,k),2)
    n=[0,0,0,500,1499500,13500000];k=[0,0,0,5,14995,135000]
    add('a3-threshold','a3',dict(trials=n,successes=k),grouped_q(n,k),2)
    add('a3-below','a3',dict(trials=n,successes=[0,0,0,4,14995,135000]))
    add('a3-empty','a3',dict(trials=[0,0,0,0,1500000,13500000],successes=[0,0,0,0,5859,52735]))
    for df,q in [(1,1),(255,255),(1499,1499),(1499,1800),(1499,1500),(2,Fraction(1,50))]:
        q=Fraction(q)
        add(f'chi-{df}-{q}','chi',dict(q=[q.numerator,q.denominator],df=df),q,df)
    baseline=complete_accounting()
    shifted=json.loads(json.dumps(baseline))
    shifted['streams'][0]['last_byte']=[0]*255+[15000000]
    next(r for r in shifted['streams'] if (r['arm'],r['stage'])==('A3','D'))['weight_successes']=[0,0,12,539,5289,52754]
    return dict(schema='hashlab-exp002-secondary-reference-v1',
        secondary_identity='hashlab-exp002-secondary-statistics-proposal-v2',
        synthetic=True,precision_digits=200,method='finite-half-integer-gamma-recurrence',
        near_one_rule='Pin p=1/logp=0 only if lower-tail Chernoff bound < exp(-250)',fixtures=rows,
        full_families=[dict(name=name,accounting=data,reference=full_reference(data))
                       for name,data in [('baseline',baseline),('exploratory-shift',shifted)]])


if __name__=='__main__':
    destination=Path(__file__).resolve().parents[1]/'tests/fixtures/exp002-secondary-v2-reference.json'
    destination.write_text(json.dumps(build(),indent=2)+'\n',encoding='utf-8')
    print('Pinned synthetic numerical vectors:',destination)
