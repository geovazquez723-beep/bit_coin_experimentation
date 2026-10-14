"""Production-only measured inference seam. No synthetic-to-production promotion."""
from .exp002_foundation import validate_accounting
from .exp002_kernel import VerifiedCapture
from .exp002_kernel_plan import ProductionPlan
from .exp002_kernel_disclosure import RestrictedInference, _INFERENCE, private_processing, KernelFailure
from .exp002_integration_statistics import persisted
from hashlab.statistics import exp002 as primary, exp002_secondary as secondary


def _calculate(accounting):
    """Count calculation shared by unit qualification; no observation authenticity claim."""
    validate_accounting(accounting,require_complete=True)
    rows={(r['arm'],r['stage']):r for r in accounting['streams']}
    def arm(a):
        return primary.Arm(a,*[primary.Stage(s,rows[a,s]['successes'],
            clusters=tuple(rows[a,s]['cluster_successes']) if a in ('A2','N2') else None)
            for s in ('D','V')])
    return dict(primary=persisted(primary.analyze([arm(a) for a in ('A1','A2','A3')])),
        controls=persisted(primary.controls([arm(a) for a in ('N1','N2')],
            *(rows[a,'C']['successes'] for a in ('P1','P2+','P2-')))),
        secondary=persisted(secondary.analyze_secondary(accounting)))


def infer_measured(capture, *, plan):
    """Requires authenticated complete production capture, never raw/count fixtures.

    The current engineering capture validator cannot issue this capability.
    The next independent production finalization increment must supply it.
    """
    result=None
    try:
        with private_processing():
            if type(capture) is not VerifiedCapture or type(plan) is not ProductionPlan:
                raise ValueError('authenticated production capture required')
            accounting=capture._production_accounting(plan)
            result=RestrictedInference(_calculate(accounting),_token=_INFERENCE)
    except BaseException:
        pass
    if result is None:
        raise KernelFailure('production inference unavailable or invalid; primary/validation withheld') from None
    return result
