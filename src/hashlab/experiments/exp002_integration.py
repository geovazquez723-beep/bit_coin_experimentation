"""E002-I3 fixed unified fixture. No production, QA2 or seed-selection entry point."""
from hashlib import sha256
from pathlib import Path
import json
import os

from hashlab.hashing.sha256 import SHA256Engine
from .exp002 import a2_prefix, a1_value, HammingPopulation, in_a1, in_a3
from .exp002_s14 import load_s14
from .exp002_synthetic import fixture_candidates as arm_candidates, fixture_spec as arm_spec
from .exp002_i2_synthetic import fixture_inputs as control_inputs, fixture_spec as control_spec
from .exp002_controls import (ControlGeometry, PermutationControls, N2Controls, ControlEngine, accepted_record)
from .exp002_foundation import (Accumulator, canonical, validate_accounting, validate_success_records)
from .exp002_provenance import inventory
from .exp002_journal import durable_create, require_plain
from .exp002_integration_statistics import statistical_inputs, infer_synthetic_counts, disclosure


def fixture_spec():
    return dict(schema='hashlab-e002-i3-fixture-v1',scope='synthetic-engineering',
        arms=arm_spec(),controls=control_spec(),candidate_evaluations=206,compression_blocks=274,
        n2_membership='all-3000-prefixes-under-I1-A2-fixture-key',attempt_budget=320,
        confirmatory_complete=False,qa2=False)


def count_fixtures(repository):
    """Explicit artificial sufficient statistics, separate from measured records."""
    raw=(Path(repository)/'tests/fixtures/exp002-secondary-v2-reference.json').read_bytes().replace(b'\r\n',b'\n')
    if sha256(raw).hexdigest()!='3b3931f43705e5dcd787db71dc088f0bc0eaadcb44ddcf87aa52a58553d151db':
        raise ValueError('accepted count-fixture source pin')
    source=json.loads(raw)
    cases=[]
    def set_successes(row,k):
        row['successes']=k
        for key,size in (('first_byte',256),('last_byte',256),('leading_zero_bits',257)):
            row[key]=[0]*size
            row[key][0 if key!='leading_zero_bits' else 256]=k
            row[key][255 if key!='leading_zero_bits' else 0]=row['trials']-k
        if row['weight_trials'] is not None:
            cumulative=0;before=0;successes=[]
            for n in row['weight_trials']:
                cumulative+=n
                now=cumulative*k//row['trials'];successes.append(now-before);before=now
            row['weight_successes']=successes
    for family in source['full_families']:
        data=json.loads(json.dumps(family['accounting']))
        for row in data['streams']:
            if row['arm'].startswith('P'):
                set_successes(row,{'P1':1000,'P2+':60000,'P2-':57000}[row['arm']])
        cases.append(dict(name=family['name'],accounting=data))
    changed=json.loads(json.dumps(cases[0]['accounting']))
    for row in changed['streams']:
        if row['arm'] in ('A1','N1'):set_successes(row,61000)
        if row['arm']=='A3':set_successes(row,56000)
    cases.append(dict(name='replicated-signals-and-null-gate-failure',accounting=changed))
    changed=json.loads(json.dumps(cases[0]['accounting']))
    for row in changed['streams']:
        if row['arm']=='P1':set_successes(row,869)
    cases.append(dict(name='positive-gate-failure',accounting=changed))
    changed=json.loads(json.dumps(cases[0]['accounting']))
    for row in changed['streams']:
        if not row['arm'].startswith('P'):
            set_successes(row,0)
            if row['cluster_successes'] is not None:row['cluster_successes']=[0]*1500
    cases.append(dict(name='not-testable-secondary-zero-successes',accounting=changed))
    return dict(schema='hashlab-e002-i3-count-fixtures-v1',scope='synthetic-full-geometry-counts',
                measured_sha256_observations=False,candidate_evaluations=0,
                source_sha256=sha256(raw).hexdigest(),cases=cases)


def evaluate_record(record, engine):
    """One base evaluation for every arm/control; effective digest drives E3."""
    raw=engine.digest(bytes.fromhex(record.candidate_hex))
    mode=record.arm if not record.arm.startswith('A') else 'N1'
    result=ControlEngine(mode).transform(raw)
    if record.arm.startswith('A'):result['mode']='identity'
    return result


def eligibility(record, attempt, history, permutation, inverse, prefixes):
    raw=bytes.fromhex(record.candidate_hex);value=int.from_bytes(raw,'big')
    if record.arm=='A1':
        rank=attempt['population_rank']
        if type(rank) is not int or not 0<=rank<256 or a1_value(rank)!=raw:
            raise ValueError('A1 fixture eligibility')
    elif record.arm=='A2':
        if record.cluster not in (0,1500) or raw != prefixes[record.cluster]+record.index.to_bytes(4,'little') or record.index>=32:
            raise ValueError('A2 fixture eligibility')
    elif record.arm=='A3':
        rank=HammingPopulation().rank(value)
        if rank!=attempt['population_rank'] or rank in history.exclusions.ranks or not 0<=rank<4096:
            raise ValueError('A3 fixture eligibility')
    elif record.arm=='N2':
        if raw[:76] in prefixes and int.from_bytes(raw[76:],'little')<10000:
            raise ValueError('unhandled N2 A2 overlap')
    else:
        source=attempt['source_index']
        if permutation.forward(source)!=value or in_a1(raw) or in_a3(raw):
            raise ValueError('control structural/source eligibility')
    if len(raw)==8 and permutation.inverse(value) in inverse.indices:
        raise ValueError('unhandled historical overlap')


