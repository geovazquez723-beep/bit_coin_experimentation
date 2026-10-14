"""Unified streaming execution kernel. Public production activation is unavailable.

Only the fixed engineering adapter can evaluate candidates. The shared scheduler,
eligibility, accounting and binary capture implement frozen production geometry.
No command, authorization parser, beacon client, retry or resume is provided.
"""
from hashlib import sha256
from pathlib import Path
import bisect
import os

from hashlab.candidates.vitter import a1_sample_ranks
from hashlab.hashing.sha256 import SHA256Engine
from .exp002 import (A1_SIZE, HammingPopulation, a1_value, a2_prefix, a2_key,
                     a2_stream, sample_ranks, arm_subseed, in_a1, in_a3, validate_prefixes)
from .exp002_foundation import Accumulator, LIMITS, canonical, decode, validate_accounting
from .exp002_controls import (ControlGeometry, PermutationControls, N2Controls, Feistel64,
                              ControlEngine, control_keys, load_control_history, N1_STOP, P_START)
from .exp002_s14 import load_s14
from .exp002_journal import durable_create, file_inventory, require_plain
from .exp002_kernel_plan import ProductionPlan, EngineeringPlan, FORMAT, source_inventory, observe_runtime
from .exp002_kernel_evidence import Attempt, ChunkWriter, create_root, iter_chunks
from .exp002_kernel_disclosure import KernelFailure, PublicOutcome, private_processing, failure_report

_CAPTURE = object()


def run_production(*args, **kwargs):
    """Unconditional action guard, before seed interpretation, I/O or generation."""
    raise PermissionError('E002 production execution is disabled; no activation capability exists')


def _engineering_inputs(audit_root, repository):
    history=load_s14(audit_root,repository)
    n1,n2=control_keys(0,'experiment-002-kat')
    permutation=Feistel64(n1)
    inverse=load_control_history(audit_root,repository,permutation)
    prefixes=tuple(a2_prefix(b'E002-I1!',j) for j in range(3000))
    return history,permutation,inverse,n2,prefixes


def _scheduled_attempts(plan, history, permutation, inverse, n2_key, prefixes, arm_seeds):
    """Lazy common schedule; inputs owned by coordinator, never a public seed API.

    Production callers must eventually obtain authenticated seed material in a
    separately reviewed activation adapter. This function grants no permission.
    """
    production=type(plan) is ProductionPlan
    if not production and type(plan) is not EngineeringPlan: raise ValueError('plan type')
    size,n,stop=(A1_SIZE,15_000_000,HammingPopulation().size) if production else (256,32,4096)
    indices={(a,s):0 for a in ('A1','A3') for s in ('D','V')}
    for stage,rank in a1_sample_ranks(size,n,n,selection_seed=arm_seeds['A1'][0],stage_seed=arm_seeds['A1'][1]):
        index=indices['A1',stage]; indices['A1',stage]+=1
        yield Attempt('A1',stage,a1_value(rank),index,population_rank=rank)
    validate_prefixes(prefixes,3000)
    if production:
        for stage,cluster,nonce,raw in a2_stream(prefixes):
            yield Attempt('A2',stage,raw,(cluster%1500)*10000+nonce,
                          source_index=cluster*10000+nonce,cluster=cluster)
    else:
        for cluster in (0,1500):
            for nonce in range(32):
                yield Attempt('A2','D' if cluster==0 else 'V',prefixes[cluster]+nonce.to_bytes(4,'little'),
                              nonce,source_index=cluster*10000+nonce,cluster=cluster)
    excluded=history.exclusions.ranks if production else tuple(r for r in history.exclusions.ranks if r<stop)
    for stage,rank in sample_ranks(stop,n,n,selection_seed=arm_seeds['A3'][0],
                                  stage_seed=arm_seeds['A3'][1],excluded=excluded):
        index=indices['A3',stage];indices['A3',stage]+=1
        yield Attempt('A3',stage,history.exclusions.population.unrank(rank).to_bytes(8,'big'),
                      index,population_rank=rank)
    geometry=ControlGeometry() if production else ControlGeometry('experiment-002-kat',2,2,2)
    prp=PermutationControls(permutation,inverse,geometry)
    n2=N2Controls(n2_key,prefixes,geometry)
    for provider in (prp.n1(),n2.attempts(),prp.positives()):
        for row in provider: yield Attempt.from_provider(row)
    if prp.failed or n2.failed: raise ValueError('failed provider')


def _production_inputs(plan, history, permutation, inverse, n2_key, prefixes, *, master):
    """No unchecked production master is accepted, including internal adapters."""
    raise PermissionError('authenticated production seed adapter is unavailable')


