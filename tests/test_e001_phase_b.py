"""Review 038 synthetic fixtures, <=4096 total occurrence records per test."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import ast
import json
import random
import sqlite3
import tracemalloc
import pytest
from hashlab.experiments import e001_phase_b as b
from hashlab.experiments import e001_phase_b_verification as bridge
from hashlab.experiments.exp002_foundation import canonical
from e001_verify import MT19937,verify_rows,classify


def plan(specs=((0,'sequential'),),d=3,v=2,**kwargs):return b.FixturePlan(specs,d,v,**kwargs)

@pytest.mark.parametrize('kind',list(b.KINDS.items()))
def test_exact_independent_streams_and_transitions(tmp_path,kind):
    p=plan((kind,),d=260 if kind[1]=='patterned' else 17,v=9)
    store=b.ExactDedup(tmp_path/'set.db')
    result=b.account_rows(p,b.fixture_rows(p),store);store.close()
    independent=verify_rows(p.specs,p.discovery,p.validation,p.seeds,b.fixture_rows(p))
    assert result['accounting']==independent['accounting']
    assert result['membership']==independent['membership']
    assert result['a3_provenance']==independent['a3_provenance']
    assert result['final_acceptance'] is False

@pytest.mark.parametrize('seed',[0,1,2,2**32,2**64-1])
def test_independent_mt_integer_seed_word_assembly(seed):
    a=MT19937(seed);c=random.Random(seed)
    # 2048 outputs total; includes several MT state-boundary transitions.
    for k in ([0,1,31,32,33,64,65,128]*256):assert a.getrandbits(k)==c.getrandbits(k)


def test_pinned_mt_vectors():
    pins=json.loads(Path('tests/fixtures/e001-mt19937-synthetic-v1.json').read_text())
    for item in pins['vectors']:
        rng=MT19937(item['seed'])
        assert [rng.getrandbits(k) for k in item['widths']]==item['values']


def test_within_cross_first_provenance_and_cross_generator(tmp_path):
    db=b.ExactDedup(tmp_path/'seen.db');raw=(1<<32).to_bytes(8,'big')
    assert db.observe(2,0,0,raw)==dict(outcome='unique',first_phase=0,first_index=0)
    assert db.observe(2,0,1,raw)['outcome']=='within'
    assert db.observe(2,1,0,raw)['outcome']=='cross'
    assert db.observe(9,0,0,raw)['outcome']=='unique'
    assert db.db.execute('SELECT typeof(candidate) FROM seen').fetchall()==[('blob',),('blob',)]
    db.close()


def test_exact_synthetic_accounting_duplicates(tmp_path):
    p=plan(((2,'uniform'),),d=2,v=2);raw=(1<<32).to_bytes(8,'big')
    rows=[(2,0,0,raw),(2,0,1,raw),(2,1,0,raw),(2,1,1,(1<<63).to_bytes(8,'big'))]
    db=b.ExactDedup(tmp_path/'seen.db');out=b.account_rows(p,rows,db);db.close()
    assert out['accounting'][0]['within']==1 and out['accounting'][1]['cross']==1
    assert out['membership']==classify(r[3] for r in rows)
    assert out['membership']['a3_occurrences']==4
    assert out['a3_provenance'][0]==dict(value_hex=raw.hex(),ordinal=2,phase=0,index=0,occurrences=3)

@pytest.mark.parametrize('change',[dict(source='a'*40),dict(config='a'*64),dict(manifest='a'*64),dict(contract='a'*64),dict(schema='old')])
def test_reject_wrong_identity(change):
    with pytest.raises(ValueError):replace(plan(),**change)

@pytest.mark.parametrize('d,v',[(4096,1),(-1,1),(True,1),(0,0)])
def test_fixture_geometry_fail_closed(d,v):
    with pytest.raises(ValueError):plan(d=d,v=v)


def test_chunk_exact_header_roundtrip():
    rows=((2,1,0,b'12345678'),(2,1,1,b'abcdefgh'))
    raw=b.encode_chunk(rows)
    assert raw[:18]==b'HLE1OCC1'+b'\x02\x01'+b'\x00'*4+b'\x00\x00\x00\x02'
    assert raw[18:]==b'\x00'*4+b'12345678'+b'\x00\x00\x00\x01abcdefgh'
    assert b.decode_chunk(raw)==rows

@pytest.mark.parametrize('mutation',['truncate','magic','duplicate-index','extra'])
def test_bad_chunks(mutation):
    raw=b.encode_chunk(((0,0,0,b'12345678'),(0,0,1,b'abcdefgh')))
    if mutation=='truncate':raw=raw[:-1]
    elif mutation=='magic':raw=b'X'+raw[1:]
    elif mutation=='duplicate-index':raw=raw[:30]+b'\x00'*4+raw[34:]
    else:raw+=b'x'
    with pytest.raises(ValueError):b.decode_chunk(raw)


def write_fixture(root,p):
    root.mkdir()
    return b.ChunkWriter(root,p,chunk_limit=2).write(b.fixture_rows(p))

@pytest.mark.parametrize('mutation',['corrupt','missing','duplicated','wrong-pin','wrong-plan','extra'])
def test_chunk_evidence_integrity(tmp_path,mutation):
    p=plan();root=tmp_path/'out';pin=write_fixture(root,p)
    assert list(b.read_chunks(root,p,pin))==list(b.fixture_rows(p))
    if mutation=='corrupt':(root/'occ-00000001.bin').write_bytes(b'bad')
    elif mutation=='missing':(root/'occ-00000001.bin').unlink()
    elif mutation=='duplicated':(root/'occ-00000002.bin').write_bytes((root/'occ-00000001.bin').read_bytes())
    elif mutation=='wrong-pin':pin='a'*64
    elif mutation=='wrong-plan':p=plan(d=4)
    else:(root/'extra').write_bytes(b'extra')
    with pytest.raises(ValueError):list(b.read_chunks(root,p,pin))


def test_checkpoint_chain_and_rewritten_tail(tmp_path):
    p=plan();check=b.Checkpoints(tmp_path,p)
    head=check.append(2);head=check.append(4,head)
    assert len(check.read(head))==2
    row=b.decode((tmp_path/'00000002.json').read_bytes());row['checked']=3
    (tmp_path/'00000002.json').write_bytes(canonical(row))
    with pytest.raises(ValueError):check.read(head)


def test_checkpoint_torn_write_no_resume(tmp_path,monkeypatch):
    original=b.durable_create
    def torn(path,raw):
        if path.suffix=='.json':original(path,raw[:9]);raise OSError('synthetic disk full')
        original(path,raw)
    monkeypatch.setattr(b,'durable_create',torn)
    cp=b.Checkpoints(tmp_path,plan())
    with pytest.raises(OSError):cp.append(1)
    assert (tmp_path/'writer.lock').exists() and (tmp_path/'00000001.json').stat().st_size==9
    with pytest.raises(ValueError):cp.append(1)


def test_chunk_disk_full_retains_partial_evidence(tmp_path,monkeypatch):
    original=b.durable_create
    def disk_full(path,raw):
        if path.suffix=='.bin':original(path,raw[:5]);raise OSError('synthetic disk full')
        original(path,raw)
    monkeypatch.setattr(b,'durable_create',disk_full)
    writer=b.ChunkWriter(tmp_path,plan(),chunk_limit=1)
    with pytest.raises(OSError):writer.write(b.fixture_rows(plan()))
    assert (tmp_path/'writer.lock').exists() and (tmp_path/'occ-00000001.bin').stat().st_size==5
    with pytest.raises(ValueError):writer.write([])


def test_sqlite_transaction_failure_poisoned_no_retry(tmp_path,monkeypatch):
    db=b.ExactDedup(tmp_path/'seen.db')
    def fail():raise sqlite3.OperationalError('synthetic disk full')
    monkeypatch.setattr(db,'_commit',fail)
    with pytest.raises(sqlite3.OperationalError):db.observe(0,0,0,b'12345678')
    assert db.failed and db.db.execute('SELECT count(*) FROM seen').fetchone()==(0,)
    with pytest.raises(ValueError):db.observe(0,0,0,b'12345678')
    db.close()


def test_configured_limits(tmp_path):
    db=b.ExactDedup(tmp_path/'seen.db',max_records=1)
    db.observe(0,0,0,b'12345678')
    with pytest.raises(ValueError):db.observe(0,0,1,b'abcdefgh')
    db.close()
    root=tmp_path/'chunks';root.mkdir();writer=b.ChunkWriter(root,plan(),max_bytes=1)
    with pytest.raises(ValueError):writer.write(b.fixture_rows(plan()))
    assert (root/'writer.lock').exists()


def test_wrong_membership_report_and_missing_or_forged_reports(tmp_path):
    p=plan();root=tmp_path/'out';pin=write_fixture(root,p)
    report=bridge.independent_report(root,p,pin)
    bridge.validate_report(report,root,p,pin)
    for field,value in (('a1',10),('a3_distinct',60721),('exclusion_sha256','a'*64)):
        bad=b.decode(report);bad['result']['membership'][field]=value
        with pytest.raises(ValueError):bridge.validate_report(canonical(bad),root,p,pin)
    with pytest.raises(ValueError):bridge.validate_report(None,root,p,pin)
    changed=b.decode(report);changed['source']='a'*40
    with pytest.raises(ValueError):bridge.validate_report(canonical(changed),root,p,pin)


class SyntheticReceiptVerifier:
    """Toy fixture receipt check; no actual external authentication claimed."""
    def verify(self,claim,receipt):return receipt==b'SYNTHETIC-UNAUTHENTICATED:'+claim.subject_sha256.encode()


def test_missing_receipt_and_invalid_final_acceptance(tmp_path):
    p=plan();root=tmp_path/'out';pin=write_fixture(root,p);report=bridge.independent_report(root,p,pin)
    rp=sha256(report).hexdigest();subject=bridge.acceptance_subject(p,pin,rp)
    receipt=b'SYNTHETIC-UNAUTHENTICATED:'+subject.encode()
    record=dict(schema='e001-final-fixture-record-v1',subject=subject,plan=p.fingerprint,manifest=pin,
        independent_report=rp,receipt_sha256=sha256(receipt).hexdigest(),decision='fixture-only',e_audit_accepted=False)
    for invalid_receipt in (b'',b'forged'):
        with pytest.raises(ValueError):bridge.validate_final_record(canonical(record),root,p,pin,report,invalid_receipt,SyntheticReceiptVerifier())
    assert bridge.validate_final_record(canonical(record),root,p,pin,report,receipt,SyntheticReceiptVerifier())['e_audit_accepted'] is False
    record['e_audit_accepted']=True
    with pytest.raises(ValueError):bridge.validate_final_record(canonical(record),root,p,pin,report,receipt,SyntheticReceiptVerifier())


def test_independent_verifier_isolation():
    allowed={'hashlib','itertools','math','core'}
    for path in Path('src/e001_verify').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.ImportFrom):assert node.module in allowed
            if isinstance(node,ast.Import):assert all(n.name in allowed for n in node.names)
    assert 'random' not in __import__('e001_verify.core',fromlist=['x']).__dict__


def test_bounded_writer_memory(tmp_path):
    peaks=[]
    # 32+1984=2016 generated (4032 including reads) occurrences TOTAL for this individual test.
    for n in (32,1984):
        p=plan(((9,'random_bytes'),),d=n,v=0);root=tmp_path/str(n);root.mkdir()
        tracemalloc.start()
        pin=b.ChunkWriter(root,p,chunk_limit=64).write(b.fixture_rows(p))
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        assert sum(1 for _ in b.read_chunks(root,p,pin))==n
        peaks.append(peak)
    print('bounded writer traced peaks:',peaks)
    assert max(peaks)<1024*1024 and peaks[1]<peaks[0]+256*1024


def test_incomplete_contract_never_final():
    raw=b.incomplete_attempt(plan(),2,'synthetic interruption',{})
    data=b.decode(raw)
    assert data['status']=='incomplete' and data['retry_authorized'] is False and data['final_acceptance'] is False


def test_sqlite_actual_page_reservation_abort(tmp_path):
    db=b.ExactDedup(tmp_path/'capped.db',max_bytes=65536,cache_kib=8)
    with pytest.raises(sqlite3.OperationalError):
        for i in range(4096):db.observe(2,0,i,i.to_bytes(8,'big'))
    assert db.failed and (tmp_path/'capped.db').stat().st_size<=65536
    with pytest.raises(ValueError):db.observe(2,0,0,b'12345678')
    db.close()


def test_accounting_failure_poison_and_strict_bool_provenance(tmp_path):
    p=plan(d=1,v=0);db=b.ExactDedup(tmp_path/'set.db')
    with pytest.raises(ValueError):b.account_rows(p,[(False,0,0,b'12345678')],db)
    assert db.failed
    with pytest.raises(ValueError):db.observe(0,0,0,b'12345678')
    db.close()


def test_independent_source_membership_rank_vectors(tmp_path):
    p=plan(((2,'uniform'),),d=4,v=0)
    raw=[(2**20).to_bytes(8,'big'),(1<<32).to_bytes(8,'big'),(1<<63).to_bytes(8,'big'),((1<<32)|1).to_bytes(8,'big')]
    db=b.ExactDedup(tmp_path/'seen.db');out=b.account_rows(p,[(2,0,i,r) for i,r in enumerate(raw)],db);db.close()
    independent=classify(raw)
    assert out['membership']==independent and independent['a1']==1 and independent['a3_distinct']==3


def test_sqlite_python_memory_bound(tmp_path):
    p=plan(((9,'random_bytes'),),d=512,v=512)
    db=b.ExactDedup(tmp_path/'set.db',cache_kib=64)
    tracemalloc.start()
    result=b.account_rows(p,b.fixture_rows(p),db)
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    db.close()
    print('SQLite/accounting Python traced peak:',peak)
    assert result['producer_complete'] and peak<1024*1024


def test_missing_checkpoint_and_incomplete_chunk_geometry(tmp_path):
    cp=b.Checkpoints(tmp_path,plan());head=cp.append(1);head=cp.append(3,head)
    (tmp_path/'00000001.json').unlink()
    with pytest.raises(ValueError):cp.read(head)
    with pytest.raises(ValueError):cp.append(4,head)
    root=tmp_path/'chunks';root.mkdir()
    writer=b.ChunkWriter(root,plan(),chunk_limit=2)
    with pytest.raises(ValueError):writer.write(iter([(0,0,0,b'12345678')]))
    assert (root/'writer.lock').exists()
    with pytest.raises(ValueError):writer.write([])


@pytest.mark.parametrize('specs',[((0,'gray'),),((0,'sequential'),(0,'sequential')),((True,'sequential'),)])
def test_independent_spec_rejection(specs):
    with pytest.raises(ValueError):verify_rows(specs,1,0,(1,2),[])


def test_false_producer_complete_and_forged_local_final_bool(tmp_path):
    p=plan();root=tmp_path/'out';write_fixture(root,p)
    manifest=b.decode((root/'manifest.json').read_bytes())
    manifest['final_acceptance']=True
    (root/'manifest.json').write_bytes(canonical(manifest))
    with pytest.raises(ValueError):list(b.read_chunks(root,p,b.fingerprint(manifest)))


def test_incomplete_inventory_schema_rejection():
    with pytest.raises(ValueError):b.incomplete_attempt(plan(),1,'error',{'../unsafe':{}})


def test_checkpoint_count_cannot_exceed_geometry(tmp_path):
    cp=b.Checkpoints(tmp_path,plan())
    with pytest.raises(ValueError):cp.append(6)
    assert not list(tmp_path.iterdir())


def test_serialized_producer_counts_independently_verified(tmp_path):
    p=plan(((8,'bit-reversed'),),d=4,v=3);root=tmp_path/'out';pin=write_fixture(root,p)
    db=b.ExactDedup(tmp_path/'seen.db');result=b.account_rows(p,b.fixture_rows(p),db);db.close()
    assert bridge.validate_producer_accounting(canonical(result),root,p,pin)==result
    for field,value in (('a1',1),('a3_occurrences',999),('exclusion_sha256','a'*64)):
        bad=json.loads(json.dumps(result));bad['membership'][field]=value
        with pytest.raises(ValueError):bridge.validate_producer_accounting(canonical(bad),root,p,pin)
    bad=json.loads(json.dumps(result));bad['a3_provenance'][0]['index']=100
    with pytest.raises(ValueError):bridge.validate_producer_accounting(canonical(bad),root,p,pin)
