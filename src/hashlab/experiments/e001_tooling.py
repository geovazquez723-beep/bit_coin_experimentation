"""S1.2 synthetic reconstruction tools. Historical activation is absent.

The production specification is S1.1 historical_schedule(), which is inert.
Every executable path here requires its unchanged <=4096 FixturePlan boundary.
No research hash engine, historical seed derivation, CLI or recovery operation.
"""
from hashlib import sha256
from pathlib import Path
import os
import sqlite3

from .e001_scheduler import fixture_schedule, iter_fixture, Occurrence
from .exp002 import HammingPopulation, in_a1, in_a3, integer
from .exp002_journal import require_plain


def fixture_occurrences(plan):
    """Lazy S1.1 provider; historical stream descriptors are not executable plans."""
    return iter_fixture(plan)


def occurrence_fields(row):
    row.__post_init__()
    s = row.stream
    return dict(ordinal=s.ordinal, generator=s.generator, family=s.family,
                phase=s.phase, index=row.index, enumeration_index=row.enumeration_index,
                candidate=row.candidate, source=s.source, configuration=s.configuration,
                historical_contract=s.historical_contract, manifest=s.manifest,
                scope=s.scope, seed=s.seed, start_index=s.start_index,
                attempts=s.attempts, dedup=s.dedup)


