"""Small engineering-only qualification. No production/QA2/benchmark activation."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import copy
import io
import json
import logging
import shutil
import struct
import traceback

import pytest
from hashing_fixture import synthetic_hashing_identity

from hashlab.experiments import exp002_kernel as k
from hashlab.experiments import exp002_kernel_plan as plans
from hashlab.experiments import exp002_kernel_evidence as binary
from hashlab.experiments import exp002_kernel_inference as inference
from hashlab.experiments import exp002_kernel_disclosure as disclosure
from hashlab.experiments.exp002 import Exclusions,HammingPopulation,a2_prefix
from hashlab.experiments.exp002_controls import Feistel64,control_keys,inverse_history
from hashlab.experiments.exp002_s14 import VerifiedS14
from hashlab.experiments.exp002_foundation import canonical
from hashlab.experiments import exp002_integration as i3
from hashlab.experiments import exp002_integration_statistics as bridge
from e002_verify import kernel as ref

REPO=Path(__file__).resolve().parents[1]
AUDIT=REPO/'results/e001-s14-audit-20261012-01'


def unit_inputs(monkeypatch):
    ranks=(0,1,2,3,32,63,127,4095,5000)
    history=VerifiedS14(Exclusions(ranks,HammingPopulation()))
    n,two=control_keys(0,'experiment-002-kat');prp=Feistel64(n)
    values=[HammingPopulation().unrank(r) for r in ranks]+[prp.forward(0),prp.forward(2**63),prp.forward(2**63)]
    inverse=inverse_history(prp,[v.to_bytes(8,'big') for v in values],identity={'unit_only':True})
    prefixes=tuple(a2_prefix(b'E002-I1!',j) for j in range(3000))
    inputs=history,prp,inverse,two,prefixes
    monkeypatch.setattr(k,'_engineering_inputs',lambda *a:inputs)
    monkeypatch.setattr(ref.arms,'load_history',lambda *a:(set(ranks),history.identity()))
    monkeypatch.setattr(ref.controls,'load_history',lambda *a:(set(values),inverse.identity,len(values)))
    return inputs


@pytest.fixture
def inputs(monkeypatch): return unit_inputs(monkeypatch)


@pytest.fixture(scope='module')
def original(tmp_path_factory):
    root=tmp_path_factory.mktemp('kernel-fixed')/'run'
    with pytest.MonkeyPatch.context() as mp:
        unit_inputs(mp)
        outcome=k.run_engineering(root,audit_root=AUDIT,repository_root=REPO)
    return root,outcome.completion_sha256


@pytest.fixture
def evidence(tmp_path,original,inputs):
    root=tmp_path/'copy';shutil.copytree(original[0],root)
    return root,original[1]


def verify(root,pin):
    return ref.verify_engineering(root,completion_sha256=pin,audit_root=AUDIT,repository_root=REPO)


def production_plan():
    runtime=plans.RuntimeBinding('CPython 3.13.0 engineering identity','unit-platform','1'*64,
                                (('PyYAML','6.0.3','2'*64),),hashing=synthetic_hashing_identity())
    return plans.ProductionPlan('16f8b30ae30a9ef3ffc0f2868e9508e70c8007cd',
        tuple(plans.Artifact(p,1,'3'*64) for p in sorted(plans.REQUIRED_SOURCES)),runtime)


@pytest.mark.parametrize('commit,round_number,randomness,pin',[
    ('0'*40,1,'0'*64,'1becffc4219d959c2e226af2a88f7488f21c7c5cc92de93631e57b68b86287fa'),
    ('0123456789abcdef0123456789abcdef01234567',42,'ff'*32,'3c43e42137e5a020e121e0b7edd168c90f5c8b68e00692c55c6b5891f3c1cac3')])
def test_public_master_vectors(commit,round_number,randomness,pin):
    material=plans.master_material(commit,round_number,randomness)
    assert material==f'hashlab-exp002-master-v1|{commit}|{round_number}|{randomness}'.encode('ascii')
    assert sha256(material).hexdigest()==pin
    assert plans.derive_master(commit,round_number,randomness)==int(pin[:16],16)


@pytest.mark.parametrize('args',[
    ('a'*39,1,'0'*64),('A'*40,1,'0'*64),('0'*40,True,'0'*64),
    ('0'*40,0,'0'*64),('0'*40,'1','0'*64),('0'*40,2**64,'0'*64),
    ('0'*40,1,'ff'),('0'*40,1,'F'*64)])
def test_bad_derivation_inputs(args):
    with pytest.raises(ValueError): plans.derive_master(*args)


def test_frozen_production_plan_roundtrip_and_geometry():
    plan=production_plan();assert plans.ProductionPlan.from_bytes(plan.serialize())==plan
    obj=plan.to_dict();assert sum(x['trials'] for x in obj['science']['streams'])==180200000
    assert obj['science']['config']['per_stage']==15000000
    assert obj['restrictions']['execution_enabled'] is False
    assert obj['seed']['domain']=='experiment-002'
    assert obj['evidence']['audit_decision'].startswith('unresolved')
    assert k._quotas(plan)['P1','C']==200000


@pytest.mark.parametrize('field',[
    'schema','identities','science','config_sha256','seed','controls','sources','runtime',
    'history','evidence','restrictions','extra'])
def test_missing_or_mismatched_plan_bindings(field):
    obj=production_plan().to_dict()
    if field=='extra': obj['extra']=True
    else: obj.pop(field)
    with pytest.raises((ValueError,KeyError)): plans.ProductionPlan.from_bytes(canonical(obj))


@pytest.mark.parametrize('mutation',[
    lambda x:x['science']['config'].update(per_stage=32),
    lambda x:x['seed'].update(domain='experiment-002-kat'),
    lambda x:x['seed']['arm_labels']['A1'].update(selection=['wrong']),
    lambda x:x['history'].update(occurrences=60721),
    lambda x:x['controls'].update(n1_stop_exclusive=31000000),
    lambda x:x['evidence'].update(format='hashlab-e002-i3-fixture-v1'),
    lambda x:x['restrictions'].update(execution_enabled=True),
    lambda x:x['identities'].update(scientific_baseline='revision-9'),
    lambda x:x['sources'].pop(),
    lambda x:x['runtime'].update(dependencies=[]),
])
def test_altered_frozen_plan(mutation):
    obj=production_plan().to_dict();mutation(obj)
    with pytest.raises(ValueError): plans.ProductionPlan.from_bytes(canonical(obj))


def test_no_quota_seed_domain_or_execution_override(tmp_path,monkeypatch):
    def touched(*a,**kw): pytest.fail('production touched I/O/generation')
    monkeypatch.setattr(k,'_engineering_inputs',touched)
    monkeypatch.setattr(k,'_scheduled_attempts',touched)
    for kwargs in ({},{'master':0},{'enabled':True},{'per_stage':32},{'domain':'experiment-002-kat'}):
        with pytest.raises(PermissionError): k.run_production(tmp_path/'forbidden',**kwargs)
    with pytest.raises(PermissionError): k._coordinate(tmp_path,production_plan(),None,None)
    with pytest.raises(PermissionError): k._production_inputs(None,None,None,None,None,None,master=0)
    with pytest.raises(TypeError): plans.ProductionPlan('0'*40,(),None,master=0)
    with pytest.raises(TypeError): plans.EngineeringPlan(per_stage=1)
    assert not (tmp_path/'forbidden').exists()


def test_domains_are_distinct():
    from hashlab.experiments.exp002 import a2_key,arm_subseed
    assert control_keys(0,'experiment-002')!=control_keys(0,'experiment-002-kat')
    assert a2_key(0,'experiment-002')!=a2_key(0,'experiment-002-kat')
    assert arm_subseed(0,'A1','selection')!=101


def test_local_source_runtime_fail_closed(monkeypatch):
    plan=production_plan()
    monkeypatch.setattr(plans,'observe_runtime',lambda:replace(plan.runtime,platform='wrong'))
    with pytest.raises(ValueError,match='runtime'): plan.validate_local_inputs(REPO,AUDIT)
    monkeypatch.setattr(plans,'observe_runtime',lambda:plan.runtime)
    with pytest.raises(ValueError,match='source'): plan.validate_local_inputs(REPO,AUDIT)


def test_complete_bounded_replay_repeat_and_one_hash(evidence,tmp_path,inputs,monkeypatch):
    root,pin=evidence
    result=verify(root,pin)
    assert result['evaluations']==206 and result['compression_blocks']==274 and result['attempts']==208
    capture=k.authenticate_capture(root,plan=plans.EngineeringPlan(),completion_sha256=pin)
    assert not capture.engineering_accounting()['complete']
    assert 'withheld' in repr(capture)
    calls=[];real=k.SHA256Engine.digest
    def counted(self,raw): calls.append(len(raw));return real(self,raw)
    monkeypatch.setattr(k.SHA256Engine,'digest',counted)
    repeat=tmp_path/'repeat';outcome=k.run_engineering(repeat,audit_root=AUDIT,repository_root=REPO)
    assert outcome.completion_sha256==pin and len(calls)==206
    assert sum((n+72)//64 for n in calls)==274
    assert {p.name:p.read_bytes() for p in root.iterdir()}=={p.name:p.read_bytes() for p in repeat.iterdir()}
    # New compact candidate payload: 208 attempts, including two history rejections.
    assert (root/'chunk-00000000.bin').stat().st_size<40000
    assert disclosure.inspect_evidence(root,plans.EngineeringPlan(),pin)['confirmatory_complete'] is False


@pytest.mark.parametrize('mode,raw,success',[
    ('P1',2**248,True),('P2+',2**248,True),('P2-',0,False)])
def test_supplied_digest_transform_propagation(mode,raw,success):
    from hashlab.experiments.exp002_controls import ControlEngine
    a=binary.Attempt(mode,'C',(2**64-1).to_bytes(8,'big'),0,source_index=2**63)
    digest=raw.to_bytes(32,'big');result=ControlEngine(mode).transform(digest)
    effective=bytes.fromhex(result['effective_digest_hex'])
    encoded=binary.encode_row(0,a,digest,effective)
    sequence,decoded,observed_raw,observed_effective,_=binary.decode_row(io.BytesIO(encoded))
    assert sequence==0 and decoded==a and observed_raw==digest and observed_effective==effective
    assert (int.from_bytes(effective,'big')<2**248) is success


@pytest.mark.parametrize('count',[1,4096,4097,8193])
def test_chunk_boundaries_constant_buffer_and_independent_decoding(tmp_path,count):
    writer=binary.ChunkWriter(tmp_path)
    for i in range(count):
        a=binary.Attempt('A1','D',(2**20+i).to_bytes(8,'big'),i,population_rank=i)
        writer.add(a,b'\xff'*32,b'\xff'*32)
    report=writer.finish()
    assert report['chunks']==(count+4095)//4096
    assert writer.handle is None and writer.row_count<=4096
    assert not any(isinstance(v,(list,dict)) for v in vars(writer).values())
    assert sum(1 for _ in binary.iter_chunks(tmp_path,expected_chunks=report['chunks'],expected_attempts=count))==count
    assert sum(1 for _ in ref.decode_chunks(tmp_path,report))==count
    assert not (tmp_path/'complete.json').exists()
    with pytest.raises(RuntimeError): writer.add(a,b'\xff'*32,b'\xff'*32)


def reseal_transport(root):
    report=json.loads((root/'complete.json').read_bytes())
    entries=[]
    for line in (root/'chunks.jsonl').read_bytes().splitlines():
        entry=json.loads(line);raw=(root/entry['name']).read_bytes()
        entry.update(size=len(raw),sha256=sha256(raw).hexdigest());entries.append(entry)
    (root/'chunks.jsonl').write_bytes(b''.join(canonical(x)+b'\n' for x in entries))
    for name,key in (('plan.json','plan'),('history.json','history'),('environment.json','environment'),('accounting.json','accounting'),('chunks.jsonl','index')):
        raw=(root/name).read_bytes();report[key]=dict(size=len(raw),sha256=sha256(raw).hexdigest())
    raw=canonical(report);(root/'complete.json').write_bytes(raw)
    return sha256(raw).hexdigest()


@pytest.mark.parametrize('mutation',[
    'missing','extra','marker','truncate','digest','duplicate','reorder','index','accounting',
    'plan','false-complete','history','failure','torn-complete'])
def test_tampered_evidence_fails_both_readers(evidence,mutation):
    root,pin=evidence;chunk=root/'chunk-00000000.bin'
    if mutation=='missing': chunk.unlink()
    elif mutation=='extra': (root/'unexpected').write_bytes(b'x')
    elif mutation=='marker': (root/'INCOMPLETE').write_bytes(b'x')
    elif mutation=='truncate': chunk.write_bytes(chunk.read_bytes()[:-1])
    elif mutation in ('digest','duplicate','reorder'):
        raw=bytearray(chunk.read_bytes());start=binary.HEADER.size;size=binary.ROW.size+8+64
        if mutation=='digest':raw[start+binary.ROW.size+8]^=1
        elif mutation=='duplicate':raw[start+size:start+2*size]=raw[start:start+size]
        else:raw[start:start+2*size]=raw[start+size:start+2*size]+raw[start:start+size]
        chunk.write_bytes(raw)
    elif mutation=='index': (root/'chunks.jsonl').write_bytes((root/'chunks.jsonl').read_bytes()*2)
    elif mutation=='accounting':
        obj=json.loads((root/'accounting.json').read_bytes());obj['streams'][0]['trials']-=1
        (root/'accounting.json').write_bytes(canonical(obj))
    elif mutation=='plan': (root/'plan.json').write_bytes(b'{}')
    elif mutation=='history': (root/'history.json').write_bytes(b'{}')
    elif mutation=='failure': (root/'failure.json').write_bytes(b'{}')
    elif mutation=='torn-complete': (root/'complete.json').write_bytes(b'{')
    else:
        obj=json.loads((root/'complete.json').read_bytes());obj['confirmatory_complete']=True
        (root/'complete.json').write_bytes(canonical(obj))
    for reader in (lambda:k.authenticate_capture(root,plan=plans.EngineeringPlan(),completion_sha256=pin),lambda:verify(root,pin)):
        with pytest.raises((ValueError,OSError,KeyError)): reader()


@pytest.mark.parametrize('mutation',['digest','rank','source','stage','effective'])
def test_resealed_semantic_corruption_rejected_independently(evidence,mutation):
    root,pin=evidence;chunk=root/'chunk-00000000.bin';raw=bytearray(chunk.read_bytes())
    start=binary.HEADER.size
    if mutation=='digest':raw[start+binary.ROW.size+8]^=1
    elif mutation=='effective':raw[start+binary.ROW.size+8+32]^=1
    else:
        fields=list(binary.ROW.unpack(raw[start:start+binary.ROW.size]))
        if mutation=='rank':fields[7]=999
        elif mutation=='source':fields[5]=1
        elif mutation=='stage':fields[2]=1-fields[2]
        raw[start:start+binary.ROW.size]=binary.ROW.pack(*fields)
    trailer_start=len(raw)-binary.TRAILER.size
    rows,length,_=binary.TRAILER.unpack(raw[trailer_start:])
    raw[trailer_start:]=binary.TRAILER.pack(rows,length,sha256(raw[binary.HEADER.size:trailer_start]).digest())
    chunk.write_bytes(raw)
    new_pin=reseal_transport(root)
    with pytest.raises(ValueError): verify(root,new_pin)


@pytest.mark.parametrize('point',['provider','engine','sink','finish'])
def test_interruptions_blind_all_normal_output_and_retain_evidence(tmp_path,inputs,monkeypatch,capsys,point):
    secret='PRIVATE_V_SUCCESS_58231_ratio_histogram'
    logger=logging.getLogger('kernel-adversarial')
    handler=logging.StreamHandler();logger.addHandler(handler)
    def fail(*args,**kwargs):
        print(secret);logger.critical(secret);logger.log(100,secret)
        raise RuntimeError(secret)
    if point=='provider':
        original=k._scheduled_attempts
        def broken(*args):
            yield next(original(*args));fail()
        monkeypatch.setattr(k,'_scheduled_attempts',broken)
    elif point=='engine':monkeypatch.setattr(k.SHA256Engine,'digest',fail)
    elif point=='sink':monkeypatch.setattr(binary.ChunkWriter,'add',fail)
    else:monkeypatch.setattr(binary.ChunkWriter,'finish',fail)
    root=tmp_path/'failed'
    try:
        with pytest.raises(disclosure.KernelFailure) as exc:
            k.run_engineering(root,audit_root=AUDIT,repository_root=REPO)
    finally:logger.removeHandler(handler)
    observed=capsys.readouterr()
    assert secret not in observed.out+observed.err+str(exc.value)+''.join(traceback.format_exception(exc.value))
    assert exc.value.__context__ is None
    assert not (root/'complete.json').exists() and (root/'INCOMPLETE').exists()
    assert secret.encode() not in (root/'failure.json').read_bytes()
    with pytest.raises(disclosure.KernelFailure):k.run_engineering(root,audit_root=AUDIT,repository_root=REPO)


@pytest.mark.parametrize('mutation',['gap','duplicate','rank','nonce','source','reorder','drop','early-v'])
def test_provider_continuity_faults_fail_before_completion(tmp_path,inputs,monkeypatch,mutation):
    original=k._scheduled_attempts
    def broken(*args):
        rows=list(original(*args)) # <=208 unit-only attempts.
        if mutation=='gap': rows[0]=replace(rows[0],accepted_index=1)
        elif mutation=='duplicate': rows.insert(1,rows[0])
        elif mutation=='rank': rows[0]=replace(rows[0],population_rank=255)
        elif mutation=='nonce': rows[64]=replace(rows[64],source_index=1)
        elif mutation=='source':
            j=next(i for i,a in enumerate(rows) if a.arm=='N1');rows[j]=replace(rows[j],source_index=1)
        elif mutation=='reorder': rows[0],rows[64]=rows[64],rows[0]
        elif mutation=='drop': rows.pop()
        else:
            j=next(i for i,a in enumerate(rows) if a.arm=='N2' and not a.reasons)
            rows[j]=replace(rows[j],stage='V',cluster=1500)
        yield from rows
    monkeypatch.setattr(k,'_scheduled_attempts',broken)
    root=tmp_path/'bad'
    with pytest.raises(disclosure.KernelFailure): k.run_engineering(root,audit_root=AUDIT,repository_root=REPO)
    assert not (root/'complete.json').exists()


def test_measured_inference_refuses_synthetic_partial_and_forged(evidence):
    root,pin=evidence;capture=k.authenticate_capture(root,plan=plans.EngineeringPlan(),completion_sha256=pin)
    for supplied in (capture,{},i3.count_fixtures(REPO)['cases'][0]['accounting'],None):
        with pytest.raises(disclosure.KernelFailure): inference.infer_measured(supplied,plan=production_plan())
    with pytest.raises(ValueError):k.VerifiedCapture({},production_plan(),'0'*64)
    with pytest.raises(ValueError):disclosure.RestrictedInference({'controls':{'statistical_gate_passed':False}})
    with pytest.raises(PermissionError): k.authenticate_capture(root,plan=production_plan(),completion_sha256=pin)
    assert disclosure.inspect_evidence(root,production_plan(),pin)['validation']=='withheld'


@pytest.mark.parametrize('case_index',range(5))
def test_unchanged_full_geometry_calculation_and_independent_statistics(case_index):
    accounting=i3.count_fixtures(REPO)['cases'][case_index]['accounting']
    # Explicit artificial count-only unit work, never an authenticated measured capture.
    result=inference._calculate(accounting)
    accepted=bridge.infer_synthetic_counts(accounting,scope='synthetic-full-geometry-counts')
    assert result=={key:accepted[key] for key in ('primary','controls','secondary')}
    from e002_verify.integration_statistics import verify_inference
    verify_inference(accounting,accepted)
    assert result['secondary']['family_size']==36


def test_inference_partial_invalid_and_unresolved_fail_closed(evidence,monkeypatch):
    root,pin=evidence
    partial=k.authenticate_capture(root,plan=plans.EngineeringPlan(),completion_sha256=pin).engineering_accounting()
    with pytest.raises(ValueError):inference._calculate(partial)
    counts=i3.count_fixtures(REPO)['cases'][0]['accounting']
    invalid=copy.deepcopy(counts);invalid['streams'][2]['cluster_successes'][0]+=1
    with pytest.raises(ValueError):inference._calculate(invalid)
    def ambiguous(*a):raise ArithmeticError('unit-only unresolved numerical cutoff')
    monkeypatch.setattr(inference.secondary,'analyze_secondary',ambiguous)
    with pytest.raises(ArithmeticError):inference._calculate(counts)


def test_restricted_final_and_f4_distinctions():
    counts=i3.count_fixtures(REPO)['cases']
    # Explicit private unit capability, not observed data or a governance receipt.
    passing=disclosure.RestrictedInference(inference._calculate(counts[0]['accounting']),_token=disclosure._INFERENCE)
    failed=disclosure.RestrictedInference(inference._calculate(counts[2]['accounting']),_token=disclosure._INFERENCE)
    assert passing.inspect()['validation']=='withheld' and 'withheld' in repr(passing)
    with pytest.raises(PermissionError): passing.disclose_f4()
    with pytest.raises(PermissionError): failed.disclose_final('invented approval')
    assert failed.disclose_f4()['failure']=='F4'
    assert failed.disclose_f4()['status']=='BLOCKED'
    assert disclosure.failure_report('F1')['primary']=='withheld'
    with pytest.raises(ValueError):disclosure.failure_report('F4')
    with pytest.raises(ValueError):disclosure.progress('PRIVATE_COUNTER',1)


def test_full_geometry_scheduler_arguments_without_production_generation(inputs,monkeypatch):
    """Spies only: zero production-density sampling, encodings or candidate hashes."""
    history,prp,inverse,two,prefixes=inputs;observed={}
    def a1(size,d,v,**kw):observed['A1']=(size,d,v,kw);return iter(())
    def a2(p):observed['A2']=len(p);return iter(())
    def a3(size,d,v,**kw):observed['A3']=(size,d,v,kw);return iter(())
    class P:
        failed=False
        def __init__(self,p,h,g):observed['P']=g
        def n1(self):return iter(())
        def positives(self):return iter(())
    class N:
        failed=False
        def __init__(self,key,p,g):observed['N2']=g
        def attempts(self):return iter(())
    monkeypatch.setattr(k,'a1_sample_ranks',a1);monkeypatch.setattr(k,'a2_stream',a2)
    monkeypatch.setattr(k,'sample_ranks',a3);monkeypatch.setattr(k,'PermutationControls',P)
    monkeypatch.setattr(k,'N2Controls',N)
    assert list(k._scheduled_attempts(production_plan(),history,prp,inverse,two,prefixes,
                                   {'A1':(1,2),'A3':(3,4)}))==[]
    assert observed['A1'][:3]==(4293918720,15000000,15000000)
    assert observed['A2']==3000
    assert observed['A3'][:3]==(82128984,15000000,15000000)
    assert observed['A3'][3]['excluded']==history.exclusions.ranks
    assert observed['P'].domain==observed['N2'].domain=='experiment-002'
    assert (observed['P'].per_stage,observed['P'].p1,observed['P'].p2)==(15000000,200000,15000000)


def test_production_inference_dispatch_with_explicit_unit_capability(monkeypatch):
    # Internal capability injection is unit-only, zero observations and never
    # serialized as a measured artifact or issued by authenticate_capture.
    plan=production_plan();counts=i3.count_fixtures(REPO)['cases'][0]['accounting']
    capture=k.VerifiedCapture(counts,plan,'0'*64,_token=k._CAPTURE)
    result=inference.infer_measured(capture,plan=plan)
    assert result.inspect()['validation']=='withheld'
    with pytest.raises(PermissionError):result.disclose_final()
    def ambiguous(*a):
        print('PRIVATE_NUMERICAL_VALIDATION_COUNT')
        raise ArithmeticError('PRIVATE_NUMERICAL_VALIDATION_COUNT')
    monkeypatch.setattr(inference.secondary,'analyze_secondary',ambiguous)
    with pytest.raises(disclosure.KernelFailure) as exc:
        inference.infer_measured(capture,plan=plan)
    assert 'PRIVATE_NUMERICAL' not in str(exc.value)


def test_inference_exception_output_is_suppressed(monkeypatch,capsys):
    plan=production_plan();counts=i3.count_fixtures(REPO)['cases'][0]['accounting']
    capture=k.VerifiedCapture(counts,plan,'0'*64,_token=k._CAPTURE)
    def fail(*a):
        print('SECRET_VALIDATION_COUNT')
        raise ArithmeticError('SECRET_VALIDATION_COUNT')
    monkeypatch.setattr(inference.primary,'analyze',fail)
    with pytest.raises(disclosure.KernelFailure) as exc:inference.infer_measured(capture,plan=plan)
    captured=capsys.readouterr()
    assert 'SECRET_VALIDATION' not in captured.out+captured.err+''.join(traceback.format_exception(exc.value))


def test_chunk_write_failure_poisoning_and_no_repair(tmp_path,monkeypatch):
    writer=binary.ChunkWriter(tmp_path)
    row=binary.Attempt('A1','D',(2**20).to_bytes(8,'big'),0,population_rank=0)
    writer.add(row,b'\xff'*32,b'\xff'*32)
    def fail(*a):raise OSError('unit fsync failure')
    monkeypatch.setattr(binary.os,'fsync',fail)
    with pytest.raises(OSError):writer.finish()
    assert writer.failed
    writer.abandon()
    with pytest.raises(RuntimeError):writer.finish()
    assert (tmp_path/'chunk-00000000.bin').exists()
    assert not (tmp_path/'complete.json').exists()


def test_off_machine_independent_import_boundary(tmp_path):
    import subprocess,sys
    script="import sys;sys.path.insert(0,sys.argv[1]);import e002_verify.kernel;assert not any(n=='hashlab' or n.startswith('hashlab.') for n in sys.modules)"
    result=subprocess.run([sys.executable,'-B','-c',script,str(REPO/'src')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_cli_cannot_dispatch_production(tmp_path):
    import subprocess,sys
    result=subprocess.run([sys.executable,'-B',str(REPO/'tools/qualify_e002_kernel.py'),
                           'production',str(tmp_path/'forbidden')],capture_output=True,text=True)
    assert result.returncode==2 and 'invalid choice' in result.stderr
    assert not (tmp_path/'forbidden').exists()


@pytest.mark.parametrize('mutation',['source-omission','counter-bool','index-bool'])
def test_resealed_metadata_type_or_binding_corruption(evidence,mutation):
    root,pin=evidence
    if mutation=='source-omission':
        env=json.loads((root/'environment.json').read_bytes());env['sources'].pop()
        (root/'environment.json').write_bytes(canonical(env))
    elif mutation=='counter-bool':
        report=json.loads((root/'complete.json').read_bytes());report['rejections']['A1']=False
        (root/'complete.json').write_bytes(canonical(report))
    else:
        entry=json.loads((root/'chunks.jsonl').read_bytes());entry['sequence']=False
        (root/'chunks.jsonl').write_bytes(canonical(entry)+b'\n')
    new_pin=reseal_transport(root)
    with pytest.raises(ValueError): verify(root,new_pin)
