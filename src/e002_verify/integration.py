"""Independent complete I3 fixture verifier. No HASHLAB imports or execution.

Reuses accepted independent I1/I2 reconstruction primitives; one combined replay
rehashes all 206 candidates and independently constructs all evidence/counts.
"""
from pathlib import Path
from hashlib import sha256
import json
import re

from . import core as arms, controls
from . import integration_statistics as stats
from .core import encode, empty_accounting, _plain, _file_hash


def spec():
    return dict(schema='hashlab-e002-i3-fixture-v1',scope='synthetic-engineering',
        arms=arms.spec(),controls=controls.spec(),candidate_evaluations=206,compression_blocks=274,
        n2_membership='all-3000-prefixes-under-I1-A2-fixture-key',attempt_budget=320,
        confirmatory_complete=False,qa2=False)


def read_json(path):
    def pairs(entries):
        value={}
        for key,item in entries:
            if key in value:raise ValueError('reference duplicate field')
            value[key]=item
        return value
    def invalid(*args):raise ValueError('reference nonfinite JSON')
    try:
        raw=path.read_bytes();value=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    except (UnicodeError,json.JSONDecodeError):raise ValueError('reference invalid JSON') from None
    if encode(value)!=raw:raise ValueError('reference noncanonical JSON')
    return value


def expected_attempts(excluded,history,prefixes):
    for record,rank in arms.candidates(excluded):
        yield dict(arm=record['arm'],stage=record['stage'],candidate_hex=record['candidate_hex'],
            accepted_index=record['index'],cluster=record['cluster'],population_rank=rank,reasons=[])
    yield from controls.replay(history,prefixes)


