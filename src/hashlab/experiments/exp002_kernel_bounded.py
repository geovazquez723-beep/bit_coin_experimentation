"""Bounded production-format engineering fixture. Never production evidence.

Uses the frozen full A1 population and the true A3 structural class (rank-limited),
production derivation labels/keys under the engineering KAT domain, public master
0, and 78 candidate evaluations. It writes the same compact chunk format as the
production kernel so an independent verifier can exercise cross-stage, cursor and
cluster continuity. It has no production plan, quota, seed or scope parameters and
its scope string can never be promoted by an authenticator.
"""
from dataclasses import dataclass
from hashlib import sha256

from hashlab.candidates.vitter import a1_sample_ranks
from hashlab.hashing.sha256 import SHA256Engine
from .exp002 import A1_SIZE, a1_value, a2_key, a2_prefix, arm_subseed, sample_ranks
from .exp002_foundation import Accumulator, canonical
from .exp002_controls import (ControlEngine, ControlGeometry, Feistel64, N2Controls, PermutationControls,
                              control_keys, load_control_history)
from .exp002_s14 import load_s14
from .exp002_journal import durable_create, file_inventory
from .exp002_kernel_plan import FORMAT, observe_runtime, source_inventory
from .exp002_kernel_evidence import Attempt, ChunkWriter, create_root
from .exp002_kernel_disclosure import KernelFailure, PublicOutcome, failure_report, private_processing

BOUNDED_MASTER = 0          # public KAT master, not a beacon-derived seed
BOUNDED_DOMAIN = 'experiment-002-kat'
A3_STOP = 4096
ATTEMPT_CAP = 160
QUOTAS = {('A1', 'D'): 6, ('A1', 'V'): 6, ('A2', 'D'): 8, ('A2', 'V'): 8, ('A3', 'D'): 6, ('A3', 'V'): 6,
          ('N1', 'D'): 6, ('N1', 'V'): 6, ('N2', 'D'): 6, ('N2', 'V'): 6,
          ('P1', 'C'): 2, ('P2+', 'C'): 6, ('P2-', 'C'): 6}


@dataclass(frozen=True)
class BoundedPlan:
    """One fixed fixture; no geometry, seed, domain or scope parameters."""
    schema: str = 'hashlab-e002-bounded-kernel-plan-v1'

    def __post_init__(self):
        if self.schema != 'hashlab-e002-bounded-kernel-plan-v1':
            raise ValueError('bounded plan identity')

    def to_dict(self):
        return dict(schema=self.schema, scope='bounded-fixture',
                    seed=dict(kind='public-engineering', master=str(BOUNDED_MASTER), domain=BOUNDED_DOMAIN,
                              a1_a3_labels='experiment-002'),
                    geometry=dict(a1_size=A1_SIZE, a1_stage=6, a2_clusters=[0, 1500], a2_nonces=8,
                                  a3_size=A3_STOP, a3_stage=6, control_stage=6, p1=2, p2=6),
                    evidence_format=FORMAT, confirmatory_complete=False, qa2=False)

    def serialize(self):
        return canonical(self.to_dict())

    @property
    def fingerprint(self):
        return sha256(self.serialize()).hexdigest()


def _bounded_inputs(audit_root, repository):
    history = load_s14(audit_root, repository)
    n1, n2 = control_keys(BOUNDED_MASTER, BOUNDED_DOMAIN)
    permutation = Feistel64(n1)
    inverse = load_control_history(audit_root, repository, permutation)
    key = a2_key(BOUNDED_MASTER, BOUNDED_DOMAIN)
    prefixes = tuple(a2_prefix(key, j) for j in range(3000))
    return history, permutation, inverse, n2, prefixes


