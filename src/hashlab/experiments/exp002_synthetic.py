"""E002-I1 fixed synthetic integration only; no research/QA2 entry point.

Uses accepted samplers, encoders, hash engine, record and accounting contracts.
The fixed geometry is deliberately separate from the immutable scientific plan.
No real master, beacon, commitment, statistical classification or controls.
"""
from hashlib import sha256
from pathlib import Path
import os

from hashlab.candidates.vitter import a1_sample_ranks
from hashlab.hashing.sha256 import SHA256Engine
from hashlab.hashing.target import digest_to_int, is_success
from .exp002 import (Config, a1_value, a2_prefix, a2_candidate, a2_stage,
                     validate_prefixes, sample_ranks)
from .exp002_foundation import Accumulator, CandidateRecord, canonical, validate_accounting
from .exp002_journal import durable_create, file_inventory, require_plain
from .exp002_r9_contracts import ACTIVE_PROTOCOL, SCIENTIFIC_BASELINE
from .exp002_s14 import load_s14


def fixture_spec():
    """Public engineering constants, not derived experiment sub-seeds."""
    return dict(schema='hashlab-e002-i1-fixture-v1', scope='synthetic-only',
                active_protocol=ACTIVE_PROTOCOL, scientific_baseline=SCIENTIFIC_BASELINE,
                target=str(Config().target), per_arm_stage=32, a1_size=256,
                a3_rank_stop=4096, a1_selection_seed=101, a1_stage_seed=102,
                a3_selection_seed=201, a3_stage_seed=202,
                a2_fixture_key_hex=b'E002-I1!'.hex(), a2_clusters=[0, 1500],
                a2_nonce_stop=32, confirmatory_complete=False, qa2=False)


def fixture_candidates(history):
    spec = fixture_spec()
    indices = {(arm, stage): 0 for arm in ('A1', 'A2', 'A3') for stage in ('D', 'V')}

    def record(arm, stage, candidate, cluster=None):
        index = indices[arm, stage]
        indices[arm, stage] += 1
        return CandidateRecord(arm, stage, index, candidate.hex(), cluster)

    for stage, rank in a1_sample_ranks(spec['a1_size'], 32, 32,
                                      selection_seed=101, stage_seed=102):
        yield record('A1', stage, a1_value(rank)), rank
    prefixes = tuple(a2_prefix(b'E002-I1!', cluster) for cluster in (0, 1500))
    validate_prefixes(prefixes, 2)
    for cluster, prefix in zip((0, 1500), prefixes):
        for nonce in range(32):
            yield record('A2', a2_stage(cluster), a2_candidate(prefix, nonce), cluster), None
    # Algorithm S iterates only this explicit prefix of the true rank class.
    excluded = tuple(r for r in history.exclusions.ranks if r < spec['a3_rank_stop'])
    for stage, rank in sample_ranks(spec['a3_rank_stop'], 32, 32,
                                    selection_seed=201, stage_seed=202, excluded=excluded):
        value = history.exclusions.population.unrank(rank).to_bytes(8, 'big')
        yield record('A3', stage, value), rank


def run_fixture(destination, *, audit_root, repository_root):
    """Exclusive new directory; completion marker is durably written last.

    An exception/interruption leaves partial bytes intact and no valid completion
    report. No resume, overwrite or automatic retry is supported. fsync durability
    remains subject to OS/filesystem guarantees.
    """
    history = load_s14(audit_root, repository_root)
    root = Path(destination).absolute()
    repository = Path(repository_root).resolve()
    if (root.resolve().is_relative_to(repository/'results')
            or root.resolve().is_relative_to(Path(audit_root).resolve())):
        raise ValueError('synthetic output forbidden beneath retained results')
    for parent in root.parents:
        require_plain(parent, directory=True)
        if (parent/'manifest.sha256').exists() or (parent/'complete.json').exists():
            raise ValueError('output beneath completed evidence')
    root.mkdir()
    durable_create(root/'fixture.json', canonical(fixture_spec()))
    durable_create(root/'history.json', canonical(history.identity()))
    accumulator = Accumulator()
    engine = SHA256Engine()
    seen = set()  # Bounded 192 actual byte strings; indices never prove uniqueness.
    excluded = set(history.exclusions.ranks)
    with (root/'records.jsonl').open('xb') as out:
        count = 0
        for record, rank in fixture_candidates(history):
            if count >= 192:
                raise ValueError('fixture candidate hash budget exceeded')
            candidate = bytes.fromhex(record.candidate_hex)
            if candidate in seen:
                raise ValueError('duplicate candidate bytes across fixture stages/arms')
            seen.add(candidate)
            if record.arm == 'A3':
                actual_rank = history.exclusions.population.rank(int.from_bytes(candidate, 'big'))
                if actual_rank != rank or actual_rank in excluded or not 0 <= actual_rank < 4096:
                    raise ValueError('A3 exclusion/boundary violation')
            digest = engine.digest(candidate)
            accumulator.add(record, digest)
            row = dict(sequence=count, candidate=record.to_dict(), population_rank=rank,
                       digest_hex=digest.hex(), success=is_success(digest_to_int(digest), Config().target))
            out.write(canonical(row)+b'\n')
            count += 1
        out.flush()
        os.fsync(out.fileno())
    accounting = accumulator.snapshot()
    validate_accounting(accounting)
    if count != 192 or any(row['trials'] != (32 if row['arm'] in ('A1','A2','A3') else 0)
                           for row in accounting['streams']):
        raise ValueError('incomplete fixture geometry')
    durable_create(root/'accounting.json', canonical(accounting))
    files = {p.name: file_inventory(p) for p in sorted(root.iterdir())}
    report = dict(schema='hashlab-e002-i1-complete-v1', scope='synthetic-only',
                  synthetic_complete=True, confirmatory_complete=False, qa2=False,
                  records=count, candidate_compression_blocks=256,
                  files=files)
    durable_create(root/'complete.json', canonical(report))
    return sha256(canonical(report)).hexdigest()
