"""Foundation qualification: supplied synthetic bytes/digests, no hashing engine."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import ast

import pytest

from hashlab.experiments import exp002_foundation as f

COMMIT='a'*40  # Synthetic metadata identity, never a selected execution seed.
GOOD=b'\0'*32
BAD=b'\xff'*32


def record(arm='A1',stage='D',index=0):
    if arm in f.CLUSTERED:
        # Repeated zero prefixes are artificial serialization/accounting fixtures.
        raw='00'*76+(index%10000).to_bytes(4,'little').hex() if arm=='A2' else '00'*80
        return f.CandidateRecord(arm,stage,index,raw,index//10000+(1500 if stage=='V' else 0))
    return f.CandidateRecord(arm,stage,index,'0000000100000000' if arm=='A3' else '0000000000100000')


def test_plan_fingerprint_contract():
    plan=f.Plan(COMMIT)
    raw=plan.serialize()
    assert f.Plan.from_dict(json.loads(raw))==plan
    # Independent encoding and domain construction against the stated contract.
    reference=json.dumps(plan.to_dict(),sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    assert sha256(b'hashlab-exp002-seedless-plan-v2\x00'+reference).hexdigest()==plan.fingerprint
    assert f.Plan('b'*40).fingerprint!=plan.fingerprint
    assert len(raw)<10000
    data=plan.to_dict()
    assert data['config']['protocol_identity']==f.PROTOCOL_IDENTITY
    assert data['config']['target']==2**248
    assert data['config']['a3_population']==82068263
    assert data['config']['master']=='derived-from-beacon'
    assert data['statistics']['secondary']['identity']==f.SECONDARY_ID


@pytest.mark.parametrize('field,value',[('extra',1),('schema','unknown'),('code_commit','A'*40)])
def test_plan_rejects_changes(field,value):
    data=f.Plan(COMMIT).to_dict()
    data[field]=value
    with pytest.raises(ValueError):f.Plan.from_dict(data)


@pytest.mark.parametrize('section,field,value',[
    ('config','per_stage',1),('config','alpha_difference','0.01'),
    ('config','a1_a3_seed_encoding','new'),('config','master',0),
    ('e001','a1_intersection',1),('statistics','secondary','bound')])
def test_frozen_nested_plan(section,field,value):
    data=f.Plan(COMMIT).to_dict()
    data[section][field]=value
    with pytest.raises(ValueError):f.Plan.from_dict(data)


@pytest.mark.parametrize('arm',f.ARMS)
def test_record_roundtrip(arm):
    r=record(arm,'C' if arm.startswith('P') else 'D')
    assert f.CandidateRecord.deserialize(r.serialize())==r
    sr=f.SuccessRecord(r,GOOD.hex())
    assert f.SuccessRecord.deserialize(sr.serialize())==sr


@pytest.mark.parametrize('digest',['01'+'00'*31,'ff'*32,'0'*63,'AA'*32])
def test_strict_success_target(digest):
    with pytest.raises(ValueError):f.SuccessRecord(record(),digest)


def test_record_invalid_geometry_and_membership():
    bad=[dict(arm='A1',stage='C'),dict(index=True),dict(index=-1),dict(index=15000000),
         dict(candidate_hex='0'*16),dict(cluster=0),dict(schema='unknown')]
    r=record()
    for changes in bad:
        with pytest.raises(ValueError):replace(r,**changes)
    a2=record('A2')
    for changes in (dict(cluster=1),dict(stage='V'),dict(candidate_hex='00'*76+'01000000'),dict(cluster=True)):
        with pytest.raises(ValueError):replace(a2,**changes)
    with pytest.raises(ValueError):replace(record('A3'),candidate_hex='0000000000000001')
    assert record('A2','V',14999999).cluster==2999
    assert record('N2','V',0).cluster==1500


@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}',b'{ "x":1}',b'{"x":NaN}',b'{"x":1.0}',b'[]\n'])
def test_noncanonical_json(raw):
    with pytest.raises(ValueError):f.decode(raw)


def test_unknown_record_fields():
    data=record().to_dict()
    data['seed']=1
    with pytest.raises(ValueError):f.CandidateRecord.deserialize(f.canonical(data))


def test_stream_counts_and_diagnostics():
    successes=[]
    chunks=[]
    indices=f.SuccessIndexCollector(chunks.append,2)
    acc=f.Accumulator(index_collector=indices,success_sink=successes.append)
    for a,s,_ in f.LIMITS:
        acc.add(record(a,s,0),GOOD)
        acc.add(record(a,s,1),BAD)
    snapshot=acc.snapshot()
    f.validate_accounting(snapshot)
    for row in snapshot['streams']:
        assert (row['trials'],row['successes'])==(2,1)
        assert row['leading_zero_bits'][256]==1 and row['leading_zero_bits'][0]==1
        assert row['first_byte'][0]==1 and row['last_byte'][255]==1
    indices.close()
    assert sum(len(c) for c in chunks)==13
    assert len(successes)==13
    snapshot['streams'][0]['trials']=99
    assert acc.snapshot()['streams'][0]['trials']==2
    with pytest.raises(ValueError):acc.finish()
    with pytest.raises(RuntimeError):acc.snapshot()


def test_cluster_boundary_streaming_fixed_memory():
    count=0
    maximum=0
    def sink(chunk):
        nonlocal count,maximum
        count+=len(chunk)
        maximum=max(maximum,len(chunk))
    collector=f.SuccessIndexCollector(sink,7)
    acc=f.Accumulator(index_collector=collector)
    for i in range(10001):
        acc.add(record('N2','D',i),GOOD)
        assert collector.buffered<7
    collector.close()
    row=next(r for r in acc.snapshot()['streams'] if r['arm']=='N2' and r['stage']=='D')
    assert row['cluster_trials'][:3]==[10000,1,0]
    assert count==10001 and maximum==7
    assert len(acc._streams)==13
    assert all(len(v['first_byte'])==256 for v in acc._streams.values())


@pytest.mark.parametrize('failure',['digest','gap','duplicate','audit','success_sink','index_sink'])
def test_fail_closed(failure):
    def fail(*args):raise OSError('synthetic failure')
    class Audit:
        def check(self,r):fail()
    acc=f.Accumulator(audit=Audit() if failure=='audit' else None,
        success_sink=fail if failure=='success_sink' else None,
        index_collector=f.SuccessIndexCollector(fail,1) if failure=='index_sink' else None)
    if failure=='duplicate':acc.add(record(),GOOD)
    with pytest.raises((ValueError,OSError)):
        acc.add(record(index=1 if failure=='gap' else 0),b'bad' if failure=='digest' else GOOD)
    with pytest.raises(RuntimeError):acc.snapshot()
    with pytest.raises(RuntimeError):acc.add(record(),GOOD)


def test_index_sink_failure_and_no_retry():
    calls=[]
    def fail(chunk):
        calls.append(chunk)
        raise OSError('synthetic disk full')
    c=f.SuccessIndexCollector(fail,1)
    with pytest.raises(OSError):c.add(record())
    with pytest.raises(RuntimeError):c.flush()
    assert len(calls)==1


@pytest.mark.parametrize('failure',[None,'missing','duplicate','order','beyond'])
def test_streaming_success_validation(failure):
    stored=[]
    acc=f.Accumulator(success_sink=stored.append)
    acc.add(record(index=0),GOOD)
    acc.add(record(index=1),GOOD)
    if failure=='missing':stored.pop()
    if failure=='duplicate':stored[1]=stored[0]
    if failure=='order':stored.reverse()
    if failure=='beyond':stored[1]=f.SuccessRecord(record(index=2),GOOD.hex()).serialize()
    if failure is None:f.validate_success_records(iter(stored),acc.snapshot())
    else:
        with pytest.raises(ValueError):f.validate_success_records(iter(stored),acc.snapshot())


def test_evidence_success_payload(tmp_path):
    records=[]
    acc=f.Accumulator(success_sink=records.append)
    acc.add(record('A2'),GOOD)
    payloads={'accounting.json':f.canonical(acc.snapshot()),'successes.jsonl':b'\n'.join(records)+b'\n'}
    entries=[]
    for name,raw in sorted(payloads.items()):
        (tmp_path/name).write_bytes(raw)
        entries.append(f.EvidenceFile(name,len(raw),sha256(raw).hexdigest()))
    plan=f.Plan(COMMIT)
    m=f.ExecutionManifest(plan.fingerprint,COMMIT,'partial',tuple(entries))
    f.validate_evidence(tmp_path,plan,m,pinned_metadata_sha256=sha256(m.serialize()).hexdigest())


def test_strict_target_adjacent_digests():
    acc=f.Accumulator()
    acc.add(record(index=0),b'\x00'+b'\xff'*31)
    acc.add(record(index=1),b'\x01'+b'\x00'*31)
    row=acc.snapshot()['streams'][0]
    assert row['successes']==1
    assert row['leading_zero_bits'][8]==1 and row['leading_zero_bits'][7]==1


def test_canonical_success_known_bytes():
    r=record()
    expected=(b'{"arm":"A1","candidate_hex":"0000000000100000","cluster":null,'
              b'"index":0,"schema":"hashlab-exp002-candidate-v1","stage":"D"}')
    assert r.serialize()==expected


def test_malformed_manifest_payloads():
    plan=f.Plan(COMMIT)
    payload=f.EvidenceFile('accounting.json',0,'0'*64)
    for values in ((),(payload,payload),(payload, f.EvidenceFile('a.json',0,'0'*64))):
        with pytest.raises(ValueError):f.ExecutionManifest(plan.fingerprint,COMMIT,'partial',values)
    with pytest.raises(ValueError):f.ExecutionManifest(plan.fingerprint,COMMIT,'unknown',(payload,))


def test_e001_reconstruction_request_is_pinned():
    req=f.E001ExclusionRequest()
    assert req.eight_byte_count==7000000 and req.a3_excluded_count==60721
    with pytest.raises(ValueError):replace(req,a1_intersection=1)
    with pytest.raises(ValueError):replace(req,a3_exclusion_sha256='0'*64)


def test_complete_synthetic_structure_without_full_stream(tmp_path):
    # Algebraic all-failure summaries: no candidate generation or iteration.
    counts=f.Accumulator().snapshot()
    counts['complete']=True
    for row,(_,_,n) in zip(counts['streams'],f.LIMITS):
        row['trials']=n
        row['first_byte'][255]=n
        row['last_byte'][255]=n
        row['leading_zero_bits'][0]=n
        if row['cluster_trials'] is not None:
            row['cluster_trials']=[10000]*1500
        if row['arm']=='A3':
            row['weight_trials']=[0,0,0,115404,1353892,13530704]
    f.validate_accounting(counts,require_complete=True)
    plan=f.Plan(COMMIT)
    payloads={'accounting.json':f.canonical(counts),'successes.jsonl':b''}
    entries=[]
    for name,raw in sorted(payloads.items()):
        (tmp_path/name).write_bytes(raw)
        entries.append(f.EvidenceFile(name,len(raw),sha256(raw).hexdigest()))
    m=f.ExecutionManifest(plan.fingerprint,COMMIT,'complete',tuple(entries))
    f.validate_evidence(tmp_path,plan,m,pinned_metadata_sha256=sha256(m.serialize()).hexdigest())


@pytest.mark.parametrize('change',['count','diagnostic','cluster','stage','completion','missing','unknown'])
def test_accounting_validation(change):
    acc=f.Accumulator()
    acc.add(record('A2'),GOOD)
    data=acc.snapshot()
    row=next(r for r in data['streams'] if r['arm']=='A2' and r['stage']=='D')
    if change=='count':row['successes']=2
    if change=='diagnostic':row['first_byte'][0]=0
    if change=='cluster':row['cluster_trials'][0]=0
    if change=='stage':row['stage']='V'
    if change=='completion':data['complete']=True
    if change=='missing':data['streams'].pop()
    if change=='unknown':row['extra']=0
    with pytest.raises(ValueError):f.validate_accounting(data)


def fixture_evidence(tmp_path):
    raw=f.canonical(f.Accumulator().snapshot())
    (tmp_path/'accounting.json').write_bytes(raw)
    plan=f.Plan(COMMIT)
    m=f.ExecutionManifest(plan.fingerprint,COMMIT,'partial',
        (f.EvidenceFile('accounting.json',len(raw),sha256(raw).hexdigest()),))
    return plan,m,sha256(m.serialize()).hexdigest()


def test_read_only_evidence_roundtrip(tmp_path):
    plan,m,pin=fixture_evidence(tmp_path)
    assert f.ExecutionManifest.deserialize(m.serialize())==m
    path=tmp_path/'accounting.json'
    before=(path.read_bytes(),path.stat().st_mtime_ns)
    f.validate_evidence(tmp_path,plan,m,pinned_metadata_sha256=pin)
    assert before==(path.read_bytes(),path.stat().st_mtime_ns)


@pytest.mark.parametrize('failure',['tamper','missing','unlisted','pin','plan','complete','rewrite_both'])
def test_evidence_failure(tmp_path,failure):
    plan,m,pin=fixture_evidence(tmp_path)
    if failure=='tamper':(tmp_path/'accounting.json').write_bytes(b'{}')
    if failure=='missing':(tmp_path/'accounting.json').unlink()
    if failure=='unlisted':(tmp_path/'extra.json').write_bytes(b'{}')
    if failure=='pin':pin='0'*64
    if failure=='plan':plan=f.Plan('b'*40)
    if failure=='complete':
        m=replace(m,status='complete')
        pin=sha256(m.serialize()).hexdigest()
    if failure=='rewrite_both':
        raw=b'{}'
        (tmp_path/'accounting.json').write_bytes(raw)
        m=replace(m,payloads=(f.EvidenceFile('accounting.json',2,sha256(raw).hexdigest()),))
    with pytest.raises(ValueError):f.validate_evidence(tmp_path,plan,m,pinned_metadata_sha256=pin)


@pytest.mark.parametrize('name',['../x','C:x','a/b','a\\b','con','nul.json','A.json','x.','manifest.json'])
def test_unsafe_names(name):
    with pytest.raises(ValueError):f.EvidenceFile(name,0,'0'*64)


def test_audit_guarantees():
    assert f.AuditResult('overlap','D',10,1,1,'synthetic handled rejection').rejected==1
    for kwargs in (dict(guarantee='Z'),dict(hits=11),dict(rejected=2),dict(reference=''),
                   dict(guarantee='P'),dict(guarantee='C')):
        defaults=dict(name='test',guarantee='D',checked=10,hits=1,rejected=1,reference='fixture')
        defaults.update(kwargs)
        with pytest.raises(ValueError):f.AuditResult(**defaults)
    assert f.AuditResult('N2','P',0,0,0,'not verified; bound supplied externally').checked==0


def test_foundation_has_no_runner_generator_or_statistics_calls():
    tree=ast.parse(Path(f.__file__).read_text())
    names={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
    assert not names & {'a2_candidate','a2_stream','engineering_arm_stream','arm_subseed',
        'derive_seed','binom_test','analyze','controls','eval','exec','__import__'}
    imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    assert not any(x and ('statistics' in x or 'engine' in x) for x in imports)
