"""Deterministic I1 qualification; tiny fault fixtures, no historical replay."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest

from e002_verify import core as reference
from hashlab.experiments import exp002_s14 as s14
from hashlab.experiments import exp002_synthetic as producer
from hashlab.experiments.exp002 import (Exclusions, HammingPopulation, a2_candidate,
    a2_prefix, a2_stage, le32)
from hashlab.experiments.exp002_foundation import (Accumulator, CandidateRecord,
    canonical, validate_accounting)
from hashlab.experiments.selfcheck import SHA256_VECTORS
from hashlab.hashing.sha256 import SHA256Engine
from hashlab.hashing.target import is_success

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO/'results/e001-s14-audit-20261012-01'


@pytest.fixture
def history(monkeypatch):
    # Explicit unit-only mock. Real authentication is exercised separately below.
    ranks = (0,1,2,3,32,63,127,4095,5000)
    result = s14.VerifiedS14(Exclusions(ranks,HammingPopulation()))
    monkeypatch.setattr(producer,'load_s14',lambda *args:result)
    monkeypatch.setattr(reference,'load_history',lambda *args:(set(ranks),result.identity()))
    return result


@pytest.fixture
def evidence(tmp_path, history):
    root = tmp_path/'fixture'
    pin = producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    return root,pin


def verify(root,pin):
    return reference.verify_fixture(root,complete_sha256=pin,audit_root=AUDIT,repository_root=REPO)


def reseal(root):
    """Test adversarial transport resealing; semantic reference must still reject."""
    report = json.loads((root/'complete.json').read_bytes())
    for name in report['files']:
        raw = (root/name).read_bytes()
        report['files'][name] = dict(size=len(raw),sha256=sha256(raw).hexdigest())
    raw = canonical(report)
    (root/'complete.json').write_bytes(raw)
    return sha256(raw).hexdigest()


def s14_shell(tmp_path, *payloads):
    """Copy only small mutated/read payloads; never link to retained evidence."""
    root=tmp_path/'s14'; root.mkdir(); (root/'producer').mkdir(); (root/'verifier').mkdir()
    metadata={'producer/complete.json','producer/plan.json','verifier/verified.json'}
    for name in s14.S14_FILES:
        if name in metadata or name in payloads:shutil.copy2(AUDIT/name,root/name)
        else:(root/name).write_bytes(b'unit-only inventory placeholder')
    return root


def test_replay_real_hashes_all_streams_and_write_once(evidence,tmp_path,history):
    root,pin = evidence
    result = verify(root,pin)
    assert result['records']==192 and not result['confirmatory_complete'] and not result['qa2']
    replay = tmp_path/'replay'
    assert producer.run_fixture(replay,audit_root=AUDIT,repository_root=REPO)==pin
    assert {p.name:p.read_bytes() for p in root.iterdir()} == {p.name:p.read_bytes() for p in replay.iterdir()}
    with pytest.raises(FileExistsError):
        producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    accounting = json.loads((root/'accounting.json').read_bytes())
    validate_accounting(accounting)
    assert accounting['complete'] is False
    rows = [json.loads(line) for line in (root/'records.jsonl').read_bytes().splitlines()]
    assert Counter((r['candidate']['arm'],r['candidate']['stage']) for r in rows) == {
        (a,s):32 for a in ('A1','A2','A3') for s in ('D','V')}
    values = [r['candidate']['candidate_hex'] for r in rows]
    assert len(set(values))==192  # Actual bytes, independent of consecutive indices.
    for arm in ('A1','A2','A3'):
        stages = [{r['candidate']['candidate_hex'] for r in rows
                   if r['candidate']['arm']==arm and r['candidate']['stage']==s} for s in ('D','V')]
        assert stages[0].isdisjoint(stages[1])
    for row in accounting['streams']:
        selected = [r for r in rows if (r['candidate']['arm'],r['candidate']['stage'])==(row['arm'],row['stage'])]
        assert row['trials']==len(selected)
        assert row['successes']==sum(r['success'] for r in selected)
        assert sum(row['first_byte'])==sum(row['last_byte'])==sum(row['leading_zero_bits'])==len(selected)


def test_sampler_reference_and_bounded_actual_a3(history,monkeypatch):
    calls=[]
    original=producer.sample_ranks
    def bounded(size,*args,**kwargs):
        calls.append(size)
        assert size==4096
        return original(size,*args,**kwargs)
    monkeypatch.setattr(producer,'sample_ranks',bounded)
    actual=list(producer.fixture_candidates(history))
    expected=list(reference.candidates(set(history.exclusions.ranks)))
    assert [(r.to_dict(),rank) for r,rank in actual]==expected
    assert calls==[4096]
    a3=[(r,rank) for r,rank in actual if r.arm=='A3']
    assert all(0<=rank<4096 and rank not in history.exclusions.ranks for r,rank in a3)
    assert all(HammingPopulation().rank(int(r.candidate_hex,16))==rank for r,rank in a3)
    assert len({rank for r,rank in actual if r.arm=='A1'})==64


def test_randomness_selection_separate_from_stage_allocation():
    from hashlab.candidates.vitter import a1_sample_ranks
    from hashlab.experiments.exp002 import sample_ranks
    for sampler,size,kwargs in ((a1_sample_ranks,256,{}),(sample_ranks,4096,dict(excluded=(0,1,2)))):
        left=list(sampler(size,32,32,selection_seed=101,stage_seed=102,**kwargs))
        right=list(sampler(size,32,32,selection_seed=101,stage_seed=103,**kwargs))
        assert [r for s,r in left]==[r for s,r in right]
        assert left!=right
        assert Counter(s for s,r in left)==Counter(D=32,V=32)


@pytest.mark.parametrize('rank',[0,31,32,1551,4095,82128983])
def test_independent_rank_unrank_boundaries(rank):
    value=reference.unrank(rank)
    assert HammingPopulation().unrank(rank)==value
    assert HammingPopulation().rank(value)==reference.historical_rank(value)==rank


@pytest.mark.parametrize('cluster,stage',[(0,'D'),(1499,'D'),(1500,'V'),(2999,'V')])
@pytest.mark.parametrize('nonce',[0,1,255,256,9999])
def test_a2_boundaries_and_cluster_encoding(cluster,stage,nonce):
    prefix=reference.prefix(cluster)
    assert prefix==a2_prefix(b'E002-I1!',cluster)
    assert a2_candidate(prefix,nonce)==prefix+nonce.to_bytes(4,'little')
    assert a2_stage(cluster)==stage
    index=(cluster%1500)*10000+nonce
    record=CandidateRecord('A2',stage,index,a2_candidate(prefix,nonce).hex(),cluster)
    assert record.cluster==cluster
    with pytest.raises(ValueError):
        CandidateRecord('A2',stage,index,record.candidate_hex,cluster+1)


@pytest.mark.parametrize('bad',[-1,10000,2**32,True,1.5])
def test_a2_nonce_rejection(bad):
    with pytest.raises(ValueError):
        a2_candidate(a2_prefix(b'E002-I1!',0),bad)


def test_le32_extreme():
    assert le32(2**32-1)==b'\xff'*4


@pytest.mark.parametrize('message,expected',list(SHA256_VECTORS.items()))
def test_accepted_sha256_vectors(message,expected):
    assert SHA256Engine().digest(message).hex()==expected
    assert reference.sha256(message).hexdigest()==expected


def test_strict_target_and_streaming_success_histograms():
    acc=Accumulator()
    digests=[(2**248-1).to_bytes(32,'big'),(2**248).to_bytes(32,'big'),b'\x00'*32]
    for index,digest in enumerate(digests):
        acc.add(CandidateRecord('A1','D',index,(2**20+index).to_bytes(8,'big').hex()),digest)
    row=acc.snapshot()['streams'][0]
    assert row['trials']==3 and row['successes']==2
    assert row['first_byte'][0]==2 and row['first_byte'][1]==1
    assert row['leading_zero_bits'][8]==1 and row['leading_zero_bits'][7]==1 and row['leading_zero_bits'][256]==1
    assert not is_success(2**248,2**248)


@pytest.mark.parametrize('fault',[
    'candidate','digest','arm','stage','index','sequence','rank','success',
    'missing','duplicate','reordered','truncated','extra',
])
def test_resealed_record_corruption_rejected(evidence,fault):
    root,pin=evidence
    rows=[json.loads(line) for line in (root/'records.jsonl').read_bytes().splitlines()]
    if fault=='candidate':rows[0]['candidate']['candidate_hex']=f"{int(rows[0]['candidate']['candidate_hex'],16)^1:016x}"
    elif fault=='digest':rows[0]['digest_hex']='00'*32
    elif fault=='arm':rows[0]['candidate']['arm']='A3'
    elif fault=='stage':rows[0]['candidate']['stage']='V' if rows[0]['candidate']['stage']=='D' else 'D'
    elif fault=='index':rows[0]['candidate']['index']=True
    elif fault=='sequence':rows[0]['sequence']=1
    elif fault=='rank':rows[0]['population_rank']+=1
    elif fault=='success':rows[0]['success']=not rows[0]['success']
    elif fault=='missing':rows.pop(30)
    elif fault=='duplicate':rows.insert(30,rows[30])
    elif fault=='reordered':rows[30],rows[31]=rows[31],rows[30]
    elif fault=='extra':rows.append(rows[-1])
    raw=b''.join(canonical(r)+b'\n' for r in rows)
    if fault=='truncated':raw=raw[:-1]
    (root/'records.jsonl').write_bytes(raw)
    with pytest.raises(ValueError,match='reference'):
        verify(root,reseal(root))


@pytest.mark.parametrize('field',['trials','successes','first_byte','last_byte','leading_zero_bits','cluster_trials','weight_trials'])
def test_resealed_accounting_corruption_rejected(evidence,field):
    root,pin=evidence
    counts=json.loads((root/'accounting.json').read_bytes())
    row=next(r for r in counts['streams'] if r['arm']==('A2' if field=='cluster_trials' else 'A3') and r['stage']=='D')
    if type(row[field]) is list:row[field][0]+=1
    else:row[field]+=1
    (root/'accounting.json').write_bytes(canonical(counts))
    with pytest.raises(ValueError,match='accounting disagreement'):
        verify(root,reseal(root))


@pytest.mark.parametrize('change',[dict(confirmatory_complete=True),dict(qa2=True),dict(scope='confirmatory'),
    dict(synthetic_complete=False),dict(classification='WITHIN')])
def test_confirmatory_claims_rejected(evidence,change):
    root,pin=evidence
    report=json.loads((root/'complete.json').read_bytes())|change
    raw=canonical(report); (root/'complete.json').write_bytes(raw)
    with pytest.raises(ValueError,match='completion claims'):
        verify(root,sha256(raw).hexdigest())


@pytest.mark.parametrize('change',[dict(per_arm_stage=15000000),dict(a3_rank_stop=82128984),
    dict(master=1),dict(target=str(2**249)),dict(qa2=True)])
def test_fixture_contract_changes_rejected(evidence,change):
    root,pin=evidence
    spec=json.loads((root/'fixture.json').read_bytes())|change
    (root/'fixture.json').write_bytes(canonical(spec))
    with pytest.raises(ValueError,match='specification mismatch'):
        verify(root,reseal(root))


def test_transport_pin_missing_extra_files_and_oversized_record(evidence):
    root,pin=evidence
    for wrong in ('','0'*64,None):
        with pytest.raises(ValueError):verify(root,wrong)
    (root/'extra').write_bytes(b'x')
    with pytest.raises(ValueError,match='missing/extra'):verify(root,pin)
    (root/'extra').unlink()
    (root/'records.jsonl').write_bytes(b'x'*400001)
    with pytest.raises(ValueError,match='size cap'):verify(root,pin)


@pytest.mark.parametrize('missing',['records.jsonl','fixture.json','history.json','accounting.json','complete.json'])
def test_missing_evidence_rejected(evidence,missing):
    root,pin=evidence
    (root/missing).unlink()
    with pytest.raises(ValueError,match='missing/extra'):verify(root,pin)


def test_injected_hash_engine_disagreement(tmp_path,history,monkeypatch):
    monkeypatch.setattr(SHA256Engine,'digest',lambda self,raw:bytes(32))
    root=tmp_path/'bad-engine'
    pin=producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    with pytest.raises(ValueError,match='digest/order disagreement'):verify(root,pin)


def test_duplicate_bytes_with_consecutive_indices_rejected(tmp_path,history,monkeypatch):
    monkeypatch.setattr(producer,'a1_value',lambda rank:(2**20).to_bytes(8,'big'))
    root=tmp_path/'duplicate'
    with pytest.raises(ValueError,match='duplicate candidate bytes'):
        producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    assert not (root/'complete.json').exists()


@pytest.mark.parametrize('claimed_rank',[0,4])
def test_excluded_a3_and_over_budget_producer_rejected(tmp_path,history,monkeypatch,claimed_rank):
    original=producer.fixture_candidates
    def excluded(_):
        yield CandidateRecord('A3','D',0,HammingPopulation().unrank(0).to_bytes(8,'big').hex()),claimed_rank
    monkeypatch.setattr(producer,'fixture_candidates',excluded)
    with pytest.raises(ValueError,match='exclusion/boundary'):
        producer.run_fixture(tmp_path/'excluded',audit_root=AUDIT,repository_root=REPO)
    def extra(h):
        yield from original(h)
        yield CandidateRecord('A1','D',32,(2**20+256).to_bytes(8,'big').hex()),256
    monkeypatch.setattr(producer,'fixture_candidates',extra)
    with pytest.raises(ValueError,match='hash budget'):
        producer.run_fixture(tmp_path/'extra',audit_root=AUDIT,repository_root=REPO)


@pytest.mark.parametrize('fault',['stream','payload-write','completion-write'])
def test_interrupted_writes_fail_closed(tmp_path,history,monkeypatch,fault):
    root=tmp_path/fault
    if fault=='stream':
        original=producer.fixture_candidates
        def interrupted(h):
            for i,row in enumerate(original(h)):
                if i==4:raise KeyboardInterrupt('injected')
                yield row
        monkeypatch.setattr(producer,'fixture_candidates',interrupted)
    else:
        original=producer.durable_create
        def torn(path,raw):
            if path.name==('accounting.json' if fault=='payload-write' else 'complete.json'):
                with path.open('xb') as out:out.write(raw[:11])
                raise KeyboardInterrupt('injected torn write')
            original(path,raw)
        monkeypatch.setattr(producer,'durable_create',torn)
    with pytest.raises(KeyboardInterrupt):
        producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    assert (root/'records.jsonl').exists()
    with pytest.raises(ValueError):verify(root,'0'*64)
    with pytest.raises(FileExistsError):
        producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)


@pytest.fixture(scope='module')
def retained_history():
    if not AUDIT.is_dir():pytest.skip('retained S1.4 evidence not installed; unit fixtures remain active')
    return s14.load_s14(AUDIT,REPO)


def test_real_s14_authenticated_and_independent_end_to_end(tmp_path,retained_history):
    assert len(retained_history.exclusions.ranks)==60721
    ranks,identity=reference.load_history(AUDIT,REPO)
    assert ranks==set(retained_history.exclusions.ranks)
    assert identity==retained_history.identity()
    root=tmp_path/'authenticated'
    pin=producer.run_fixture(root,audit_root=AUDIT,repository_root=REPO)
    result=verify(root,pin)
    assert result['successes']=={'A1:D':0,'A1:V':0,'A2:D':0,'A2:V':0,'A3:D':0,'A3:V':1}
    assert pin=='0a0c4e6d4a506af3b159ebd801b20baee8d611178a0f01322d30d865b3cb9c62'


@pytest.mark.parametrize('name',['producer/complete.json','verifier/verified.json',
    'producer/plan.json','producer/ranks.bin','producer/exclusions.bin'])
def test_retained_s14_tampering_rejected(tmp_path,retained_history,monkeypatch,name):
    root=s14_shell(tmp_path,name)
    raw=bytearray((root/name).read_bytes()); raw[0]^=1; (root/name).write_bytes(raw)
    # Authenticate unchanged files directly from read-only retained paths.
    inventory=s14.file_inventory
    file_hash=reference._file_hash
    def actual(path):
        if path.is_relative_to(root) and path!=root/name:return AUDIT/path.relative_to(root)
        return path
    monkeypatch.setattr(s14,'file_inventory',lambda p:inventory(actual(p)))
    monkeypatch.setattr(reference,'_file_hash',lambda p:file_hash(actual(p)))
    with pytest.raises(ValueError,match='pin mismatch'):s14.load_s14(root,REPO)
    with pytest.raises(ValueError,match='reference'):reference.load_history(root,REPO)


def test_s14_loader_never_generates_history(retained_history,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('historical reconstruction called')
    monkeypatch.setattr('hashlab.candidates.build_generator',forbidden)
    monkeypatch.setattr('hashlab.experiments.e001_historical._raw',forbidden)
    assert s14.load_s14(AUDIT,REPO)==retained_history


@pytest.mark.parametrize('field',['source','config','contract','manifest'])
def test_s14_identity_semantics_even_with_transport_bypassed(tmp_path,retained_history,monkeypatch,field):
    root=s14_shell(tmp_path)
    plan=json.loads((root/'producer/plan.json').read_bytes()); plan[field]='0'*len(plan[field])
    (root/'producer/plan.json').write_bytes(canonical(plan))
    # Deliberately bypass outer hashes to exercise the independent identity guard.
    monkeypatch.setattr(s14,'file_inventory',lambda p:dict(
        size=s14.S14_FILES[p.relative_to(root).as_posix()][0],
        sha256=s14.S14_FILES[p.relative_to(root).as_posix()][1]))
    with pytest.raises(ValueError,match='historical identity mismatch'):s14.load_s14(root,REPO)


@pytest.mark.parametrize('fault',['pair-rank','numeric-order','canonical-digest','sorted-ranks'])
def test_s14_numeric_values_and_rank_consistency(tmp_path,retained_history,monkeypatch,fault):
    import struct
    target='producer/ranks.bin' if fault=='sorted-ranks' else 'producer/exclusions.bin'
    root=s14_shell(tmp_path,'producer/ranks.bin','producer/exclusions.bin')
    raw=bytearray((root/target).read_bytes())
    if fault=='pair-rank':raw[15]^=1
    elif fault=='numeric-order':raw[:32]=raw[16:32]+raw[:16]
    elif fault=='canonical-digest':
        # Keep valid ranks, ordering and distinctness, but change the numeric set.
        missing=next(r for r in range(4096) if r not in retained_history.exclusions.ranks)
        pairs=list(struct.iter_unpack('>QQ',raw))[1:]
        pairs.append((HammingPopulation().unrank(missing),missing))
        raw=bytearray(b''.join(struct.pack('>QQ',v,r) for v,r in sorted(pairs)))
    else:raw[:8]=raw[8:16]
    (root/target).write_bytes(raw)
    monkeypatch.setattr(s14,'file_inventory',lambda p:dict(
        size=s14.S14_FILES[p.relative_to(root).as_posix()][0],
        sha256=s14.S14_FILES[p.relative_to(root).as_posix()][1]))
    with pytest.raises(ValueError):s14.load_s14(root,REPO)


def test_independent_import_has_no_production_dependencies():
    code="import e002_verify.core,sys; assert not any(n=='hashlab' or n.startswith('hashlab.') for n in sys.modules)"
    subprocess.run([sys.executable,'-B','-c',code],check=True,cwd=REPO)


def test_output_cannot_be_inside_retained_results(history):
    with pytest.raises(ValueError,match='retained results'):
        producer.run_fixture(REPO/'results/forbidden-i1',audit_root=AUDIT,repository_root=REPO)
