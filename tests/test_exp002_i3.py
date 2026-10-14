"""Unified I3 integration, independent replay and synthetic count qualification."""
from hashlib import sha256
from fractions import Fraction
from pathlib import Path
import copy
import json
import shutil
import subprocess
import sys

import pytest

from hashlab.experiments import exp002_integration as p
from hashlab.experiments import exp002_integration_statistics as bridge
from hashlab.experiments.exp002_controls import Feistel64,control_keys,inverse_history,ControlEngine
from hashlab.experiments.exp002_s14 import VerifiedS14
from hashlab.experiments.exp002 import Exclusions,HammingPopulation
from hashlab.experiments.exp002_foundation import Accumulator,CandidateRecord,canonical,validate_accounting
from hashlab.statistics import exp002 as primary
from e002_verify import integration as reference
from e002_verify import integration_statistics as stats_ref

REPO=Path(__file__).resolve().parents[1]
AUDIT=REPO/'results/e001-s14-audit-20261012-01'


def bind_history(monkeypatch):
    ranks=(0,1,2,3,32,63,127,4095,5000)
    history=VerifiedS14(Exclusions(ranks,HammingPopulation()))
    n,two=control_keys(0,'experiment-002-kat');prp=Feistel64(n)
    values=[HammingPopulation().unrank(r) for r in ranks]+[prp.forward(0),prp.forward(2**63),prp.forward(2**63)]
    inverse=inverse_history(prp,[v.to_bytes(8,'big') for v in values],identity={'unit_only':True})
    monkeypatch.setattr(p,'load_s14',lambda *args:history)
    monkeypatch.setattr(p,'control_inputs',lambda *args:(prp,inverse,two,()))
    monkeypatch.setattr(reference.arms,'load_history',lambda *args:(set(ranks),history.identity()))
    monkeypatch.setattr(reference.controls,'load_history',lambda *args:(set(values),inverse.identity,len(values)))
    return history


@pytest.fixture
def history(monkeypatch):
    return bind_history(monkeypatch)


@pytest.fixture(scope='module')
def base_evidence(tmp_path_factory):
    root=tmp_path_factory.mktemp('i3-shared')/'producer'
    with pytest.MonkeyPatch.context() as mp:
        bind_history(mp)
        pin=p.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    return root,pin


@pytest.fixture
def evidence(tmp_path,base_evidence,history):
    root=tmp_path/'copy';shutil.copytree(base_evidence[0],root)
    return root,base_evidence[1]


def verify(root,pin):
    return reference.verify_fixture(root,complete_sha256=pin,audit_root=AUDIT,repository_root=REPO)


def reseal(root):
    report=json.loads((root/'complete.json').read_bytes())
    for name in report['files']:
        raw=(root/name).read_bytes();report['files'][name]=dict(size=len(raw),sha256=sha256(raw).hexdigest())
    raw=canonical(report);(root/'complete.json').write_bytes(raw)
    return sha256(raw).hexdigest()


