"""Fixed 14-evaluation I2 fixture; no configurable experiment entry point."""
from hashlib import sha256
from pathlib import Path
import os

from .exp002 import a2_key, a2_prefix, validate_prefixes
from .exp002_controls import (ControlGeometry, Feistel64, control_keys, load_control_history,
                             PermutationControls, N2Controls, ControlEngine, accepted_record)
from .exp002_foundation import Accumulator, canonical, validate_accounting
from .exp002_journal import durable_create, file_inventory, require_plain
from .exp002_r9_contracts import ACTIVE_PROTOCOL, SCIENTIFIC_BASELINE


def fixture_spec():
    return dict(schema='hashlab-e002-i2-fixture-v1', scope='synthetic-only',
                active_protocol=ACTIVE_PROTOCOL, scientific_baseline=SCIENTIFIC_BASELINE,
                domain='experiment-002-kat', engineering_input=0, per_stage=2, p1=2, p2=2,
                a2_prefixes=3000, target=str(2**248), n1_stop=30_999_999,
                p_start=str(2**63), confirmatory_complete=False, qa2=False,
                n2_uniqueness='probabilistic-not-verified', candidate_hash_budget=14)


def fixture_inputs(audit_root, repository_root):
    n, two = control_keys(0, 'experiment-002-kat')
    permutation = Feistel64(n)
    history = load_control_history(audit_root, repository_root, permutation)
    key = a2_key(0, 'experiment-002-kat')
    prefixes = tuple(a2_prefix(key, j) for j in range(3000))
    validate_prefixes(prefixes, 3000)
    return permutation, history, two, prefixes


def run_fixture(destination, *, audit_root, repository_root):
    """Authenticate first, write exclusively, durably publish completion last."""
    root, repository = Path(destination).absolute(), Path(repository_root).resolve()
    if (root.resolve().is_relative_to(repository/'results') or
            root.resolve().is_relative_to(Path(audit_root).resolve())):
        raise ValueError('synthetic output forbidden beneath retained results')
    for parent in root.parents:
        require_plain(parent, directory=True)
        if (parent/'manifest.sha256').exists() or (parent/'complete.json').exists():
            raise ValueError('output beneath completed evidence')
    permutation, history, key, prefixes = fixture_inputs(audit_root, repository_root)
    root.mkdir()
    durable_create(root/'fixture.json', canonical(fixture_spec()))
    durable_create(root/'history.json', canonical(history.summary()))
    geometry = ControlGeometry('experiment-002-kat', 2, 2, 2)
    prp = PermutationControls(permutation, history, geometry)
    n2 = N2Controls(key, prefixes, geometry)
    accumulator = Accumulator()
    count = blocks = attempts = 0
    with (root/'records.jsonl').open('xb') as records, (root/'attempts.jsonl').open('xb') as audit:
        for stream in (prp.n1(), n2.attempts(), prp.positives()):
            for attempt in stream:
                # Fixed fixture can fail, never enlarge or hunt for successes.
                if attempts >= 128:
                    raise ValueError('fixture attempt budget exceeded')
                audit.write(canonical(dict(sequence=attempts, **attempt))+b'\n')
                attempts += 1
                if attempt['reasons']:
                    continue
                if count >= 14:
                    raise ValueError('fixture candidate hash budget exceeded')
                record = accepted_record(attempt)
                candidate = bytes.fromhex(record.candidate_hex)
                result = ControlEngine(record.arm).evaluate(candidate)
                accumulator.add(record, bytes.fromhex(result['effective_digest_hex']))
                records.write(canonical(dict(sequence=count, candidate=record.to_dict(),
                                             attempt_sequence=attempts-1, **result))+b'\n')
                count += 1
                blocks += (len(candidate)+9+63)//64
        for out in (records, audit):
            out.flush()
            os.fsync(out.fileno())
    accounting = accumulator.snapshot()
    validate_accounting(accounting)
    expected = {(a, s): 2 for a in ('N1','N2') for s in ('D','V')}
    expected.update({(a,'C'):2 for a in ('P1','P2+','P2-')})
    if (count != 14 or blocks != 18 or prp.failed or n2.failed or
            any(row['trials'] != expected.get((row['arm'],row['stage']),0) for row in accounting['streams'])):
        raise ValueError('incomplete I2 fixture geometry')
    durable_create(root/'accounting.json', canonical(accounting))
    durable_create(root/'rejections.json', canonical(dict(prp.counts, N2=n2.counts)))
    files = {p.name:file_inventory(p) for p in sorted(root.iterdir())}
    report = dict(schema='hashlab-e002-i2-complete-v1', scope='synthetic-only',
                  synthetic_complete=True, confirmatory_complete=False, qa2=False,
                  records=count, attempts=attempts, candidate_compression_blocks=blocks, files=files)
    durable_create(root/'complete.json', canonical(report))
    return sha256(canonical(report)).hexdigest()
