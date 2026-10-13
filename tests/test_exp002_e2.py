"""Synthetic counts only; independent finite-law and integer reference checks."""
from decimal import Decimal, localcontext
from fractions import Fraction
import ast
from pathlib import Path

import pytest
from hashlab.statistics import exp002 as s


def balanced(total, size=1500):
    q,r=divmod(total,size)
    return (q+1,)*r+(q,)*(size-r)


def arm(name,d=58594,v=58594):
    return s.Arm(name,s.Stage('D',d,clusters=balanced(d) if name in ('A2','N2') else None),
                 s.Stage('V',v,clusters=balanced(v) if name in ('A2','N2') else None))


@pytest.mark.parametrize('d,v,diff',[(58594,58594,'NONE'),(64000,64000,'REP'),
    (53000,53000,'REP'),(64000,53000,'UNREP'),(53000,64000,'UNREP'),
    (64000,58594,'UNREP'),(58594,64000,'NONE')])
def test_difference(d,v,diff):
    results=s.analyze([arm(n,d,v) for n in ('A3','A1','A2')])
    assert [r['arm'] for r in results]==['A1','A2','A3']
    assert all(r['difference']==diff for r in results)
    if diff=='NONE':
        assert all(r['validation_p'] is None for r in results)


@pytest.mark.parametrize('k', [0,30_000_000,113850,113851,113852,115838,115839,
    115840,118518,118519,118520,120545,120546,120547])
def test_frozen_margin(k):
    _,result=s.cp_margin(k)
    expected='WITHIN' if 115839<=k<=118519 else 'BEYOND' if k<=113851 or k>=120546 else 'UNDET'
    assert result==expected


@pytest.mark.parametrize('lo,hi,result',[(Fraction(49,50),1,'UNDET'),
    (1,Fraction(51,50),'UNDET'),(0,Fraction(49,50),'UNDET'),
    (Fraction(51,50),2,'UNDET'),(Fraction(99,100),Fraction(101,100),'WITHIN')])
def test_strict_boundaries(lo,hi,result):
    assert s.interval_outcome(lo,hi)==result


@pytest.mark.parametrize('diff',s.MATRIX)
@pytest.mark.parametrize('margin',['WITHIN','UNDET','BEYOND'])
def test_all_matrix_cells(diff,margin):
    reference={
      ('NONE','WITHIN'):'equivalent-within-margin',
      ('NONE','UNDET'):'inconclusive-at-margin',
      ('NONE','BEYOND'):'discordant-requires-investigation',
      ('UNREP','WITHIN'):'equivalent-within-margin',
      ('UNREP','UNDET'):'unreplicated-discovery-signal',
      ('UNREP','BEYOND'):'discordant-requires-investigation',
      ('REP','WITHIN'):'replicated-deviation-within-margin',
      ('REP','UNDET'):'replicated-deviation-margin-undetermined',
      ('REP','BEYOND'):'replicated-deviation-beyond-margin'}
    assert s.classify(diff,margin)==reference[diff,margin]


def test_cluster_independent_reference_and_heterogeneity():
    clusters=balanced(58594)+balanced(58594)
    ci, outcome, mean,var=s.cluster_interval(clusters)
    with localcontext() as ctx:
        ctx.prec=60
        ratios=[Decimal(k)*Decimal(256)/10000 for k in clusters]
        avg=sum(ratios)/3000
        variance=sum((x-avg)**2 for x in ratios)/2999
        radius=Decimal('2.9376')*(variance/3000).sqrt()
        assert abs(ci[0]-(avg-radius))<Decimal('1e-50')
        assert abs(ci[1]-(avg+radius))<Decimal('1e-50')
    assert outcome=='WITHIN'
    # Match the same D/V totals with concentrated counts.
    concentrated=(0,)*1125+balanced(58594,375)
    a=s.Arm('A2',s.Stage('D',58594,clusters=concentrated),s.Stage('V',58594,clusters=concentrated))
    result=s.analyze([arm('A1'),a,arm('A3')])[1]
    assert result['cp_outcome']=='WITHIN'
    assert result['t_outcome']=='UNDET' and result['margin']=='UNDET'
    assert result['observed_ratio']==Fraction(117188*256,30000000)


@pytest.mark.parametrize('k',[0,39,10000])
def test_zero_variance(k):
    ci,_,mean,var=s.cluster_interval((k,)*3000)
    assert var==0 and ci[0]==ci[1]


@pytest.mark.parametrize('k',[-1,15000001,True,1.5,'1'])
def test_bad_counts(k):
    with pytest.raises(ValueError): s.Stage('D',k)


