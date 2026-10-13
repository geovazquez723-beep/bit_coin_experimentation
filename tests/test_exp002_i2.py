"""I2 fixed public fixtures, supplied-digest boundaries and hostile evidence."""
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json
import random
import struct
import subprocess
import sys

import pytest

from hashlab.experiments import exp002_controls as c
from hashlab.experiments import exp002_i2_synthetic as producer
from hashlab.experiments.exp002_foundation import canonical, validate_accounting
from hashlab.experiments.controls import BiasedControlEngine
from hashlab.hashing.target import Target
from e002_verify import controls as ref

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO/'results/e001-s14-audit-20261012-01'
GEOMETRY = c.ControlGeometry('experiment-002-kat',2,2,2)
PAIRS = [('0000000000000000','91e3cb22ac8c8eef'),
         ('0000000000000001','88cc10e00103efb3'),
         ('0123456789abcdef','edc1a6ceb00cf3f5'),
         ('8000000000000000','2169c0539d09e12a'),
         ('ffffffffffffffff','b5e9d7a3edc0b59e')]
STREAM = [
 '38e16fae6d0d050bae5563bb522d74bc271ebff447debfb20132bc3cb71f4e9bf3e306906421786de857521aaf56d957689efae9308419fc2c2fbdd8db5c376e5d891954273eff8476e73caf6b59fcfe',
 'd00a2761d537388a0f57bc4cddbba3c29f90f69c35e1d572c1a4fb0af27e472279bcddfaae653abd4f7419417e69f97f86799ec7d3a9385c64fed68e1089ea860ad2fb64ecd27c4a85dcbc74d62b0d56',
 'c2b5825914d5b1f9d35046e2ad9c10f7030282029bf5b440db294fb6282f2fe32cafb1abd632cdcf63cf67b36c8d96f631d10f4dccbc8ddc87f968a1d19ed8fccb5477eb33652d9a9b8d570e31d24fd5']


def prp():
    return c.Feistel64(c.control_keys(0,'experiment-002-kat')[0])


def test_key_messages_round_and_permutation_kats():
    assert c.control_keys(0,'experiment-002-kat') == ref.keys() == (
        bytes.fromhex('215fe337c843c87d'),bytes.fromhex('0000000000000000256aba5e63d013c1'))
    for a,p,h in [('N1-feistel64-w8','permutation-key-v1','7dc843c837e35f21e983a668b40bf73fa32c5b6689757f5f90befce993f6396e'),
                  ('N2-random-bytes-w80','stream-key-v1','256aba5e63d013c139d364eb1aaf8d33b244229077005fa7ec5dcd1ccf83419b')]:
        assert sha256(f'hashlab-seed-v1|0|experiment-002-kat|{a}|{p}'.encode()).hexdigest()==h
    msg=c.ROUND_LABEL+bytes(5)
    assert len(msg)==36
    assert msg.hex()=='686173686c61622d6578703030322d6665697374656c2d726f756e642d76310000000000'
    assert c.blake2b(msg,key=prp().key).hexdigest() == '22c4ea33018741ff7a99241949a892d44e8060d567f467099379b15356a74ccea43b566d7eb9951001a5e1b315e455709c0c751d0c850826bee607ae02c0cb93'
    assert prp().round_function(0,0)==ref.round_value(prp().key,0,0)==0x22c4ea33
    L=R=0
    states=[]
    for r in range(6):
        L,R=R,L^prp().round_function(r,R)
        states.append(f'{L:08x}{R:08x}')
    assert states==['0000000022c4ea33','22c4ea33f353df1f','f353df1fa8d9106b',
                    'a8d9106be4b86d5d','e4b86d5d91e3cb22','91e3cb22ac8c8eef']
    for x,y in PAIRS:
        assert prp().forward(int(x,16))==ref.permutation(int(x,16))==int(y,16)
        assert prp().inverse(int(y,16))==ref.permutation(int(y,16),reverse=True)==int(x,16)


def test_bijection_boundary_and_sampled_identity():
    rng=random.Random(301)
    values=list(range(256))+[2**32-1,2**32,2**63-1,2**63,2**64-1]+[rng.getrandbits(64) for _ in range(256)]
    outputs=[prp().forward(x) for x in values]
    assert len(set(outputs))==len(set(values))
    for x,y in zip(values,outputs):
        assert prp().inverse(y)==x and prp().forward(prp().inverse(x))==x
        assert ref.permutation(x)==y


