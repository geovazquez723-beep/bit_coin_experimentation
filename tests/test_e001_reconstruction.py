"""E5 Phase A fixtures only. No full enumeration or candidate SHA-256."""
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
import json
import shutil
import tracemalloc
import pytest
from hashlab.experiments import e001_reconstruction as e
from hashlab.experiments.exp002_foundation import E001ExclusionRequest
from e001_reference import reference, rank_reference

ROOT=Path(__file__).resolve().parents[1]
SEALED=ROOT/'results/20261011T205056Z-exp001-fc1d75fc'
IDS=[s['id'] for s in e.contract()['config']['generators']]

@pytest.fixture
def provider():return e.BoundedE001Reconstruction(SEALED,ROOT)

@pytest.mark.parametrize('gid',IDS)
@pytest.mark.parametrize('phase',e.PHASES)
def test_independent_exact_occurrence_vectors(provider,gid,phase):
    if gid.startswith('pattern-') and phase=='validation':
        with pytest.raises(ValueError,match='unauthorized'):list(provider.records(gid,phase,count=3))
        return
    rows=list(provider.records(gid,phase,count=9))
    assert [r.candidate for r in rows]==reference(gid,phase,0,9)
    assert [r.index for r in rows]==list(range(9))
    assert all(r.generator==gid and r.ordinal==IDS.index(gid) and r.source==e.SOURCE and r.manifest==e.MANIFEST for r in rows)

@pytest.mark.parametrize('gid',IDS)
def test_window_offsets(provider,gid):
    rows=list(provider.records(gid,'discovery',start=17,count=5))
    assert [r.candidate for r in rows]==reference(gid,'discovery',17,5)

@pytest.mark.parametrize('gid',['seq-be-w8','seq-dec-w16','struct-gray-w8','struct-stride-w8','struct-bitrev-w8'])
def test_last_sealed_index_boundary(provider,gid):
    rows=list(provider.records(gid,'validation',start=499999,count=1))
    assert rows[0].enumeration_index==999999
    assert rows[0].candidate==reference(gid,'validation',499999,1)[0]
    with pytest.raises(ValueError):list(provider.records(gid,'validation',start=499999,count=2))

@pytest.mark.parametrize('kwargs',[dict(start=True),dict(count=-1),dict(count=4097),dict(start=500000),dict(start=4096,count=1)])
def test_reject_unbounded_windows(provider,kwargs):
    with pytest.raises(ValueError):list(provider.records('uniform-be-w8','discovery',**kwargs))

@pytest.mark.parametrize('name',['manifest.json','config.resolved.json','seeds.json','environment.json','results.json'])
def test_historical_tampering_rejected(tmp_path,name):
    for src in SEALED.iterdir(): shutil.copyfile(src,tmp_path/src.name)
    with (tmp_path/name).open('ab') as out:out.write(b' ')
    with pytest.raises(ValueError):e.BoundedE001Reconstruction(tmp_path,ROOT)


def test_missing_provenance_and_source_revision(tmp_path):
    for src in SEALED.iterdir():shutil.copyfile(src,tmp_path/src.name)
    (tmp_path/'environment.json').unlink()
    with pytest.raises(ValueError):e.validate_history(tmp_path,ROOT)
    with pytest.raises((ValueError,FileNotFoundError)):e.validate_history(SEALED,tmp_path)
    with pytest.raises(ValueError):e.strict_json(b'{"source":1,"source":2}')
    with pytest.raises(ValueError):e.strict_json(b'{"bad":NaN}')


def test_prefix_provider_protocol_is_explicitly_incomplete(provider):
    values=list(provider.candidates(E001ExclusionRequest()))
    assert len(values)==56 and all(len(v)==8 for v in values)
    with pytest.raises(ValueError):list(provider.candidates(None))
    with pytest.raises(ValueError):list(provider.records('not-historical','discovery'))


