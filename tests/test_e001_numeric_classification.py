"""G1-C: the 86 E001 secondary floating-point differences are a CPython float ``sum`` change.

Read-only: runs the pure historical analysis on the sealed counts in memory.  No tolerance is used;
every float is compared by IEEE-754 bit pattern.  Skipped if the sealed evidence is absent.
"""
from pathlib import Path
import json
import struct
import sys

import pytest

from hashlab.experiments.analysis import analyze_results
from hashlab.statistics import distribution

SEALED = Path('results/20261011T205056Z-exp001-fc1d75fc')
pytestmark = pytest.mark.skipif(not (SEALED / 'analysis.json').exists(), reason='sealed E001 evidence not present')


def bits(x):
    return struct.pack('>d', x).hex()


def naive_sum(iterable, start=0):
    total = start
    for item in iterable:
        total = total + item
    return total


def analysis():
    results = json.loads((SEALED / 'results.json').read_bytes())
    resolved = json.loads((SEALED / 'config.resolved.json').read_bytes())
    # results.json is stored with sorted keys; the original in-memory run followed configuration order.
    results['generators'] = {s['id']: results['generators'][s['id']] for s in resolved['generators']}
    return analyze_results(results, resolved)


def float_differences(a, b, path=''):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        return [d for k in a for d in float_differences(a[k], b[k], f'{path}/{k}')]
    if isinstance(a, list):
        assert len(a) == len(b)
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in float_differences(x, y, f'{path}[{i}]')]
    if isinstance(a, float):
        return [path] if bits(a) != bits(b) else []
    assert type(a) is type(b) and a == b, path
    return []


def sealed():
    value = json.loads((SEALED / 'analysis.json').read_bytes())
    return value


def strip_time(a):
    a = dict(a)
    a.pop('analyzed_at_utc')
    return a


def test_left_fold_sum_reproduces_every_sealed_float_bit_exactly(monkeypatch):
    monkeypatch.setattr(distribution, 'sum', naive_sum, raising=False)
    assert float_differences(strip_time(sealed()), strip_time(analysis())) == []


@pytest.mark.skipif(sys.version_info < (3, 12), reason='compensated float sum() starts in CPython 3.12')
def test_builtin_sum_differs_in_exactly_the_86_recorded_fields_and_no_decision_changes():
    diffs = float_differences(strip_time(sealed()), strip_time(analysis()))
    ledger = json.loads(Path('docs/reviews/architecture-review-036-e001-numerical-differences.json').read_text())
    assert len(diffs) == len(ledger['differences']) == 86
    assert all(d.endswith('/statistic') or d.endswith('/p_value') for d in diffs)
    assert all(d.startswith('/secondary_tests[') for d in diffs)