@pytest.mark.parametrize('bad',[-1,2**64,True,1.5,None])
def test_integer_domain_rejections(bad):
    for method in (prp().forward,prp().inverse):
        with pytest.raises(ValueError):method(bad)
    with pytest.raises(ValueError):c.control_keys(bad,'experiment-002-kat')


def test_seed_separation_geometry_and_history_key_binding():
    assert c.control_keys(0,'experiment-002')!=ref.keys()
    assert c.control_keys(1,'experiment-002-kat')!=ref.keys()
    with pytest.raises(ValueError):c.control_keys(0,'other')
    with pytest.raises(ValueError):c.ControlGeometry(per_stage=2)
    with pytest.raises(ValueError):c.ControlGeometry('experiment-002-kat',10001,2,2)
    history=c.inverse_history(prp(),[])
    with pytest.raises(ValueError,match='complete authenticated'):c.PermutationControls(prp(),history)
    with pytest.raises(ValueError,match='different permutation'):
        c.PermutationControls(c.Feistel64(bytes(8)),history,GEOMETRY)


def test_inverse_overlap_outside_a3_and_duplicate_occurrences():
    # Both these raw historical examples are outside A3; the A3 subset loses them.
    raw=bytes.fromhex('2169c0539d09e12a')
    assert not c.in_a3(raw) and not c.in_a3(bytes(8))
    history=c.inverse_history(prp(),[raw,raw,bytes(8)])
    assert history.occurrences==3 and len(history.indices)==2
    assert 2**63 in history.indices and prp().inverse(0) in history.indices
    p=c.PermutationControls(prp(),history,GEOMETRY)
    rows=list(p.positives())
    assert rows[0]['source_index']==2**63 and rows[0]['reasons']==['E001']
    assert p.counts['P1']['rejected']==1 and p.counts['P1']['accepted']==2
    with pytest.raises(ValueError):c.inverse_history(prp(),[bytes(7)])


def test_structural_boundaries_and_overlapping_reasons(monkeypatch):
    for x,one,three in [(2**20-1,False,False),(2**20,True,False),(2**32-1,True,False),
                        (2**32,False,True),(2**64-1,False,False)]:
        raw=x.to_bytes(8,'big')
        assert c.in_a1(raw)==one and c.in_a3(raw)==three
    permutation=prp()
    monkeypatch.setattr(permutation,'forward',lambda source: [2**20,2**32,2**64-1,2**64-2,2**64-3,2**64-4][source])
    history=c.InverseHistory(frozenset((0,1)),2,{'unit_only':True},permutation.key)
    provider=c.PermutationControls(permutation,history,GEOMETRY)
    rows=list(provider.n1())
    assert rows[0]['reasons']==['C1','E001'] and rows[1]['reasons']==['C3','E001']
    assert provider.counts['N1']==dict(attempted=6,rejected=2,accepted=4,reasons=dict(C1=1,C3=1,E001=2,A2=0))
    assert [r['source_index'] for r in rows if not r['reasons']]==[2,3,4,5]


def test_shared_p_allocation_and_n1_stage_rejection_kats():
    permutation=prp()
    history=c.inverse_history(permutation,[permutation.forward(1).to_bytes(8,'big'),
        permutation.forward(2**63+1).to_bytes(8,'big')])
    provider=c.PermutationControls(permutation,history,GEOMETRY)
    n=list(provider.n1());p=list(provider.positives())
    assert [(r['stage'],r['source_index']) for r in n if not r['reasons']]==[('D',0),('D',2),('V',3),('V',4)]
    assert [(r['arm'],r['source_index']-2**63) for r in p if not r['reasons']]==[
        ('P1',0),('P1',2),('P2+',3),('P2+',4),('P2-',5),('P2-',6)]
    assert provider.p_cursor==2**63+7 and provider.n1_cursor==5
    assert len({r['candidate_hex'] for r in n+p if not r['reasons']})==10
    with pytest.raises(RuntimeError):list(provider.positives())
    with pytest.raises(RuntimeError):list(provider.n1())


