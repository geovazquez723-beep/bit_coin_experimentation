"""Independent disk-backed S1.3 replay. No HASHLAB imports or shared accounting.

Only the accepted independent core algorithms and generic stdlib dependencies
are reused. AI authorship/cryptographic-library/runtime limitations remain.
"""
from hashlib import sha256
from math import comb
from pathlib import Path
import json
import os
import sqlite3
import stat
import struct

from e001_verify.core import _stream

HISTORICAL_VERIFICATION_ENABLED = False  # separate explicit activation required
FAMILIES = {0: ('sequential', 'seq-be-w8'), 2: ('uniform', 'uniform-be-w8'),
            4: ('patterned', 'pattern-bytes-w8'), 6: ('gray', 'struct-gray-w8'),
            7: ('stride', 'struct-stride-w8'), 8: ('bit-reversed', 'struct-bitrev-w8'),
            9: ('random_bytes', 'random-bytes-w8')}
PINS = dict(source='ef595f5c2f2166923fd277def39708409f564419',
            config='d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b',
            contract='008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04',
            manifest='546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b')
RECORD = struct.Struct('>BBII8sB')
EXCLUSION = struct.Struct('>8sQ')


def _plain(path, directory=False):
    info = Path(path).lstat()
    if (getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError('unsupported verifier path')


def _json(path):
    _plain(path)
    if path.stat().st_size > 65536:
        raise ValueError('metadata size cap')
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result: raise ValueError('duplicate metadata key')
            result[k] = v
        return result
    def invalid(value): raise ValueError('nonfinite metadata')
    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=invalid)


def _exact(a, b):
    if type(a) is not type(b): return False
    if type(b) is dict: return a.keys() == b.keys() and all(_exact(a[k], b[k]) for k in b)
    if type(b) is list: return len(a) == len(b) and all(_exact(x, y) for x, y in zip(a, b))
    return a == b


def synthetic_plan(ordinals, discovery, validation, seeds=(1, 2), *, manual=False):
    if (type(ordinals) is not tuple or not ordinals
            or any(type(o) is not int or o not in FAMILIES for o in ordinals)
            or list(ordinals) != sorted(set(ordinals))
            or type(discovery) is not int or type(validation) is not int
            or min(discovery, validation) < 0
            or not 1 <= len(ordinals)*(discovery+validation) <= 262144
            or type(seeds) is not tuple or seeds not in ((1, 2), (1, 1))
            or any(type(s) is not int for s in seeds) or type(manual) is not bool):
        raise ValueError('independent synthetic geometry')
    streams = []
    for o in ordinals:
        for p, count in enumerate((discovery, validation)):
            streams.append(dict(ordinal=o, generator=FAMILIES[o][1], family=FAMILIES[o][0],
                                phase=p, attempts=count, start_index=0 if o in (2, 9) or p == 0 else discovery,
                                seed=seeds[p] if o in (2, 9) else None, dedup=o in (2, 9)))
    return dict(PINS, schema='e001-s13-plan-v1', scope='synthetic-qualification',
                reference='manual' if manual else 'algorithmic', streams=streams, sealed_counts=None)


def historical_plan(contract_path):
    """Independent, inert historical metadata from the hash-pinned contract."""
    path = Path(contract_path)
    _plain(path)
    if path.stat().st_size > 65536:
        raise ValueError('historical contract cap')
    if sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != PINS['contract']:
        raise ValueError('independent historical contract pin')
    c = _json(path)
    streams, counts = [], []
    for o, (family, gid) in FAMILIES.items():
        spec = c['config']['generators'][o]
        if spec['id'] != gid or spec['width'] != 8:
            raise ValueError('independent historical identity')
        for p, phase in enumerate(('discovery', 'validation')):
            seeded = o in (2, 9)
            count = c['counts'][gid][phase]
            if count['attempted'] != 500000 or count['exhausted']:
                raise ValueError('independent historical geometry')
            streams.append(dict(ordinal=o, generator=gid, family=family, phase=p, attempts=500000,
                                start_index=0 if seeded or p == 0 else 500000,
                                seed=c['seeds']['generators'][gid][phase] if seeded else None, dedup=seeded))
            counts.append(dict(ordinal=o, phase=p, attempted=500000, unique=count['unique'],
                               within=count['duplicates_within_phase'], cross=count['duplicates_cross_phase']))
    return dict(PINS, schema='e001-s13-plan-v1', scope='historical', reference='algorithmic',
                streams=streams, sealed_counts=counts)


