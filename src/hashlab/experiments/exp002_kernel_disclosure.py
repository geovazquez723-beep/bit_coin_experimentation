"""Normal-path disclosure control, not protection from a hostile sole operator.

Single-threaded kernel only. Private files remain complete; filesystem access,
debuggers, native writes and deliberate code bypass are outside this boundary.
"""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from dataclasses import dataclass
import io
import logging
import sys


class KernelFailure(RuntimeError):
    """Sanitized public exception: never includes an internal error or counter."""


class _Discard(io.TextIOBase):
    def write(self, value): return len(value)
    def flush(self): pass


@contextmanager
def private_processing():
    """Discard incidental Python output and logging; retain no sensitive buffer."""
    previous=logging.root.manager.disable
    logging.disable(max(previous,sys.maxsize))
    try:
        with redirect_stdout(_Discard()), redirect_stderr(_Discard()):
            yield
    finally:
        logging.disable(previous)


@dataclass(frozen=True)
class PublicOutcome:
    status: str
    scope: str
    completion_sha256: str | None = None

    def to_dict(self):
        return dict(status=self.status,scope=self.scope,completion_sha256=self.completion_sha256)


def progress(phase, processed):
    if phase not in ('initializing','processing','finalizing') or type(processed) is not int or processed<0:
        raise ValueError('invalid public progress')
    # No arbitrary diagnostic/callback input or per-arm/cluster outcome fields.
    return dict(phase=phase,processed=processed)


def failure_report(failure):
    if failure not in ('F1','F2','F3'): raise ValueError('F4 requires verified control inference')
    return dict(status='INCOMPLETE' if failure!='F3' else 'HARNESS INTEGRITY FAILURE',
                failure=failure,primary='withheld',validation='withheld')


_INFERENCE = object()


class RestrictedInference:
    __slots__=('__payload','__gate_failed')

    def __init__(self, payload, *, _token=None):
        if _token is not _INFERENCE: raise ValueError('authenticated inference required')
        self.__payload=payload
        self.__gate_failed=payload['controls']['statistical_gate_passed'] is False

    def __repr__(self): return '<RestrictedInference primary=withheld validation=withheld>'

    def __reduce__(self): raise TypeError('private inference cannot be serialized or copied')
    __getstate__ = __reduce__

    def inspect(self):
        return dict(primary='withheld',validation='withheld',final_disclosure='authorization-unavailable')

    def disclose_f4(self):
        if not self.__gate_failed: raise PermissionError('F4 disclosure requires control-gate failure')
        # Mandatory failure disclosure is only available after authenticated complete inference.
        import copy
        blocked=any(r['difference']=='REP' for r in self.__payload['controls']['nulls'])
        return dict(status='BLOCKED' if blocked else 'UNINFORMATIVE',failure='F4',
                    statistics=copy.deepcopy(self.__payload))

    def disclose_final(self, *args, **kwargs):
        raise PermissionError('authorized final-disclosure adapter is not implemented')


def inspect_evidence(root, plan, pin):
    from .exp002_kernel_plan import EngineeringPlan, ProductionPlan
    if type(plan) is ProductionPlan:
        return dict(scope='production-disabled',primary='withheld',validation='withheld')
    if type(plan) is not EngineeringPlan: raise ValueError('typed plan required')
    from .exp002_kernel import authenticate_capture
    capture=authenticate_capture(root,plan=plan,completion_sha256=pin)
    return dict(scope='engineering-only',confirmatory_complete=False,
                accounting=capture.engineering_accounting())
