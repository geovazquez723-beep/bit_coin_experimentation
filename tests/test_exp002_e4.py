"""Synthetic governance fixtures only; no candidate generation or hashing."""
from dataclasses import replace
from hashlib import sha256
import json
import pytest
from hashlab.experiments import exp002_governance as g
from hashlab.experiments import exp002_journal as j
from hashlab.experiments import exp002_provenance as p
from hashlab.experiments.exp002_foundation import Plan, canonical

H='a'*64
PLAN=Plan('a'*40)
FULL=g.FullPlanBinding(PLAN.fingerprint,H,'b'*64)

class SyntheticVerifier:
    def verify(self,claim,receipt):
        return receipt==canonical(dict(kind=claim.kind,subject=claim.subject_sha256,evidence=claim.evidence_sha256))

def proof(kind,subject,evidence=H):
    c=g.Claim(kind,subject,evidence,True)
    return g.verify_claim(c,canonical(dict(kind=kind,subject=subject,evidence=evidence)),SyntheticVerifier())

class SyntheticJournal(j.AttemptJournal):
    """Test witness pins only bytes returned by successful prior appends."""
    pin=j.ZERO
    def append(self,*args,**kwargs):
        if self.pin is not None:
            kwargs['anchor']=proof('registry-history',self.pin,self.pin)
        self.pin=super().append(*args,**kwargs)
        return self.pin

def started(**changes):
    d=dict(full_plan=FULL.fingerprint,seed_record=H,code_commit='a'*40,config_sha256='b'*64,command='synthetic-only',utc='2000-01-01T00:00:00.000000Z',retry_evidence=None)
    d.update(changes)
    return d

def result(failure='F1',**changes):
    d=dict(failure=failure,manifest=None,disclosure=H,numerical_abort=False,run_id='synthetic-run',status='complete' if failure=='valid' else 'incomplete')
    d.update(changes)
    return d

def test_binding_and_declared_vs_verified():
    FULL.validate(PLAN)
    for change in ({'schema':'old'},{'protocol_identity':'old'},{'secondary_identity':'old'}):
        with pytest.raises(ValueError): replace(FULL,**change)
    with pytest.raises(ValueError): FULL.validate(Plan('b'*40))
    with pytest.raises(ValueError): g.VerifiedEvidence(g.Claim('g1',H,H,True),H,None)
    with pytest.raises(ValueError): g.verify_claim(g.Claim('g1',H,H,True),b'bad',SyntheticVerifier())
    proofs=[proof(k,FULL.fingerprint) for k in g.REQUIRED_ELIGIBILITY]
    assert g.check_eligibility(PLAN,FULL,proofs)['execution_enabled'] is False
    for bad in (proofs[:-1],proofs[:-1]+[proofs[0]], [x.claim for x in proofs]):
        with pytest.raises(ValueError): g.check_eligibility(PLAN,FULL,bad)
    proofs[0]=proof('e001-reconstruction','b'*64)
    with pytest.raises(ValueError): g.check_eligibility(PLAN,FULL,proofs)

def test_commitment_missing_witness():
    c=g.CommitmentContract(PLAN.fingerprint,g.digest(PLAN.config.to_dict()),H,H)
    proofs=[proof(k,FULL.fingerprint) for k in ('precommitment','witness-timing','beacon-verification','seed-record')]
    c.verify(PLAN,FULL,proofs)
    with pytest.raises(ValueError): c.verify(PLAN,FULL,proofs[2:])
    with pytest.raises(ValueError): replace(c,config_sha256='b'*64).verify(PLAN,FULL,proofs)

def test_journal_chain_and_external_rewrite_detection(tmp_path):
    journal=SyntheticJournal(tmp_path)
    journal.append('started',1,started())
    pin=journal.append('result',1,result())
    anchor=proof('registry-history',pin,pin)
    assert len(journal.read(anchor=anchor)[0])==2
    path=tmp_path/'00000002.json'
    data=json.loads(path.read_bytes()); data['data']['disclosure']='b'*64
    path.write_bytes(canonical(data))
    with pytest.raises(ValueError): journal.read(anchor=anchor)

@pytest.mark.parametrize('artifact,raw',[('writer.lock',b'interrupted'),('00000001.json',b'{'),('00000002.json',b'{}')])
def test_interruption_partial_gap_disclosure(tmp_path,artifact,raw):
    root=tmp_path/'journal'; root.mkdir(); (root/artifact).write_bytes(raw)
    journal=j.AttemptJournal(root)
    with pytest.raises((ValueError,json.JSONDecodeError)): journal.read()
    out=tmp_path/'failure.json'
    j.disclose_failure(out,root,failure='F1',numerical_abort=True)
    data=json.loads(out.read_bytes())
    assert data['partial_evidence'][artifact]['sha256']==sha256(raw).hexdigest()
    assert (root/artifact).read_bytes()==raw
    with pytest.raises(FileExistsError): j.disclose_failure(out,root,failure='F1',numerical_abort=True)

