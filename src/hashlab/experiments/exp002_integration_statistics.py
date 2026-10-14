"""I3 adapters only: immutable E2/E3/secondary contracts remain unchanged."""
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from fractions import Fraction
import math

from .exp002_foundation import validate_accounting
from hashlab.statistics import exp002 as primary, exp002_secondary as secondary


def persisted(value):
    """Canonical JSON-safe results: explicit exact rationals, decimal strings."""
    if is_dataclass(value):
        return persisted(asdict(value))
    if isinstance(value, Fraction):
        return dict(numerator=value.numerator, denominator=value.denominator)
    if isinstance(value, Decimal):
        return str(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('nonfinite inference result')
        return repr(value)
    if type(value) is dict:
        return {k:persisted(v) for k,v in value.items()}
    if type(value) in (tuple,list):
        return [persisted(v) for v in value]
    if value is None or type(value) in (str,int,bool):
        return value
    raise ValueError('unsupported inference result')


def statistical_inputs(accounting):
    """Same effective-count construction for measured partial and synthetic full data.

    This constructs inputs, never treats partial geometry as confirmatory.
    """
    validate_accounting(accounting)
    return dict(schema='hashlab-e002-i3-statistical-inputs-v1',
                frozen_geometry_complete=accounting['complete'],
                streams=[dict(arm=r['arm'],stage=r['stage'],trials=r['trials'],
                              successes=r['successes'],clusters=r['cluster_successes'])
                         for r in accounting['streams']])


def infer_synthetic_counts(accounting, *, scope):
    if scope != 'synthetic-full-geometry-counts':
        raise ValueError('explicit synthetic count scope required; production dispatch unavailable')
    validate_accounting(accounting, require_complete=True)
    inputs = statistical_inputs(accounting)
    rows = {(r['arm'],r['stage']):r for r in inputs['streams']}
    def arm(name):
        return primary.Arm(name, *[primary.Stage(s,rows[name,s]['successes'],
            clusters=tuple(rows[name,s]['clusters']) if name in ('A2','N2') else None) for s in ('D','V')])
    return dict(scope=scope,candidate_evaluations=0,measured_sha256_observations=False,
        primary=persisted(primary.analyze([arm(a) for a in ('A1','A2','A3')])),
        controls=persisted(primary.controls([arm(a) for a in ('N1','N2')],
            *(rows[a,'C']['successes'] for a in ('P1','P2+','P2-')))),
        secondary=persisted(secondary.analyze_secondary(accounting)))


def disclosure(scope):
    """Synthetic diagnostics never authorize production validation disclosure."""
    if scope not in ('synthetic-engineering','synthetic-full-geometry-counts','production'):
        raise ValueError('disclosure scope')
    return dict(scope=scope,validation_diagnostics_allowed=scope != 'production',
                confirmatory_complete=False,production_blinded=scope=='production')