@pytest.mark.parametrize('positive,limit',[(False,30999999),(True,2**64)])
def test_index_exhaustion_and_no_silent_shortening(positive,limit):
    provider=c.PermutationControls(prp(),c.inverse_history(prp(),[]),GEOMETRY)
    if positive:provider.p_cursor=limit-1
    else:provider.n1_cursor=limit-1
    stream=provider.positives() if positive else provider.n1()
    assert next(stream)['source_index']==limit-1
    with pytest.raises(ValueError,match='exhaustion'):next(stream)
    assert provider.failed
    with pytest.raises(RuntimeError):list(provider.n1())
    provider=c.PermutationControls(prp(),c.inverse_history(prp(),[]),GEOMETRY)
    if positive:provider.p_cursor=limit
    else:provider.n1_cursor=limit
    with pytest.raises(ValueError,match='exhaustion'):next(provider.positives() if positive else provider.n1())


def test_n2_slicing_kats_seek_and_counter_exhaustion():
    key=ref.keys()[1];stream=c.ByteStream80(key)
    for i,expected in enumerate(STREAM):
        assert stream.next().hex()==ref.random_candidate(i).hex()==expected
        assert c.ByteStream80(key,start_raw_index=i).next().hex()==expected
    for index in (3,4,5,63,64,65):
        assert c.ByteStream80(key,start_raw_index=index).next()==ref.random_candidate(index)
    assert stream.block(0)==c.blake2b(bytes(16),key=key).digest()
    assert stream.block(2**128-1)==c.blake2b(b'\xff'*16,key=key).digest()
    with pytest.raises(ValueError):stream.block(2**128)
    last=(64*2**128)//80-1
    final=c.ByteStream80(key,start_raw_index=last)
    assert len(final.next())==80
    with pytest.raises(ValueError,match='exhaustion'):final.next()


def test_n2_retains_tails_without_repeating_counters(monkeypatch):
    stream=c.ByteStream80(ref.keys()[1]);calls=[]
    original=stream.block
    def block(counter):
        calls.append(counter)
        return original(counter)
    monkeypatch.setattr(stream,'block',block)
    for i in range(4):assert stream.next()==ref.random_candidate(i)
    assert calls==[0,1,2,3,4]


def fixture_prefixes():
    return tuple(i.to_bytes(76,'big') for i in range(3000))


def test_independent_complete_a2_fixture_prefix_set():
    from hashlab.experiments.exp002 import a2_key,a2_prefix
    key=a2_key(0,'experiment-002-kat')
    assert {a2_prefix(key,j) for j in range(3000)}==ref.prefixes()


@pytest.mark.parametrize('q,expected',[(9999,('D',9999,0)),(10000,('D',10000,1)),
    (14999999,('D',14999999,1499)),(15000000,('V',0,1500)),(29999999,('V',14999999,2999))])
def test_n2_production_stage_cluster_boundaries(q,expected):
    assert c.n2_assignment(q)==expected


def test_n2_membership_rejections_and_no_dedup(monkeypatch):
    n=c.N2Controls(ref.keys()[1],fixture_prefixes(),GEOMETRY)
    accepted=bytes(76)+(10000).to_bytes(4,'little')
    raw=[bytes(80),bytes(76)+(9999).to_bytes(4,'little'),accepted,accepted,
         bytes(80),b'\x01'+bytes(79),accepted]
    def next_raw():
        value=raw[n.stream.raw_index]
        n.stream.raw_index+=1
        return value
    monkeypatch.setattr(n.stream,'next',next_raw)
    rows=list(n.attempts())
    assert rows[0]['reasons']==rows[1]['reasons']==['A2']
    assert [(r['raw_index'],r['byte_offset'],r['stage'],r['accepted_index'],r['cluster'])
        for r in rows if not r['reasons']]==[(2,160,'D',0,0),(3,240,'D',1,0),(5,400,'V',0,1500),(6,480,'V',1,1500)]
    assert rows[4]['stage']=='V' and rows[4]['accepted_index'] is None
    assert n.counts==dict(attempted=7,rejected=3,accepted=4,reasons=dict(C1=0,C3=0,E001=0,A2=3))
    with pytest.raises(ValueError):c.accepted_record(rows[0])
    with pytest.raises(RuntimeError):list(n.attempts())
    with pytest.raises(ValueError):c.N2Controls(ref.keys()[1],fixture_prefixes()[:2],GEOMETRY)
    with pytest.raises(ValueError):c.N2Controls(ref.keys()[1],[bytes(76)]*3000,GEOMETRY)