def _scheduled(history, permutation, inverse, n2_key, prefixes):
    index = {(a, s): 0 for a in ('A1', 'A3') for s in ('D', 'V')}
    seeds = {arm: (arm_subseed(BOUNDED_MASTER, arm, 'selection'),
                   arm_subseed(BOUNDED_MASTER, arm, 'stage-allocation')) for arm in ('A1', 'A3')}
    for stage, rank in a1_sample_ranks(A1_SIZE, 6, 6, selection_seed=seeds['A1'][0], stage_seed=seeds['A1'][1]):
        yield Attempt('A1', stage, a1_value(rank), index['A1', stage], population_rank=rank)
        index['A1', stage] += 1
    for cluster in (0, 1500):
        for nonce in range(8):
            yield Attempt('A2', 'D' if cluster == 0 else 'V', prefixes[cluster] + nonce.to_bytes(4, 'little'),
                          nonce, source_index=cluster*10000+nonce, cluster=cluster)
    excluded = tuple(r for r in history.exclusions.ranks if r < A3_STOP)
    for stage, rank in sample_ranks(A3_STOP, 6, 6, selection_seed=seeds['A3'][0],
                                    stage_seed=seeds['A3'][1], excluded=excluded):
        yield Attempt('A3', stage, history.exclusions.population.unrank(rank).to_bytes(8, 'big'),
                      index['A3', stage], population_rank=rank)
        index['A3', stage] += 1
    geometry = ControlGeometry(BOUNDED_DOMAIN, 6, 2, 6)
    prp, n2 = PermutationControls(permutation, inverse, geometry), N2Controls(n2_key, prefixes, geometry)
    for provider in (prp.n1(), n2.attempts(), prp.positives()):
        for row in provider:
            yield Attempt.from_provider(row)
    if prp.failed or n2.failed:
        raise ValueError('failed provider')


def _coordinate(root, attempts):
    acc, engine, writer = Accumulator(), SHA256Engine(), ChunkWriter(root)
    counts = {k: 0 for k in QUOTAS}
    rejections = {a: 0 for a, _ in QUOTAS}
    evaluations = blocks = attempted = successes = 0
    try:
        for attempt in attempts:
            attempted += 1
            if attempted > ATTEMPT_CAP:
                raise ValueError('bounded attempt cap')
            if attempt.reasons:
                rejections[attempt.arm] += 1
                writer.add(attempt)
                continue
            key = attempt.arm, attempt.stage
            if key not in counts or counts[key] >= QUOTAS[key] or attempt.accepted_index != counts[key]:
                raise ValueError('accepted quota/index continuity')
            raw = engine.digest(attempt.candidate)
            transformed = ControlEngine(attempt.arm if not attempt.arm.startswith('A') else 'N1').transform(raw)
            effective = bytes.fromhex(transformed['effective_digest_hex'])
            acc.add(attempt.record(), effective)
            writer.add(attempt, raw, effective)
            counts[key] += 1
            evaluations += 1
            blocks += (len(attempt.candidate) + 72) // 64
            successes += int(transformed['success'])
        if counts != QUOTAS:
            raise ValueError('incomplete bounded geometry')
        accounting = acc.snapshot()
        chunk_info = writer.finish()
        durable_create(root/'accounting.json', canonical(accounting))
        summary = dict(schema='hashlab-e002-kernel-completion-v1', scope='bounded-fixture', format=FORMAT,
            plan_sha256=BoundedPlan().fingerprint, confirmatory_complete=False, qa2=False,
            evaluations=evaluations, compression_blocks=blocks, successes=successes,
            rejections=rejections, **chunk_info, plan=file_inventory(root/'plan.json'),
            history=file_inventory(root/'history.json'), environment=file_inventory(root/'environment.json'),
            accounting=file_inventory(root/'accounting.json'))
        (root/'INCOMPLETE').unlink()
        raw_summary = canonical(summary)
        durable_create(root/'complete.json', raw_summary)
        return sha256(raw_summary).hexdigest()
    except BaseException:
        writer.abandon()
        raise


def run_bounded(destination, *, audit_root, repository_root):
    """Fixed 78 evaluations; failure retains evidence and never resumes or repairs."""
    root = outcome = None
    try:
        with private_processing():
            plan = BoundedPlan()
            history, permutation, inverse, n2_key, prefixes = _bounded_inputs(audit_root, repository_root)
            root = create_root(destination, repository=repository_root, audit_root=audit_root)
            durable_create(root/'plan.json', plan.serialize())
            durable_create(root/'history.json', canonical(inverse.summary()))
            durable_create(root/'environment.json', canonical(dict(
                schema='hashlab-e002-kernel-bounded-environment-v1', scope='bounded-fixture',
                runtime=observe_runtime().to_dict(),
                sources=[x.to_dict() for x in source_inventory(repository_root)],
                source_commit_correspondence='unqualified;engineering-working-copy',
                runtime_approval='not-claimed')))
            pin = _coordinate(root, _scheduled(history, permutation, inverse, n2_key, prefixes))
            outcome = PublicOutcome('complete', 'bounded-fixture', pin)
    except BaseException:
        if root is not None:
            try:
                durable_create(root/'failure.json', canonical(failure_report('F1')))
            except BaseException:
                pass
    if outcome is None:
        raise KernelFailure('E002 bounded attempt failed; evidence retained; primary/validation withheld') from None
    return outcome