def test_invalid_contracts():
    calls=[lambda:s.Stage('X',0),lambda:s.Stage('D',0,1),
        lambda:s.Stage('D',0,clusters=(0,)*1499),
        lambda:s.Stage('D',1,clusters=(0,)*1500),
        lambda:s.Arm('A2',s.Stage('D',0),s.Stage('V',0)),
        lambda:s.Arm('A1',s.Stage('V',0),s.Stage('D',0)),
        lambda:s.analyze([arm('A1')]*3),lambda:s.classify('BAD','WITHIN'),
        lambda:s.cluster_interval((10001,)*3000)]
    for call in calls:
        with pytest.raises(ValueError):call()


def test_controls_negative_lift():
    result=s.controls([arm('N1'),arm('N2')],1000,60000,57000)
    assert result['statistical_gate_passed']
    assert result['positives'][2]['detected']
    assert result['positives'][2]['ratio']<1
    assert not s.controls([arm('N1',64000,64000),arm('N2')],1000,60000,57000)['statistical_gate_passed']


@pytest.mark.parametrize('index,k,detected',[(0,869,False),(0,870,True),(0,871,True),
    (1,59342,False),(1,59343,True),(1,59344,True),
    (2,57847,True),(2,57848,True),(2,57849,False)])
def test_control_detection_boundaries(index,k,detected):
    from exp002_reference import tails
    counts=[1000,60000,57000]
    counts[index]=k
    r=s.controls([arm('N1'),arm('N2')],*counts)
    lo,hi=tails(k,200000 if index==0 else s.N)
    assert detected==((lo if index==2 else hi)<Decimal('.001'))
    assert r['positives'][index]['detected']==detected


def test_statistical_gate_failures():
    nulls=[arm('N1'),arm('N2')]
    for counts in [(781,60000,57000),(1000,58594,58594),(1000,58594,57000)]:
        assert not s.controls(nulls,*counts)['statistical_gate_passed']
    # D-only null control signal is diagnostic, not blocking.
    assert s.controls([arm('N1',64000,58594),arm('N2')],1000,60000,57000)['statistical_gate_passed']