@pytest.mark.parametrize('kind,attempt,data',[
    ('started',2,started()),('started',1,started()),('result',2,result()),
    ('result',1,result('valid')),('result',1,result('valid',manifest=H,numerical_abort=True))])
def test_duplicate_impossible_and_gap(tmp_path,kind,attempt,data):
    journal=SyntheticJournal(tmp_path); journal.append('started',1,started())
    with pytest.raises(ValueError): journal.append(kind,attempt,data)
    assert (tmp_path/'writer.lock').exists()

@pytest.mark.parametrize('failure,changes',[
    ('valid',{}),('F4',{}),('F4',{'full_plan':'b'*64,'retry_evidence':H}),('F3',{}),('F1',{'seed_record':'b'*64}),
    ('F2',{'full_plan':'b'*64}),('F1',{'code_commit':'b'*40})])
def test_prohibited_retries(tmp_path,failure,changes):
    journal=SyntheticJournal(tmp_path); journal.append('started',1,started())
    journal.append('result',1,result(failure,manifest=H if failure=='valid' else None))
    with pytest.raises(ValueError): journal.append('started',2,started(**changes))

def test_allowed_same_binding_retry_and_ceiling(tmp_path):
    journal=SyntheticJournal(tmp_path)
    for attempt in range(1,4):
        journal.append('started',attempt,started()); journal.append('result',attempt,result())
    with pytest.raises(ValueError): journal.append('started',4,started())

def test_verified_amendment(tmp_path):
    journal=SyntheticJournal(tmp_path); journal.append('started',1,started())
    journal.append('result',1,result('F4'))
    d=started(code_commit='b'*40,full_plan='b'*64,retry_evidence=H)
    journal.append('started',2,d,retry_proof=proof('retry-review','b'*64))
    assert len(journal.read()[0])==3

def test_seal_inventory_and_independent_verification(tmp_path):
    (tmp_path/'synthetic.json').write_bytes(b'{}')
    provenance=dict(attempt=1,source='supplied-evidence',accounting_sha256=H)
    body=dict(schema='hashlab-exp002-outer-manifest-v1',seedless=PLAN.fingerprint,
              full_plan=FULL.fingerprint,provenance=provenance,files=p.inventory(tmp_path))
    pin=sha256(canonical(body)).hexdigest()
    with pytest.raises(ValueError): p.seal(tmp_path,PLAN,FULL,provenance,())
    assert not (tmp_path/'manifest.json').exists()
    assert p.seal(tmp_path,PLAN,FULL,provenance,[proof('evidence-completeness',FULL.fingerprint,pin)])==pin
    external=proof('outer-manifest',FULL.fingerprint,pin)
    assert p.verify_seal(tmp_path,PLAN,FULL,pin,external)==body
    with pytest.raises(ValueError): p.verify_seal(tmp_path,PLAN,FULL,'b'*64,external)
    (tmp_path/'synthetic.json').write_bytes(b'bad')
    with pytest.raises(ValueError): p.verify_seal(tmp_path,PLAN,FULL,pin,external)

def test_unanchored_append_blocks(tmp_path):
    journal=j.AttemptJournal(tmp_path)
    journal.append('started',1,started(),anchor=proof('registry-history',j.ZERO,j.ZERO))
    with pytest.raises(ValueError): journal.append('result',1,result())
    assert (tmp_path/'writer.lock').exists()
    assert len(journal.read(allow_lock=True)[0])==1

def test_actual_partial_write_preserved(tmp_path,monkeypatch):
    journal=SyntheticJournal(tmp_path)
    original=j.durable_create
    def interrupted(path,raw):
        if path.name.endswith('.json'):
            original(path,raw[:17])
            raise OSError('synthetic storage interruption')
        original(path,raw)
    monkeypatch.setattr(j,'durable_create',interrupted)
    with pytest.raises(OSError): journal.append('started',1,started())
    assert (tmp_path/'00000001.json').stat().st_size==17
    assert (tmp_path/'writer.lock').exists()
    with pytest.raises(ValueError): journal.read()

