"""Independent complete bounded kernel replay; no HASHLAB imports.

Binary decoding is specified here independently. Reuses accepted independent
I1/I2 generators and scalar/statistical references. No production-audit claim.
"""
from hashlib import sha256
from pathlib import Path
import struct

from . import core as arms, controls, integration
from .core import encode, _plain, _file_hash

_HEAD=struct.Struct('>8sIQQ')
_ROW=struct.Struct('>QBBBBQQQQI')
_END=struct.Struct('>QQ32s')
_ARMS=('A1','A2','A3','N1','N2','P1','P2+','P2-')
_STAGES=('D','V','C')
_REASONS=('C1','C3','E001','A2')
_ABSENT=2**64-1


def _json(path,cap):
    if path.stat().st_size>cap: raise ValueError('reference metadata cap')
    return integration.read_json(path)


def decode_chunks(root,report):
    """Constant-memory independent decoder; exhausted iterator checks terminal state."""
    sequence=chunk=0
    with (root/'chunks.jsonl').open('rb') as index:
        while line:=index.readline(1025):
            if len(line)>1024 or not line.endswith(b'\n'): raise ValueError('reference index framing')
            import json
            entry=json.loads(line)
            if encode(entry)+b'\n'!=line or set(entry)!={'sequence','name','first','rows','size','sha256'}:
                raise ValueError('reference index encoding')
            if (type(entry['sequence']) is not int or type(entry['first']) is not int
                    or type(entry['size']) is not int
                    or entry['sequence']!=chunk or entry['first']!=sequence or entry['name']!=f'chunk-{chunk:08d}.bin'
                    or type(entry['rows']) is not int or not 1<=entry['rows']<=4096
                    or chunk>=report['chunks'] or (chunk<report['chunks']-1 and entry['rows']!=4096)):
                raise ValueError('reference index continuity')
            path=root/entry['name'];_plain(path)
            if not _HEAD.size+_END.size<=path.stat().st_size<=_HEAD.size+_END.size+192*entry['rows']:
                raise ValueError('reference chunk size cap')
            info=_file_hash(path)
            if info!=dict(bytes=entry['size'],sha256=entry['sha256']): raise ValueError('reference chunk identity')
            with path.open('rb') as source:
                if source.read(_HEAD.size)!=_HEAD.pack(b'E002KRN1',1,chunk,sequence): raise ValueError('reference chunk header')
                h=sha256();length=0
                for _ in range(entry['rows']):
                    head=source.read(_ROW.size)
                    if len(head)!=_ROW.size: raise ValueError('reference torn row')
                    seq,arm,stage,mask,width,src,accepted,rank,offset,cluster=_ROW.unpack(head)
                    if seq!=sequence or arm>=8 or stage>=3 or mask>=16 or width not in (8,80):
                        raise ValueError('reference row tags')
                    payload=source.read(width+(0 if mask else 64))
                    if len(payload)!=width+(0 if mask else 64): raise ValueError('reference torn payload')
                    h.update(head+payload);length+=len(head+payload);sequence+=1
                    yield dict(arm=_ARMS[arm],stage=_STAGES[stage],candidate_hex=payload[:width].hex(),
                        source_index=None if src==_ABSENT else src,
                        accepted_index=None if accepted==_ABSENT else accepted,
                        population_rank=None if rank==_ABSENT else rank,
                        byte_offset=None if offset==_ABSENT else offset,
                        cluster=None if cluster==2**32-1 else cluster,
                        reasons=[r for i,r in enumerate(_REASONS) if mask&(1<<i)],
                        raw=None if mask else payload[width:width+32],
                        effective=None if mask else payload[width+32:])
                if source.read(_END.size)!=_END.pack(entry['rows'],length,h.digest()) or source.read(1):
                    raise ValueError('reference chunk trailer')
            chunk+=1
    if (sequence,chunk)!=(report['attempts'],report['chunks']): raise ValueError('reference incomplete chunks')