def occurrence(raw,index=0):return e.Occurrence('struct-bitrev-w8',8,'discovery',index,index,raw)

def schedule(rows):return tuple((r.generator,r.ordinal,r.phase,r.index) for r in rows)


def test_a3_rank_digest_independent_numeric_encoding():
    raw=[(1<<63).to_bytes(8,'big'),(1<<32).to_bytes(8,'big'),((1<<32)|1).to_bytes(8,'big')]
    out=e.exclusion_representation(raw+[raw[0]])
    assert out['ranks']==tuple(sorted(rank_reference(v) for v in raw))
    assert out['distinct']==3
    assert out['sha256']==sha256(b''.join(sorted(raw))).hexdigest()
    assert e.exclusion_representation(reversed(raw))==out
    # Numerical values and weight/colex ranks have different sort orders.
    assert out['ranks'][0]==0


def test_duplicate_occurrences_and_a1_zero_fixture():
    rows=[occurrence((1<<32).to_bytes(8,'big'),i) for i in range(2)]
    out=e.fixture_audit(rows,schedule(rows))
    assert out['a1_occurrences']==0 and out['duplicate_occurrences']==1
    assert out['exclusions']['distinct']==1 and out['checked']==2
    assert out['status']=='fixture-complete' and out['e_audit_passed'] is False


def test_a1_hit_is_never_passed():
    row=occurrence((2**20).to_bytes(8,'big'))
    out=e.fixture_audit([row],schedule([row]))
    assert out['a1_occurrences']==1 and out['status']=='fixture-a1-hit' and not out['e_audit_passed']

@pytest.mark.parametrize('bad',[b'',b'\x00'*8,b'\x01'*16,(1).to_bytes(8,'big'),((1<<32)|127).to_bytes(8,'big')])
def test_invalid_exclusions(bad):
    with pytest.raises(ValueError):e.exclusion_representation([bad])


def test_order_count_and_incomplete_interrupt():
    rows=[occurrence((1<<32).to_bytes(8,'big'),i) for i in range(3)]
    expected=schedule(rows)
    assert e.fixture_audit(rows[:1],expected)['status']=='incomplete'
    for bad in (rows[::-1],rows+[rows[0]],[rows[0],rows[0],rows[2]]):
        with pytest.raises(ValueError):e.fixture_audit(bad,expected)
    def interrupted():
        yield rows[0]
        raise OSError('synthetic interrupted enumeration')
    with pytest.raises(e.InterruptedAudit) as caught:e.fixture_audit(interrupted(),expected)
    assert caught.value.summary['checked']==1 and caught.value.summary['status']=='incomplete'
    assert caught.value.summary['e_audit_passed'] is False

@pytest.mark.parametrize('changes',[dict(source='a'*40),dict(manifest='a'*64),dict(ordinal=0),dict(enumeration_index=1),dict(index=True),dict(scope='production')])
def test_bad_occurrence_provenance(changes):
    with pytest.raises(ValueError):replace(occurrence((1<<32).to_bytes(8,'big')),**changes)


def test_bounded_memory_and_no_candidate_sha(provider,monkeypatch):
    original=e.sha256
    def metadata_only(raw=b''):
        assert len(raw) not in (8,16), 'candidate SHA-256 forbidden'
        return original(raw)
    monkeypatch.setattr(e,'sha256',metadata_only)
    peaks=[]
    for count in (32,4096):
        tracemalloc.start()
        emitted=sum(1 for _ in provider.records('random-bytes-w8','discovery',count=count))
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        assert emitted==count
        peaks.append(peak)
    assert max(peaks)<4*1024*1024 and peaks[1]<peaks[0]+1024*1024


def test_e001_read_only_preservation(provider):
    def snapshot():return {p.name:(sha256(p.read_bytes()).hexdigest(),p.stat().st_size,p.stat().st_mtime_ns) for p in SEALED.iterdir()}
    before=snapshot()
    list(provider.records('seq-be-w8','discovery',count=3))
    assert snapshot()==before

