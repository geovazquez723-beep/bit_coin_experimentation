"""S1.3 streaming reconstruction. Historical execution is disabled in source.

No CLI or startup job. Synthetic qualification is a separate bounded interface;
accepted S1.1/S1.2 fixture caps and implementations are unchanged.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
import sqlite3
import struct

from hashlab.candidates import build_generator
from .e001_scheduler import historical_schedule
from .e001_reconstruction import contract, validate_history, SOURCE, CONTRACT, MANIFEST
from .e001_phase_b import CONFIG, KINDS
from .exp002 import integer, in_a1, in_a3, HammingPopulation
from .exp002_journal import require_plain

HISTORICAL_EXECUTION_ENABLED = False  # separate Director-approved source change required
SYNTHETIC_LIMIT = 262144
ROW = struct.Struct('>BBII8sB')  # ordinal, phase, raw index, enum index, bytes, outcome
PAIR = struct.Struct('>8sQ')  # numeric-sorted value and its population rank


def _historical_guard(plan=None):
    if (plan is None or plan['scope'] == 'historical') and not HISTORICAL_EXECUTION_ENABLED:
        raise PermissionError('historical reconstruction disabled pending Director activation')


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _write(path, raw):
    with open(path, 'xb') as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def _inventory(path):
    digest = sha256()
    with open(path, 'rb') as src:
        for raw in iter(lambda: src.read(65536), b''):
            digest.update(raw)
    return dict(bytes=path.stat().st_size, sha256=digest.hexdigest())


@dataclass(frozen=True)
class SyntheticGeometry:
    discovery: int
    validation: int
    ordinals: tuple = tuple(KINDS)
    seeds: tuple = (1, 2)

    def __post_init__(self):
        if (type(self.ordinals) is not tuple or not self.ordinals
                or any(type(o) is not int or o not in KINDS for o in self.ordinals)
                or list(self.ordinals) != sorted(set(self.ordinals))):
            raise ValueError('synthetic generator ordering')
        integer(self.discovery, 0, SYNTHETIC_LIMIT)
        integer(self.validation, 0, SYNTHETIC_LIMIT)
        integer(len(self.ordinals)*(self.discovery+self.validation), 1, SYNTHETIC_LIMIT)
        if type(self.seeds) is not tuple or self.seeds not in ((1, 2), (1, 1)) or any(type(s) is not int for s in self.seeds):
            raise ValueError('only fixed synthetic keys 1/2 or 1/1')


@dataclass(frozen=True)
class Limits:
    batch: int = 1024
    cache_kib: int = 1024
    database_bytes: int = 128*1024*1024
    output_bytes: int = 1024*1024*1024

    def __post_init__(self):
        integer(self.batch, 1, 4096)
        integer(self.cache_kib, 64, 4096)
        integer(self.database_bytes, 65536, 512*1024*1024)
        integer(self.output_bytes, 65536, 2*1024**3)


def _plan(streams, scope, reference, expected_counts=None):
    return dict(schema='e001-s13-plan-v1', scope=scope, reference=reference,
                source=SOURCE, config=CONFIG, contract=CONTRACT, manifest=MANIFEST,
                streams=streams, sealed_counts=expected_counts)


def synthetic_plan(geometry, *, manual=False):
    if type(geometry) is not SyntheticGeometry or type(manual) is not bool:
        raise ValueError('synthetic geometry required')
    geometry.__post_init__()
    specs = contract()['config']['generators']
    streams = []
    for o in geometry.ordinals:
        for phase, attempts in enumerate((geometry.discovery, geometry.validation)):
            seeded = o in (2, 9)
            streams.append(dict(ordinal=o, generator=specs[o]['id'], family=KINDS[o],
                                phase=phase, attempts=attempts,
                                start_index=0 if seeded or phase == 0 else geometry.discovery,
                                seed=geometry.seeds[phase] if seeded else None, dedup=seeded))
    return _plan(streams, 'synthetic-qualification', 'manual' if manual else 'algorithmic')


def historical_plan(sealed, source_root):
    """Authenticate and describe fourteen streams without constructing generators."""
    c = validate_history(sealed, source_root)
    streams, counts = [], []
    for s in historical_schedule():
        phase = ('discovery', 'validation').index(s.phase)
        streams.append(dict(ordinal=s.ordinal, generator=s.generator, family=s.family,
                            phase=phase, attempts=s.attempts, start_index=s.start_index,
                            seed=s.seed, dedup=s.dedup))
        count = c['counts'][s.generator][s.phase]
        counts.append(dict(ordinal=s.ordinal, phase=phase, attempted=count['attempted'],
                           unique=count['unique'], within=count['duplicates_within_phase'],
                           cross=count['duplicates_cross_phase']))
    return _plan(streams, 'historical', 'algorithmic', counts)


def _raw(plan):
    _check_plan(plan)  # also guards internal entry points
    specs = contract()['config']['generators']
    previous = None
    continuing = None
    for s in plan['streams']:
        o = s['ordinal']
        if s['dedup']:
            source = build_generator(specs[o]).stream(s['seed'], 0)
        else:
            if previous != o:
                continuing = build_generator(specs[o]).stream(None, 0)
            source = continuing
        previous = o
        for i in range(s['attempts']):
            try:
                raw = next(source)
            except StopIteration:
                raise ValueError('premature generator termination') from None
            yield o, s['phase'], i, s['start_index']+i, raw


def _new_output(path):
    path = Path(path).absolute()
    for parent in path.parents:
        require_plain(parent, directory=True)
        if (parent/'manifest.sha256').exists():
            raise ValueError('output beneath sealed evidence')
    path.mkdir()  # exclusive attempt directory; no reopen, retry or repair
    return path


def _check_plan(plan):
    _historical_guard(plan)
    if plan['scope'] == 'historical':
        # Authenticated files are checked by run_historical before this boundary.
        return
    if plan['scope'] != 'synthetic-qualification':
        raise ValueError('unknown reconstruction scope')
    streams = plan['streams']
    if type(streams) is not list or not streams or len(streams) % 2:
        raise ValueError('synthetic stream pairs required')
    seeds = next(((streams[i]['seed'], streams[i+1]['seed'])
                  for i in range(0, len(streams), 2) if streams[i]['ordinal'] in (2, 9)), (1, 2))
    geometry = SyntheticGeometry(streams[0]['attempts'], streams[1]['attempts'],
                                 tuple(s['ordinal'] for s in streams[::2]), seeds)
    if plan['reference'] not in ('algorithmic', 'manual'):
        raise ValueError('unknown synthetic reference mode')
    expected = synthetic_plan(geometry, manual=plan['reference'] == 'manual')
    if encode(plan) != encode(expected):
        raise ValueError('synthetic source/configuration/schedule mismatch')
    if plan['reference'] == 'manual' and sum(s['attempts'] for s in streams) > 4096:
        raise ValueError('manual fixture reference cap')


class _Store:
    def __init__(self, path, limits):
        self.path, self.limits = path, limits
        self.peak_database = self.peak_journal = 0
        _write(path, b'')
        self.db = sqlite3.connect(path, timeout=0)
        try:
            self.db.executescript(f'''
                PRAGMA page_size=4096;
                PRAGMA max_page_count={limits.database_bytes//4096};
                PRAGMA cache_size=-{limits.cache_kib};
                PRAGMA temp_store=FILE;
                PRAGMA journal_mode=DELETE;
                PRAGMA synchronous=FULL;
                CREATE TABLE run(status TEXT NOT NULL, attempted INTEGER NOT NULL);
                INSERT INTO run VALUES('incomplete',0);
                CREATE TABLE first_seen(g INTEGER NOT NULL, value BLOB NOT NULL
                  CHECK(typeof(value)='blob' AND length(value)=8), p INTEGER NOT NULL,
                  PRIMARY KEY(g,value)) WITHOUT ROWID;
                CREATE TABLE excluded(value BLOB PRIMARY KEY
                  CHECK(typeof(value)='blob' AND length(value)=8), rank INTEGER NOT NULL UNIQUE) WITHOUT ROWID;
            ''')
            self.db.commit()
        except BaseException:
            self.db.close()
            raise

    def sample(self):
        main = self.path.stat().st_size
        journal = Path(str(self.path)+'-journal')
        size = journal.stat().st_size if journal.exists() else 0
        self.peak_database = max(self.peak_database, main)
        self.peak_journal = max(self.peak_journal, size)
        # Journal pages include per-page checksums and sector headers.
        if main > self.limits.database_bytes or size > self.limits.database_bytes*2:
            raise ValueError('database/journal reservation exceeded')

    def commit(self, attempted):
        self.db.execute('UPDATE run SET attempted=?', (attempted,))
        self.sample()
        self.db.commit()
        self.sample()

    def observe(self, s, raw):
        outcome = 0
        if s['dedup']:
            first = self.db.execute('SELECT p FROM first_seen WHERE g=? AND value=?', (s['ordinal'], raw)).fetchone()
            if first is None:
                self.db.execute('INSERT INTO first_seen VALUES(?,?,?)', (s['ordinal'], raw, s['phase']))
            else:
                outcome = 1 if first[0] == s['phase'] else 2
        a1 = int(outcome == 0 and in_a1(raw))
        a3 = int(outcome == 0 and in_a3(raw))
        if a3:
            self.db.execute('INSERT OR IGNORE INTO excluded VALUES(?,?)',
                            (raw, HammingPopulation().rank(int.from_bytes(raw, 'big'))))
        return outcome, a1, a3


def _run(plan, output, rows, limits):
    _check_plan(plan)
    limits.__post_init__()
    total = sum(s['attempts'] for s in plan['streams'])
    if plan['scope'] == 'synthetic-qualification' and not 1 <= total <= SYNTHETIC_LIMIT:
        raise ValueError('synthetic occurrence cap')
    # Reserve worst-case exact evidence plus main DB/twice-main rollback journal.
    # Indexed traversals need no unbounded SQLite temporary sort files.
    reservation = 3*limits.database_bytes + total*(ROW.size+PAIR.size+8) + 131072
    if reservation > limits.output_bytes:
        raise ValueError('configured output budget cannot reserve worst-case files')
    root = _new_output(output)
    plan_raw = encode(plan)
    _write(root/'INCOMPLETE', b'incomplete; no retry or resumption')
    _write(root/'plan.json', plan_raw)
    store = None
    n = 0
    try:
        store = _Store(root/'accounting.sqlite', limits)
        def disk_check():
            store.sample()
            if sum(p.stat().st_size for p in root.iterdir()) > limits.output_bytes:
                raise ValueError('total output reservation exceeded')
        rows = iter(rows)
        counts = []
        a1 = a3 = 0
        with open(root/'occurrences.bin', 'xb', buffering=65536) as out:
            for s in plan['streams']:
                c = dict(ordinal=s['ordinal'], phase=s['phase'], attempted=0, unique=0, within=0, cross=0)
                for i in range(s['attempts']):
                    row = next(rows, None)
                    if (type(row) is not tuple or len(row) != 5
                            or row[:4] != (s['ordinal'], s['phase'], i, s['start_index']+i)
                            or any(type(x) is not int for x in row[:4])
                            or type(row[4]) is not bytes or len(row[4]) != 8):
                        raise ValueError('missing/reordered/malformed occurrence')
                    outcome, x1, x3 = store.observe(s, row[4])
                    # Check logical bytes before writes, regardless of buffering.
                    if (n+1)*ROW.size > limits.output_bytes//2:
                        raise ValueError('occurrence evidence reservation exceeded')
                    out.write(ROW.pack(*row, outcome))
                    n += 1
                    c['attempted'] += 1
                    c[('unique', 'within', 'cross')[outcome]] += 1
                    a1 += x1
                    a3 += x3
                    if n % limits.batch == 0:
                        out.flush()
                        disk_check()
                        store.commit(n)
                counts.append(c)
            sentinel = object()
            if next(rows, sentinel) is not sentinel:
                raise ValueError('extra occurrence')
            out.flush()
            os.fsync(out.fileno())
        if plan['sealed_counts'] is not None and counts != plan['sealed_counts']:
            raise ValueError('sealed historical accounting disagreement')
        digest = sha256()
        distinct = 0
        with open(root/'exclusions.bin', 'xb') as out:
            for raw, rank in store.db.execute('SELECT value,rank FROM excluded ORDER BY value'):
                if (distinct+1)*PAIR.size > limits.output_bytes//4:
                    raise ValueError('exclusion output reservation exceeded')
                out.write(PAIR.pack(raw, rank))
                digest.update(raw)  # exact canonical exclusion-set encoding
                distinct += 1
            out.flush()
            os.fsync(out.fileno())
        with open(root/'ranks.bin', 'xb') as out:
            for rank, in store.db.execute('SELECT rank FROM excluded ORDER BY rank'):
                out.write(struct.pack('>Q', rank))
            out.flush()
            os.fsync(out.fileno())
        if plan['scope'] == 'historical' and (a1 != 0 or distinct != 60721 or digest.hexdigest() != '7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c'):
            raise ValueError('historical exclusion expectations disagree with observed values')
        disk_check()
        store.db.execute("UPDATE run SET status='complete'")
        store.commit(n)
        metrics = dict(peak_database_bytes=store.peak_database, peak_journal_bytes=store.peak_journal)
        store.db.close()
        store = None
        names = ('plan.json', 'occurrences.bin', 'exclusions.bin', 'ranks.bin', 'accounting.sqlite')
        report = dict(schema='e001-s13-complete-v1', scope=plan['scope'], reference=plan['reference'],
                      raw_attempted=n, unique_evaluated=sum(c['unique'] for c in counts),
                      qualifying_a1=a1, qualifying_a3=a3, distinct_excluded_a3=distinct,
                      exclusion_sha256=digest.hexdigest(), accounting=counts,
                      files={name: _inventory(root/name) for name in names}, resources=metrics,
                      historical_complete=plan['scope'] == 'historical', final_acceptance=False)
        report_raw = encode(report)
        if sum(p.stat().st_size for p in root.iterdir())+len(report_raw) > limits.output_bytes:
            raise ValueError('final output reservation exceeded')
        _write(root/'complete.json', report_raw)
        root.joinpath('INCOMPLETE').unlink()  # final completion boundary
        return report
    finally:
        if store is not None:
            store.db.rollback()
            store.db.close()
        close = getattr(rows, 'close', None)
        if close is not None:
            close()


def run_synthetic(geometry, output, *, reference_rows=None, limits=Limits()):
    """Fixed synthetic geometry, <=262144 attempts; manual references <=4096.

    Shares the full streaming/accounting/evidence kernel, not the old fixture cap.
    Manual injection qualifies accounting, never algorithmic generator identity.
    """
    plan = synthetic_plan(geometry, manual=reference_rows is not None)
    if reference_rows is not None and sum(s['attempts'] for s in plan['streams']) > 4096:
        raise ValueError('manual fixture reference cap')
    return _run(plan, output, _raw(plan) if reference_rows is None else reference_rows, limits)


def run_historical(sealed, source_root, output, *, limits=Limits()):
    """Disabled action boundary. No windows or caller-supplied enable parameter."""
    _historical_guard()  # fails before metadata access, output writes or generation
    plan = historical_plan(sealed, source_root)
    return _run(plan, output, _raw(plan), limits)
