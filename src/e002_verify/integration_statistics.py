"""Independent I3 inference checks using accepted Decimal reference algorithms.

No HASHLAB inference, input construction, accumulation or serialization imports.
CP endpoints are checked by finite-law tail inversion; other results are computed
from inputs independently. Floating probability tolerances are explicit below.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json
import math
from e001_stream_verify.streaming import _exact

from .binomial_reference import tails
from .secondary_reference import chi_reference, pearson, cluster_q, grouped_q

SOURCE_PIN='3b3931f43705e5dcd787db71dc088f0bc0eaadcb44ddcf87aa52a58553d151db'
N=15000000


def inputs(accounting):
    return dict(schema='hashlab-e002-i3-statistical-inputs-v1',frozen_geometry_complete=accounting['complete'],
        streams=[dict(arm=r['arm'],stage=r['stage'],trials=r['trials'],successes=r['successes'],
                      clusters=r['cluster_successes']) for r in accounting['streams']])


def count_fixtures(repository):
    raw=(Path(repository)/'tests/fixtures/exp002-secondary-v2-reference.json').read_bytes().replace(b'\r\n',b'\n')
    if sha256(raw).hexdigest()!=SOURCE_PIN:raise ValueError('reference accepted count source pin')
    original=json.loads(raw)
    def update(row,k):
        row['successes']=k
        row['first_byte']=[k]+[0]*254+[row['trials']-k]
        row['last_byte']=list(row['first_byte'])
        row['leading_zero_bits']=[row['trials']-k]+[0]*255+[k]
        if row['arm']=='A3':
            edges=[0]
            for n in row['weight_trials']:edges.append(edges[-1]+n)
            row['weight_successes']=[b*k//row['trials']-a*k//row['trials'] for a,b in zip(edges,edges[1:])]
    cases=[]
    for f in original['full_families']:
        data=json.loads(json.dumps(f['accounting']))
        for row in data['streams']:
            if row['arm'].startswith('P'):update(row,dict(P1=1000,**{'P2+':60000,'P2-':57000})[row['arm']])
        cases.append(dict(name=f['name'],accounting=data))
    data=json.loads(json.dumps(cases[0]['accounting']))
    for row in data['streams']:
        if row['arm']=='A3':update(row,56000)
        elif row['arm'] in ('A1','N1'):update(row,61000)
    cases.append(dict(name='replicated-signals-and-null-gate-failure',accounting=data))
    data=json.loads(json.dumps(cases[0]['accounting']))
    update(next(r for r in data['streams'] if r['arm']=='P1'),869)
    cases.append(dict(name='positive-gate-failure',accounting=data))
    data=json.loads(json.dumps(cases[0]['accounting']))
    for row in data['streams']:
        if not row['arm'].startswith('P'):
            update(row,0)
            if row['cluster_successes'] is not None:row['cluster_successes']=[0]*1500
    cases.append(dict(name='not-testable-secondary-zero-successes',accounting=data))
    return dict(schema='hashlab-e002-i3-count-fixtures-v1',scope='synthetic-full-geometry-counts',
        measured_sha256_observations=False,candidate_evaluations=0,source_sha256=SOURCE_PIN,cases=cases)


def rational(value):
    value=Fraction(value)
    return dict(numerator=value.numerator,denominator=value.denominator)


def near(actual,expected, *, absolute=1e-10, relative=1e-12):
    if actual is None or expected is None:
        if actual is not expected:raise ValueError('reference missing numeric result')
        return
    try:a,b=float(actual),float(expected)
    except (TypeError,ValueError):raise ValueError('reference numeric representation') from None
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>absolute+relative*abs(b):
        raise ValueError('reference numerical disagreement')


def reported_number(actual,expected,**tolerances):
    # Accepted binomial/Holm code sometimes returns integer 1 from min(1,p).
    if type(actual) is int and actual in (0,1) and expected is not None and actual==expected:
        return
    if expected is not None and type(actual) is not str:
        raise ValueError('reference numeric result must be a string')
    near(actual,expected,**tolerances)


def holm(probabilities):
    result=[Decimal(1)]*len(probabilities);running=Decimal(0)
    for rank,i in enumerate(sorted(range(len(probabilities)),key=lambda i:probabilities[i])):
        running=max(running,min(Decimal(1),probabilities[i]*(len(probabilities)-rank)))
        result[i]=running
    return result


def binomial(k,n,direction=None):
    lower,upper=tails(k,n)
    return lower if direction=='less' else upper if direction=='greater' else min(Decimal(1),2*min(lower,upper))


def cp_check(actual,k,n):
    if type(actual) is not list or len(actual)!=2 or any(type(x) is not str for x in actual):raise ValueError('reference CP shape')
    lower,upper=[float(x)/256 for x in actual]
    if not 0<=lower<=upper<=1:raise ValueError('reference CP bounds')
    if k==0:
        near(lower,0)
    else:
        _,p=tails(k,n,Decimal.from_float(lower),1);near(p,Decimal(1)/600,absolute=1e-8)
    if k==n:
        near(upper,1)
    else:
        p,_=tails(k,n,Decimal.from_float(upper),1);near(p,Decimal(1)/600,absolute=1e-8)
    lc,ls=tails(k,n,49,12800);hc,hs=tails(k,n,51,12800)
    level=Decimal(1)/600
    return 'WITHIN' if ls<level and hc<level else 'BEYOND' if lc<level or hs<level else 'UNDET'


def family(rows,names,actual,primary):
    if type(actual) is not list or len(actual)!=len(names):raise ValueError('reference primary family shape')
    d=[binomial(rows[a,'D']['successes'],N) for a in names]
    adjusted=holm(d) if primary else d
    flags=[i for i,p in enumerate(adjusted) if p < (Decimal('.005') if primary else Decimal('.005')/3)]
    directions=['greater' if rows[a,'D']['successes']*256>N else 'less' if rows[a,'D']['successes']*256<N else None for a in names]
    vp=[binomial(rows[names[i],'V']['successes'],N,directions[i]) for i in flags]
    va=holm(vp) if primary else vp
    validation=dict(zip(flags,zip(vp,va)))
    for i,(a,result) in enumerate(zip(names,actual)):
        k=rows[a,'D']['successes']+rows[a,'V']['successes']
        cm=cp_check(result['cp_interval'],k,2*N)
        margin=cm;ti=tm=variance=None
        if a in ('A2','N2'):
            clusters=rows[a,'D']['cluster_successes']+rows[a,'V']['cluster_successes']
            total=sum(clusters);mean=Fraction(total*256,30000000)
            variance=Fraction((3000*sum(x*x for x in clusters)-total**2)*256**2,3000*2999*10000**2)
            radius2=Fraction(Decimal('2.9376'))**2*variance/3000
            lo,hi=Fraction(49,50),Fraction(51,50)
            tm=('WITHIN' if lo<mean<hi and radius2<min(mean-lo,hi-mean)**2 else
                'BEYOND' if (mean<lo and radius2<(lo-mean)**2) or (mean>hi and radius2<(mean-hi)**2) else 'UNDET')
            with localcontext() as ctx:
                ctx.prec=60
                center=Decimal(mean.numerator)/Decimal(mean.denominator)
                radius=(Decimal(radius2.numerator)/Decimal(radius2.denominator)).sqrt();ti=[center-radius,center+radius]
            margin='WITHIN' if cm==tm=='WITHIN' else 'BEYOND' if cm==tm=='BEYOND' and (k<30000000*49/12800 and mean<lo or k>30000000*51/12800 and mean>hi) else 'UNDET'
        diff='NONE' if i not in flags else 'REP' if validation[i][1]<Decimal('.005') else 'UNREP'
        matrix=[['equivalent-within-margin','inconclusive-at-margin','discordant-requires-investigation'],
                ['equivalent-within-margin','unreplicated-discovery-signal','discordant-requires-investigation'],
                ['replicated-deviation-within-margin','replicated-deviation-margin-undetermined','replicated-deviation-beyond-margin']]
        expected=dict(arm=a,difference=diff,margin=margin,classification=matrix[['NONE','UNREP','REP'].index(diff)][['WITHIN','UNDET','BEYOND'].index(margin)],
            direction=directions[i],cp_outcome=cm,t_outcome=tm,cluster_variance=None if variance is None else rational(variance),
            notes=['unreplicated-discovery-signal'] if diff=='UNREP' else [],discovery_count=rows[a,'D']['successes'],validation_count=rows[a,'V']['successes'],
            pooled_count=k,pooled_trials=2*N,cluster_sum_squares=sum(x*x for x in rows[a,'D']['cluster_successes']+rows[a,'V']['cluster_successes']) if a in ('A2','N2') else None,
            observed_ratio=rational(Fraction(k*256,2*N)),discovery_ratio=rational(Fraction(rows[a,'D']['successes']*256,N)),
            validation_ratio=rational(Fraction(rows[a,'V']['successes']*256,N)),
            estimand='model-mean-of-evaluated-inputs' if a in ('A2','N2') else 'finite-population-fraction-design-based',
            interpretation='strict model-null test; direction descriptive; no cryptographic or economic claim')
        numeric={'discovery_p':d[i],'discovery_adjusted':adjusted[i],
                 'validation_p':validation[i][0] if i in validation else None,'validation_adjusted':validation[i][1] if i in validation else None}
        if set(result)!=set(expected)|set(numeric)|{'cp_interval','t_interval','hull'}:raise ValueError('reference primary fields')
        for key,value in expected.items():
            if not _exact(result[key],value):raise ValueError('reference primary '+key)
        for key,value in numeric.items():reported_number(result[key],value)
        if ti is None:
            if result['t_interval'] is not None:raise ValueError('reference unexpected t interval')
            hull=result['cp_interval']
        else:
            if type(result['t_interval']) is not list or len(result['t_interval'])!=2:raise ValueError('reference t interval shape')
            for x,y in zip(result['t_interval'],ti):reported_number(x,y,absolute=1e-12)
            hull=[min(Decimal(result['cp_interval'][0]),ti[0]),max(Decimal(result['cp_interval'][1]),ti[1])]
        if len(result['hull'])!=2:raise ValueError('reference hull shape')
        for x,y in zip(result['hull'],hull):reported_number(x,y,absolute=1e-12)


def secondary(rows,result):
    slots=[]
    for a in ('A1','A2','A3','N1','N2'):
        for s in ('D','V'):
            row=rows[a,s];n=row['trials']
            h=row['leading_zero_bits'];bins=0
            while bins<256 and n>=5*2**(bins+1):bins+=1
            if not bins:slots.append((f'{a}:{s}:leading_zero_bits',None,None,'no qualifying leading-zero bins'))
            else:slots.append((f'{a}:{s}:leading_zero_bits',pearson(h[:bins]+[sum(h[bins:])],[Fraction(n,2**(j+1)) for j in range(bins)]+[Fraction(n,2**bins)]),bins,''))
            for key in ('first_byte','last_byte'):
                slots.append((f'{a}:{s}:{key}',pearson(row[key],[Fraction(n,256)]*256) if n>=1280 else None,255 if n>=1280 else None,'' if n>=1280 else 'expected byte count below five'))
    for a in ('A2','N2'):
        for s in ('D','V'):
            k=rows[a,s]['successes'];ok=7500<=k<=N-7500
            slots.append((f'{a}:{s}:dispersion',cluster_q(rows[a,s]['cluster_successes']) if ok else None,1499 if ok else None,'' if ok else 'zero fitted variance or expected cluster cell below five'))
    for s in ('D','V'):
        row=rows['A3',s];t=row['weight_trials'];k=row['weight_successes'];total=sum(k);group=[sum(t[:4]),t[4],t[5]]
        ok=all(x*total>=5*N and x*(N-total)>=5*N for x in group)
        slots.append((f'A3:{s}:weight_groups',grouped_q(t,k) if ok else None,2 if ok else None,'' if ok else 'fixed group empty or expected grouped cell below five'))
    expected_meta=dict(schema='hashlab-exp002-exploratory-results-v1',secondary_identity='hashlab-exp002-secondary-statistics-proposal-v2',role='exploratory-only',family_size=36,alpha='0.01',correction='Holm')
    if set(result)!=set(expected_meta)|{'outcomes'} or any(not _exact(result[k],v) for k,v in expected_meta.items()) or len(result['outcomes'])!=36:
        raise ValueError('reference secondary family metadata')
    probabilities=[chi_reference(q,df) if q is not None else (Decimal(1),Decimal(0)) for _,q,df,_ in slots]
    # Holm in log space also preserves the accepted extreme-tail fixture.
    # Default Decimal exponent limits cannot multiply exp(-1.9e9) by 36.
    logs=[logp for _,logp in probabilities];adjusted=[Decimal(0)]*36
    with localcontext() as ctx:
        ctx.prec=200
        running=Decimal('-Infinity')
        for rank,i in enumerate(sorted(range(36),key=lambda i:logs[i])):
            running=max(running,min(Decimal(0),logs[i]+Decimal(36-rank).ln()))
            adjusted[i]=running
    for actual,(slot,q,df,reason),(p,logp),adjlog in zip(result['outcomes'],slots,probabilities,adjusted):
        tested=q is not None
        expected=dict(slot=slot,status='tested' if tested else 'not-testable',statistic=rational(q) if tested else None,
                      df=df,reason=reason,role='exploratory-only',flagged=tested and adjlog<Decimal('.01').ln(),underflow=tested and float(p)==0.)
        if set(actual)!=set(expected)|{'p_value','log_p_value','adjusted_p','adjusted_log_p'} or any(not _exact(actual[k],v) for k,v in expected.items()):
            raise ValueError('reference secondary exact result')
        reported_number(actual['p_value'],p if tested else None)
        reported_number(actual['log_p_value'],logp if tested else None,absolute=3e-9,relative=1e-13)
        reported_number(actual['adjusted_p'],adjlog.exp())
        reported_number(actual['adjusted_log_p'],adjlog,absolute=3e-9,relative=1e-13)


def verify_inference(accounting,result):
    if set(result)!={'scope','candidate_evaluations','measured_sha256_observations','primary','controls','secondary'} or result['scope']!='synthetic-full-geometry-counts' or type(result['candidate_evaluations']) is not int or result['candidate_evaluations']!=0 or result['measured_sha256_observations'] is not False:
        raise ValueError('reference synthetic inference scope')
    rows={(r['arm'],r['stage']):r for r in accounting['streams']}
    family(rows,['A1','A2','A3'],result['primary'],True)
    controls=result['controls']
    if set(controls)!={'statistical_gate_passed','nulls','positives'}:raise ValueError('reference controls shape')
    family(rows,['N1','N2'],controls['nulls'],False)
    if len(controls['positives'])!=3:raise ValueError('reference positive family shape')
    for arm,out,direction in zip(('P1','P2+','P2-'),controls['positives'],('greater','greater','less')):
        row=rows[arm,'C'];k,n=row['successes'],row['trials'];p=binomial(k,n,direction)
        margin=cp_check(out['interval'],k,n)
        if set(out)!={'p','detected','interval','margin','ratio'} or not _exact(out['detected'],p<Decimal('.001')) or out['margin']!=margin or not _exact(out['ratio'],rational(Fraction(k*256,n))):
            raise ValueError('reference positive inference')
        reported_number(out['p'],p)
    passed=controls['positives'][0]['detected'] and any(p['detected'] for p in controls['positives'][1:]) and all(p['margin']!='WITHIN' for p in controls['positives'][1:]) and all(n['difference']!='REP' for n in controls['nulls'])
    if not _exact(controls['statistical_gate_passed'],passed):raise ValueError('reference control gate')
    secondary(rows,result['secondary'])