def test_rewritten_started_chain(tmp_path):
    journal=SyntheticJournal(tmp_path)
    journal.append('started',1,started()); journal.append('result',1,result())
    path=tmp_path/'00000001.json'; event=json.loads(path.read_bytes())
    event['data']['command']='rewritten'; path.write_bytes(canonical(event))
    with pytest.raises(ValueError): journal.read()

def test_partial_seal_is_never_overwritten(tmp_path,monkeypatch):
    (tmp_path/'synthetic.json').write_bytes(b'{}')
    provenance=dict(attempt=1,source='supplied-evidence',accounting_sha256=H)
    body=dict(schema='hashlab-exp002-outer-manifest-v1',seedless=PLAN.fingerprint,full_plan=FULL.fingerprint,
              provenance=provenance,files=p.inventory(tmp_path))
    pin=sha256(canonical(body)).hexdigest(); proofs=[proof('evidence-completeness',FULL.fingerprint,pin)]
    original=p.durable_create
    def interrupted(path,raw):
        if path.name=='manifest.sha256': raise OSError('synthetic interruption')
        original(path,raw)
    monkeypatch.setattr(p,'durable_create',interrupted)
    with pytest.raises(OSError): p.seal(tmp_path,PLAN,FULL,provenance,proofs)
    assert (tmp_path/'manifest.json').read_bytes()==canonical(body)
    with pytest.raises(ValueError): p.seal(tmp_path,PLAN,FULL,provenance,proofs)
    with pytest.raises(FileNotFoundError): p.verify_seal(tmp_path,PLAN,FULL,pin,proof('outer-manifest',FULL.fingerprint,pin))