class Supplied:
    name='supplied'
    def __init__(self):self.calls=0
    def digest(self,data):
        self.calls+=1
        return data


@pytest.mark.parametrize('mode,a,p',[('P1',4210752,Fraction(83886079,17179869184)),
    ('P2+',336860,Fraction(1095216649,274877906944)),('P2-',85899345,Fraction(4209067951,1099511627776))])
def test_exact_probabilities_and_transform_boundaries(mode,a,p):
    base=Supplied();engine=c.ControlEngine(mode,base)
    assert engine.threshold==a and engine.expected_probability==p
    values=[0,c.TARGET-1,c.TARGET,c.TARGET+1,2**256-1]
    for u in (a-1,a,a+1):
        values += [u,c.TARGET+u]
    for value in values:
        raw=value.to_bytes(32,'big')
        result=engine.evaluate(raw)
        assert result==ref.transform(mode,raw)
        assert result['success']==(int(result['effective_digest_hex'],16)<c.TARGET)
        if mode!='P2-':
            legacy=BiasedControlEngine(Supplied(),Target(c.TARGET),.25 if mode=='P1' else .02)
            assert result['effective_digest_hex']==legacy.digest(raw).hex()
        if value==c.TARGET and mode=='P2-':assert not result['success'] and not result['transformed']
    assert base.calls==len(values)
    assert engine.transform((a-1).to_bytes(32,'big'))['transformed']==(mode=='P2-')
    assert not engine.transform(a.to_bytes(32,'big'))['transformed']


@pytest.mark.parametrize('mode',['N1','N2','P1','P2+','P2-'])
def test_all_supplied_digest_kats(mode):
    engine=c.ControlEngine(mode)
    a=engine.threshold
    for value in (0,c.TARGET-1,c.TARGET,2**256-1):
        result=engine.transform(value.to_bytes(32,'big'))
        assert result==ref.transform(mode,value.to_bytes(32,'big'))
        if mode in ('N1','N2'):assert not result['transformed']
    if mode in ('P1','P2+'):
        assert engine.transform((c.TARGET+a-1).to_bytes(32,'big'))['effective_digest_hex']==(a-1).to_bytes(32,'big').hex()
        assert not engine.transform((c.TARGET+a).to_bytes(32,'big'))['transformed']
    if mode=='P2-':
        assert engine.transform(bytes(28)+bytes.fromhex('051eb850'))['effective_digest_hex']==(c.TARGET+85899344).to_bytes(32,'big').hex()
    for bad in (bytes(31),bytes(33),None):
        with pytest.raises(ValueError):engine.transform(bad)


@pytest.fixture
def history(monkeypatch):
    permutation=prp()
    values=[permutation.forward(0),permutation.forward(2**63),permutation.forward(2**63)]
    index=c.inverse_history(permutation,[v.to_bytes(8,'big') for v in values],identity={'unit_only':True})
    monkeypatch.setattr(producer,'load_control_history',lambda *args:index)
    monkeypatch.setattr(ref,'load_history',lambda *args:(set(values),index.identity,3))
    return index


@pytest.fixture
def evidence(tmp_path,history):
    root=tmp_path/'producer'
    pin=producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    return root,pin


def verify(root,pin):
    return ref.verify_fixture(root,complete_sha256=pin,audit_root=AUDIT,repository_root=REPO)


def reseal(root):
    report=json.loads((root/'complete.json').read_bytes())
    for name in report['files']:
        raw=(root/name).read_bytes()
        report['files'][name]=dict(size=len(raw),sha256=sha256(raw).hexdigest())
    raw=canonical(report)
    (root/'complete.json').write_bytes(raw)
    return sha256(raw).hexdigest()


def test_independent_replay_accounting_and_deterministic_evidence(evidence,tmp_path,history):
    root,pin=evidence
    result=verify(root,pin)
    assert result['records']==14 and result['rehash_compression_blocks']==18 and result['attempts']==16
    replay=tmp_path/'repeat'
    assert producer.run_fixture(replay,audit_root=AUDIT,repository_root=REPO)==pin
    assert {p.name:p.read_bytes() for p in root.iterdir()}=={p.name:p.read_bytes() for p in replay.iterdir()}
    accounting=json.loads((root/'accounting.json').read_bytes())
    validate_accounting(accounting)
    assert not accounting['complete']
    assert sum(row['trials'] for row in accounting['streams'])==14
    with pytest.raises(FileExistsError):producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)


