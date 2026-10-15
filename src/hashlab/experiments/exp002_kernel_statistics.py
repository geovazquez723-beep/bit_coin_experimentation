"""Private persistence of measured production statistics from an authenticated capture.

Only a production ``VerifiedCapture`` (issued by ``authenticate_production_capture``)
reaches the calculation. The file holds unblinded numbers; creating it is a deliberate
step and it is never produced by capture authentication. It does not authorize disclosure.
"""
from hashlib import sha256
import os
import stat

from .exp002_foundation import canonical
from .exp002_journal import durable_create
from .exp002_kernel import VerifiedCapture
from .exp002_kernel_plan import ProductionPlan
from .exp002_kernel_disclosure import KernelFailure, RestrictedInference, _INFERENCE, private_processing
from .exp002_kernel_inference import _calculate
from .exp002_finalization import STATISTICS_SCHEMA


def commit_statistics(capture, *, plan, destination):
    """Returns (RestrictedInference, statistics_sha256); failures are sanitized."""
    result = None
    try:
        with private_processing():
            if type(capture) is not VerifiedCapture or type(plan) is not ProductionPlan:
                raise ValueError('authenticated production capture required')
            accounting = capture._production_accounting(plan)
            payload = _calculate(accounting)
            raw = canonical(dict(schema=STATISTICS_SCHEMA, scope='measured-production',
                                 accounting_sha256=sha256(canonical(accounting)).hexdigest(),
                                 plan_sha256=plan.fingerprint,
                                 completion_sha256=capture._VerifiedCapture__pin,
                                 publication='not-authorized', result=payload))
            durable_create(destination, raw)
            os.chmod(destination, stat.S_IREAD)   # integrity protection only; not access control
            result = (RestrictedInference(payload, _token=_INFERENCE), sha256(raw).hexdigest())
    except BaseException:
        pass
    if result is None:
        raise KernelFailure('measured statistics unavailable or invalid; primary/validation withheld') from None
    return result
