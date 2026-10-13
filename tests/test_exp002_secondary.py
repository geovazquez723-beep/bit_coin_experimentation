"""All fixtures are synthetic sufficient statistics, never research hashes."""
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
import ast
import copy
import json
import math
from pathlib import Path

import pytest

from hashlab.experiments import exp002_foundation as f
from hashlab.statistics import exp002_secondary as s
from hashlab.statistics import exp002 as primary

FIXTURES=json.loads((Path(__file__).parent/'fixtures/exp002-secondary-v2-reference.json').read_text(encoding='utf-8'))


def complete_counts():
    data=f.Accumulator().snapshot()
    data['complete']=True
    for row,(_,_,n) in zip(data['streams'],f.LIMITS):
        row['trials']=n
        row['first_byte'][255]=row['last_byte'][255]=row['leading_zero_bits'][0]=n
        if row['cluster_trials'] is not None:
            row['cluster_trials']=[10000]*1500
        if row['arm']=='A3':
            row['weight_trials']=[2,100,3000,112302,1353892,13530704]
    f.validate_accounting(data,require_complete=True)
    return data


@pytest.mark.parametrize('fixture',FIXTURES['fixtures'],ids=lambda row:row['name'])
def test_independently_pinned_reference(fixture):
    kind,inputs,ref=fixture['kind'],fixture['inputs'],fixture['reference']
    if kind=='leading':out=s.leading_zero(inputs)
    elif kind=='byte':out=s.uniform_byte(inputs)
    elif kind=='cluster':out=s.cluster_dispersion(inputs,[10000]*1500)
    elif kind=='a3':out=s.a3_groups(inputs['trials'],inputs['successes'])
    else:
        q=Fraction(*inputs['q'])
        logp=s.chi_square_logsf(q,inputs['df'])
        out=s.Outcome('reference','tested',q,inputs['df'],math.exp(logp),logp,math.exp(logp)==0.)
    assert out.status==ref['status']
    if out.status=='not-testable':
        assert out.statistic is out.df is out.p_value is out.log_p_value is None
        return
    assert out.statistic==Fraction(*ref['statistic']) and out.df==ref['df']
    assert out.p_value==pytest.approx(float(Decimal(ref['p'])),abs=1e-10,rel=0)
    assert out.log_p_value==pytest.approx(float(Decimal(ref['log_p'])),abs=3e-9,rel=1e-13)
    assert out.underflow==(out.p_value==0.)


