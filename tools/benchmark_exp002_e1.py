"""Review 027's fixed bounded sampling benchmark; no candidate/hash evaluation.

Run with the qualified interpreter. Six disclosed passes: timing and a traced
replay for each authorized count. Existing ledgers are never overwritten. A
failure is retained and stops the benchmark without retry or seed replacement.
This engineering ledger is not the later operational attempt registry.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from hashlab.candidates.vitter import SamplingError, vitter_ranks
from hashlab.experiments.exp002 import A1_SIZE, PROTOCOL_IDENTITY


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def main():
    output = ROOT / 'docs/reviews/architecture-review-027-e1-performance.json'
    if output.exists():
        raise SystemExit('Benchmark ledger already exists; refuse overwrite or undisclosed repeat')
    ledger = {
        'schema': 'hashlab-exp002-e1-engineering-benchmark-v1',
        'scope': 'non-confirmatory rank sampling only; no candidate encoding or hashing',
        'protocol_identity': PROTOCOL_IDENTITY,
        'population': A1_SIZE,
        'selection_seed': 7,
        'seed_role': 'explicit engineering sub-seed; not an execution master',
        'counts': [1000, 5000, 10000],
        'python': sys.version,
        'python_executable': sys.executable,
        'platform': platform.platform(),
        'created_utc': utc(),
        'attempts': [],
    }

    def persist():
        temporary = output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)

    persist()
    for count in ledger['counts']:
        replay = None
        for mode in ('timing', 'tracemalloc-replay'):
            attempt = dict(id=f"B{len(ledger['attempts'])+1}", requested=count,
                           mode=mode, status='started', started_utc=utc(),
                           resource_cap_event=False, numeric_abort=False)
            ledger['attempts'].append(attempt)
            persist()  # Disclose the pass before invoking the iterator.
            emitted, first, last, rank_sum = 0, None, None, 0
            if mode == 'tracemalloc-replay':
                tracemalloc.start()
            started = time.perf_counter()
            error = None
            try:
                for rank in vitter_ranks(A1_SIZE, count, seed=7):
                    if not 0 <= rank < A1_SIZE or (last is not None and rank <= last):
                        raise RuntimeError('rank boundary/uniqueness violation')
                    if first is None:
                        first = rank
                    last = rank
                    rank_sum += rank
                    emitted += 1
                if emitted != count:
                    raise RuntimeError('wrong sample size')
                observation = (emitted, first, last, rank_sum)
                if replay is not None and observation != replay:
                    raise RuntimeError('traced replay summary differs')
                replay = observation
            except BaseException as exc:
                error = exc
                attempt.update(status='aborted', error_type=type(exc).__name__, error=str(exc),
                               numeric_abort=isinstance(exc, SamplingError),
                               resource_cap_event=isinstance(exc, SamplingError) and
                               any(label in str(exc) for label in ('limit', '4096', 'unresolved')))
            finally:
                attempt['elapsed_seconds'] = time.perf_counter() - started
                if mode == 'tracemalloc-replay':
                    attempt['peak_traced_bytes'] = tracemalloc.get_traced_memory()[1]
                    tracemalloc.stop()
                attempt.update(emitted=emitted, first_rank=first, last_rank=last,
                               rank_sum=rank_sum, finished_utc=utc())
                if error is None:
                    attempt['status'] = 'complete'
                persist()
                print(json.dumps(attempt), flush=True)
            if error is not None:
                raise SystemExit('Benchmark aborted; attempt disclosed, no retry or seed replacement')
    ledger['completed_utc'] = utc()
    persist()


if __name__ == '__main__':
    main()
