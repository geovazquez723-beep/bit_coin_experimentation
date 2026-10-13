"""Read-only bridge to isolated verifier and external evidence. No accept/run API."""
from hashlib import sha256
from e001_verify import verify_rows
from .e001_phase_b import read_chunks,fingerprint,CONFIG
from .exp002_foundation import canonical,decode
from .exp002_governance import Claim,verify_claim,require_verified


def independent_report(root,plan,manifest_pin):
    calculated=verify_rows(plan.specs,plan.discovery,plan.validation,plan.seeds,read_chunks(root,plan,manifest_pin))
    return canonical(dict(schema='e001-bound-independent-fixture-report-v1',plan=plan.fingerprint,
        manifest=manifest_pin,source=plan.source,config=CONFIG,result=calculated))


def validate_report(raw,root,plan,manifest_pin):
    if type(raw) is not bytes or raw!=independent_report(root,plan,manifest_pin):
        raise ValueError('missing/forged/mismatched independent report')
    return sha256(raw).hexdigest()


def acceptance_subject(plan,manifest_pin,report_pin):
    return fingerprint(dict(schema='e001-final-acceptance-subject-v1',plan=plan.fingerprint,
                            manifest=manifest_pin,independent_report=report_pin))


def validate_final_record(raw,root,plan,manifest_pin,report,receipt,verifier):
    """Only validates externally supplied FIXTURE records; no historical E pass.

    External authority must independently authenticate the completed manifest,
    report, receipt custody and decision. In-process callbacks are a trust
    boundary; no real authority implementation is supplied or selected here.
    """
    report_pin=validate_report(report,root,plan,manifest_pin)
    subject=acceptance_subject(plan,manifest_pin,report_pin)
    claim=Claim('e001-final-fixture-record',subject,manifest_pin,True)
    proof=verify_claim(claim,receipt,verifier)
    require_verified((proof,),'e001-final-fixture-record',subject,evidence=manifest_pin)
    expected=dict(schema='e001-final-fixture-record-v1',subject=subject,plan=plan.fingerprint,
        manifest=manifest_pin,independent_report=report_pin,receipt_sha256=sha256(receipt).hexdigest(),
        decision='fixture-only',e_audit_accepted=False)
    if type(raw) is not bytes or decode(raw)!=expected or raw!=canonical(expected):
        raise ValueError('invalid final fixture record; historical acceptance prohibited')
    return expected


def validate_producer_accounting(raw,root,plan,manifest_pin):
    """Independently recompute every producer count, rank and first provenance."""
    independent=decode(independent_report(root,plan,manifest_pin))['result']
    expected=dict(schema='e001-producer-fixture-accounting-v1',plan=plan.fingerprint,
        producer_complete=True,accounting=independent['accounting'],membership=independent['membership'],
        a3_provenance=independent['a3_provenance'],final_acceptance=False)
    if type(raw) is not bytes or raw!=canonical(expected):
        raise ValueError('producer accounting differs from independent reconstruction')
    return expected