@pytest.mark.parametrize('change',[dict(ranks=(1,0)),dict(ranks=(0,0)),dict(ranks=(True,)),dict(distinct=60721),dict(sha256='a'*64)])
def test_supplied_exclusion_contract_rejection(change):
    good=e.exclusion_representation([(1<<32).to_bytes(8,'big')])
    assert e.validate_exclusion_representation(good)==good
    with pytest.raises(ValueError):e.validate_exclusion_representation(dict(good,**change))


def test_pattern_primitive_boundary(provider):
    for gid,start in (('pattern-bytes-w8',254),('pattern-chars-w16',93)):
        rows=list(provider.records(gid,'discovery',start=start,count=6))
        assert [r.candidate for r in rows]==reference(gid,'discovery',start,6)


def test_schedule_validation_even_without_records():
    with pytest.raises(ValueError):e.fixture_audit([], (('wrong',8,'discovery',0),))
    rows=[occurrence((1<<32).to_bytes(8,'big'),i) for i in (1,0)]
    with pytest.raises(ValueError):e.fixture_audit([],schedule(rows))


def test_modified_source_and_post_construction_mutation(tmp_path):
    # Source identity must match bytes of the accepted historical revision.
    c=e.contract()
    for name in c['source_sha256_lf']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    with (tmp_path/'src/hashlab/candidates/random.py').open('ab') as out:out.write(b'\n#changed')
    with pytest.raises(ValueError,match='source differs'):e.validate_history(SEALED,tmp_path)
    evidence=tmp_path/'evidence';evidence.mkdir()
    for src in SEALED.iterdir():shutil.copyfile(src,evidence/src.name)
    adapter=e.BoundedE001Reconstruction(evidence,ROOT)
    (evidence/'seeds.json').write_bytes(b'{}')
    with pytest.raises(ValueError):list(adapter.records('random-bytes-w8','discovery'))


def test_guarded_read_only_opens(provider,monkeypatch):
    import builtins
    original=builtins.open
    def guarded(path,mode='r',*args,**kwargs):
        if str(SEALED) in str(path):assert not any(flag in mode for flag in 'wax+')
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(builtins,'open',guarded)
    assert len(list(provider.records('seq-be-w8','discovery',count=3)))==3

@pytest.mark.parametrize('gid',['uniform-be-w8','uniform-dec-w16','random-bytes-w8'])
def test_original_seed_material_derivation(gid):
    # SHA-256 of historical label material only, never candidate bytes.
    from e001_reference import SEEDS
    for phase,pin in zip(e.PHASES,SEEDS[gid]):
        material=f'hashlab-seed-v1|20261011|{gid}|{phase}'.encode('utf-8')
        assert int.from_bytes(sha256(material).digest()[:8],'big')==pin
        assert e.contract()['seeds']['generators'][gid][phase]==pin


def test_contract_exact_sealed_payloads_and_original_source():
    import subprocess
    c=e.contract()
    for name,key in (('config.resolved.json','config'),('seeds.json','seeds'),('environment.json','environment')):
        assert json.loads((SEALED/name).read_bytes())==c[key]
    for name,pin in c['source_sha256_lf'].items():
        raw=subprocess.check_output(['git','show',e.SOURCE+':'+name],cwd=ROOT)
        assert sha256(raw).hexdigest()==pin


def test_empty_exclusion_representation():
    empty=e.exclusion_representation([])
    assert empty==dict(ranks=(),distinct=0,sha256=sha256(b'').hexdigest())
    assert e.validate_exclusion_representation(empty)==empty


def test_guarded_path_opens_are_read_only(provider,monkeypatch):
    import io
    original=io.open
    def guarded(path,mode='r',*args,**kwargs):
        if str(SEALED) in str(path): assert mode in ('r','rb')
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(io,'open',guarded)
    list(provider.records('random-bytes-w8','validation',count=3))