def test_independent_exact_small_binomial():
    # Integer finite-law numerator, independent of incomplete beta implementation.
    from math import comb
    for n in (1,8,32,256):
        denominator=256**n
        masses=[comb(n,k)*255**(n-k) for k in range(n+1)]
        for k in (0,1,n//2,n):
            low=Fraction(sum(masses[:k+1]),denominator)
            high=Fraction(sum(masses[k:]),denominator)
            expected=float(min(1,2*min(low,high)))
            assert s.binom_test(k,n,s.P0)==pytest.approx(expected,abs=1e-12,rel=0)


def test_discovery_approved_reference_boundaries():
    for k,flag in [(57834,True),(57835,True),(57836,False),(59355,False),(59356,True),(59357,True)]:
        r=s.analyze([arm(n,k,k) for n in ('A1','A2','A3')])
        assert (r[0]['difference']=='REP')==flag


def test_matrix_reachable_count_inputs():
    # A2/A3 strongly reject first, leaving the .005 Holm level for A1.
    cases=[(58594,58594,'NONE','WITHIN'),(58594,60000,'NONE','UNDET'),
        (58594,64000,'NONE','BEYOND'),(59356,58594,'UNREP','WITHIN'),
        (60000,58594,'UNREP','UNDET'),(64000,58594,'UNREP','BEYOND'),
        (59274,59218,'REP','WITHIN'),(60000,60000,'REP','UNDET'),
        (64000,64000,'REP','BEYOND')]
    for d,v,diff,margin in cases:
        r=s.analyze([arm('A1',d,v),arm('A2',64000,64000),arm('A3',64000,64000)])[0]
        assert (r['difference'],r['margin'])==(diff,margin)


@pytest.mark.parametrize('family',[1,2,3])
def test_discovery_all_holm_levels(family):
    from exp002_reference import distribution
    cdf,sf=distribution(s.N)
    level=Decimal('.005')/(2*family)
    lo=max(k for k,p in cdf.items() if p<level)
    hi=min(k for k,p in sf.items() if p<level)
    assert s.DISCOVERY_CRITICAL[family]==(lo,hi)


def test_exact_t_boundary_by_squared_distance():
    # The production comparison uses rational squared distances; Decimal
    # endpoints are descriptive only. Zero variance at margin equality is UNDET.
    assert s.interval_outcome(s.LOW,s.LOW)=='UNDET'
    assert s.interval_outcome(s.HIGH,s.HIGH)=='UNDET'


def test_explicit_full_geometry_reference_fixtures():
    import json
    data=json.loads((Path(__file__).parent/'fixtures/exp002-e2-synthetic.json').read_text())
    outcomes={}
    for fixture in data['fixtures']:
        counts=tuple(fixture['clusters'])
        a=s.Arm('A2',s.Stage('D',fixture['discovery_total'],clusters=counts[:1500]),
            s.Stage('V',fixture['validation_total'],clusters=counts[1500:]))
        result=s.analyze([arm('A1'),a,arm('A3')])[1]
        ref=fixture['reference']
        assert result['cp_outcome']==ref['cp_outcome']
        assert result['t_outcome']==ref['t_outcome']
        for actual,expected in zip(result['t_interval'],ref['t_interval']):
            assert abs(actual-Decimal(expected))<Decimal('1e-50')
        outcomes[fixture['name']]=result
    assert outcomes['t_inside']['margin']=='WITHIN'
    assert outcomes['t_outside']['margin']=='UNDET'
    assert outcomes['heterogeneous']['margin']=='UNDET'


def test_holm_ties_and_empty():
    assert s.holm([])==[]
    assert s.holm([.001,.001,.01])==[.003,.003,.01]


@pytest.mark.parametrize('family',[1,2,3])
@pytest.mark.parametrize('direction',['less','greater'])
def test_validation_critical_reference(family,direction):
    from exp002_reference import critical,tails
    boundary=critical(s.N,direction,family)
    discovery=53000 if direction=='less' else 64000
    names=('A1','A2','A3')
    for k in (boundary-1,boundary,boundary+1):
        inputs=[arm(name,discovery,k) if i<family else arm(name) for i,name in enumerate(names)]
        results=s.analyze(inputs)
        lo,hi=tails(k,s.N)
        expected=lo if direction=='less' else hi
        assert results[0]['validation_p']==pytest.approx(float(expected),abs=1e-10,rel=0)
        assert (results[0]['difference']=='REP')==(expected<Decimal('.005')/family)


@pytest.mark.parametrize('k',[57835,57836,58594,59355,59356])
def test_full_geometry_independent_pvalues(k):
    from exp002_reference import tails
    lo,hi=tails(k,s.N)
    assert s.binom_test(k,s.N,s.P0)==pytest.approx(float(min(1,2*min(lo,hi))),abs=1e-10,rel=0)


@pytest.mark.parametrize('k',[113851,117188,120546])
def test_cp_endpoints_independent_tail_inversion(k):
    from exp002_reference import tails
    lo,hi=s.clopper_pearson(k,2*s.N)
    # Reference evaluates the finite-law tail at each returned beta root.
    _,lower_tail=tails(k,2*s.N,Decimal.from_float(lo),1)
    upper_tail,_=tails(k,2*s.N,Decimal.from_float(hi),1)
    assert abs(lower_tail-Decimal(1)/600)<Decimal('1e-10')
    assert abs(upper_tail-Decimal(1)/600)<Decimal('1e-10')


@pytest.mark.parametrize('k',[56719,56720,56721,58125,58126,58127,59049,59050,59051,60483,60484,60485])
def test_positive_control_margin_boundaries(k):
    from exp002_reference import tails
    lc,ls=tails(k,s.N,49,12800)
    hc,hs=tails(k,s.N,51,12800)
    level=Decimal(1)/600
    expected='WITHIN' if ls<level and hc<level else 'BEYOND' if lc<level or hs<level else 'UNDET'
    assert s.cp_margin(k,s.N)[1]==expected


@pytest.mark.parametrize('k',[113850,113851,113852,115838,115839,115840,
    118518,118519,118520,120545,120546,120547])
def test_independent_margin_decision_tails(k):
    from exp002_reference import tails
    # 0.98*p0=49/12800; 1.02*p0=51/12800.
    lower_cdf,lower_sf=tails(k,2*s.N,49,12800)
    upper_cdf,upper_sf=tails(k,2*s.N,51,12800)
    level=Decimal(1)/600
    expected=('WITHIN' if lower_sf<level and upper_cdf<level else
              'BEYOND' if lower_cdf<level or upper_sf<level else 'UNDET')
    assert s.cp_margin(k)[1]==expected


def test_no_candidate_or_hash_dependencies():
    tree=ast.parse(Path(s.__file__).read_text())
    imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    assert set(imports)=={'dataclasses','decimal','fractions','math','inference'}
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in
                   ('open','eval','exec','__import__') for n in ast.walk(tree))