class DiskAccounting:
    """Exclusive one-attempt SQLite store; never opens an existing audit.

    <=64 occurrences/transaction, 64 KiB cache, 8 MiB main database cap.
    DELETE rollback journal has a separate 8 MiB reservation (16 MiB total).
    Only exhausted input plus an extra-row check can persist complete status.
    A crash leaves incomplete status; partial rows are never a complete report.
    """
    def __init__(self, path, plan, *, batch_size=64):
        self.streams = fixture_schedule(plan)  # revalidates plan and cap first
        integer(batch_size, 1, 64)
        self.batch_size = batch_size
        self.path = Path(path).absolute()
        for parent in self.path.parents:
            require_plain(parent, directory=True)
            if (parent / 'manifest.sha256').exists():
                raise ValueError('output must be outside sealed evidence')
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        self.used = False
        self._active = None
        self.status = 'incomplete'
        self.db = sqlite3.connect(self.path, timeout=0)
        try:
            self.db.executescript('''
                PRAGMA page_size=4096;
                PRAGMA max_page_count=2048;
                PRAGMA cache_size=-64;
                PRAGMA temp_store=FILE;
                PRAGMA synchronous=FULL;
                PRAGMA journal_mode=DELETE;
                CREATE TABLE run (plan TEXT NOT NULL, status TEXT NOT NULL);
                CREATE TABLE seen (
                    generator INTEGER NOT NULL, candidate BLOB NOT NULL
                    CHECK(typeof(candidate)='blob' AND length(candidate)=8),
                    phase TEXT NOT NULL CHECK(phase IN ('discovery','validation')),
                    PRIMARY KEY(generator,candidate)) WITHOUT ROWID;
                CREATE TABLE counts (
                    stream INTEGER PRIMARY KEY, attempted INTEGER NOT NULL DEFAULT 0,
                    unique_count INTEGER NOT NULL DEFAULT 0,
                    within_count INTEGER NOT NULL DEFAULT 0,
                    cross_count INTEGER NOT NULL DEFAULT 0,
                    a1 INTEGER NOT NULL DEFAULT 0, a3 INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE excluded (
                    candidate BLOB PRIMARY KEY
                    CHECK(typeof(candidate)='blob' AND length(candidate)=8),
                    rank INTEGER NOT NULL UNIQUE) WITHOUT ROWID;
            ''')
            self.db.execute('INSERT INTO run VALUES (?,?)', (plan.fingerprint, self.status))
            self.db.executemany('INSERT INTO counts(stream) VALUES (?)',
                                ((i,) for i in range(len(self.streams))))
            self.db.commit()
        except BaseException:
            self.db.close()
            raise

    def _commit(self):
        # Main DB is bounded by max_page_count; cap its rollback sidecar too.
        for suffix in ('', '-journal'):
            p = Path(str(self.path) + suffix)
            if p.exists() and p.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('SQLite disk reservation exceeded')
        self.db.commit()

    def observations(self, rows):
        if self.used or self.status != 'incomplete':
            raise ValueError('one-use accounting; no retry/resumption')
        self.used = True
        self._active = self._observe(rows)
        return self._active

    def _observe(self, rows):
        pending = 0
        try:
            rows = iter(rows)
            for number, stream in enumerate(self.streams):
                for index in range(stream.attempts):
                    row = next(rows, None)
                    if type(row) is not Occurrence or row.stream != stream or row.index != index:
                        raise ValueError('missing/reordered occurrence')
                    record = occurrence_fields(row)
                    outcome = 'unique'
                    if stream.dedup:
                        first = self.db.execute('SELECT phase FROM seen WHERE generator=? AND candidate=?',
                                                (stream.ordinal, row.candidate)).fetchone()
                        if first:
                            outcome = 'within' if first[0] == stream.phase else 'cross'
                        else:
                            self.db.execute('INSERT INTO seen VALUES (?,?,?)',
                                            (stream.ordinal, row.candidate, stream.phase))
                    a1 = int(outcome == 'unique' and in_a1(row.candidate))
                    a3 = int(outcome == 'unique' and in_a3(row.candidate))
                    if a3:
                        self.db.execute('INSERT OR IGNORE INTO excluded VALUES (?,?)',
                                        (row.candidate, HammingPopulation().rank(int.from_bytes(row.candidate, 'big'))))
                    column = {'unique': 'unique_count', 'within': 'within_count', 'cross': 'cross_count'}[outcome]
                    self.db.execute(f'UPDATE counts SET attempted=attempted+1, {column}={column}+1, a1=a1+?, a3=a3+? WHERE stream=?',
                                    (a1, a3, number))
                    pending += 1
                    if pending == self.batch_size:
                        self._commit()
                        pending = 0
                    yield dict(record, outcome=outcome)
            sentinel = object()
            if next(rows, sentinel) is not sentinel:
                raise ValueError('extra occurrence')
            self.db.execute("UPDATE run SET status='fixture-complete'")
            self._commit()
            self.status = 'fixture-complete'
        except BaseException:
            self.status = 'interrupted'
            self.db.rollback()
            # Persisted status remains incomplete, even when earlier batches committed.
            raise

    def report(self):
        """Only complete runs can report; no acceptance of partial accounting."""
        if self.status != 'fixture-complete':
            raise ValueError('incomplete accounting cannot report')
        counts = []
        a1 = a3 = 0
        for s, c in zip(self.streams, self.db.execute('SELECT attempted,unique_count,within_count,cross_count,a1,a3 FROM counts ORDER BY stream')):
            attempted, unique, within, cross, x1, x3 = c
            counts.append(dict(ordinal=s.ordinal, phase=s.phase, attempted=attempted,
                               unique=unique, within=within, cross=cross))
            a1 += x1
            a3 += x3
        digest = sha256()  # exclusion-set serialization only; never candidate evaluation
        values = []
        for raw, in self.db.execute('SELECT candidate FROM excluded ORDER BY candidate'):
            digest.update(raw)
            values.append(raw.hex())
        ranks = [r for r, in self.db.execute('SELECT rank FROM excluded ORDER BY rank')]
        return dict(schema='e001-s12-exclusions-v1', scope='synthetic-only',
                    status=self.status, verification='not-independently-verified',
                    raw_attempted=sum(c['attempted'] for c in counts),
                    unique_evaluated=sum(c['unique'] for c in counts),
                    qualifying_a1=a1, qualifying_a3=a3, distinct_excluded_a3=len(ranks),
                    a3_values_numeric_hex=values, a3_ranks=ranks,
                    exclusion_sha256=digest.hexdigest(), accounting=counts,
                    historical_complete=False, final_acceptance=False)

    def close(self):
        if self._active is not None:
            self._active.close()  # abandon/roll back before closing the connection
        if self.status != 'fixture-complete':
            self.status = 'interrupted'
        self.db.close()  # SQLite rolls back any outstanding batch

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