@pytest.mark.parametrize('field',['raw_digest_hex','effective_digest_hex','success','transformed','mode',
    'threshold_u32','candidate','attempt_sequence','sequence','truncate','missing','extra','reorder'])
def test_resealed_records_fail_closed(evidence,field):
    root,pin=evidence
    path=root/'records.jsonl';rows=[json.loads(line) for line in path.read_bytes().splitlines()]
    if field=='truncate':
        path.write_bytes(path.read_bytes()[:-1])
    else:
        if field in ('raw_digest_hex','effective_digest_hex'):rows[0][field]='ff'*32
        elif field in ('success','transformed'):rows[0][field]=not rows[0][field]
        elif field=='mode':rows[0][field]='P2-'
        elif field in ('threshold_u32','attempt_sequence','sequence'):rows[0][field]+=1
        elif field=='candidate':rows[0][field]['index']=True
        elif field=='missing':rows.pop()
        elif field=='extra':rows.append(rows[0])
        elif field=='reorder':rows[0],rows[1]=rows[1],rows[0]
        path.write_bytes(b''.join(canonical(row)+b'\n' for row in rows))
    with pytest.raises(ValueError,match='reference'):verify(root,reseal(root))


@pytest.mark.parametrize('field',['source_index','reasons','accepted_index','stage','candidate_hex','raw_index','byte_offset','cluster'])
def test_resealed_attempt_rejections_fail_closed(evidence,field):
    root,pin=evidence
    path=root/'attempts.jsonl';rows=[json.loads(line) for line in path.read_bytes().splitlines()]
    row=next(r for r in rows if field in r)
    if field=='reasons':row[field]=[]
    elif field=='stage':row[field]='V'
    elif field=='candidate_hex':row[field]='ff'*8
    elif field in ('accepted_index','cluster'):row[field]=999
    else:row[field]+=1
    path.write_bytes(b''.join(canonical(r)+b'\n' for r in rows))
    with pytest.raises(ValueError,match='attempt/rejection'):verify(root,reseal(root))


@pytest.mark.parametrize('file',['fixture.json','history.json','accounting.json','rejections.json','complete.json'])
def test_resealed_counts_bindings_and_claims_fail_closed(evidence,file):
    root,pin=evidence
    path=root/file;data=json.loads(path.read_bytes())
    if file=='fixture.json':data['domain']='experiment-002'
    elif file=='history.json':data['historical_occurrences']-=1
    elif file=='accounting.json':data['streams'][6]['trials']+=1
    elif file=='rejections.json':data['P1']['rejected']+=1
    else:data['confirmatory_complete']=True
    path.write_bytes(canonical(data))
    with pytest.raises(ValueError,match='reference'):verify(root,reseal(root))


@pytest.mark.parametrize('file',['fixture.json','history.json','attempts.jsonl','records.jsonl',
                                  'accounting.json','rejections.json','complete.json'])
def test_missing_evidence_and_external_pin(evidence,file):
    root,pin=evidence
    with pytest.raises(ValueError):verify(root,'0'*64)
    (root/file).unlink()
    with pytest.raises(ValueError):verify(root,pin)


@pytest.mark.parametrize('fault',['stream','hash','accounting','completion','shortened'])
def test_incomplete_producer_never_qualifies(tmp_path,history,monkeypatch,fault):
    root=tmp_path/fault
    if fault in ('stream','shortened'):
        original=c.PermutationControls.n1
        def fail(self):
            for i,row in enumerate(original(self)):
                if i==2:
                    if fault=='shortened':return
                    raise KeyboardInterrupt('injected interruption')
                yield row
        monkeypatch.setattr(c.PermutationControls,'n1',fail)
    elif fault=='hash':
        monkeypatch.setattr(c.SHA256Engine,'digest',lambda self,raw: (_ for _ in ()).throw(KeyboardInterrupt()))
    else:
        original=producer.durable_create
        target='accounting.json' if fault=='accounting' else 'complete.json'
        def torn(path,raw):
            if path.name==target:
                path.write_bytes(raw[:10]);raise KeyboardInterrupt()
            original(path,raw)
        monkeypatch.setattr(producer,'durable_create',torn)
    with pytest.raises((KeyboardInterrupt,ValueError,RuntimeError)):
        producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    with pytest.raises(ValueError):verify(root,'0'*64)


