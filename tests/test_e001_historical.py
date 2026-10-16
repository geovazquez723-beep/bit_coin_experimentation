"""S1.3 synthetic streaming qualification. No new historical-prefix execution."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import ast
import json
import sqlite3
import struct
import subprocess
import sys

import pytest

from hashlab.experiments import e001_historical as p
from e001_stream_verify import streaming as v

SEALED = Path('results/20261011T205056Z-exp001-fc1d75fc')
CONTRACT = Path('src/hashlab/experiments/e001_contract.json')


def run(tmp_path, geometry=None, **kwargs):
    g = geometry or p.SyntheticGeometry(3, 4)
    report = p.run_synthetic(g, tmp_path/'producer', **kwargs)
    verified = v.verify_synthetic(tmp_path/'producer', tmp_path/'verifier', g.ordinals,
                                  g.discovery, g.validation, g.seeds)
    return g, report, verified


@pytest.mark.parametrize('ordinal', p.KINDS)
def test_all_families_production_streaming(tmp_path, ordinal):
    g, report, verified = run(tmp_path, p.SyntheticGeometry(510 if ordinal == 4 else 17, 9, (ordinal,)))
    assert verified['accounting'] == report['accounting']
    assert verified['exclusion_sha256'] == report['exclusion_sha256']
    assert verified['raw_attempted'] == g.discovery+g.validation
    assert not verified['historical_complete'] and not verified['final_acceptance']
    assert not (tmp_path/'producer/INCOMPLETE').exists()
    assert not (tmp_path/'verifier/INCOMPLETE').exists()
    if ordinal == 4:
        raw = (tmp_path/'producer/occurrences.bin').read_bytes()
        candidates = [p.ROW.unpack_from(raw, i*p.ROW.size)[4] for i in range(509, 514)]
        assert candidates == [bytes(m)*4 for m in ((0,254),(0,255),(1,0),(1,2),(1,3))]


@pytest.mark.parametrize('ordinal', (2, 9))
def test_seeded_restarts_and_cross_precedence(tmp_path, ordinal):
    _, report, verified = run(tmp_path, p.SyntheticGeometry(8, 8, (ordinal,), (1,1)))
    assert [c['unique'] for c in report['accounting']] == [8, 0]
    assert report['accounting'][1]['cross'] == 8
    assert verified['unique_evaluated'] == 8


@pytest.mark.parametrize('d,w', [(0,3),(3,0)])
def test_empty_phase(tmp_path, d, w):
    _, report, verified = run(tmp_path, p.SyntheticGeometry(d,w))
    assert verified['raw_attempted'] == report['raw_attempted'] == 7*(d+w)


def test_production_like_geometry_is_separate_from_unchanged_fixture_cap(tmp_path):
    from hashlab.experiments.e001_phase_b import FixturePlan
    with pytest.raises(ValueError): FixturePlan(((2,'uniform'),),4096,1)
    _, report, verified = run(tmp_path, p.SyntheticGeometry(2050,2050,(2,9)))
    assert verified['raw_attempted'] == report['raw_attempted'] == 8200
    assert (tmp_path/'producer/occurrences.bin').stat().st_size == 8200*19


def test_patterned_period_three_continuation(tmp_path):
    # The first 256+65,280 emitted patterns have periods one/two; index 65,536
    # is the first primitive period-three output. This is synthetic geometry.
    _,report,verified=run(tmp_path,p.SyntheticGeometry(65535,3,(4,)))
    with open(tmp_path/'producer/occurrences.bin','rb') as src:
        src.seek(65535*19)
        rows=[p.ROW.unpack(src.read(19)) for _ in range(3)]
    assert [r[4] for r in rows]==[bytes([255,254])*4,(bytes([0,0,1])*3)[:8],(bytes([0,0,2])*3)[:8]]
    assert [(r[1],r[2],r[3]) for r in rows]==[(1,0,65535),(1,1,65536),(1,2,65537)]
    assert verified['raw_attempted']==report['raw_attempted']==65538


def test_inert_historical_spec_and_disabled_internal_boundaries(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail('historical generator construction')
    monkeypatch.setattr(p, 'build_generator', forbidden)
    plan = p.historical_plan(SEALED, Path.cwd())
    assert plan == v.historical_plan(CONTRACT)
    assert len(plan['streams']) == 14
    assert sum(s['attempts'] for s in plan['streams']) == 7000000
    for action in (lambda: p.run_historical(SEALED, Path.cwd(), tmp_path/'out'),
                   lambda: next(p._raw(plan)),
                   lambda: p._run(plan, tmp_path/'out', (), p.Limits()),
                   lambda: v.verify_historical(tmp_path/'out', tmp_path/'work', CONTRACT),
                   lambda: v._verify(tmp_path/'out', tmp_path/'work', plan, None, 1024, 128*1024**2)):
        with pytest.raises(PermissionError, match='disabled'): action()
    assert not (tmp_path/'out').exists() and not (tmp_path/'work').exists()
    assert p.HISTORICAL_EXECUTION_ENABLED is False
    assert v.HISTORICAL_VERIFICATION_ENABLED is False


def test_lazy_maximum_synthetic_provider_has_no_hidden_prefix_replay(monkeypatch):
    drawn=0
    class Counted:
        def stream(self,seed,start):
            nonlocal drawn
            assert seed is None and start==0
            for i in range(262145):
                drawn+=1
                assert drawn<=262144
                yield i.to_bytes(8,'big')
    monkeypatch.setattr(p,'build_generator',lambda spec:Counted())
    source=p._raw(p.synthetic_plan(p.SyntheticGeometry(131072,131072,(4,))))
    assert drawn==0
    n=0
    for row in source:
        assert row[3]==n
        n+=1
    assert n==drawn==262144


def rows_for(g, values):
    source = iter(values)
    for s in p.synthetic_plan(g, manual=True)['streams']:
        for i in range(s['attempts']):
            yield s['ordinal'],s['phase'],i,s['start_index']+i,next(source)


def test_manual_exact_membership_values_ranks_and_digest(tmp_path):
    a,b,c,last = 1<<32,1<<63,(1<<32)|1,63<<58
    raw = tuple(x.to_bytes(8,'big') for x in
                (a,a,1<<20,(1<<32)-1,a,a,b,b,c,c,last,(1<<20)-1,c,b,127<<57,0))
    g = p.SyntheticGeometry(4,4,(2,9))
    report = p.run_synthetic(g,tmp_path/'producer',reference_rows=rows_for(g,raw),limits=p.Limits(batch=3))
    result = v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',g.ordinals,4,4,reference=raw,batch=2)
    assert (result['raw_attempted'],result['unique_evaluated'],result['qualifying_a1'],
            result['qualifying_a3'],result['distinct_excluded_a3']) == (16,10,2,5,4)
    records = (tmp_path/'producer/exclusions.bin').read_bytes()
    assert [p.PAIR.unpack_from(records,i*16) for i in range(4)] == [
        (a.to_bytes(8,'big'),0),(c.to_bytes(8,'big'),32),
        (b.to_bytes(8,'big'),31),(last.to_bytes(8,'big'),82128983)]
    assert struct.unpack('>4Q',(tmp_path/'producer/ranks.bin').read_bytes()) == (0,31,32,82128983)
    assert report['exclusion_sha256'] == 'd65c8c02efc910c357685ed6a2f1b3a23711458121c052624dbfbc9483891b49'
    with pytest.raises(ValueError):
        v.verify_synthetic(tmp_path/'producer',tmp_path/'algorithmic',g.ordinals,4,4)


def reseal(root, name):
    report = json.loads((root/'complete.json').read_bytes())
    raw = (root/name).read_bytes()
    report['files'][name] = dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    (root/'complete.json').write_bytes(p.encode(report))


@pytest.mark.parametrize('failure',['candidate','index','enum','ordinal','phase','outcome','missing','extra','reorder','truncated'])
def test_independent_rejects_resealed_occurrence_corruption(tmp_path,failure):
    g = p.SyntheticGeometry(3,4,(2,))
    p.run_synthetic(g,tmp_path/'producer')
    path = tmp_path/'producer/occurrences.bin'
    raw = bytearray(path.read_bytes())
    row = list(p.ROW.unpack(raw[:19]))
    if failure in ('candidate','index','enum','ordinal','phase','outcome'):
        pos = dict(candidate=4,index=2,enum=3,ordinal=0,phase=1,outcome=5)[failure]
        row[pos] = bytes(8) if pos == 4 else row[pos]+1
        raw[:19] = p.ROW.pack(*row)
    elif failure == 'missing': del raw[-19:]
    elif failure == 'extra': raw.extend(raw[:19])
    elif failure == 'reorder': raw[:38] = raw[19:38]+raw[:19]
    else: del raw[-1:]
    path.write_bytes(raw)
    reseal(path.parent,path.name)
    with pytest.raises(ValueError): v.verify_synthetic(path.parent,tmp_path/'verifier',(2,),3,4)


@pytest.mark.parametrize('field',['source','config','contract','manifest','scope','streams'])
def test_exact_plan_identity_rejects_resealed_tampering(tmp_path,field):
    g = p.SyntheticGeometry(2,2,(2,))
    p.run_synthetic(g,tmp_path/'producer')
    path = tmp_path/'producer/plan.json'
    plan = json.loads(path.read_bytes())
    if field == 'streams': plan[field][1]['start_index'] = 99
    else: plan[field] = 'wrong'
    path.write_bytes(p.encode(plan))
    reseal(path.parent,path.name)
    with pytest.raises(ValueError,match='plan'): v.verify_synthetic(path.parent,tmp_path/'verifier',(2,),2,2)


@pytest.mark.parametrize('field,value',[('raw_attempted',True),('unique_evaluated',0),('qualifying_a1',1),
    ('qualifying_a3',0),('distinct_excluded_a3',0),('exclusion_sha256','0'*64),
    ('historical_complete',True),('accounting',[]),('final_acceptance',True)])
def test_independent_rejects_false_reports(tmp_path,field,value):
    p.run_synthetic(p.SyntheticGeometry(2,2,(8,)),tmp_path/'producer')
    path = tmp_path/'producer/complete.json'
    report = json.loads(path.read_bytes());report[field]=value
    path.write_bytes(p.encode(report))
    with pytest.raises(ValueError): v.verify_synthetic(path.parent,tmp_path/'verifier',(8,),2,2)


@pytest.mark.parametrize('name',['exclusions.bin','ranks.bin'])
def test_resealed_rank_value_tampering(tmp_path,name):
    p.run_synthetic(p.SyntheticGeometry(2,2,(8,)),tmp_path/'producer')
    path = tmp_path/'producer'/name
    raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
    reseal(path.parent,name)
    with pytest.raises(ValueError): v.verify_synthetic(path.parent,tmp_path/'verifier',(8,),2,2)


def test_resealed_incomplete_sqlite_state_rejected(tmp_path):
    p.run_synthetic(p.SyntheticGeometry(2,2,(2,)),tmp_path/'producer')
    with sqlite3.connect(tmp_path/'producer/accounting.sqlite') as db:
        db.execute("UPDATE run SET status='incomplete'")
    reseal(tmp_path/'producer','accounting.sqlite')
    with pytest.raises(ValueError,match='incomplete producer database'):
        v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',(2,),2,2)


def test_missing_generator_stream_rejected(tmp_path):
    p.run_synthetic(p.SyntheticGeometry(2,2),tmp_path/'producer')
    path=tmp_path/'producer/occurrences.bin'
    raw=path.read_bytes()
    path.write_bytes(raw[:4*19]+raw[8*19:])  # remove both uniform phases
    reseal(path.parent,path.name)
    with pytest.raises(ValueError): v.verify_synthetic(path.parent,tmp_path/'verifier',(0,2,4,6,7,8,9),2,2)


@pytest.mark.parametrize('failure',['short','extra','interrupt','reorder'])
def test_failed_producer_stays_incomplete(tmp_path,failure):
    g=p.SyntheticGeometry(3,4,(2,))
    rows=list(p._raw(p.synthetic_plan(g)))
    if failure=='short': rows.pop()
    elif failure=='extra': rows.append(rows[-1])
    elif failure=='reorder': rows[0],rows[1]=rows[1],rows[0]
    else:
        first=rows[0]
        def broken():
            yield first
            raise OSError('injected interruption')
        rows=broken()
    with pytest.raises((ValueError,OSError)):
        p.run_synthetic(g,tmp_path/'producer',reference_rows=rows,limits=p.Limits(batch=2))
    assert (tmp_path/'producer/INCOMPLETE').exists()
    assert not (tmp_path/'producer/complete.json').exists()
    with pytest.raises(FileNotFoundError):
        v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',(2,),3,4,reference=(bytes(8),)*7)
    with pytest.raises(FileExistsError): p.run_synthetic(g,tmp_path/'producer')


def test_sqlite_interrupted_commit_rolls_back(tmp_path,monkeypatch):
    def broken(self,n): raise OSError('commit interrupted')
    monkeypatch.setattr(p._Store,'commit',broken)
    with pytest.raises(OSError): p.run_synthetic(p.SyntheticGeometry(3,0,(2,)),tmp_path/'producer',limits=p.Limits(batch=2))
    with sqlite3.connect(f'file:{tmp_path / "producer/accounting.sqlite"}?mode=ro',uri=True) as db:
        assert db.execute('SELECT count(*) FROM first_seen').fetchone()==(0,)
        assert db.execute('SELECT status,attempted FROM run').fetchone()==('incomplete',0)


def test_abrupt_process_exit_leaves_unusable_evidence(tmp_path):
    # Exit a child during an open synthetic transaction; never open/recover its DB.
    script='''
import os,sys
from hashlab.experiments import e001_historical as p
g=p.SyntheticGeometry(3,4,(2,))
source=p._raw(p.synthetic_plan(g))
def interrupted():
    yield next(source)
    yield next(source)
    yield next(source)
    os._exit(23)
p.run_synthetic(g,sys.argv[1],reference_rows=interrupted(),limits=p.Limits(batch=2))
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path/'producer')],check=False)
    assert result.returncode==23
    assert (tmp_path/'producer/INCOMPLETE').exists()
    assert not (tmp_path/'producer/complete.json').exists()
    with pytest.raises(FileNotFoundError):
        v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',(2,),3,4,reference=(bytes(8),)*7)
    with pytest.raises(FileExistsError): p.run_synthetic(p.SyntheticGeometry(3,4,(2,)),tmp_path/'producer')


def test_independent_interruption_poisoned_attempt(tmp_path,monkeypatch):
    p.run_synthetic(p.SyntheticGeometry(3,4,(2,)),tmp_path/'producer')
    original=v._stream
    def broken(kind,seed):
        yield next(original(kind,seed))
        raise OSError('independent interruption')
    monkeypatch.setattr(v,'_stream',broken)
    with pytest.raises(OSError): v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',(2,),3,4)
    assert (tmp_path/'verifier/INCOMPLETE').exists()
    assert not (tmp_path/'verifier/verified.json').exists()
    with sqlite3.connect(f'file:{tmp_path / "verifier/reference.sqlite"}?mode=ro',uri=True) as db:
        assert db.execute('SELECT checked,status FROM progress').fetchone()==(0,'incomplete')
    with pytest.raises(FileExistsError): v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',(2,),3,4)


def test_real_producer_disagreement(tmp_path,monkeypatch):
    class Wrong:
        def stream(self,seed,start):
            while True: yield bytes(8)
    monkeypatch.setattr(p,'build_generator',lambda spec:Wrong())
    p.run_synthetic(p.SyntheticGeometry(3,4,(2,)),tmp_path/'producer')
    with pytest.raises(ValueError,match='bytes/order'):
        v.verify_synthetic(tmp_path/'producer',tmp_path/'verifier',(2,),3,4)


def test_limits_disk_full_and_no_sealed_outputs(tmp_path):
    with pytest.raises(ValueError): p.SyntheticGeometry(262144,1,(2,))
    with pytest.raises(ValueError): p.SyntheticGeometry(1,1,(2,),(710289665967761509,8231496708541735395))
    with pytest.raises(ValueError): p.run_synthetic(p.SyntheticGeometry(3,4),tmp_path/'small',limits=p.Limits(output_bytes=65536))
    with pytest.raises(sqlite3.OperationalError):
        p.run_synthetic(p.SyntheticGeometry(4096,0,(2,)),tmp_path/'full',limits=p.Limits(database_bytes=65536,output_bytes=2*1024**2))
    assert (tmp_path/'full/INCOMPLETE').exists() and not (tmp_path/'full/complete.json').exists()
    (tmp_path/'manifest.sha256').write_text('synthetic sealed marker')
    with pytest.raises(ValueError,match='sealed'): p.run_synthetic(p.SyntheticGeometry(1,0),tmp_path/'sealed-out')


def test_internal_synthetic_cap_and_scope_cannot_bypass(tmp_path):
    plan=p.synthetic_plan(p.SyntheticGeometry(1,1,(2,)))
    plan['streams'][0]['attempts']=262144
    with pytest.raises(ValueError): next(p._raw(plan))
    with pytest.raises(ValueError): p._run(plan,tmp_path/'out',(),p.Limits())
    with pytest.raises(ValueError): v._verify(tmp_path/'out',tmp_path/'work',plan,None,1024,128*1024**2)
    assert not (tmp_path/'out').exists()


def test_no_hash_engine_or_derivation_and_verifier_isolation(tmp_path,monkeypatch):
    from hashlab.hashing.sha256 import SHA256Engine
    from hashlab.candidates import base
    def forbidden(*a,**k): pytest.fail('research hashing or execution seed derivation')
    monkeypatch.setattr(SHA256Engine,'digest',forbidden)
    monkeypatch.setattr(base,'derive_seed',forbidden)
    run(tmp_path)
    tree=ast.parse(Path(v.__file__).read_text())
    allowed={'hashlib','math','pathlib','json','os','sqlite3','stat','struct','e001_verify.core'}
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom): assert node.module in allowed
        if isinstance(node,ast.Import): assert all(n.name in allowed for n in node.names)
    for module in (p,v): assert not hasattr(module,'main')


def test_resource_probe_rejects_sealed_output_before_directory_creation(tmp_path):
    (tmp_path/'manifest.sha256').write_text('synthetic sealed marker')
    result=subprocess.run([sys.executable,'-B','tools/qualify_e001_readiness.py',str(tmp_path/'forbidden')],
                          check=False,capture_output=True,text=True)
    assert result.returncode!=0 and 'sealed' in result.stderr
    assert not (tmp_path/'forbidden').exists()


def test_original_sources_and_e001_preserved():
    from hashlab.experiments.e001_reconstruction import validate_history
    from hashlab.evidence.manifest import verify_manifest
    validate_history(SEALED,Path.cwd())
    assert verify_manifest(SEALED)==[]
    # The snapshot is a point-in-time local working-checkout inventory (see tests/e001_snapshot.py):
    # sealed evidence must match exactly; the wider inventory is checked against the pinned present baseline.
    from e001_snapshot import check_snapshot_file
    assert check_snapshot_file(Path('results-smoke/e001-s13-qualification/before.json'))==[]