def test_unified_replay_repeat_and_all_streams(evidence,tmp_path,history,monkeypatch):
    root,pin=evidence;result=verify(root,pin)
    assert result['records']==206 and result['rehash_compression_blocks']==274 and result['attempts']==208
    assert result['synthetic_count_cases']==5 and result['secondary_slots_per_case']==36
    calls=[];real=p.SHA256Engine.digest
    def spy(self,data):calls.append(len(data));return real(self,data)
    monkeypatch.setattr(p.SHA256Engine,'digest',spy)
    replay=tmp_path/'repeat';assert p.run_fixture(replay,audit_root=AUDIT,repository_root=REPO)==pin
    assert len(calls)==206 and sum((n+72)//64 for n in calls)==274
    assert {f.name:f.read_bytes() for f in root.iterdir()}=={f.name:f.read_bytes() for f in replay.iterdir()}
    rows=[json.loads(line) for line in (root/'records.jsonl').read_bytes().splitlines()]
    assert {r['candidate']['arm'] for r in rows}=={'A1','A2','A3','N1','N2','P1','P2+','P2-'}
    accounting=json.loads((root/'accounting.json').read_bytes());validate_accounting(accounting)
    assert not accounting['complete']
    assert not json.loads((root/'statistical-inputs.json').read_bytes())['frozen_geometry_complete']
    with pytest.raises(FileExistsError):p.run_fixture(root,audit_root=AUDIT,repository_root=REPO)


def test_shared_evaluation_and_effective_inputs_supplied():
    acc=Accumulator();calls=[]
    class Supplied:
        def __init__(self,raw):self.raw=raw
        def digest(self,data):calls.append(data);return self.raw
    for mode,raw,expected in [('P1',2**248,True),('P2+',2**248,True),('P2-',0,False)]:
        record=CandidateRecord(mode,'C',0,(2**64-1).to_bytes(8,'big').hex())
        result=p.evaluate_record(record,Supplied(raw.to_bytes(32,'big')))
        assert result['success'] is expected and result['transformed']
        acc.add(record,bytes.fromhex(result['effective_digest_hex']))
    assert len(calls)==3
    accounting=acc.snapshot();inputs=bridge.statistical_inputs(accounting)
    actual={r['arm']:r['successes'] for r in inputs['streams'] if r['stage']=='C'}
    assert actual=={'P1':1,'P2+':1,'P2-':0}
    with pytest.raises(ValueError):bridge.infer_synthetic_counts(accounting,scope='synthetic-full-geometry-counts')
    artificial=p.count_fixtures(REPO)['cases'][0]['accounting']
    for row in artificial['streams']:
        if row['arm'] in actual:
            k=actual[row['arm']];row['successes']=k
            row['first_byte']=[k]+[0]*254+[row['trials']-k];row['last_byte']=list(row['first_byte'])
            row['leading_zero_bits']=[row['trials']-k]+[0]*255+[k]
    result=bridge.infer_synthetic_counts(artificial,scope='synthetic-full-geometry-counts')
    stats_ref.verify_inference(artificial,result)
    assert result['controls']['positives'][0]['ratio']=={'numerator':4,'denominator':3125}
    assert not result['controls']['statistical_gate_passed']


def test_supplied_transformations_persist_successes_in_entire_path(evidence,tmp_path,history,monkeypatch):
    rows=[json.loads(line) for line in (evidence[0]/'records.jsonl').read_bytes().splitlines()]
    forced={bytes.fromhex(r['candidate']['candidate_hex']): (0 if r['candidate']['arm']=='P2-' else 2**248).to_bytes(32,'big')
            for r in rows if r['candidate']['arm'].startswith('P')}
    real=p.SHA256Engine.digest;calls=[]
    def supplied(self,data):calls.append(data);return forced[data] if data in forced else real(self,data)
    monkeypatch.setattr(p.SHA256Engine,'digest',supplied)
    root=tmp_path/'injected-only';pin=p.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    assert len(calls)==206
    inputs=json.loads((root/'statistical-inputs.json').read_bytes())
    assert {r['arm']:r['successes'] for r in inputs['streams'] if r['stage']=='C'}=={'P1':2,'P2+':2,'P2-':0}
    successes=[json.loads(line) for line in (root/'successes.jsonl').read_bytes().splitlines()]
    assert sum(s['candidate']['arm'] in ('P1','P2+') for s in successes)==4
    assert all(s['candidate']['arm']!='P2-' for s in successes)
    with pytest.raises(ValueError,match='digest/transform'):verify(root,pin)


def test_synthetic_count_cases_all_interfaces_and_independent_references():
    artificial=p.count_fixtures(REPO);assert artificial==stats_ref.count_fixtures(REPO)
    results=[]
    for case in artificial['cases']:
        result=bridge.infer_synthetic_counts(case['accounting'],scope=artificial['scope'])
        stats_ref.verify_inference(case['accounting'],result);results.append(result)
    assert [r['controls']['statistical_gate_passed'] for r in results]==[True,True,False,False,False]
    assert results[0]['primary']==results[1]['primary'] and results[0]['controls']==results[1]['controls']
    assert [o['flagged'] for o in results[0]['secondary']['outcomes']]!=[o['flagged'] for o in results[1]['secondary']['outcomes']]
    assert sum(o['status']=='not-testable' for o in results[4]['secondary']['outcomes'])==6
    assert all(o['adjusted_p']=='1.0' and o['p_value'] is None for o in results[4]['secondary']['outcomes'] if o['status']=='not-testable')
    assert all(r['validation_p'] is None for r in results[0]['primary'])
    assert results[2]['primary'][0]['difference']=='REP'
    with pytest.raises(ValueError):bridge.infer_synthetic_counts(artificial['cases'][0]['accounting'],scope='production')


@pytest.mark.parametrize('difference',['NONE','UNREP','REP'])
@pytest.mark.parametrize('margin',['WITHIN','UNDET','BEYOND'])
def test_nine_cell_accepted_mapping(difference,margin):
    matrix=[['equivalent-within-margin','inconclusive-at-margin','discordant-requires-investigation'],
            ['equivalent-within-margin','unreplicated-discovery-signal','discordant-requires-investigation'],
            ['replicated-deviation-within-margin','replicated-deviation-margin-undetermined','replicated-deviation-beyond-margin']]
    assert primary.classify(difference,margin)==matrix[['NONE','UNREP','REP'].index(difference)][['WITHIN','UNDET','BEYOND'].index(margin)]


def test_disclosure_production_boundary_and_no_geometry_override(history):
    assert bridge.disclosure('production')['production_blinded']
    assert not bridge.disclosure('production')['validation_diagnostics_allowed']
    assert bridge.disclosure('synthetic-engineering')['validation_diagnostics_allowed']
    with pytest.raises(ValueError):bridge.disclosure('qa2')
    with pytest.raises(TypeError):p.fixture_spec(per_stage=15000000)
    assert p.fixture_spec()['arms']['per_arm_stage']==32 and p.fixture_spec()['controls']['per_stage']==2


@pytest.mark.parametrize('field',['raw_digest_hex','effective_digest_hex','mode','success','transformed','threshold_u32',
    'candidate','attempt_sequence','sequence','missing','extra','reorder','truncate'])
def test_resealed_record_corruption(evidence,field):
    root,_=evidence;path=root/'records.jsonl';rows=[json.loads(line) for line in path.read_bytes().splitlines()]
    if field in ('raw_digest_hex','effective_digest_hex'):rows[0][field]='ff'*32
    elif field in ('success','transformed'):rows[0][field]=not rows[0][field]
    elif field=='mode':rows[0][field]='P2-'
    elif field=='candidate':rows[0][field]['index']=True
    elif field=='missing':rows.pop()
    elif field=='extra':rows.append(rows[0])
    elif field=='reorder':rows[0],rows[1]=rows[1],rows[0]
    elif field!='truncate':rows[0][field]+=1
    raw=b''.join(canonical(r)+b'\n' for r in rows);path.write_bytes(raw[:-1] if field=='truncate' else raw)
    with pytest.raises(ValueError,match='reference'):verify(root,reseal(root))


@pytest.mark.parametrize('field',['population_rank','source_index','raw_index','byte_offset','cluster','reasons','accepted_index','stage'])
def test_resealed_attempt_corruption(evidence,field):
    root,_=evidence;path=root/'attempts.jsonl';rows=[json.loads(line) for line in path.read_bytes().splitlines()]
    row=next(r for r in rows if field in r)
    if field=='reasons':row[field]=['E001']
    elif field=='stage':row[field]='C'
    elif field in ('population_rank','cluster','accepted_index'):row[field]=999
    else:row[field]+=1
    path.write_bytes(b''.join(canonical(r)+b'\n' for r in rows))
    with pytest.raises(ValueError,match='reference'):verify(root,reseal(root))


@pytest.mark.parametrize('file',['fixture.json','history.json','successes.jsonl','accounting.json','statistical-inputs.json',
    'rejections.json','count-fixtures.json','disclosure.json','complete.json'])
def test_resealed_payload_corruption(evidence,file):
    root,_=evidence;path=root/file
    if file=='successes.jsonl':path.write_bytes(path.read_bytes()+b'{}\n')
    else:
        data=json.loads(path.read_bytes())
        if file=='fixture.json':data['candidate_evaluations']=207
        elif file=='history.json':data['historical_occurrences']-=1
        elif file=='accounting.json':data['streams'][0]['successes']+=1
        elif file=='statistical-inputs.json':data['streams'][-1]['successes']+=1
        elif file=='rejections.json':data['P1']['accepted']+=1
        elif file=='count-fixtures.json':data['measured_sha256_observations']=True
        elif file=='disclosure.json':data['confirmatory_complete']=True
        else:data['confirmatory_complete']=True
        path.write_bytes(canonical(data))
    with pytest.raises(ValueError,match='reference'):verify(root,reseal(root))


@pytest.mark.parametrize('field',['primary-count','primary-classification','validation-disclosure','control-gate','control-ratio',
    'secondary-statistic','secondary-df','secondary-flag','secondary-log','secondary-missing','scope','inputs'])
def test_resealed_synthetic_inference_corruption(evidence,field):
    root,_=evidence;path=root/'synthetic-inference.json';data=json.loads(path.read_bytes());case=data['cases'][0]
    result=case['results']
    if field=='primary-count':result['primary'][0]['pooled_count']+=1
    elif field=='primary-classification':result['primary'][0]['classification']='discordant-requires-investigation'
    elif field=='validation-disclosure':result['primary'][0]['validation_p']='0.1'
    elif field=='control-gate':result['controls']['statistical_gate_passed']=False
    elif field=='control-ratio':result['controls']['positives'][0]['ratio']['numerator']+=1
    elif field=='secondary-statistic':result['secondary']['outcomes'][0]['statistic']['numerator']+=1
    elif field=='secondary-df':result['secondary']['outcomes'][0]['df']+=1
    elif field=='secondary-flag':result['secondary']['outcomes'][0]['flagged']=True
    elif field=='secondary-log':result['secondary']['outcomes'][0]['adjusted_log_p']='-100.0'
    elif field=='secondary-missing':result['secondary']['outcomes'].pop()
    elif field=='scope':result['scope']='production'
    else:case['inputs']['streams'][-1]['successes']+=1
    path.write_bytes(canonical(data))
    with pytest.raises(ValueError,match='reference'):verify(root,reseal(root))


@pytest.mark.parametrize('file',['complete.json','records.jsonl','successes.jsonl','synthetic-inference.json'])
def test_missing_or_unpinned_evidence(evidence,file):
    root,pin=evidence
    with pytest.raises(ValueError):verify(root,'0'*64)
    (root/file).unlink()
    with pytest.raises(ValueError):verify(root,pin)


@pytest.mark.parametrize('fault',['evaluation','eligibility','inference','success-sink','completion'])
def test_interruptions_fail_closed(tmp_path,history,monkeypatch,fault):
    root=tmp_path/'partial'
    if fault in ('evaluation','eligibility'):
        name='evaluate_record' if fault=='evaluation' else 'eligibility'
        monkeypatch.setattr(p,name,lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()))
    elif fault=='inference':monkeypatch.setattr(p,'infer_synthetic_counts',lambda *args,**kwargs: (_ for _ in ()).throw(KeyboardInterrupt()))
    elif fault=='success-sink':
        real=p.Accumulator
        def broken(**kwargs):
            kwargs['success_sink']=lambda raw: (_ for _ in ()).throw(KeyboardInterrupt())
            return real(**kwargs)
        monkeypatch.setattr(p,'Accumulator',broken)
        monkeypatch.setattr(p.SHA256Engine,'digest',lambda *args:bytes(32))
    else:
        real=p.durable_create
        def torn(path,raw):
            if path.name=='complete.json':path.write_bytes(raw[:5]);raise KeyboardInterrupt()
            return real(path,raw)
        monkeypatch.setattr(p,'durable_create',torn)
    with pytest.raises(KeyboardInterrupt):p.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    with pytest.raises(ValueError):verify(root,'0'*64)


