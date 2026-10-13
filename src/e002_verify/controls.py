"""Independent, stdlib-only I2 reference; no HASHLAB imports.

Reuses only I1's independent evidence authentication and empty histogram shape.
All control calculations, replay, rejection decisions and counts are separate.
Full retained history is read, never regenerated. Bijection makes distinct raw
history cardinality equal distinct inverse-index cardinality; only inverses
relevant to this bounded replay need evaluation in the reference.
"""
from hashlib import sha256, blake2b
from pathlib import Path
import json
import re
import struct

from .core import load_history as authenticate_history, empty_accounting, encode, ACTIVE, SCIENTIFIC
from e001_stream_verify.streaming import _plain, _file_hash, _json

T = 1 << 248
ROW = struct.Struct('>BBII8sB')


def keys():
    result = []
    for arm, purpose, width, endian in [('N1-feistel64-w8','permutation-key-v1',8,'little'),
                                       ('N2-random-bytes-w80','stream-key-v1',16,'big')]:
        material = f'hashlab-seed-v1|0|experiment-002-kat|{arm}|{purpose}'.encode('ascii')
        seed = int.from_bytes(sha256(material).digest()[:8], 'big')
        result.append(seed.to_bytes(width, endian))
    return tuple(result)


def round_value(key, r, half):
    message = b'hashlab-exp002-feistel-round-v1' + struct.pack('>BI', r, half)
    return struct.unpack('>I', blake2b(message, key=key).digest()[:4])[0]


