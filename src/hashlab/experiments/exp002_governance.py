"""E4 governance contracts only. No seed selection, beacon client or dispatcher.

Verified evidence is created only through a caller-owned external verifier.
This is a trust boundary, not an implementation of witness/signature checks.
"""
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from .exp002_foundation import Plan, PROTOCOL_IDENTITY, SECONDARY_ID, canonical, _hex


def digest(data):
    return sha256(canonical(data)).hexdigest()


@dataclass(frozen=True)
class FullPlanBinding:
    """Seed-record-reference binding; not a resolved executable candidate plan.

    Only a seed record digest is accepted. Never accepts or derives a master.
    An external seed-record verifier must bind this digest to the protocol's
    full resolved plan/configuration before any future execution eligibility.
    """
    seedless_sha256: str
    seed_record_sha256: str
    resolved_config_sha256: str
    protocol_identity: str = PROTOCOL_IDENTITY
    secondary_identity: str = SECONDARY_ID
    schema: str = 'hashlab-exp002-full-plan-binding-v1'

    def __post_init__(self):
        for value in (self.seedless_sha256,self.seed_record_sha256,self.resolved_config_sha256):
            _hex(value,64)
        if (self.protocol_identity!=PROTOCOL_IDENTITY or self.secondary_identity!=SECONDARY_ID
                or self.schema!='hashlab-exp002-full-plan-binding-v1'):
            raise ValueError('incompatible full/seedless protocol binding')

    def validate(self, seedless: Plan):
        if type(seedless) is not Plan or self.seedless_sha256!=seedless.fingerprint:
            raise ValueError('seedless/full binding mismatch')

    @property
    def fingerprint(self):
        return digest(dict(schema=self.schema,seedless_sha256=self.seedless_sha256,
            seed_record_sha256=self.seed_record_sha256,resolved_config_sha256=self.resolved_config_sha256,
            protocol_identity=self.protocol_identity,secondary_identity=self.secondary_identity))


@dataclass(frozen=True)
class Claim:
    kind: str
    subject_sha256: str
    evidence_sha256: str
    declared_pass: bool

    def __post_init__(self):
        if type(self.kind) is not str or not self.kind or type(self.declared_pass) is not bool:
            raise ValueError('invalid declared condition')
        _hex(self.subject_sha256,64)
        _hex(self.evidence_sha256,64)


class ExternalVerifier(Protocol):
    def verify(self, claim: Claim, receipt: bytes) -> bool:
        """Independently authenticate exact kind, subject, evidence and pass status.

        Timing witnesses must validate pre-reveal timing and the >=24h gap;
        seed receipts must verify beacon/derivation and same-round requirements.
        No identity or verification service is chosen by this foundation.
        """
        ...


_VERIFIED = object()


@dataclass(frozen=True)
class VerifiedEvidence:
    claim: Claim
    receipt_sha256: str
    _verification: object

    def __post_init__(self):
        if self._verification is not _VERIFIED or type(self.claim) is not Claim or not self.claim.declared_pass:
            raise ValueError('declaration is not independently verified evidence')
        _hex(self.receipt_sha256,64)


def verify_claim(claim: Claim, receipt: bytes, verifier: ExternalVerifier):
    if type(claim) is not Claim or not claim.declared_pass or type(receipt) is not bytes or not receipt:
        raise ValueError('missing passing claim or external receipt')
    # Do not coerce truthy objects or catch/convert an external verification failure.
    if verifier.verify(claim,receipt) is not True:
        raise ValueError('external verification failed')
    return VerifiedEvidence(claim,sha256(receipt).hexdigest(),_VERIFIED)


REQUIRED_ELIGIBILITY = (
    'e001-reconstruction','overlap-audits','g1','qa2-statistical','qa2-hashing','g2',
    'precommitment','witness-timing','beacon-verification','seed-record',
    'registry-history','release-approval','director-authorization',
)


def require_verified(proofs, kind, subject, *, evidence=None):
    matches=[p for p in proofs if type(p) is VerifiedEvidence and p._verification is _VERIFIED
             and p.claim.kind==kind and p.claim.subject_sha256==subject
             and (evidence is None or p.claim.evidence_sha256==evidence)]
    if len(matches)!=1:
        raise ValueError(f'missing, duplicate or mismatched externally verified evidence: {kind}')
    return matches[0]


def check_eligibility(seedless: Plan, full: FullPlanBinding, proofs):
    """Gate decision only; no capability to dispatch or authorize an execution.

    All prerequisite evidence must be independently bound to this exact full
    binding, not an arbitrary passing declaration or a different study.
    """
    if type(full) is not FullPlanBinding:
        raise ValueError('missing full plan binding')
    full.validate(seedless)
    proofs=tuple(proofs)
    if len(proofs)!=len(REQUIRED_ELIGIBILITY) or any(type(p) is not VerifiedEvidence for p in proofs):
        raise ValueError('incomplete externally verified eligibility')
    for kind in REQUIRED_ELIGIBILITY:
        require_verified(proofs,kind,full.fingerprint,
                         evidence=full.seed_record_sha256 if kind=='seed-record' else None)
    return dict(schema='hashlab-exp002-eligibility-check-v1',subject_sha256=full.fingerprint,
                prerequisites_verified=True,execution_enabled=False)


@dataclass(frozen=True)
class CommitmentContract:
    """Caller-supplied commitment references; no seed, round or witness field."""
    seedless_sha256: str
    config_sha256: str
    preregistration_sha256: str
    seed_record_sha256: str

    def __post_init__(self):
        for value in (self.seedless_sha256,self.config_sha256,self.preregistration_sha256,self.seed_record_sha256):
            _hex(value,64)

    def verify(self, plan: Plan, full: FullPlanBinding, proofs):
        full.validate(plan)
        if (self.seedless_sha256!=plan.fingerprint or self.seed_record_sha256!=full.seed_record_sha256
                or self.config_sha256!=digest(plan.config.to_dict())):
            raise ValueError('commitment/plan identity mismatch')
        for kind,evidence in (('precommitment',self.preregistration_sha256),('witness-timing',self.preregistration_sha256),
                              ('beacon-verification',self.seed_record_sha256),('seed-record',self.seed_record_sha256)):
            require_verified(proofs,kind,full.fingerprint,evidence=evidence)