def run_fixture(destination, *, audit_root, repository_root):
    root=Path(destination).absolute();repo=Path(repository_root).resolve()
    if root.resolve().is_relative_to(repo/'results') or root.resolve().is_relative_to(Path(audit_root).resolve()):
        raise ValueError('output beneath retained results')
    for parent in root.parents:
        require_plain(parent,directory=True)
        if (parent/'manifest.sha256').exists() or (parent/'complete.json').exists():
            raise ValueError('output beneath completed evidence')
    history=load_s14(audit_root,repo)
    permutation,inverse,key,_=control_inputs(audit_root,repo)
    prefixes=tuple(a2_prefix(b'E002-I1!',j) for j in range(3000))
    prp=PermutationControls(permutation,inverse,ControlGeometry('experiment-002-kat',2,2,2))
    n2=N2Controls(key,prefixes,ControlGeometry('experiment-002-kat',2,2,2))
    def attempts():
        for record,rank in arm_candidates(history):
            yield dict(arm=record.arm,stage=record.stage,candidate_hex=record.candidate_hex,
                accepted_index=record.index,cluster=record.cluster,population_rank=rank,reasons=[])
        yield from prp.n1();yield from n2.attempts();yield from prp.positives()
    root.mkdir()
    durable_create(root/'fixture.json',canonical(fixture_spec()))
    durable_create(root/'history.json',canonical(inverse.summary()))
    count=blocks=attempt_count=0;engine=SHA256Engine()
    with (root/'records.jsonl').open('xb') as records,(root/'attempts.jsonl').open('xb') as audit,(root/'successes.jsonl').open('xb') as successes:
        accumulator=Accumulator(success_sink=lambda raw:successes.write(raw+b'\n'))
        for attempt in attempts():
            if attempt_count>=320:raise ValueError('attempt budget exceeded')
            audit.write(canonical(dict(sequence=attempt_count,**attempt))+b'\n');attempt_count+=1
            if attempt['reasons']:continue
            if count>=206:raise ValueError('candidate hash budget exceeded')
            record=accepted_record(attempt)
            eligibility(record,attempt,history,permutation,inverse,prefixes)
            result=evaluate_record(record,engine)
            accumulator.add(record,bytes.fromhex(result['effective_digest_hex']))
            records.write(canonical(dict(sequence=count,attempt_sequence=attempt_count-1,candidate=record.to_dict(),**result))+b'\n')
            count+=1;blocks+=(len(bytes.fromhex(record.candidate_hex))+72)//64
        for stream in (records,audit,successes):stream.flush();os.fsync(stream.fileno())
    accounting=accumulator.snapshot();validate_accounting(accounting)
    expected={(a,s):32 if a.startswith('A') else 2 for a in ('A1','A2','A3','N1','N2') for s in ('D','V')}
    expected.update({(a,'C'):2 for a in ('P1','P2+','P2-')})
    if count!=206 or blocks!=274 or prp.failed or n2.failed or any(r['trials']!=expected[r['arm'],r['stage']] for r in accounting['streams']):
        raise ValueError('incomplete unified fixture')
    with (root/'successes.jsonl').open('rb') as source:validate_success_records((line.rstrip(b'\n') for line in source),accounting)
    durable_create(root/'accounting.json',canonical(accounting))
    durable_create(root/'statistical-inputs.json',canonical(statistical_inputs(accounting)))
    durable_create(root/'rejections.json',canonical(dict(prp.counts,N2=n2.counts)))
    artificial=count_fixtures(repo)
    durable_create(root/'count-fixtures.json',canonical(artificial))
    results=[dict(name=f['name'],inputs=statistical_inputs(f['accounting']),
                  results=infer_synthetic_counts(f['accounting'],scope=artificial['scope'])) for f in artificial['cases']]
    durable_create(root/'synthetic-inference.json',canonical(dict(scope=artificial['scope'],cases=results)))
    durable_create(root/'disclosure.json',canonical(disclosure('synthetic-engineering')))
    report=dict(schema='hashlab-e002-i3-complete-v1',scope='synthetic-engineering',synthetic_complete=True,
        confirmatory_complete=False,qa2=False,records=count,attempts=attempt_count,candidate_compression_blocks=blocks,
        measured_inference=False,synthetic_count_cases=len(results),files=inventory(root))
    durable_create(root/'complete.json',canonical(report))
    return sha256(canonical(report)).hexdigest()