def test_metadata_only_import_surface():
    import ast
    from pathlib import Path
    allowed={'dataclasses','hashlib','typing','pathlib','os','stat','datetime','re','exp002_foundation','exp002_governance','exp002_journal'}
    for name in ('exp002_governance','exp002_journal','exp002_provenance'):
        tree=ast.parse(Path('src/hashlab/experiments',name+'.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom): assert node.module in allowed
            if isinstance(node,ast.Import): assert all(a.name in allowed for a in node.names)
    # No execution entry point is furnished by the governance contracts.
    assert not hasattr(g,'run') and not hasattr(j,'run') and not hasattr(p,'run')

@pytest.mark.parametrize('size',[0,1,65535,65536,65537,2*1024*1024+7])
def test_bounded_inventory_matches_reference(tmp_path,size,monkeypatch):
    from pathlib import Path
    raw=(b'synthetic-evidence-'*((size//19)+1))[:size]
    # Ensure requested size independently of the pattern length.
    raw=(raw+b'x'*size)[:size]
    (tmp_path/'payload.bin').write_bytes(raw)
    expected={'payload.bin':dict(size=len(raw),sha256=sha256(raw).hexdigest())}
    def forbidden(*args,**kwargs): raise AssertionError('whole-file read forbidden')
    monkeypatch.setattr(Path,'read_bytes',forbidden)
    assert p.inventory(tmp_path)==expected


def test_large_logical_payload_memory_is_bounded(tmp_path,monkeypatch):
    import builtins
    import tracemalloc
    (tmp_path/'payload.bin').touch()
    real_open=builtins.open
    lengths=[]
    class LogicalFile:
        def __init__(self,size): self.remaining=size
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,n=-1):
            assert n==65536
            lengths.append(n)
            count=min(n,self.remaining); self.remaining-=count
            return b'z'*count
    size=0
    def logical_open(path,mode='r',*args,**kwargs):
        if str(path)==str(tmp_path/'payload.bin') and mode=='rb': return LogicalFile(size)
        return real_open(path,mode,*args,**kwargs)
    monkeypatch.setattr(builtins,'open',logical_open)
    peaks=[]
    for size in (1024*1024,128*1024*1024):
        lengths.clear()
        tracemalloc.start()
        result=p.inventory(tmp_path)
        _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        peaks.append(peak)
        reference=sha256()
        for _ in range(size//65536): reference.update(b'z'*65536)
        assert result['payload.bin']==dict(size=size,sha256=reference.hexdigest())
        assert lengths and max(lengths)==65536
    # Includes Python stream overhead, two transient chunks and call bookkeeping.
    assert max(peaks)<512*1024
    assert peaks[1]<peaks[0]+128*1024


@pytest.mark.parametrize('operation',['inventory','disclosure'])
def test_unexpected_directory_blocks_complete_inventory(tmp_path,operation):
    root=tmp_path/'journal'; root.mkdir()
    (root/'writer.lock').write_bytes(b'interrupted')
    (root/'unexpected').mkdir()
    before=(root/'writer.lock').read_bytes()
    out=tmp_path/'disclosure.json'
    with pytest.raises(ValueError):
        if operation=='inventory': p.inventory(root)
        else: j.disclose_failure(out,root,failure='F1',numerical_abort=True)
    assert not out.exists()
    assert (root/'writer.lock').read_bytes()==before
    assert (root/'unexpected').is_dir()


@pytest.mark.parametrize('directory',[False,True])
def test_symbolic_links_block_inventory_and_disclosure(tmp_path,directory):
    root=tmp_path/'journal'; root.mkdir()
    target=tmp_path/'target'
    if directory: target.mkdir()
    else: target.write_bytes(b'synthetic')
    link=root/'link'
    try: link.symlink_to(target,target_is_directory=directory)
    except (OSError,NotImplementedError) as exc: pytest.skip(f'symlinks unavailable: {exc}')
    for operation in (p.inventory,j.inspect_partial):
        with pytest.raises(ValueError): operation(root)
    assert link.is_symlink()


def test_windows_junction_rejected(tmp_path):
    import os
    import subprocess
    if os.name!='nt': pytest.skip('Windows junction qualification')
    root=tmp_path/'journal'; root.mkdir()
    target=tmp_path/'target'; target.mkdir()
    link=root/'junction'
    completed=subprocess.run(['cmd','/c','mklink','/J',str(link),str(target)],capture_output=True)
    assert completed.returncode==0,completed.stderr
    for operation in (p.inventory,j.inspect_partial):
        with pytest.raises(ValueError): operation(root)
    with pytest.raises(ValueError): p.inventory(link)
    assert link.exists() and target.is_dir()


@pytest.mark.parametrize('receipt_kind',['missing','declaration','wrong-subject'])
def test_retry_review_requires_acceptable_external_receipt(tmp_path,receipt_kind):
    journal=SyntheticJournal(tmp_path)
    journal.append('started',1,started()); journal.append('result',1,result('F3'))
    review=None
    if receipt_kind=='declaration': review=g.Claim('retry-review',FULL.fingerprint,H,True)
    if receipt_kind=='wrong-subject': review=proof('retry-review','b'*64)
    before={x.name:x.read_bytes() for x in tmp_path.iterdir()}
    with pytest.raises(ValueError): journal.append('started',2,started(retry_evidence=H),retry_proof=review)
    assert {x.name:x.read_bytes() for x in tmp_path.iterdir() if x.name!='writer.lock'}==before
    assert (tmp_path/'writer.lock').exists()


def test_outer_seal_bytes_preserved_and_verification_read_only(tmp_path):
    (tmp_path/'synthetic.json').write_bytes(b'{}')
    provenance=dict(attempt=1,source='supplied-evidence',accounting_sha256=H)
    # Independent old whole-file inventory algorithm for this bounded fixture.
    files={'synthetic.json':dict(size=2,sha256=sha256(b'{}').hexdigest())}
    body=dict(schema='hashlab-exp002-outer-manifest-v1',seedless=PLAN.fingerprint,
              full_plan=FULL.fingerprint,provenance=provenance,files=files)
    expected=canonical(body); pin=sha256(expected).hexdigest()
    assert p.seal(tmp_path,PLAN,FULL,provenance,[proof('evidence-completeness',FULL.fingerprint,pin)])==pin
    assert (tmp_path/'manifest.json').read_bytes()==expected
    before={x.name:(x.read_bytes(),x.stat().st_mtime_ns) for x in tmp_path.iterdir()}
    assert p.verify_seal(tmp_path,PLAN,FULL,pin,proof('outer-manifest',FULL.fingerprint,pin))==body
    assert before=={x.name:(x.read_bytes(),x.stat().st_mtime_ns) for x in tmp_path.iterdir()}

@pytest.mark.parametrize('mode,attributes',[(0o010600,0),(0o100600,0x400),(0o120777,0)])
def test_unsupported_entry_metadata_rejected(tmp_path,monkeypatch,mode,attributes):
    from pathlib import Path
    from types import SimpleNamespace
    path=tmp_path/'unexpected'; path.touch()
    original=Path.lstat
    def fake_lstat(self,*args,**kwargs):
        if self==path: return SimpleNamespace(st_mode=mode,st_file_attributes=attributes)
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'lstat',fake_lstat)
    for operation in (p.inventory,j.inspect_partial):
        with pytest.raises(ValueError): operation(tmp_path)


def test_unknown_regular_artifact_included_without_omission(tmp_path):
    (tmp_path/'unexpected.bin').write_bytes(b'partial-unknown')
    assert j.inspect_partial(tmp_path)=={'unexpected.bin':dict(size=15,sha256=sha256(b'partial-unknown').hexdigest())}