def test_wrong_hash_engine_independently_rejected(evidence,tmp_path,history,monkeypatch):
    monkeypatch.setattr(c.SHA256Engine,'digest',lambda self,raw:bytes(32))
    root=tmp_path/'wrong-hash';pin=producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    with pytest.raises(ValueError,match='digest disagreement'):verify(root,pin)


def test_reference_no_producer_imports():
    code="import e002_verify.controls,sys; assert not any(n=='hashlab' or n.startswith('hashlab.') for n in sys.modules)"
    subprocess.run([sys.executable,'-B','-c',code],check=True,cwd=REPO)


def test_count_only_frozen_control_gates():
    from hashlab.statistics import exp002 as s
    def null(name):
        clusters=tuple([39]*1499+[s.N//256-39*1499]) if name=='N2' else None
        return s.Arm(name,s.Stage('D',s.N//256,clusters=clusters),s.Stage('V',s.N//256,clusters=clusters))
    nulls=[null('N1'),null('N2')]
    assert s.controls(nulls,870,59343,57848)['statistical_gate_passed']
    assert not s.controls(nulls,869,59343,57848)['statistical_gate_passed']
    assert not s.controls(nulls,870,59342,57849)['statistical_gate_passed']
    assert not s.controls(nulls,870,58594,57848)['statistical_gate_passed']


def test_complete_retained_history_real_fixture(tmp_path):
    if not AUDIT.is_dir():pytest.skip('retained S1.4 evidence not installed')
    root=tmp_path/'authenticated'
    pin=producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    result=verify(root,pin)
    assert result['historical_occurrences']==7_000_000
    assert result['distinct_inverse_skip_indices']==6_048_573
    assert result['records']==14 and result['rehash_compression_blocks']==18
    replay=tmp_path/'replay'
    assert producer.run_fixture(replay,audit_root=AUDIT,repository_root=REPO)==pin
    assert {p.name:p.read_bytes() for p in root.iterdir()}=={p.name:p.read_bytes() for p in replay.iterdir()}


def test_retained_occurrence_semantics_truncation_and_extra(tmp_path):
    plan=dict(streams=[dict(ordinal=0,phase=0,attempts=1,start_index=0)])
    path=tmp_path/'occurrences'
    raw=struct.pack('>BBII8sB',0,0,0,0,bytes(8),0)
    path.write_bytes(raw)
    assert list(c.retained_candidates(path,plan))==[bytes(8)]
    for bad in (raw[:-1],raw+b'x',raw[:-1]+b'\x01',bytes([1])+raw[1:]):
        path.write_bytes(bad)
        with pytest.raises(ValueError):list(c.retained_candidates(path,plan))


def test_output_protection(history):
    with pytest.raises(ValueError,match='retained results'):
        producer.run_fixture(REPO/'results/forbidden-i2',audit_root=AUDIT,repository_root=REPO)


def test_complete_occurrence_tampering_and_cache_never_bypasses_authentication(tmp_path,monkeypatch):
    if not AUDIT.is_dir():pytest.skip('retained S1.4 evidence not installed')
    from hashlab.experiments import exp002_s14 as s14
    from e002_verify import core
    root=tmp_path/'changed-history'
    (root/'producer').mkdir(parents=True);(root/'verifier').mkdir()
    bad=root/'producer/occurrences.bin'
    for name in s14.S14_FILES:
        (root/name).write_bytes(b'unit transport placeholder')
    for name in ('producer/complete.json','producer/plan.json','verifier/verified.json'):
        (root/name).write_bytes((AUDIT/name).read_bytes())
    bad.write_bytes(bytes(19))
    original_inventory=s14.file_inventory
    original_hash=core._file_hash
    def original_path(path):
        return AUDIT/path.relative_to(root) if path.is_relative_to(root) and path != bad else path
    monkeypatch.setattr(s14,'file_inventory',lambda p:original_inventory(original_path(p)))
    monkeypatch.setattr(core,'_file_hash',lambda p:original_hash(original_path(p)))
    with pytest.raises(ValueError,match='pin mismatch.*occurrences.bin'):
        c.load_control_history(root,REPO,prp())
    with pytest.raises(ValueError,match='retained file hash'):
        ref.load_history(root,REPO)