def test_reference_rebuilder_reproduces_pins():
    # Runs independent reference code only, not a production snapshot generator.
    import importlib.util
    path=Path(__file__).parents[1]/'tools/build_exp002_secondary_references.py'
    spec=importlib.util.spec_from_file_location('secondary_builder',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.build()==FIXTURES


def test_all_36_slots_fixed_order_and_separate_role():
    data=complete_counts()
    before=copy.deepcopy(data)
    result=s.analyze_secondary(data)
    assert data==before
    assert result['family_size']==36 and result['alpha']=='0.01'
    assert result['secondary_identity']==s.SECONDARY_ID
    assert tuple(o.slot for o in result['outcomes'])==f.SECONDARY_SLOTS
    assert all(o.role=='exploratory-only' for o in result['outcomes'])
    assert all(o.status=='not-testable' and o.adjusted_p==1 and not o.flagged for o in result['outcomes'][30:])
    assert len([o for o in result['outcomes'] if o.status=='tested'])==30
    assert all(not o.slot.startswith('P') for o in result['outcomes'])


@pytest.mark.parametrize('family',FIXTURES['full_families'],ids=lambda v:v['name'])
def test_full_36_slot_independent_references(family):
    result=s.analyze_secondary(family['accounting'])
    for actual,ref in zip(result['outcomes'],family['reference']):
        assert actual.slot==ref['slot'] and actual.statistic==Fraction(*ref['statistic'])
        assert actual.df==ref['df'] and actual.status=='tested'
        assert actual.p_value==pytest.approx(float(Decimal(ref['p'])),abs=1e-10,rel=0)
        assert actual.log_p_value==pytest.approx(float(Decimal(ref['log_p'])),abs=3e-9,rel=1e-13)
        assert actual.adjusted_p==pytest.approx(float(Decimal(ref['adjusted_p'])),abs=1e-10,rel=0)
        assert actual.flagged==ref['flagged']


def test_shared_inputs_secondary_changes_cannot_change_primary():
    def primary_inputs(data):
        rows={(r['arm'],r['stage']):r for r in data['streams']}
        def arm(name):
            return primary.Arm(name,*[primary.Stage(stage,rows[name,stage]['successes'],
                clusters=tuple(rows[name,stage]['cluster_successes']) if name in ('A2','N2') else None)
                for stage in ('D','V')])
        return (primary.analyze([arm(n) for n in ('A1','A2','A3')]),
                primary.controls([arm(n) for n in ('N1','N2')],1000,60000,57000))
    baseline,shifted=[v['accounting'] for v in FIXTURES['full_families']]
    before=primary_inputs(baseline)
    a=s.analyze_secondary(baseline);b=s.analyze_secondary(shifted)
    assert [o.flagged for o in a['outcomes']] != [o.flagged for o in b['outcomes']]
    assert before==primary_inputs(shifted)==primary_inputs(baseline)
    assert all(r['difference']=='NONE' and r['margin']=='WITHIN' for r in before[0])
    assert before[1]['statistical_gate_passed']


def test_holm_exact_boundaries_ties_fixed_family():
    p=[Fraction(1)]*36
    p[0]=Fraction(1,3600)
    adjusted,flags=s.holm_exact(p)
    assert adjusted[0]==Fraction(1,100) and not flags[0]
    p[0]-=Fraction(1,10**20)
    assert s.holm_exact(p)[1][0]
    p[1]=p[0]
    adjusted,flags=s.holm_exact(p)
    assert adjusted[0]==adjusted[1] and flags[0]==flags[1]
    p[0]=Fraction(1,3600)+Fraction(1,10**20)
    p[1]=Fraction(1)
    assert not s.holm_exact(p)[1][0]
    for n in (0,35,37):
        with pytest.raises(ValueError):s.holm_exact([Fraction(1)]*n)


@pytest.mark.parametrize('remaining',range(1,37))
def test_every_holm_rank_strict_boundary(remaining):
    rank=36-remaining
    p=[Fraction(0)]*rank+[Fraction(1,100*remaining)]+[Fraction(1)]*(remaining-1)
    adjusted,flags=s.holm_exact(p)
    assert adjusted[rank]==Fraction(1,100) and not flags[rank]
    p[rank]-=Fraction(1,10**20)
    assert s.holm_exact(p)[1][rank]
    p[rank]+=Fraction(2,10**20)
    assert not s.holm_exact(p)[1][rank]


def test_log_holm_underflow_and_no_dropping():
    outcomes=[s._nt(slot,'fixture') for slot in f.SECONDARY_SLOTS]
    for i in range(2):
        outcomes[i]=s._tested(f.SECONDARY_SLOTS[i],Fraction(2000),2)
    corrected=s.correct_family(outcomes)
    assert corrected[0].underflow and corrected[0].p_value==0.
    assert corrected[0].adjusted_log_p==pytest.approx(-1000+math.log(36),abs=1e-12)
    assert corrected[0].adjusted_log_p==corrected[1].adjusted_log_p
    assert corrected[0].flagged and corrected[1].flagged
    assert all(o.adjusted_p==1 and not o.flagged for o in corrected[2:])
    with pytest.raises(ValueError):s.correct_family(outcomes[::-1])


def test_numerically_ambiguous_holm_fails_closed():
    outcomes=[s._nt(slot,'fixture') for slot in f.SECONDARY_SLOTS]
    logp=math.log(.01/36)
    outcomes[0]=s.Outcome(f.SECONDARY_SLOTS[0],'tested',Fraction(1),2,math.exp(logp),logp)
    with pytest.raises(ArithmeticError):s.correct_family(outcomes)


@pytest.mark.parametrize('bad',[-1,1.5,True,'1'])
def test_malformed_counts(bad):
    hist=[0]*256;hist[0]=bad
    with pytest.raises(ValueError):s.uniform_byte(hist)


def test_cluster_invalid_geometry_and_boundaries():
    for counts,trials in [([39]*1499,[10000]*1500),([39]*1500,[10000]*1499),
        ([10001]*1500,[10000]*1500),([39]*1500,[9999]*1500)]:
        with pytest.raises(ValueError):s.cluster_dispersion(counts,trials)
    assert s.cluster_dispersion([5]*1500,[10000]*1500).status=='tested'
    assert s.cluster_dispersion([4]+[5]*1499,[10000]*1500).status=='not-testable'
    assert s.cluster_dispersion([9995]*1500,[10000]*1500).status=='tested'
    assert s.cluster_dispersion([9996]+[9995]*1499,[10000]*1500).status=='not-testable'


def test_lz_expected_count_boundary_and_empty_bins():
    assert s.leading_zero([9]+[0]*256).status=='not-testable'
    o=s.leading_zero([5,5]+[0]*255)
    assert o.df==1 and o.statistic==0 and o.p_value==1
    assert s.leading_zero([0]*256+[10]).statistic==10
    assert s.uniform_byte([5]*256).status=='tested'
    with pytest.raises(ValueError):s.leading_zero([0]*256)


def test_a3_aggregation_invalid_inputs_and_no_removal():
    n=[2,100,3000,112302,1353892,13530704]
    k=[0,0,12,539,5289,52754]
    ref=s.a3_groups(n,k)
    k2=[0,0,0,551,5289,52754]
    assert s.a3_groups(n,k2).statistic==ref.statistic
    assert ref.df==2
    for nt,ks in [(n[:-1],k),(n,k[:-1]),(n,[3,0,12,539,5289,52754]),
        ([0,0,0,700000,1000000,13300000],[0]*6)]:
        with pytest.raises(ValueError):s.a3_groups(nt,ks)
    empty=s.a3_groups([0,0,0,0,1500000,13500000],[0,0,0,0,5859,52735])
    assert empty.status=='not-testable' and empty.df is None


def test_raw_weight_accumulation_and_success_revalidation():
    saved=[]
    acc=f.Accumulator(success_sink=saved.append)
    for index,weight in enumerate(range(1,7)):
        # Explicit engineering records, supplied digests; no engine evaluation.
        value=(1<<32)|((1<<(weight-1))-1)
        r=f.CandidateRecord('A3','D',index,f'{value:016x}')
        acc.add(r,b'\0'*32 if weight%2 else b'\xff'*32)
    data=acc.snapshot();f.validate_accounting(data)
    row=next(r for r in data['streams'] if (r['arm'],r['stage'])==('A3','D'))
    assert row['weight_trials']==[1]*6
    assert row['weight_successes']==[1,0,1,0,1,0]
    f.validate_success_records(saved,data)
    row['weight_successes']=[0,1,1,0,1,0]
    with pytest.raises(ValueError):f.validate_success_records(saved,data)


@pytest.mark.parametrize('change',['schema','identity','missing','total','impossible','unexpected','group'])
def test_v2_accounting_validation(change):
    data=complete_counts()
    a3=next(r for r in data['streams'] if r['arm']=='A3')
    if change=='schema':data['schema']='hashlab-exp002-accounting-v1'
    if change=='identity':data['secondary_identity']='other'
    if change=='missing':a3['weight_trials'].pop()
    if change=='total':a3['weight_trials'][0]+=1
    if change=='impossible':a3['weight_successes'][0]=3
    if change=='unexpected':data['streams'][0]['weight_trials']=[0]*6
    if change=='group':a3['weight_trials']=[0,0,0,700000,1000000,13300000]
    with pytest.raises(ValueError):f.validate_accounting(data)


def test_versioned_plan_rejects_v1_and_wrong_secondary():
    data=f.Plan('a'*40).to_dict()
    assert data['schema']=='hashlab-exp002-seedless-plan-v2'
    assert len(data['statistics']['secondary']['slots'])==36
    assert data['config']['alpha_difference']==data['config']['alpha_margin']=='0.005'
    data['schema']='hashlab-exp002-seedless-plan-v1'
    with pytest.raises(ValueError):f.Plan.from_dict(data)


def test_raw_weights_population_and_missing_identity():
    data=complete_counts()
    a3=[r for r in data['streams'] if r['arm']=='A3']
    for row in a3:
        row['weight_trials'][0]=7
        row['weight_trials'][3]-=5
    with pytest.raises(ValueError):f.validate_accounting(data)
    data=complete_counts();del data['secondary_identity']
    with pytest.raises(ValueError):f.validate_accounting(data)
    data=complete_counts();a3=next(r for r in data['streams'] if r['arm']=='A3')
    a3['weight_trials'][0]=13;a3['weight_trials'][3]-=11
    with pytest.raises(ValueError):f.validate_accounting(data)
    data=f.Plan('a'*40).to_dict();data['statistics']['secondary']['identity']='v1'
    with pytest.raises(ValueError):f.Plan.from_dict(data)


def test_partial_accounting_not_treated_as_a_secondary_run():
    with pytest.raises(ValueError):s.analyze_secondary(f.Accumulator().snapshot())


def test_primary_classifications_and_control_gates_unaffected():
    def balanced(k):
        q,r=divmod(k,1500)
        return (q+1,)*r+(q,)*(1500-r)
    def arm(name):
        clusters=balanced(58594) if name in ('A2','N2') else None
        return primary.Arm(name,primary.Stage('D',58594,clusters=clusters),
                           primary.Stage('V',58594,clusters=clusters))
    arms=[arm(n) for n in ('A1','A2','A3')]
    nulls=[arm(n) for n in ('N1','N2')]
    before=primary.analyze(arms),primary.controls(nulls,1000,60000,57000)
    result=s.analyze_secondary(complete_counts())
    assert any(o.flagged for o in result['outcomes'])
    assert before==(primary.analyze(arms),primary.controls(nulls,1000,60000,57000))
    assert before[1]['statistical_gate_passed']


def test_no_primary_or_operational_dependency():
    tree=ast.parse(Path(s.__file__).read_text(encoding='utf-8'))
    modules={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    assert modules=={'dataclasses','fractions','hashlab.experiments.exp002_foundation'}
    called={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
    assert not called & {'sha256','derive_seed','analyze','controls','a2_stream','engineering_arm_stream'}