def test_reference_independence_and_reused_accepted_algorithms():
    code="import e002_verify.integration,sys; assert not any(n=='hashlab' or n.startswith('hashlab.') for n in sys.modules)"
    subprocess.run([sys.executable,'-B','-c',code],cwd=REPO,check=True)
    for original,copied in [('tests/exp002_reference.py','src/e002_verify/binomial_reference.py'),
        ('tests/exp002_secondary_reference.py','src/e002_verify/secondary_reference.py')]:
        assert (REPO/original).read_bytes().replace(b'\r\n',b'\n')==(REPO/copied).read_bytes()


def test_real_complete_history_and_combined_fixture(tmp_path):
    if not AUDIT.is_dir():pytest.skip('retained S1.4 evidence unavailable')
    root=tmp_path/'real';pin=p.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    result=verify(root,pin)
    assert result['records']==206 and result['rehash_compression_blocks']==274
    assert result['successes']['A3:V']==1 and sum(result['successes'].values())==1
    replay=tmp_path/'repeat';assert p.run_fixture(replay,audit_root=AUDIT,repository_root=REPO)==pin
    assert {f.name:f.read_bytes() for f in root.iterdir()}=={f.name:f.read_bytes() for f in replay.iterdir()}


def test_output_cannot_touch_retained_history(history):
    with pytest.raises(ValueError):p.run_fixture(REPO/'results/forbidden-i3',audit_root=AUDIT,repository_root=REPO)