class _Eligibility:
    def __init__(self,plan,history,permutation,inverse,prefixes):
        self.production=type(plan) is ProductionPlan
        self.history,self.permutation,self.inverse,self.prefixes=history,permutation,inverse,prefixes
        validate_prefixes(prefixes,3000)
        if inverse.permutation_key!=permutation.key: raise ValueError('inverse key mismatch')
        self.prefix_set=frozenset(prefixes)
        self.cursor={'N1':0,'P':P_START,'N2':0}
        self.previous_rank={'A1':-1,'A3':-1}
        self.arm_position=-1
        self.accepted={'A2':0,'N1':0,'N2':0}

    def check(self,a):
        if type(a) is not Attempt: raise ValueError('typed attempt')
        order=('A1','A2','A3','N1','N2','P1','P2+','P2-').index(a.arm)
        if order<self.arm_position: raise ValueError('generation arm order')
        self.arm_position=order
        raw=a.candidate;value=int.from_bytes(raw,'big')
        if a.arm in ('A1','A3'):
            rank=a.population_rank
            stop=(A1_SIZE if a.arm=='A1' else HammingPopulation().size) if self.production else (256 if a.arm=='A1' else 4096)
            if (type(rank) is not int or not self.previous_rank[a.arm]<rank<stop or a.reasons
                    or any(x is not None for x in (a.source_index,a.byte_offset,a.cluster))):
                raise ValueError('primary rank/source continuity')
            self.previous_rank[a.arm]=rank
            if a.arm=='A1':
                if raw!=a1_value(rank): raise ValueError('A1 encoding')
                # Authenticated S1.4 proves zero complete-history A1 intersection.
            else:
                ranks=self.history.exclusions.ranks
                at=bisect.bisect_left(ranks,rank)
                if ((at<len(ranks) and ranks[at]==rank) or self.history.exclusions.population.rank(value)!=rank):
                    raise ValueError('A3 exclusion/encoding')
        elif a.arm=='A2':
            if a.reasons or a.cluster is None or a.population_rank is not None or a.byte_offset is not None:
                raise ValueError('A2 provenance')
            nonce=int.from_bytes(raw[76:],'little')
            position=self.accepted['A2']
            expected_cluster=position//10000 if self.production else (0 if position<32 else 1500)
            expected_nonce=position%10000 if self.production else position%32
            if (a.source_index!=a.cluster*10000+nonce or raw[:76]!=self.prefixes[a.cluster]
                    or (a.cluster,nonce)!=(expected_cluster,expected_nonce)
                    or nonce>=10000 or (not self.production and (a.cluster not in (0,1500) or nonce>=32))):
                raise ValueError('A2 source/prefix/nonce')
            self.accepted['A2']+=1
        elif a.arm=='N2':
            if a.source_index!=self.cursor['N2'] or a.byte_offset!=80*a.source_index or a.population_rank is not None:
                raise ValueError('N2 raw continuity')
            self.cursor['N2']+=1
            reasons=('A2',) if raw[:76] in self.prefix_set and int.from_bytes(raw[76:],'little')<10000 else ()
            if a.reasons!=reasons: raise ValueError('N2 membership rejection')
            local_quota=15_000_000 if self.production else 2
            position=self.accepted['N2']
            expected_stage='D' if position<local_quota else 'V'
            expected_cluster=(position%local_quota)//10000+(1500 if expected_stage=='V' else 0)
            if (a.stage!=expected_stage or (not reasons and
                    (a.accepted_index,a.cluster)!=(position%local_quota,expected_cluster))
                    or (reasons and a.cluster is not None)):
                raise ValueError('N2 accepted-order stage/cluster')
            self.accepted['N2']+=not reasons
        else:
            group='N1' if a.arm=='N1' else 'P'
            if (a.source_index!=self.cursor[group] or a.source_index>=(N1_STOP if group=='N1' else 2**64)
                    or any(x is not None for x in (a.population_rank,a.byte_offset,a.cluster))):
                raise ValueError('control source continuity')
            self.cursor[group]+=1
            if self.permutation.forward(a.source_index)!=value: raise ValueError('control encoding')
            reasons=tuple(name for name,hit in (('C1',in_a1(raw)),('C3',in_a3(raw)),
                                               ('E001',a.source_index in self.inverse.indices)) if hit)
            if a.reasons!=reasons: raise ValueError('control rejection')
            if group=='N1':
                quota=15_000_000 if self.production else 2
                stage='D' if self.accepted['N1']<quota else 'V'
                if a.stage!=stage: raise ValueError('N1 accepted-order stage')
                self.accepted['N1']+=not reasons


def _quotas(plan):
    if type(plan) is ProductionPlan: return {(a,s):n for a,s,n in LIMITS}
    if type(plan) is EngineeringPlan:
        return {(a,s):(32 if a.startswith('A') else 2) for a,s,_ in LIMITS}
    raise ValueError('typed plan')


