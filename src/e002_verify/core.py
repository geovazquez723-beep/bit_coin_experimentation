"""Separately specified stdlib reference for the one fixed I1 fixture.

No producer candidate generation, record parser, deduplication, hash engine or
accounting imports. Dense A1 Method A uses exact Fraction survival probabilities
and the specified MT19937 bit draws. A3 uses binary-search combinatorial unrank
and integer Algorithm S. SHA-256 is hashlib.sha256(raw candidate bytes), with
big-endian integer comparison <2**248. Shared Python/hashlib remain limitations.
"""
from fractions import Fraction
from hashlib import sha256, blake2b
from math import comb
from pathlib import Path
import json
import random
import re
import struct

from e001_stream_verify.streaming import PINS, rank as historical_rank, _plain, _json, _file_hash

PRODUCER = 'c4fe9ba89f1c4390c5300a7a5512aaf20f2bc6fcbbfcbe2292b1af564f70ddc1'
VERIFIER = '3ed80c4d663614fb5245902f88037573776889dc3c3afc47e32018add11d42eb'
EXCLUSION = '7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c'
SCIENTIFIC = 'proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1'
ACTIVE = SCIENTIFIC.replace('revision-8', 'revision-9')


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def spec():
    return dict(schema='hashlab-e002-i1-fixture-v1', scope='synthetic-only',
                active_protocol=ACTIVE, scientific_baseline=SCIENTIFIC,
                target=str(2**248), per_arm_stage=32, a1_size=256,
                a3_rank_stop=4096, a1_selection_seed=101, a1_stage_seed=102,
                a3_selection_seed=201, a3_stage_seed=202,
                a2_fixture_key_hex=b'E002-I1!'.hex(), a2_clusters=[0,1500],
                a2_nonce_stop=32, confirmatory_complete=False, qa2=False)