def verify_engineering(root, *, completion_sha256, audit_root, repository_root):
    root=Path(root);_plain(root,directory=True)
    if _file_hash(root/'complete.json')['sha256']!=completion_sha256: raise ValueError('reference completion pin')
    report=_json(root/'complete.json',8192)
    if (report.get('schema')!='hashlab-e002-kernel-completion-v1' or report.get('scope')!='engineering-only'
            or type(report.get('attempts')) is not int or not 206<=report['attempts']<=320
            or type(report.get('chunks')) is not int or not 1<=report['chunks']<=320):
        raise ValueError('reference completion contract')
    expected_names={'plan.json','history.json','environment.json','accounting.json','chunks.jsonl','complete.json'}
    if {p.name for p in root.iterdir()}!=expected_names|{f'chunk-{i:08d}.bin' for i in range(report['chunks'])}:
        raise ValueError('reference inventory')
    for path in root.iterdir(): _plain(path)
    for name,key in (('plan.json','plan'),('history.json','history'),('environment.json','environment'),('accounting.json','accounting'),('chunks.jsonl','index')):
        entry=_file_hash(root/name)
        if report.get(key)!=dict(size=entry['bytes'],sha256=entry['sha256']): raise ValueError('reference payload pin')
    environment=_json(root/'environment.json',131072)
    if (set(environment)!={'schema','scope','runtime','sources','source_commit_correspondence','runtime_approval'}
            or environment['schema']!='hashlab-e002-kernel-engineering-environment-v1'
            or environment['scope']!='engineering-only' or environment['runtime_approval']!='not-claimed'
            or environment['source_commit_correspondence']!='unqualified;engineering-working-copy'):
        raise ValueError('reference environment scope')
    names=[]
    for source in environment['sources']:
        if type(source) is not dict or set(source)!={'path','size','sha256'}:
            raise ValueError('reference source inventory shape')
        name=source['path']
        if type(name) is not str or not name.startswith('src/hashlab/') or '..' in name or '\\' in name:
            raise ValueError('reference source path')
        names.append(name)
        entry=_file_hash(Path(repository_root)/name)
        if dict(size=entry['bytes'],sha256=entry['sha256'])!={key:source[key] for key in ('size','sha256')}:
            raise ValueError('reference observed source bytes')
    expected_sources=sorted(['src/hashlab/'+p.relative_to(Path(repository_root)/'src/hashlab').as_posix()
        for p in (Path(repository_root)/'src/hashlab').rglob('*.py')]
        + ['src/hashlab/experiments/e001_contract.json'])
    if names!=expected_sources: raise ValueError('reference complete source inventory')
    rt=environment['runtime']
    if (type(rt) is not dict or set(rt)!={'python_version','platform','interpreter_sha256','dependencies'}
            or type(rt['python_version']) is not str or not rt['python_version'].startswith('CPython ')
            or type(rt['platform']) is not str or not rt['platform']
            or type(rt['interpreter_sha256']) is not str or len(rt['interpreter_sha256'])!=64
            or type(rt['dependencies']) is not list or not rt['dependencies']):
        raise ValueError('reference runtime binding')
    plan=dict(schema='hashlab-e002-kernel-engineering-plan-v1',scope='engineering-only',
              fixture=integration.spec(),evidence_format='hashlab-e002-kernel-chunks-v1',confirmatory_complete=False,qa2=False)
    if (root/'plan.json').read_bytes()!=encode(plan): raise ValueError('reference fixed plan')
    excluded,_=arms.load_history(audit_root,repository_root)
    history,identity,historical_count=controls.load_history(audit_root,repository_root)
    summary=dict(identity,historical_occurrences=historical_count,distinct_inverse_skip_indices=len(history),
                 complete_occurrence_evidence=True,permutation_key_hex=controls.keys()[0].hex())
    if (root/'history.json').read_bytes()!=encode(summary): raise ValueError('reference history')
    prefixes={arms.prefix(i) for i in range(3000)}
    if len(prefixes)!=3000: raise ValueError('reference prefixes')
    expected=integration.expected_attempts(excluded,history,prefixes)
    accounting=arms.empty_accounting();streams={(r['arm'],r['stage']):r for r in accounting['streams']}
    rejected={a:0 for a in _ARMS};evaluations=blocks=successes=attempted=0
    for row in decode_chunks(root,report):
        attempt=next(expected,None)
        if attempt is None: raise ValueError('reference extra attempt')
        src=attempt.get('source_index',attempt.get('raw_index'))
        if attempt['arm']=='A2': src=attempt['cluster']*10000+attempt['accepted_index']
        anticipated=dict(arm=attempt['arm'],stage=attempt['stage'],candidate_hex=attempt['candidate_hex'],
            accepted_index=attempt['accepted_index'],source_index=src,population_rank=attempt.get('population_rank'),
            byte_offset=attempt.get('byte_offset'),cluster=attempt.get('cluster'),reasons=attempt['reasons'])
        if {k:v for k,v in row.items() if k not in ('raw','effective')}!=anticipated:
            raise ValueError('reference candidate/source/rejection/stage mismatch')
        attempted+=1
        if attempt['reasons']: rejected[attempt['arm']]+=1;continue
        raw=bytes.fromhex(attempt['candidate_hex']);digest=sha256(raw).digest()
        mode=attempt['arm'] if not attempt['arm'].startswith('A') else 'N1'
        effective=bytes.fromhex(controls.transform(mode,digest)['effective_digest_hex'])
        if row['raw']!=digest or row['effective']!=effective: raise ValueError('reference digest/outcome mismatch')
        target=int.from_bytes(effective,'big')<2**248
        r=streams[attempt['arm'],attempt['stage']];r['trials']+=1;r['successes']+=target
        r['first_byte'][effective[0]]+=1;r['last_byte'][effective[-1]]+=1
        r['leading_zero_bits'][256-int.from_bytes(effective,'big').bit_length()]+=1
        if attempt.get('cluster') is not None:
            j=attempt['cluster']%1500;r['cluster_trials'][j]+=1;r['cluster_successes'][j]+=target
        if attempt['arm']=='A3':
            j=int.from_bytes(raw,'big').bit_count()-1;r['weight_trials'][j]+=1;r['weight_successes'][j]+=target
        evaluations+=1;blocks+=(len(raw)+72)//64;successes+=target
    if next(expected,None) is not None or (evaluations,blocks)!=(206,274): raise ValueError('reference missing evaluations')
    if (root/'accounting.json').read_bytes()!=encode(accounting): raise ValueError('reference measured accounting')
    exact=dict(schema='hashlab-e002-kernel-completion-v1',scope='engineering-only',
        format='hashlab-e002-kernel-chunks-v1',plan_sha256=sha256(encode(plan)).hexdigest(),
        confirmatory_complete=False,qa2=False,evaluations=evaluations,compression_blocks=blocks,
        successes=successes,rejections=rejected,chunks=report['chunks'],attempts=attempted,
        **{k:report[k] for k in ('index','plan','history','environment','accounting')})
    if encode(report)!=encode(exact): raise ValueError('reference false completion claims')
    return dict(scope='engineering-only',verification='independent-full-bounded-regeneration-and-rehash',
                evaluations=evaluations,compression_blocks=blocks,attempts=attempted,
                confirmatory_complete=False,qa2=False)
