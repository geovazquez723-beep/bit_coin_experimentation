"""Independent S1.2 occurrence verifier: no HASHLAB imports.

Reference algorithms are specified in core, not production generators. Generic
hashlib BLAKE2b/SHA-256 and AI authorship are shared limitations. Original-runtime
compatibility and historical completion are not qualified by these fixtures.
"""
from .core import _stream, classify

_FAMILIES = {0: ('sequential', 'seq-be-w8'), 2: ('uniform', 'uniform-be-w8'),
             4: ('patterned', 'pattern-bytes-w8'), 6: ('gray', 'struct-gray-w8'),
             7: ('stride', 'struct-stride-w8'), 8: ('bit-reversed', 'struct-bitrev-w8'),
             9: ('random_bytes', 'random-bytes-w8')}
_PINS = dict(source='ef595f5c2f2166923fd277def39708409f564419',
             configuration='d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b',
             historical_contract='008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04',
             manifest='546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b')


def _geometry(specs, discovery, validation, seeds):
    if (type(specs) is not tuple or not specs
            or type(discovery) is not int or type(validation) is not int
            or min(discovery, validation) < 0
            or not 1 <= len(specs) * (discovery + validation) <= 4096):
        raise ValueError('bounded synthetic geometry required')
    ordinals = []
    for spec in specs:
        if (type(spec) is not tuple or len(spec) != 2 or type(spec[0]) is not int
                or spec[0] not in _FAMILIES or _FAMILIES[spec[0]][0] != spec[1]):
            raise ValueError('independent family mismatch')
        ordinals.append(spec[0])
    if ordinals != sorted(set(ordinals)):
        raise ValueError('independent generator order')
    if (type(seeds) is not tuple or len(seeds) != 2
            or any(type(x) is not int or not 0 <= x < 2**64 for x in seeds)):
        raise ValueError('synthetic seeds required')


def verify_fixture(specs, discovery, validation, seeds, observations, report):
    """Algorithmic replay, exact wire metadata/outcomes and final report check."""
    return _verify(specs, discovery, validation, seeds, observations, report, None)


def verify_manual_fixture(specs, discovery, validation, seeds, observations, report, reference):
    """Manually specified fault/collision fixtures; no generator-validity claim.

    Reference is an immutable, <=4096 list of expected eight-byte occurrences,
    independently supplied by the test author. Scope remains synthetic-only.
    """
    _geometry(specs, discovery, validation, seeds)
    if (type(reference) is not tuple or len(reference) != len(specs)*(discovery+validation)
            or any(type(x) is not bytes or len(x) != 8 for x in reference)):
        raise ValueError('bounded manual reference required')
    return _verify(specs, discovery, validation, seeds, observations, report, iter(reference))


def _verify(specs, discovery, validation, seeds, observations, report, manual):
    _geometry(specs, discovery, validation, seeds)
    observations = iter(observations)
    counts = []
    evaluated = []
    for ordinal, family in specs:
        seen = {}
        seeded = ordinal in (2, 9)
        continuation = None if seeded or manual is not None else _stream(family)
        for phase_number, attempts in enumerate((discovery, validation)):
            phase = ('discovery', 'validation')[phase_number]
            start = 0 if seeded or phase_number == 0 else discovery
            source = manual if manual is not None else _stream(family, seeds[phase_number]) if seeded else continuation
            c = dict(ordinal=ordinal, phase=phase, attempted=attempts, unique=0, within=0, cross=0)
            for index in range(attempts):
                raw = next(source)
                expected = dict(_PINS, ordinal=ordinal, generator=_FAMILIES[ordinal][1],
                                family=family, phase=phase, index=index,
                                enumeration_index=start+index, candidate=raw,
                                scope='synthetic-fixture', seed=seeds[phase_number] if seeded else None,
                                start_index=start, attempts=attempts, dedup=seeded)
                outcome = 'unique'
                if seeded:
                    if raw in seen:
                        outcome = 'within' if seen[raw] == phase else 'cross'
                    else:
                        seen[raw] = phase
                expected['outcome'] = outcome
                sentinel = object()
                actual = next(observations, sentinel)
                if (type(actual) is not dict or actual != expected
                        or any(type(actual[k]) is not type(v) for k, v in expected.items())):
                    raise ValueError('independent occurrence bytes/metadata/outcome mismatch')
                c[outcome] += 1
                if outcome == 'unique':
                    evaluated.append(raw)
            counts.append(c)
    sentinel = object()
    if next(observations, sentinel) is not sentinel:
        raise ValueError('extra independent occurrence')
    membership = classify(evaluated)
    excluded = sorted({raw for raw in evaluated
                       if int.from_bytes(raw, 'big') >> 32 and int.from_bytes(raw, 'big').bit_count() <= 6})
    expected_report = dict(schema='e001-s12-exclusions-v1', scope='synthetic-only',
                           status='fixture-complete', verification='not-independently-verified',
                           raw_attempted=len(specs)*(discovery+validation), unique_evaluated=len(evaluated),
                           qualifying_a1=membership['a1'], qualifying_a3=membership['a3_occurrences'],
                           distinct_excluded_a3=membership['a3_distinct'], a3_ranks=membership['ranks'],
                           a3_values_numeric_hex=[raw.hex() for raw in excluded],
                           exclusion_sha256=membership['exclusion_sha256'], accounting=counts,
                           historical_complete=False, final_acceptance=False)
    # Recursive type-sensitive comparison rejects bool-as-int and missing fields.
    def exact(a, b):
        if type(a) is not type(b):
            return False
        if type(b) is dict:
            return a.keys() == b.keys() and all(exact(a[k], b[k]) for k in b)
        if type(b) is list:
            return len(a) == len(b) and all(exact(x, y) for x, y in zip(a, b))
        return a == b
    if not exact(report, expected_report):
        raise ValueError('independent accounting/exclusion/completeness mismatch')
    return dict(expected_report, verification='independently-verified-synthetic',
                reference='manual' if manual is not None else 'algorithmic')