def load_history(audit_root, repository_root):
    """Read retained bytes only, authenticated before reference construction."""
    root, repo = Path(audit_root), Path(repository_root)
    for p in (root, root/'producer', root/'verifier'):
        _plain(p, directory=True)
    if {p.name for p in root.iterdir()} != {'producer','verifier'}:
        raise ValueError('reference S1.4 inventory')
    for name, size, pin in (('producer/complete.json',2104,PRODUCER),
                            ('verifier/verified.json',1881,VERIFIER)):
        _plain(root/name)
        if _file_hash(root/name) != dict(bytes=size,sha256=pin):
            raise ValueError('reference S1.4 report pin')
    producer = _json(root/'producer/complete.json')
    verifier = _json(root/'verifier/verified.json')
    files = producer['files']  # Authenticated by the independently retained report pin.
    if {p.name for p in (root/'producer').iterdir()} != set(files)|{'complete.json'}:
        raise ValueError('reference S1.4 producer files')
    if {p.name for p in (root/'verifier').iterdir()} != {'verified.json','reference.sqlite'}:
        raise ValueError('reference S1.4 verifier files')
    for name, inventory in files.items():
        _plain(root/'producer'/name)
        if _file_hash(root/'producer'/name) != inventory:
            raise ValueError('reference retained file hash')
    _plain(root/'verifier/reference.sqlite')
    if _file_hash(root/'verifier/reference.sqlite') != dict(bytes=37789696,
            sha256='e024010e7585a019487fc47c1afcbc22ae1d7c7c497f1fc7e6a9cbf25f31970c'):
        raise ValueError('reference retained database hash')
    plan = _json(root/'producer/plan.json')
    if any(plan[k] != v for k,v in PINS.items()):
        raise ValueError('reference historical identities')
    if (verifier['evidence_report_sha256'] != PRODUCER
            or verifier['verification'] != 'independent-stream-replay'
            or producer['accounting'] != verifier['accounting']
            or producer['accounting'] != plan['sealed_counts']):
        raise ValueError('reference S1.4 agreement')
    sealed = repo/'results/20261011T205056Z-exp001-fc1d75fc'
    _plain(sealed, directory=True)
    _plain(sealed/'manifest.json')
    _plain(sealed/'manifest.sha256')
    if _file_hash(sealed/'manifest.json')['sha256'] != PINS['manifest']:
        raise ValueError('reference original manifest pin')
    if (sealed/'manifest.sha256').read_bytes() != (PINS['manifest']+'  manifest.json\n').encode('ascii'):
        raise ValueError('reference original manifest self-hash')
    manifest = _json(sealed/'manifest.json')
    if {p.name for p in sealed.iterdir()} != set(manifest['files'])|{'manifest.json','manifest.sha256'}:
        raise ValueError('reference sealed inventory')
    for name, entry in manifest['files'].items():
        _plain(sealed/name)
        if _file_hash(sealed/name) != entry:
            raise ValueError('reference original sealed file hash')
    contract_path = repo/'src/hashlab/experiments/e001_contract.json'
    _plain(contract_path)
    if sha256(contract_path.read_bytes().replace(b'\r\n',b'\n')).hexdigest() != PINS['contract']:
        raise ValueError('reference contract pin')
    contract = _json(contract_path)
    if (contract['environment']['git']['revision'] != PINS['source']
            or contract['environment']['git']['dirty']
            or _file_hash(sealed/'config.resolved.json')['sha256'] != PINS['config']):
        raise ValueError('reference source/config identity')
    for name, pin in contract['source_sha256_lf'].items():
        _plain(repo/name)
        if sha256((repo/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() != pin:
            raise ValueError('reference historical source pin')
    pairs = list(struct.iter_unpack('>QQ', (root/'producer/exclusions.bin').read_bytes()))
    values = [v for v,r in pairs]
    ranks = [r for r, in struct.iter_unpack('>Q', (root/'producer/ranks.bin').read_bytes())]
    if (len(values) != 60721 or values != sorted(set(values))
            or len(ranks) != 60721 or ranks != sorted(set(ranks))
            or sorted(historical_rank(v) for v in values) != ranks
            or any(historical_rank(v) != r for v,r in pairs)
            or sha256(b''.join(v.to_bytes(8,'big') for v in values)).hexdigest() != EXCLUSION):
        raise ValueError('reference canonical exclusion values/ranks/digest')
    identity = dict(PINS, producer_sha256=PRODUCER, verifier_sha256=VERIFIER,
                    exclusion_sha256=EXCLUSION, distinct_exclusions=60721)
    return set(ranks), identity


def a1_ranks():
    """Fixed dense fixture only; exact survival inversion, no production sampler."""
    rng = random.Random(101)
    stages = random.Random(102)
    N, n, offset, discovery = 256, 64, 0, 32
    while n:
        if n == N:
            skip = 0
        elif n == 1:
            skip = rng.randrange(N)
        else:
            block = rng.getrandbits(64)
            lower, upper = Fraction(block,2**64), Fraction(block+1,2**64)
            survival = Fraction(1)
            for skip in range(N-n+1):
                survival *= Fraction(N-n-skip,N-skip)
                if lower > survival:
                    break
                if not upper < survival:
                    raise ValueError('reference fixture random interval ambiguity')
        stage = 'D' if stages.randrange(n) < discovery else 'V'
        discovery -= stage == 'D'
        yield stage, offset+skip
        offset += skip+1
        N -= skip+1
        n -= 1


def unrank(index):
    """Independent binary-search colex decoding in the true 64/32/6 class."""
    if type(index) is not int or not 0 <= index < 82128984:
        raise ValueError('reference A3 rank bounds')
    for weight in range(1,7):
        size = comb(64,weight)-comb(32,weight)
        if index < size:
            break
        index -= size
    index += comb(32,weight)
    value, ceiling = 0,64
    for k in range(weight,0,-1):
        lo, hi = k-1,ceiling
        while hi-lo > 1:
            middle = (lo+hi)//2
            if comb(middle,k) <= index:
                lo = middle
            else:
                hi = middle
        value += 2**lo
        index -= comb(lo,k)
        ceiling = lo
    return value


def a3_ranks(excluded):
    rng, stages = random.Random(201), random.Random(202)
    remaining = 4096-len(excluded & set(range(4096)))
    need, discovery = 64,32
    for r in range(4096):
        if not need:
            break
        if r in excluded:
            continue
        if rng.randrange(remaining) < need:
            stage = 'D' if stages.randrange(need) < discovery else 'V'
            discovery -= stage == 'D'
            need -= 1
            yield stage,r
        remaining -= 1
    if need:
        raise ValueError('reference fixture A3 exhausted')


def prefix(cluster):
    blocks = [blake2b(b'hashlab-exp002-prefix'+struct.pack('<II',cluster,counter),
                      key=b'E002-I1!',digest_size=64).digest() for counter in (0,1)]
    return blocks[0]+blocks[1][:12]


def candidates(excluded):
    counters = {(a,s):0 for a in ('A1','A2','A3') for s in ('D','V')}

    def record(a,s,value,rank,cluster=None):
        index = counters[a,s]
        counters[a,s] += 1
        return dict(arm=a,stage=s,index=index,candidate_hex=value.hex(),cluster=cluster,
                    schema='hashlab-exp002-candidate-v1'),rank

    for s,r in a1_ranks():
        yield record('A1',s,struct.pack('>Q',2**20+r),r)
    for cluster,stage in ((0,'D'),(1500,'V')):
        p = prefix(cluster)
        for nonce in range(32):
            yield record('A2',stage,p+struct.pack('<I',nonce),None,cluster)
    for s,r in a3_ranks(excluded):
        yield record('A3',s,struct.pack('>Q',unrank(r)),r)


def empty_accounting():
    rows = []
    for a in ('A1','A2','A3','N1','N2','P1','P2+','P2-'):
        for s in (('C',) if a.startswith('P') else ('D','V')):
            rows.append(dict(arm=a,stage=s,trials=0,successes=0,first_byte=[0]*256,
                last_byte=[0]*256,leading_zero_bits=[0]*257,
                cluster_trials=[0]*1500 if a in ('A2','N2') else None,
                cluster_successes=[0]*1500 if a in ('A2','N2') else None,
                weight_trials=[0]*6 if a=='A3' else None,
                weight_successes=[0]*6 if a=='A3' else None))
    return dict(schema='hashlab-exp002-accounting-v2',
                secondary_identity='hashlab-exp002-secondary-statistics-proposal-v2',
                complete=False,streams=rows)


def verify_fixture(root, *, complete_sha256, audit_root, repository_root):
    """Read-only full-stream verification, requiring an externally retained pin."""
    if type(complete_sha256) is not str or not re.fullmatch('[0-9a-f]{64}',complete_sha256):
        raise ValueError('reference requires external completion pin')
    root = Path(root)
    _plain(root,directory=True)
    names = {'fixture.json','history.json','records.jsonl','accounting.json','complete.json'}
    if {p.name for p in root.iterdir()} != names:
        raise ValueError('reference missing/extra fixture evidence')
    for p in root.iterdir():
        _plain(p)
        cap = 2000000 if p.name=='accounting.json' else 400000 if p.name=='records.jsonl' else 65536
        if p.stat().st_size > cap:
            raise ValueError('reference evidence size cap')
    if _file_hash(root/'complete.json')['sha256'] != complete_sha256:
        raise ValueError('reference external completion pin mismatch')
    _json(root/'complete.json')
    inventory = {name:dict(size=entry['bytes'],sha256=entry['sha256'])
                 for name in sorted(names-{'complete.json'})
                 for entry in [_file_hash(root/name)]}
    expected_report = dict(schema='hashlab-e002-i1-complete-v1', scope='synthetic-only',
        synthetic_complete=True,confirmatory_complete=False,qa2=False,records=192,
        candidate_compression_blocks=256,files=inventory)
    if (root/'complete.json').read_bytes() != encode(expected_report):
        raise ValueError('reference completion claims/inventory mismatch')
    excluded, identity = load_history(audit_root,repository_root)
    if (root/'fixture.json').read_bytes() != encode(spec()):
        raise ValueError('reference fixture specification mismatch')
    if (root/'history.json').read_bytes() != encode(identity):
        raise ValueError('reference history binding mismatch')
    accounting = empty_accounting()
    streams = {(r['arm'],r['stage']):r for r in accounting['streams']}
    seen = set()
    with (root/'records.jsonl').open('rb') as source:
        for sequence,(record,population_rank) in enumerate(candidates(excluded)):
            candidate = bytes.fromhex(record['candidate_hex'])
            if candidate in seen:
                raise ValueError('reference duplicate candidate bytes')
            seen.add(candidate)
            if record['arm']=='A3' and (historical_rank(int.from_bytes(candidate,'big')) in excluded
                                       or historical_rank(int.from_bytes(candidate,'big')) != population_rank
                                       or population_rank >= 4096):
                raise ValueError('reference exclusion/rank boundary')
            digest = sha256(candidate).digest()
            h = int.from_bytes(digest,'big')
            success = h < 2**248
            expected = dict(sequence=sequence,candidate=record,population_rank=population_rank,
                            digest_hex=digest.hex(),success=success)
            if source.readline(2049) != encode(expected)+b'\n':
                raise ValueError('reference candidate/digest/order disagreement at '+str(sequence))
            row = streams[record['arm'],record['stage']]
            row['trials'] += 1
            row['successes'] += success
            row['first_byte'][digest[0]] += 1
            row['last_byte'][digest[-1]] += 1
            row['leading_zero_bits'][256-h.bit_length()] += 1
            if record['arm']=='A2':
                c = record['cluster']-(1500 if record['stage']=='V' else 0)
                row['cluster_trials'][c] += 1
                row['cluster_successes'][c] += success
            if record['arm']=='A3':
                w = int.from_bytes(candidate,'big').bit_count()-1
                row['weight_trials'][w] += 1
                row['weight_successes'][w] += success
        if source.read(1):
            raise ValueError('reference extra records')
    if len(seen) != 192 or (root/'accounting.json').read_bytes() != encode(accounting):
        raise ValueError('reference streaming accounting disagreement')
    return dict(schema='hashlab-e002-i1-verified-v1',scope='synthetic-only',
                verification='independent-complete-stream',producer_sha256=complete_sha256,
                records=192,rehash_compression_blocks=256,confirmatory_complete=False,qa2=False,
                successes={a+':'+s:streams[a,s]['successes'] for a in ('A1','A2','A3') for s in ('D','V')})
