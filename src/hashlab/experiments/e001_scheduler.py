"""Historical E001 schedule metadata and <=4096-occurrence synthetic replay.

No historical iteration/provider, hash engine, seed derivation or audit acceptance.
Ordering and dedup semantics follow pinned baseline.run_experiment/run_phase.
"""
from dataclasses import dataclass
from itertools import islice

from hashlab.candidates import build_generator
from .e001_reconstruction import CONTRACT, MANIFEST, SOURCE, PHASES, contract
from .e001_phase_b import CONFIG, KINDS, FixturePlan


def _integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('invalid scheduler integer')
    return value


@dataclass(frozen=True)
class Stream:
    ordinal: int
    generator: str
    family: str
    phase: str
    attempts: int
    start_index: int
    seed: int | None
    dedup: bool
    scope: str
    source: str = SOURCE
    configuration: str = CONFIG
    historical_contract: str = CONTRACT
    manifest: str = MANIFEST

    def __post_init__(self):
        _integer(self.ordinal, 0, 9)
        _integer(self.attempts, 0, 500000)
        _integer(self.start_index, 0, 500000)
        if self.seed is not None:
            _integer(self.seed, 0, 2**64 - 1)
        if (self.family != KINDS.get(self.ordinal) or self.phase not in PHASES
                or type(self.dedup) is not bool
                or self.dedup != (self.family in ('uniform', 'random_bytes'))
                or (self.seed is not None) != self.dedup
                or self.scope not in ('synthetic-fixture', 'historical-metadata-only')
                or (self.source, self.configuration, self.historical_contract, self.manifest)
                != (SOURCE, CONFIG, CONTRACT, MANIFEST)):
            raise ValueError('invalid stream metadata')

    @property
    def phase_behavior(self):
        return 'phase-seed-restart' if self.dedup else 'seedless-continuation'


def historical_schedule():
    """Fourteen immutable stream descriptors; no generator construction/advancement.

    Historical seeds are copied from pinned records, never selected or derived.
    Call validate_history separately to authenticate actual evidence/source files.
    """
    c = contract()
    streams = []
    for ordinal, spec in enumerate(c['config']['generators']):
        if spec['width'] != 8:
            continue
        family = spec.get('mode') if spec['type'] == 'structured' else spec['type']
        if KINDS.get(ordinal) != family:
            raise ValueError('historical family disagreement')
        seeded = family in ('uniform', 'random_bytes')
        consumed = 0
        for phase in PHASES:
            counts = c['counts'][spec['id']][phase]
            attempts = c['config']['phases'][phase]['candidates_per_generator']
            seed = c['seeds']['generators'][spec['id']][phase] if seeded else None
            start = 0 if seeded else consumed
            if (type(attempts) is not int or attempts != 500000
                    or counts['attempted'] != attempts or counts['exhausted']
                    or counts['start_index'] != start or counts['seed'] != seed
                    or c['config']['execution']['dedup'] != 'auto'):
                raise ValueError('historical phase/configuration disagreement')
            streams.append(Stream(ordinal, spec['id'], family, phase, attempts,
                                  start, seed, seeded, 'historical-metadata-only'))
            consumed += counts['attempted']
    if len(streams) != 14 or sum(s.attempts for s in streams) != 7000000:
        raise ValueError('historical geometry disagreement')
    return tuple(streams)


def fixture_schedule(plan):
    """Same ordering/restart rules with existing synthetic FixturePlan limits."""
    if type(plan) is not FixturePlan:
        raise ValueError('synthetic FixturePlan required')
    plan.__post_init__()
    historical = {s.ordinal: s for s in historical_schedule() if s.phase == 'discovery'}
    streams = []
    for ordinal, family in plan.specs:
        original = historical[ordinal]
        for p, (phase, attempts) in enumerate(zip(PHASES, (plan.discovery, plan.validation))):
            streams.append(Stream(ordinal, original.generator, family, phase, attempts,
                                  0 if original.dedup or p == 0 else plan.discovery,
                                  plan.seeds[p] if original.dedup else None,
                                  original.dedup, 'synthetic-fixture'))
    return tuple(streams)


@dataclass(frozen=True)
class Occurrence:
    stream: Stream
    index: int
    enumeration_index: int
    candidate: bytes

    def __post_init__(self):
        if type(self.stream) is not Stream or self.stream.scope != 'synthetic-fixture':
            raise ValueError('synthetic stream required')
        self.stream.__post_init__()
        _integer(self.index, 0, self.stream.attempts - 1)
        if (type(self.enumeration_index) is not int
                or self.enumeration_index != self.stream.start_index + self.index):
            raise ValueError('wrong enumeration index')
        if type(self.candidate) is not bytes or len(self.candidate) != 8:
            raise ValueError('eight-byte candidate required')