def _coordinate(root, plan, attempts, eligibility):
    # A second unconditional boundary prevents private-call production dispatch.
    if type(plan) is ProductionPlan: run_production()
    if type(plan) is not EngineeringPlan: raise ValueError('typed plan required')
    quotas=_quotas(plan);acc=Accumulator();engine=SHA256Engine();writer=ChunkWriter(root)
    counts={k:0 for k in quotas};rejections={a:0 for a,_,_ in LIMITS}
    evaluations=blocks=attempted=successes=0
    try:
        for attempt in attempts:
            if type(plan) is EngineeringPlan and attempted>=320: raise ValueError('engineering attempt cap')
            eligibility.check(attempt)
            attempted+=1
            if attempt.reasons:
                rejections[attempt.arm]+=1;writer.add(attempt);continue
            key=attempt.arm,attempt.stage
            if counts[key]>=quotas[key] or attempt.accepted_index!=counts[key]:
                raise ValueError('accepted quota/index continuity')
            record=attempt.record()
            raw=engine.digest(attempt.candidate)  # Exactly one base evaluation.
            transformed=ControlEngine(attempt.arm if not attempt.arm.startswith('A') else 'N1').transform(raw)
            effective=bytes.fromhex(transformed['effective_digest_hex'])
            acc.add(record,effective);writer.add(attempt,raw,effective)
            counts[key]+=1;evaluations+=1;blocks+=(len(attempt.candidate)+72)//64
            successes+=int(transformed['success'])
        expected_evaluations=sum(quotas.values())
        expected_blocks=sum(n*(2 if a in ('A2','N2') else 1) for (a,s),n in quotas.items())
        if counts!=quotas or (evaluations,blocks)!=(expected_evaluations,expected_blocks):
            raise ValueError('incomplete exact geometry')
        accounting=acc.finish() if type(plan) is ProductionPlan else acc.snapshot()
        validate_accounting(accounting,require_complete=type(plan) is ProductionPlan)
        chunk_info=writer.finish()
        durable_create(root/'accounting.json',canonical(accounting))
        summary=dict(schema='hashlab-e002-kernel-completion-v1',scope='engineering-only',
            format=FORMAT,plan_sha256=plan.fingerprint,confirmatory_complete=False,qa2=False,
            evaluations=evaluations,compression_blocks=blocks,successes=successes,
            rejections=rejections,**chunk_info,plan=file_inventory(root/'plan.json'),
            history=file_inventory(root/'history.json'),environment=file_inventory(root/'environment.json'),
            accounting=file_inventory(root/'accounting.json'))
        # No external E4 seal/approval claim. The pin authenticates local capture only.
        # Completion follows all payload fsyncs; a leftover marker is always invalid.
        (root/'INCOMPLETE').unlink()
        raw_summary=canonical(summary);durable_create(root/'complete.json',raw_summary)
        return sha256(raw_summary).hexdigest()
    except BaseException:
        writer.abandon()
        raise


def run_engineering(destination, *, audit_root, repository_root):
    """Fixed 206 evaluations; no inputs for seed, quota, production scope or resume."""
    root=None;outcome=None
    try:
        with private_processing():
            plan=EngineeringPlan()
            history,permutation,inverse,n2_key,prefixes=_engineering_inputs(audit_root,repository_root)
            root=create_root(destination,repository=repository_root,audit_root=audit_root)
            durable_create(root/'plan.json',plan.serialize())
            durable_create(root/'history.json',canonical(inverse.summary()))
            durable_create(root/'environment.json',canonical(dict(
                schema='hashlab-e002-kernel-engineering-environment-v1',scope='engineering-only',
                runtime=observe_runtime().to_dict(),sources=[x.to_dict() for x in source_inventory(repository_root)],
                source_commit_correspondence='unqualified;engineering-working-copy',
                runtime_approval='not-claimed')))
            attempts=_scheduled_attempts(plan,history,permutation,inverse,n2_key,prefixes,
                                         {'A1':(101,102),'A3':(201,202)})
            pin=_coordinate(root,plan,attempts,_Eligibility(plan,history,permutation,inverse,prefixes))
            outcome=PublicOutcome('complete','engineering-only',pin)
    except BaseException:
        # Do not include exception text/locals, primary counts or derived diagnostics.
        # Partial binary bytes/locks remain; even disclosure I/O failure cannot complete.
        if root is not None:
            try: durable_create(root/'failure.json',canonical(failure_report('F1')))
            except BaseException: pass
    if outcome is None:
        raise KernelFailure('E002 kernel attempt failed; evidence retained; primary/validation withheld') from None
    return outcome