def verify_fixture(root, *, complete_sha256, audit_root, repository_root):
    if type(complete_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',complete_sha256):
        raise ValueError('reference external completion pin required')
    root=Path(root);_plain(root,directory=True)
    names={'fixture.json','history.json','attempts.jsonl','records.jsonl','successes.jsonl',
        'accounting.json','statistical-inputs.json','rejections.json','count-fixtures.json',
        'synthetic-inference.json','disclosure.json','complete.json'}
    if {p.name for p in root.iterdir()}!=names:raise ValueError('reference missing/extra evidence')
    for p in root.iterdir():
        _plain(p)
        if p.stat().st_size>2000000:raise ValueError('reference evidence cap')
    if _file_hash(root/'complete.json')['sha256']!=complete_sha256:raise ValueError('reference completion pin')
    report=read_json(root/'complete.json')
    count_attempts=report.get('attempts')
    if type(count_attempts) is not int or not 206<=count_attempts<=320:raise ValueError('reference attempt budget')
    inventory={name:dict(size=entry['bytes'],sha256=entry['sha256']) for name in sorted(names-{'complete.json'}) for entry in [_file_hash(root/name)]}
    expected=dict(schema='hashlab-e002-i3-complete-v1',scope='synthetic-engineering',synthetic_complete=True,
        confirmatory_complete=False,qa2=False,records=206,attempts=count_attempts,candidate_compression_blocks=274,
        measured_inference=False,synthetic_count_cases=5,files=inventory)
    if encode(expected)!=(root/'complete.json').read_bytes():raise ValueError('reference completion claims/inventory')
    excluded,_=arms.load_history(audit_root,repository_root)
    history,identity,historical_count=controls.load_history(audit_root,repository_root)
    summary=dict(identity,historical_occurrences=historical_count,distinct_inverse_skip_indices=len(history),
        complete_occurrence_evidence=True,permutation_key_hex=controls.keys()[0].hex())
    if (root/'history.json').read_bytes()!=encode(summary) or (root/'fixture.json').read_bytes()!=encode(spec()):
        raise ValueError('reference history/specification binding')
    accounting=empty_accounting();streams={(r['arm'],r['stage']):r for r in accounting['streams']}
    rejected={a:dict(attempted=0,rejected=0,accepted=0,reasons=dict(C1=0,C3=0,E001=0,A2=0)) for a in ('N1','P1','P2+','P2-','N2')}
    prefixes={arms.prefix(j) for j in range(3000)}
    if len(prefixes)!=3000:raise ValueError('reference A2 prefix uniqueness')
    count=blocks=attempts=success_count=0
    with (root/'attempts.jsonl').open('rb') as audit,(root/'records.jsonl').open('rb') as records,(root/'successes.jsonl').open('rb') as successes:
        for sequence,attempt in enumerate(expected_attempts(excluded,history,prefixes)):
            if sequence>=320:raise ValueError('reference attempt budget')
            if audit.readline(4097)!=encode(dict(sequence=sequence,**attempt))+b'\n':
                raise ValueError('reference attempt/eligibility/source disagreement')
            attempts+=1
            if attempt['arm'] in rejected:
                row=rejected[attempt['arm']];row['attempted']+=1
                row['rejected' if attempt['reasons'] else 'accepted']+=1
                for reason in attempt['reasons']:row['reasons'][reason]+=1
            if attempt['reasons']:continue
            candidate=dict(arm=attempt['arm'],stage=attempt['stage'],index=attempt['accepted_index'],
                candidate_hex=attempt['candidate_hex'],cluster=attempt.get('cluster'),schema='hashlab-exp002-candidate-v1')
            raw=bytes.fromhex(candidate['candidate_hex']);value=int.from_bytes(raw,'big')
            if len(raw)==8 and value in history:raise ValueError('reference historical overlap')
            if candidate['arm']=='A3' and arms.historical_rank(value) in excluded:raise ValueError('reference A3 overlap')
            mode=candidate['arm'] if not candidate['arm'].startswith('A') else 'N1'
            result=controls.transform(mode,sha256(raw).digest())
            if candidate['arm'].startswith('A'):result['mode']='identity'
            expected_row=dict(sequence=count,attempt_sequence=sequence,candidate=candidate,**result)
            if records.readline(4097)!=encode(expected_row)+b'\n':raise ValueError('reference candidate/digest/transform disagreement')
            effective=bytes.fromhex(result['effective_digest_hex'])
            if result['success']:
                success=dict(schema='hashlab-exp002-success-v1',candidate=candidate,digest_hex=effective.hex())
                if successes.readline(4097)!=encode(success)+b'\n':raise ValueError('reference effective success evidence')
                success_count+=1
            row=streams[candidate['arm'],candidate['stage']];row['trials']+=1;row['successes']+=result['success']
            row['first_byte'][effective[0]]+=1;row['last_byte'][effective[-1]]+=1
            row['leading_zero_bits'][256-int.from_bytes(effective,'big').bit_length()]+=1
            if candidate['cluster'] is not None:
                cluster=candidate['cluster']%1500;row['cluster_trials'][cluster]+=1;row['cluster_successes'][cluster]+=result['success']
            if candidate['arm']=='A3':
                weight=value.bit_count()-1;row['weight_trials'][weight]+=1;row['weight_successes'][weight]+=result['success']
            count+=1;blocks+=(len(raw)+72)//64
        if audit.read(1) or records.read(1) or successes.read(1):raise ValueError('reference extra rows')
    if (count,blocks,attempts)!=(206,274,count_attempts):raise ValueError('reference incomplete geometry')
    for name,value in [('accounting.json',accounting),('statistical-inputs.json',stats.inputs(accounting)),('rejections.json',rejected),
        ('disclosure.json',dict(scope='synthetic-engineering',validation_diagnostics_allowed=True,confirmatory_complete=False,production_blinded=False))]:
        if (root/name).read_bytes()!=encode(value):raise ValueError('reference '+name+' disagreement')
    artificial=stats.count_fixtures(repository_root)
    if (root/'count-fixtures.json').read_bytes()!=encode(artificial):raise ValueError('reference artificial count binding')
    inference=read_json(root/'synthetic-inference.json')
    if set(inference)!={'scope','cases'} or inference['scope']!=artificial['scope'] or len(inference['cases'])!=5:
        raise ValueError('reference synthetic inference family')
    for f,result in zip(artificial['cases'],inference['cases']):
        if set(result)!={'name','inputs','results'} or result['name']!=f['name'] or encode(result['inputs'])!=encode(stats.inputs(f['accounting'])):
            raise ValueError('reference statistical input construction')
        stats.verify_inference(f['accounting'],result['results'])
    return dict(schema='hashlab-e002-i3-verified-v1',scope='synthetic-engineering',
        verification='independent-complete-unified-fixture',producer_sha256=complete_sha256,
        records=count,attempts=attempts,rehash_compression_blocks=blocks,success_records=success_count,
        synthetic_count_cases=5,secondary_slots_per_case=36,confirmatory_complete=False,qa2=False,
        successes={a+':'+s:r['successes'] for (a,s),r in streams.items()})