def iter_fixture(plan, *, start=0, count=None):
    """Lazy bounded raw occurrences, including duplicates; never tops up.

    Windows use global fixture occurrence order. Skipped prefix generation plus
    returned occurrences never exceeds the FixturePlan's 4096 total. Seedless
    fixtures keep one continuing iterator instead of replaying discovery prefixes;
    its position equals the original start_index (including patterned offsets).
    No historical metadata can be passed as an execution plan.
    """
    streams = fixture_schedule(plan)
    total = sum(s.attempts for s in streams)
    _integer(start, 0, total)
    count = total - start if count is None else _integer(count, 0, total - start)

    def rows():
        if not count:
            return
        stop, position = start + count, 0
        continuing = None
        continuing_ordinal = None
        cursor = 0
        specs = contract()['config']['generators']
        for stream in streams:
            end = position + stream.attempts
            if end > start and position < stop:
                lower, upper = max(0, start - position), min(stream.attempts, stop - position)
                if stream.dedup:
                    gen = build_generator(specs[stream.ordinal])
                    source = islice(gen.stream(stream.seed, 0), lower, upper)
                else:
                    if continuing_ordinal != stream.ordinal:
                        gen = build_generator(specs[stream.ordinal])
                        continuing = gen.stream(None, 0)
                        continuing_ordinal, cursor = stream.ordinal, 0
                    target = stream.start_index + lower
                    source = islice(continuing, target - cursor, target - cursor + upper - lower)
                    cursor = stream.start_index + upper
                for index in range(lower, upper):
                    try:
                        raw = next(source)
                    except StopIteration:
                        raise ValueError('premature fixture generator exhaustion') from None
                    yield Occurrence(stream, index, stream.start_index + index, raw)
            position = end
            if position >= stop:
                break
    return rows()


@dataclass(frozen=True)
class Counts:
    stream: Stream
    attempted: int
    unique: int
    within: int
    cross: int


@dataclass(frozen=True)
class Summary:
    status: str
    expected: int
    checked: int
    counts: tuple[Counts, ...]
    scope: str = 'synthetic-fixture-only'
    e_audit_passed: bool = False
    final_acceptance: bool = False


@dataclass(frozen=True)
class Observation:
    occurrence: Occurrence
    outcome: str


class FixtureAccounting:
    """One-use, bounded observations; no full historical dedup qualification.

    Auto mode bypasses sets for unique-by-construction families, exactly as E001.
    For seeded families, first discovery membership wins over current-phase
    membership. Values in different generators never deduplicate one another.
    Complete requires exhaustion AND the no-extra-row check, not just count==n.
    """
    def __init__(self, plan):
        self._streams = fixture_schedule(plan)
        self._counts = [[0, 0, 0, 0] for _ in self._streams]
        self._expected = sum(s.attempts for s in self._streams)
        self._checked = 0
        self._status = 'incomplete'
        self._used = False

    def snapshot(self):
        return Summary(self._status, self._expected, self._checked,
                       tuple(Counts(s, *c) for s, c in zip(self._streams, self._counts)))

    def observations(self, rows):
        if self._used:
            raise ValueError('fixture accounting is one-use; no retry/resumption')
        self._used = True
        return self._observe(rows)

    def _observe(self, rows):
        seen = {}
        previous_ordinal = None
        try:
            rows = iter(rows)
            for stream, counts in zip(self._streams, self._counts):
                if stream.ordinal != previous_ordinal:
                    seen.clear()
                    previous_ordinal = stream.ordinal
                for index in range(stream.attempts):
                    row = next(rows, None)
                    if (type(row) is not Occurrence or row.stream != stream
                            or type(row.index) is not int or row.index != index):
                        raise ValueError('missing/out-of-order fixture occurrence')
                    # Revalidate even directly forged frozen dataclass instances.
                    row.__post_init__()
                    outcome = 'unique'
                    if stream.dedup:
                        first = seen.get(row.candidate)
                        if first is not None:
                            outcome = 'cross' if first != stream.phase else 'within'
                        else:
                            seen[row.candidate] = stream.phase
                    counts[0] += 1
                    counts[{'unique': 1, 'within': 2, 'cross': 3}[outcome]] += 1
                    self._checked += 1
                    yield Observation(row, outcome)
            sentinel = object()
            if next(rows, sentinel) is not sentinel:
                raise ValueError('extra fixture occurrence')
            self._status = 'fixture-complete'
        except (ValueError, TypeError):
            self._status = 'invalid'
            raise
        except BaseException:
            self._status = 'interrupted'
            raise