class VerifiedCapture:
    """Opaque counts authenticated to an externally supplied local completion pin.

    Transport/accounting authentication is not independent outcome verification.
    Engineering capture can never enter the production inference adapter.
    """
    __slots__=('__accounting','__plan','__pin')
    def __init__(self,accounting,plan,pin,*,_token=None):
        if _token is not _CAPTURE: raise ValueError('capture must be authenticated')
        self.__accounting=canonical(accounting);self.__plan=plan;self.__pin=pin

    def __repr__(self): return '<VerifiedCapture primary=withheld validation=withheld>'

    def engineering_accounting(self):
        if type(self.__plan) is not EngineeringPlan: raise PermissionError('production observations withheld')
        return decode(self.__accounting)

    def _production_accounting(self,plan):
        if type(plan) is not ProductionPlan or type(self.__plan) is not ProductionPlan or plan!=self.__plan:
            raise ValueError('authenticated production capture required')
        return decode(self.__accounting)


def authenticate_capture(root, *, plan, completion_sha256):
    """Bounded read-only transport + measured accounting replay, no candidate rehash.

    Current production captures are rejected: resolved seed/finalization verification
    is deliberately the next increment. No synthetic receipt is promoted to measured.
    """
    if type(plan) is not EngineeringPlan:
        raise PermissionError('production capture authentication awaits independent production finalization')
    from .exp002_foundation import _hex
    _hex(completion_sha256,64)
    root=Path(root);require_plain(root,directory=True)
    if (root/'INCOMPLETE').exists(): raise ValueError('incomplete marker')
    path=root/'complete.json'
    if path.stat().st_size>8192 or file_inventory(path)['sha256']!=completion_sha256:
        raise ValueError('completion pin/size')
    report=decode(path.read_bytes())
    keys={'schema','scope','format','plan_sha256','confirmatory_complete','qa2','evaluations',
          'compression_blocks','successes','rejections','chunks','attempts','index','plan','history','environment','accounting'}
    if (type(report) is not dict or set(report)!=keys or report['schema']!='hashlab-e002-kernel-completion-v1'
            or report['scope']!='engineering-only' or report['format']!=FORMAT or report['qa2'] is not False
            or report['confirmatory_complete'] is not False or report['plan_sha256']!=plan.fingerprint
            or type(report['attempts']) is not int or not 206<=report['attempts']<=320
            or report['evaluations']!=206 or report['compression_blocks']!=274
            or type(report['chunks']) is not int or not 1<=report['chunks']<=320):
        raise ValueError('completion contract')
    if (type(report['successes']) is not int or type(report['rejections']) is not dict
            or set(report['rejections'])!={a for a,_,_ in LIMITS}
            or any(type(n) is not int or n<0 for n in report['rejections'].values())):
        raise ValueError('completion counter types')
    expected_names={'plan.json','history.json','environment.json','accounting.json','chunks.jsonl','complete.json'}
    entries=0
    for item in root.iterdir():
        require_plain(item)
        if item.name not in expected_names:
            import re
            m=re.fullmatch(r'chunk-([0-9]{8})\.bin',item.name)
            if m is None or int(m[1])>=report['chunks']: raise ValueError('extra evidence')
        entries+=1
    if entries!=len(expected_names)+report['chunks']: raise ValueError('missing evidence')
    for filename,key,cap in (('plan.json','plan',131072),('history.json','history',131072),
                             ('environment.json','environment',131072),
                             ('accounting.json','accounting',2_000_000),('chunks.jsonl','index',327680)):
        p=root/filename
        if p.stat().st_size>cap or file_inventory(p)!=report[key]: raise ValueError('payload integrity')
    if (root/'plan.json').read_bytes()!=plan.serialize(): raise ValueError('plan binding')
    acc=Accumulator();evaluations=blocks=successes=0;rejections={a:0 for a,_,_ in LIMITS}
    for attempt,raw,effective in iter_chunks(root,expected_chunks=report['chunks'],expected_attempts=report['attempts']):
        if attempt.reasons:
            rejections[attempt.arm]+=1;continue
        mode=attempt.arm if not attempt.arm.startswith('A') else 'N1'
        if bytes.fromhex(ControlEngine(mode).transform(raw)['effective_digest_hex'])!=effective:
            raise ValueError('raw/effective transformation mismatch')
        acc.add(attempt.record(),effective)
        evaluations+=1;blocks+=(len(attempt.candidate)+72)//64;successes+=int.from_bytes(effective,'big')<2**248
    accounting=acc.snapshot();validate_accounting(accounting)
    if (any(r['trials']!=_quotas(plan)[r['arm'],r['stage']] for r in accounting['streams'])
            or (evaluations,blocks,successes,rejections)!=(report['evaluations'],report['compression_blocks'],report['successes'],report['rejections'])
            or (root/'accounting.json').read_bytes()!=canonical(accounting)):
        raise ValueError('capture accounting/completeness mismatch')
    return VerifiedCapture(accounting,plan,completion_sha256,_token=_CAPTURE)