def rank(value):
    """Independent combinatorial rank in weight/colex, excluding all-low subsets."""
    weight = value.bit_count()
    if value >> 32 == 0 or not 1 <= weight <= 6:
        raise ValueError('outside independent A3 population')
    earlier = sum(comb(64, w)-comb(32, w) for w in range(1, weight))
    remaining = weight
    for bit in range(63, -1, -1):
        if (value >> bit) & 1:
            earlier += comb(bit, remaining) if bit >= remaining else 0
            remaining -= 1
    return earlier-comb(32, weight)


def _file_hash(path):
    digest = sha256()
    with open(path, 'rb') as src:
        for raw in iter(lambda: src.read(65536), b''): digest.update(raw)
    return dict(bytes=path.stat().st_size, sha256=digest.hexdigest())


def _verify(root, work, expected, reference, batch, database_bytes):
    if expected['scope'] == 'historical' and not HISTORICAL_VERIFICATION_ENABLED:
        raise PermissionError('historical verifier disabled pending Director activation')
    if expected['scope'] != 'historical':
        streams = expected['streams']
        if not streams or len(streams) % 2: raise ValueError('independent stream pairs')
        seeds = next(((streams[i]['seed'], streams[i+1]['seed'])
                      for i in range(0,len(streams),2) if streams[i]['ordinal'] in (2,9)), (1,2))
        canonical = synthetic_plan(tuple(s['ordinal'] for s in streams[::2]),
                                   streams[0]['attempts'],streams[1]['attempts'],seeds,manual=reference is not None)
        if not _exact(expected,canonical): raise ValueError('independent synthetic plan mismatch')
    if type(batch) is not int or not 1 <= batch <= 4096 or type(database_bytes) is not int or not 65536 <= database_bytes <= 512*1024**2:
        raise ValueError('independent resource limits')
    root, work = Path(root).absolute(), Path(work).absolute()
    for parent in (root, *root.parents): _plain(parent, directory=True)
    for parent in work.parents:
        _plain(parent, directory=True)
        if (parent/'manifest.sha256').exists() or parent == root:
            raise ValueError('verifier scratch must be outside sealed/producer evidence')
    report = _json(root/'complete.json')
    if not _exact(_json(root/'plan.json'), expected):
        raise ValueError('independent plan/source/configuration mismatch')
    names = {'plan.json', 'occurrences.bin', 'exclusions.bin', 'ranks.bin', 'accounting.sqlite'}
    if {p.name for p in root.iterdir()} != names | {'complete.json'}:
        raise ValueError('incomplete/unlisted evidence')
    total = sum(s['attempts'] for s in expected['streams'])
    if type(report) is not dict or type(report.get('files')) is not dict or set(report['files']) != names:
        raise ValueError('independent evidence inventory')
    caps = dict(zip(('plan.json', 'occurrences.bin', 'exclusions.bin', 'ranks.bin', 'accounting.sqlite'),
                    (65536, total*RECORD.size, total*EXCLUSION.size, total*8, 512*1024**2)))
    for name in names:
        path = root/name
        _plain(path)
        if path.stat().st_size > caps[name] or not _exact(report['files'][name], _file_hash(path)):
            raise ValueError('independent file size/integrity mismatch')
    # Read only the producer's completion marker, never its dedup/accounting data.
    # immutable=1 prevents SQLite from attempting journal recovery or repair.
    producer_state = None
    try:
        producer_state = sqlite3.connect((root/'accounting.sqlite').as_uri()+'?mode=ro&immutable=1',
                                         uri=True,timeout=0)
        producer_state.execute('PRAGMA query_only=ON')
        state = producer_state.execute('SELECT status,attempted FROM run LIMIT 2').fetchall()
    except sqlite3.DatabaseError as exc:
        raise ValueError('unreadable producer completion state') from exc
    finally:
        if producer_state is not None: producer_state.close()
    if state != [('complete',total)]:
        raise ValueError('incomplete producer database state')
    work.mkdir()  # exclusive independent attempt; no existing database is opened
    with open(work/'INCOMPLETE', 'xb') as out: out.write(b'incomplete')
    with open(work/'reference.sqlite', 'xb'): pass
    db = sqlite3.connect(work/'reference.sqlite', timeout=0)
    peaks = [0, 0]
    try:
        db.executescript(f'''
            PRAGMA page_size=4096;
            PRAGMA max_page_count={database_bytes//4096};
            PRAGMA cache_size=-1024;
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=FULL;
            PRAGMA temp_store=FILE;
            CREATE TABLE membership(g INTEGER, phase INTEGER, candidate BLOB
              CHECK(typeof(candidate)='blob' AND length(candidate)=8),
              PRIMARY KEY(g,phase,candidate)) WITHOUT ROWID;
            CREATE TABLE x3(candidate BLOB PRIMARY KEY
              CHECK(typeof(candidate)='blob' AND length(candidate)=8), position INTEGER UNIQUE) WITHOUT ROWID;
            CREATE TABLE progress(checked INTEGER, status TEXT);
            INSERT INTO progress VALUES(0,'incomplete');
        ''')
        db.commit()
        def sample():
            journal = work/'reference.sqlite-journal'
            sizes = [(work/'reference.sqlite').stat().st_size, journal.stat().st_size if journal.exists() else 0]
            peaks[:] = [max(a, b) for a, b in zip(peaks, sizes)]
            if sizes[0] > database_bytes or sizes[1] > database_bytes*2:
                raise ValueError('independent disk reservation exceeded')
        def commit(n):
            db.execute('UPDATE progress SET checked=?', (n,))
            sample()
            db.commit()
            sample()
        counts = []
        checked = a1 = a3 = unique_total = 0
        previous = None
        continuation = None
        manual = iter(reference) if reference is not None else None
        with open(root/'occurrences.bin', 'rb', buffering=65536) as src:
            for s in expected['streams']:
                g, phase = s['ordinal'], s['phase']
                if manual is not None:
                    source = manual
                elif g in (2, 9):
                    source = _stream(FAMILIES[g][0], s['seed'])
                else:
                    if previous != g: continuation = _stream(FAMILIES[g][0])
                    source = continuation
                previous = g
                c = dict(ordinal=g, phase=phase, attempted=0, unique=0, within=0, cross=0)
                for i in range(s['attempts']):
                    chunk = src.read(RECORD.size)
                    if len(chunk) != RECORD.size: raise ValueError('missing independent occurrence')
                    expected_raw = next(source)
                    outcome = 0
                    if g in (2, 9):
                        # Independently implement prior-phase-first precedence using
                        # separate discovery/validation memberships, not first_seen.
                        discovery = db.execute('SELECT 1 FROM membership WHERE g=? AND phase=0 AND candidate=?', (g, expected_raw)).fetchone()
                        current = db.execute('SELECT 1 FROM membership WHERE g=? AND phase=? AND candidate=?', (g, phase, expected_raw)).fetchone()
                        if phase == 1 and discovery is not None: outcome = 2
                        elif current is not None: outcome = 1
                        else: db.execute('INSERT INTO membership VALUES(?,?,?)', (g, phase, expected_raw))
                    if RECORD.unpack(chunk) != (g, phase, i, s['start_index']+i, expected_raw, outcome):
                        raise ValueError('independent bytes/order/indices/duplicate mismatch')
                    c['attempted'] += 1
                    c[('unique', 'within', 'cross')[outcome]] += 1
                    if outcome == 0:
                        unique_total += 1
                        v = int.from_bytes(expected_raw, 'big')
                        a1 += int(2**20 <= v < 2**32)
                        if v >> 32 and 1 <= v.bit_count() <= 6:
                            a3 += 1
                            db.execute('INSERT OR IGNORE INTO x3 VALUES(?,?)', (expected_raw, rank(v)))
                    checked += 1
                    if checked % batch == 0: commit(checked)
                counts.append(c)
            if src.read(1): raise ValueError('extra independent occurrence')
        if manual is not None and next(manual, None) is not None:
            raise ValueError('extra manual reference')
        digest = sha256()
        distinct = 0
        with open(root/'exclusions.bin', 'rb') as src:
            for raw, position in db.execute('SELECT candidate,position FROM x3 ORDER BY candidate'):
                if src.read(EXCLUSION.size) != EXCLUSION.pack(raw, position):
                    raise ValueError('independent exclusion values/ranks mismatch')
                digest.update(raw)
                distinct += 1
            if src.read(1): raise ValueError('extra independent exclusion')
        with open(root/'ranks.bin', 'rb') as src:
            for position, in db.execute('SELECT position FROM x3 ORDER BY position'):
                if src.read(8) != position.to_bytes(8, 'big'): raise ValueError('independent rank ordering mismatch')
            if src.read(1): raise ValueError('extra independent rank')
        if expected['sealed_counts'] is not None and not _exact(counts, expected['sealed_counts']):
            raise ValueError('independent sealed historical accounting disagreement')
        scientific = dict(schema='e001-s13-complete-v1', scope=expected['scope'], reference=expected['reference'],
                          raw_attempted=checked, unique_evaluated=unique_total, qualifying_a1=a1,
                          qualifying_a3=a3, distinct_excluded_a3=distinct, exclusion_sha256=digest.hexdigest(),
                          accounting=counts, historical_complete=expected['scope'] == 'historical', final_acceptance=False)
        if set(report) != set(scientific) | {'files', 'resources'} or not _exact({k: report[k] for k in scientific}, scientific):
            raise ValueError('independent summary/completeness mismatch')
        if expected['scope'] == 'historical' and (a1 != 0 or distinct != 60721 or digest.hexdigest() != '7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c'):
            raise ValueError('independent historical exclusion disagreement')
        db.execute("UPDATE progress SET status='complete'")
        commit(checked)
        result = dict(scientific, verification='independent-stream-replay',
                      evidence_report_sha256=_file_hash(root/'complete.json')['sha256'],
                      resources=dict(peak_database_bytes=peaks[0], peak_journal_bytes=peaks[1]))
        with open(work/'verified.json', 'xb') as out:
            out.write(json.dumps(result, sort_keys=True).encode())
            out.flush()
            os.fsync(out.fileno())
        work.joinpath('INCOMPLETE').unlink()
        return result
    finally:
        db.rollback()
        db.close()


def verify_synthetic(root, work, ordinals, discovery, validation, seeds=(1, 2), *, reference=None, batch=1024, database_bytes=128*1024**2):
    expected = synthetic_plan(ordinals, discovery, validation, seeds, manual=reference is not None)
    if reference is not None:
        n = len(ordinals)*(discovery+validation)
        if (type(reference) is not tuple or n > 4096 or len(reference) != n
                or any(type(x) is not bytes or len(x) != 8 for x in reference)):
            raise ValueError('bounded independent manual reference')
    return _verify(root, work, expected, reference, batch, database_bytes)


def verify_historical(root, work, contract_path, *, batch=1024, database_bytes=128*1024**2):
    if not HISTORICAL_VERIFICATION_ENABLED:
        raise PermissionError('historical verifier disabled pending Director activation')
    return _verify(root, work, historical_plan(contract_path), None, batch, database_bytes)