def permutation(value, *, reverse=False, key=None):
    if key is None:
        key = keys()[0]
    halves = [value // 2**32, value % 2**32]
    for r in (range(5,-1,-1) if reverse else range(6)):
        if reverse:
            halves = [halves[1] ^ round_value(key,r,halves[0]), halves[0]]
        else:
            halves = [halves[1], halves[0] ^ round_value(key,r,halves[1])]
    return halves[0]*2**32 + halves[1]


def random_candidate(index, key=None):
    if key is None:
        key = keys()[1]
    begin, end = 80*index, 80*(index+1)
    result = bytearray()
    for counter in range(begin//64, (end-1)//64+1):
        block = blake2b(struct.pack('>QQ',counter>>64,counter & (2**64-1)),key=key).digest()
        result.extend(block[max(0,begin-counter*64):min(64,end-counter*64)])
    return bytes(result)


def prefixes():
    msg = b'hashlab-seed-v1|0|experiment-002-kat|A2-prefix-nonce-w80|prefix-key-v1'
    key = struct.pack('<Q',int.from_bytes(sha256(msg).digest()[:8],'big'))
    result = set()
    for j in range(3000):
        blocks = [blake2b(b'hashlab-exp002-prefix'+struct.pack('<II',j,c),key=key).digest() for c in (0,1)]
        result.add(blocks[0]+blocks[1][:12])
    if len(result) != 3000:
        raise ValueError('reference duplicate A2 prefixes')
    return result


def transform(mode, raw):
    threshold = {'N1':0,'N2':0,'P1':4210752,'P2+':336860,'P2-':85899345}[mode]
    value = int.from_bytes(raw,'big')
    u = struct.unpack('>I',raw[28:])[0]
    change = (u < threshold and (value < T if mode=='P2-' else value >= T))
    effective = value
    if change:
        effective = value+T if mode=='P2-' else value % T
    return dict(mode=mode,threshold_u32=threshold,transformed=change,
                raw_digest_hex=raw.hex(),effective_digest_hex=effective.to_bytes(32,'big').hex(),
                success=effective < T)


_HISTORY = None


def load_history(audit_root, repository_root):
    """Independent pins authenticate the entire retained file before caching."""
    global _HISTORY
    _, identity = authenticate_history(audit_root, repository_root)
    root = Path(audit_root)/'producer'
    pin = _file_hash(root/'occurrences.bin')['sha256']
    identity = identity | dict(occurrences_sha256=pin)
    if _HISTORY is not None:
        return _HISTORY[0], identity, _HISTORY[1]
    values, count = set(), 0
    plan = _json(root/'plan.json')
    with (root/'occurrences.bin').open('rb') as source:
        for stream in plan['streams']:
            for i in range(stream['attempts']):
                chunk = source.read(19)
                if len(chunk) != 19:
                    raise ValueError('reference truncated history')
                g,p,index,enum,value,outcome = ROW.unpack(chunk)
                if (g,p,index,enum,outcome) != (stream['ordinal'],stream['phase'],i,stream['start_index']+i,0):
                    raise ValueError('reference retained history semantics')
                values.add(int.from_bytes(value,'big'))
                count += 1
        if source.read(1) or count != 7000000:
            raise ValueError('reference complete historical occurrences required')
    _HISTORY = frozenset(values), count
    return _HISTORY[0], identity, count


def spec():
    return dict(schema='hashlab-e002-i2-fixture-v1',scope='synthetic-only',active_protocol=ACTIVE,
                scientific_baseline=SCIENTIFIC,domain='experiment-002-kat',engineering_input=0,
                per_stage=2,p1=2,p2=2,a2_prefixes=3000,target=str(T),n1_stop=30999999,
                p_start=str(2**63),confirmatory_complete=False,qa2=False,
                n2_uniqueness='probabilistic-not-verified',candidate_hash_budget=14)


def replay(history, a2_prefixes):
    """Yield all expected attempts, including rejections, independently."""
    cursors = dict(N1=0,P=2**63)
    for arm, stages in [('N1',('D','V')),('N2',('D','V')),('P1',('C',)),('P2+',('C',)),('P2-',('C',))]:
        for stage in stages:
            local = 0
            while local < 2:
                if arm == 'N2':
                    index = cursors.get('N2',0)
                    cursors['N2'] = index+1
                    raw = random_candidate(index)
                    reject = raw[:76] in a2_prefixes and struct.unpack('<I',raw[76:])[0] < 10000
                    attempt = dict(arm=arm,stage=stage,raw_index=index,byte_offset=80*index,
                        candidate_hex=raw.hex(),accepted_index=None if reject else local,
                        cluster=None if reject else (1500 if stage=='V' else 0),reasons=['A2'] if reject else [])
                else:
                    kind = 'N1' if arm=='N1' else 'P'
                    index = cursors[kind]
                    if index >= (30999999 if kind=='N1' else 2**64):
                        raise ValueError('reference index exhaustion')
                    cursors[kind] += 1
                    value = permutation(index)
                    raw = struct.pack('>Q',value)
                    reasons = []
                    if 2**20 <= value < 2**32:
                        reasons.append('C1')
                    if value//2**32 and value.bit_count() <= 6:
                        reasons.append('C3')
                    if value in history:
                        if permutation(value,reverse=True) != index:
                            raise ValueError('reference inverse overlap mismatch')
                        reasons.append('E001')
                    attempt = dict(arm=arm,stage=stage,source_index=index,candidate_hex=raw.hex(),
                                   accepted_index=None if reasons else local,reasons=reasons)
                if not attempt['reasons']:
                    local += 1
                yield attempt


def verify_fixture(root, *, complete_sha256, audit_root, repository_root):
    if type(complete_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',complete_sha256):
        raise ValueError('reference external completion pin required')
    root = Path(root)
    _plain(root,directory=True)
    names = {'fixture.json','history.json','attempts.jsonl','records.jsonl','accounting.json','rejections.json','complete.json'}
    if {p.name for p in root.iterdir()} != names:
        raise ValueError('reference missing/extra fixture evidence')
    for p in root.iterdir():
        _plain(p)
        if p.stat().st_size > (2000000 if p.name=='accounting.json' else 65536):
            raise ValueError('reference evidence size cap')
    if _file_hash(root/'complete.json')['sha256'] != complete_sha256:
        raise ValueError('reference completion pin mismatch')
    report = _json(root/'complete.json')
    inventory = {name:dict(size=entry['bytes'],sha256=entry['sha256'])
                 for name in sorted(names-{'complete.json'}) for entry in [_file_hash(root/name)]}
    if type(report.get('attempts')) is not int or not 14 <= report['attempts'] <= 128:
        raise ValueError('reference attempt budget')
    expected = dict(schema='hashlab-e002-i2-complete-v1',scope='synthetic-only',synthetic_complete=True,
        confirmatory_complete=False,qa2=False,records=14,attempts=report['attempts'],
        candidate_compression_blocks=18,files=inventory)
    if (root/'complete.json').read_bytes() != encode(expected):
        raise ValueError('reference completion claims/inventory')
    history, identity, historical_count = load_history(audit_root,repository_root)
    summary = dict(identity,historical_occurrences=historical_count,
                   distinct_inverse_skip_indices=len(history),complete_occurrence_evidence=True,
                   permutation_key_hex=keys()[0].hex())
    if (root/'fixture.json').read_bytes() != encode(spec()) or (root/'history.json').read_bytes() != encode(summary):
        raise ValueError('reference fixture/history binding')
    accounting = empty_accounting()
    streams = {(r['arm'],r['stage']):r for r in accounting['streams']}
    counts = {a:dict(attempted=0,rejected=0,accepted=0,reasons=dict(C1=0,C3=0,E001=0,A2=0))
              for a in ('N1','P1','P2+','P2-','N2')}
    count = blocks = attempts = 0
    with (root/'attempts.jsonl').open('rb') as audit, (root/'records.jsonl').open('rb') as records:
        for sequence, attempt in enumerate(replay(history,prefixes())):
            if sequence >= 128:
                raise ValueError('reference attempt budget')
            if audit.readline(4097) != encode(dict(sequence=sequence,**attempt))+b'\n':
                raise ValueError('reference attempt/rejection disagreement')
            attempts += 1
            stats = counts[attempt['arm']]
            stats['attempted'] += 1
            stats['rejected' if attempt['reasons'] else 'accepted'] += 1
            for reason in attempt['reasons']:
                stats['reasons'][reason] += 1
            if attempt['reasons']:
                continue
            candidate = dict(arm=attempt['arm'],stage=attempt['stage'],index=attempt['accepted_index'],
                candidate_hex=attempt['candidate_hex'],cluster=attempt.get('cluster'),schema='hashlab-exp002-candidate-v1')
            raw = bytes.fromhex(candidate['candidate_hex'])
            digest = sha256(raw).digest()  # One independent candidate evaluation.
            result = transform(candidate['arm'],digest)
            expected_row = dict(sequence=count,candidate=candidate,attempt_sequence=sequence,**result)
            if records.readline(4097) != encode(expected_row)+b'\n':
                raise ValueError('reference candidate/raw/effective digest disagreement')
            effective = bytes.fromhex(result['effective_digest_hex'])
            row = streams[candidate['arm'],candidate['stage']]
            row['trials'] += 1
            row['successes'] += result['success']
            row['first_byte'][effective[0]] += 1
            row['last_byte'][effective[-1]] += 1
            row['leading_zero_bits'][256-int.from_bytes(effective,'big').bit_length()] += 1
            if candidate['arm']=='N2':
                cluster = candidate['cluster'] % 1500
                row['cluster_trials'][cluster] += 1
                row['cluster_successes'][cluster] += result['success']
            count += 1
            blocks += (len(raw)+72)//64
        if audit.read(1) or records.read(1):
            raise ValueError('reference extra fixture rows')
    if count != 14 or blocks != 18 or attempts != report['attempts']:
        raise ValueError('reference incomplete fixture')
    if (root/'accounting.json').read_bytes() != encode(accounting):
        raise ValueError('reference accounting disagreement')
    if (root/'rejections.json').read_bytes() != encode(counts):
        raise ValueError('reference rejection accounting disagreement')
    return dict(schema='hashlab-e002-i2-verified-v1',scope='synthetic-only',
                verification='independent-complete-bounded-fixture',producer_sha256=complete_sha256,
                records=count,rehash_compression_blocks=blocks,attempts=attempts,
                historical_occurrences=historical_count,distinct_inverse_skip_indices=len(history),
                confirmatory_complete=False,qa2=False,
                successes={a+':'+s:streams[a,s]['successes'] for a,s in streams if a in counts})
