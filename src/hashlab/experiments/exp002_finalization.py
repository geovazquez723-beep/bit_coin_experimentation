"""Evidence finalization for kernel evidence. No dispatch, seed selection or authorization.

Five claims stay separate and are never inferred from one another:

  capture        completed evidence capture (kernel completion pin, local replay)
  verification   independent full regeneration/rehash report (external proof)
  receipt        authenticated external receipts (timestamp, checkpoint, archive)
  disclosure     authorized disclosure of outcomes
  execution      Director authorization to execute

Every externally authenticated claim requires an E4 ``VerifiedEvidence`` produced
by a caller-owned ``ExternalVerifier``. No verifier, trust root, credential or
signature scheme is approved in this repository, so the receipt adapter is
unavailable and fails closed. Nothing here fabricates a receipt, timestamp,
signature, archive guarantee or approval.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from .exp002 import Config
from .exp002_foundation import (Accumulator, LIMITS, Plan, canonical, decode, validate_accounting, _hex)
from .exp002_governance import FullPlanBinding, require_verified
from .exp002_journal import AttemptJournal, durable_create, file_inventory, require_plain, inspect_partial
from .exp002_provenance import inventory as evidence_inventory, seal, verify_seal
from .exp002_controls import ControlEngine
from . import exp002_r9_contracts as r9
from .exp002_kernel import VerifiedCapture, _CAPTURE
from .exp002_kernel_plan import FORMAT, ProductionPlan, derive_master
from .exp002_kernel_evidence import iter_chunks

KIND_CAPTURE = 'evidence-capture'
KIND_VERIFICATION = 'independent-verification'
KIND_STATISTICS = 'statistics-verification'
KIND_RECEIPTS = ('external-timestamp', 'history-checkpoint', 'solo-archive')
KIND_DISCLOSURE = 'disclosure-authorization'
KIND_EXECUTION = 'director-authorization'
KIND_SEED = 'seed-record'
KIND_TIMESTAMP, KIND_CHECKPOINT, KIND_ARCHIVE = KIND_RECEIPTS
SEED_COMMITMENT_SCHEMA = 'hashlab-e002-seed-commitment-v1'
PREREGISTRATION_SCHEMA = 'hashlab-e002-preregistration-bundle-v1'
BEACON = dict(chain_hash='52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971',
              scheme='bls-unchained-g1-rfc9380', beacon_id='quicknet', period='3', genesis_unix='1692803367',
              public_key_hex='83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a')
ALL_KINDS = (KIND_CAPTURE, KIND_VERIFICATION, KIND_STATISTICS, *KIND_RECEIPTS, KIND_DISCLOSURE, KIND_EXECUTION)
SEED_RECORD_SCHEMA = 'hashlab-e002-seed-record-v1'
REPORT_SCHEMA = 'hashlab-e002-production-verification-v1'
STATISTICS_SCHEMA = 'hashlab-e002-measured-statistics-v1'
STATISTICS_VERIFICATION_SCHEMA = 'hashlab-e002-statistics-verification-v1'
PRODUCTION_EVALUATIONS = sum(n for _, _, n in LIMITS)
PRODUCTION_BLOCKS = sum(n * (2 if a in ('A2', 'N2') else 1) for a, _, n in LIMITS)


class FinalizationUnavailable(PermissionError):
    """A required external service, trust root or credential configuration does not exist."""


# ------------------------------------------------------------ seed binding

def timestamp_subject(c_pre, bundle_sha256):
    """The authenticated external timestamp must bind BOTH the C_pre identity and the bundle digest."""
    _hex(c_pre, 40)
    _hex(bundle_sha256, 64)
    return sha256(canonical(dict(schema='hashlab-e002-timestamp-subject-v1', c_pre=c_pre,
                                 preregistration_bundle_sha256=bundle_sha256))).hexdigest()


def preregistration_bundle(plan, round_number):
    """Retained C_pre bundle content (frozen seedless identities and the predetermined round)."""
    if type(plan) is not ProductionPlan or type(round_number) is not int or not 1 <= round_number < 2**64:
        raise ValueError('production plan and predetermined round required')
    return canonical(dict(schema=PREREGISTRATION_SCHEMA, reveal_round=str(round_number), chain_hash=BEACON['chain_hash'],
                          seedless_plan_sha256=Plan(plan.code_commit).fingerprint,
                          config_sha256=sha256(canonical(Config().to_dict())).hexdigest()))


def beacon_seed_record(c_pre, round_number, signature_hex, *, witness_receipt_sha256, witnessed_unix,
                       preregistration_bundle_sha256):
    """Content of the seed record (S1-S5, 3.8.1). Pure calculation; signature validity is NOT checked
    here (a pinned BLS client is an unmet operational dependency) and no beacon is retrieved."""
    _hex(c_pre, 40)
    _hex(signature_hex, 96)
    _hex(witness_receipt_sha256, 64)
    _hex(preregistration_bundle_sha256, 64)
    randomness = sha256(bytes.fromhex(signature_hex)).hexdigest()
    master = derive_master(c_pre, round_number, randomness)
    scheduled = int(BEACON['genesis_unix']) + (round_number - 1) * int(BEACON['period'])
    if type(witnessed_unix) is not int or witnessed_unix < 0 or witnessed_unix + 24 * 3600 > scheduled:
        raise ValueError('C_pre witness must precede the scheduled R* time by at least 24 hours')
    return canonical(dict(schema=SEED_RECORD_SCHEMA, kind='beacon', c_pre=c_pre,
        beacon=dict(BEACON, round=str(round_number), scheduled_unix=str(scheduled), signature_hex=signature_hex,
                    randomness_hex=randomness),
        witness=dict(receipt_sha256=witness_receipt_sha256, witnessed_unix=str(witnessed_unix),
                     bundle_sha256=preregistration_bundle_sha256),
        master=str(master), domain='experiment-002'))


def _beacon_fields(seed_record_bytes):
    record = decode(seed_record_bytes)
    if (type(record) is not dict or record.get('schema') != SEED_RECORD_SCHEMA or record.get('kind') != 'beacon'
            or record.get('domain') != 'experiment-002'):
        raise ValueError('beacon seed record required')
    try:
        b, w = record['beacon'], record['witness']
        expected = beacon_seed_record(record['c_pre'], int(b['round']), b['signature_hex'],
                                      witness_receipt_sha256=w['receipt_sha256'], witnessed_unix=int(w['witnessed_unix']),
                                      preregistration_bundle_sha256=w['bundle_sha256'])
    except (KeyError, TypeError) as exc:
        raise ValueError('malformed beacon seed record') from exc
    if expected != seed_record_bytes:
        raise ValueError('seed record differs from the exact S1-S5 derivation')
    return record


def full_binding(plan, seed_record_bytes):
    """FullPlanBinding: seedless plan, seed-record digest, and the seeded (resolved) configuration digest."""
    if type(plan) is not ProductionPlan or type(seed_record_bytes) is not bytes:
        raise ValueError('production plan and seed record bytes required')
    record = _beacon_fields(seed_record_bytes)
    seeded = dict(Config().to_dict(), master=record['master'])
    return FullPlanBinding(Plan(plan.code_commit).fingerprint, sha256(seed_record_bytes).hexdigest(),
                           sha256(canonical(seeded)).hexdigest())


def seed_commitment(plan, seed_record_bytes):
    """Content committed at C_seed (S5), kept outside the seed-record bytes so no digest is circular."""
    full = full_binding(plan, seed_record_bytes)
    record = _beacon_fields(seed_record_bytes)
    return canonical(dict(schema=SEED_COMMITMENT_SCHEMA, c_pre=record['c_pre'], seed_record_sha256=full.seed_record_sha256,
        preregistration_bundle_sha256=record['witness']['bundle_sha256'],
        master=record['master'], seedless_plan_sha256=full.seedless_sha256,
        config_sha256=sha256(canonical(Config().to_dict())).hexdigest(),
        seeded_config_sha256=full.resolved_config_sha256, full_plan_sha256=full.fingerprint))


# ------------------------------------------------------- claim separation

def claim_ledger(full, proofs, *, expected):
    """Report each claim independently. ``expected`` maps claim kind -> exact evidence digest.

    A claim is True only when a single externally verified proof exists for that
    kind, this full-plan subject and that evidence digest. Missing evidence digests
    leave a claim False; no claim implies another.
    """
    if type(full) is not FullPlanBinding or type(expected) is not dict or not set(expected) <= set(ALL_KINDS):
        raise ValueError('typed binding and known claim kinds required')
    ledger = {}
    for kind in ALL_KINDS:
        evidence = expected.get(kind)
        try:
            ledger[kind] = evidence is not None and bool(require_verified(proofs, kind, full.fingerprint, evidence=evidence))
        except ValueError:
            ledger[kind] = False
    return ledger


# --------------------------------------------------- external receipt adapter

APPROVED_SIGNATURE_SCHEMES = {}   # Intentionally empty: no scheme has been approved.


@dataclass(frozen=True)
class TrustRoot:
    """Explicit receipt trust root. All fields are required and externally approved."""
    identity: str
    scheme: str
    key_fingerprint: str
    approval_sha256: str

    def __post_init__(self):
        if type(self.identity) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', self.identity):
            raise ValueError('trust-root identity required')
        if type(self.scheme) is not str or self.scheme not in APPROVED_SIGNATURE_SCHEMES:
            raise FinalizationUnavailable('no approved receipt signature scheme exists')
        _hex(self.key_fingerprint, 64)
        _hex(self.approval_sha256, 64)


class HeadChainReceiptVerifier:
    """ExternalVerifier for signed, head-chained receipts. Constructible only with an
    approved trust root and signature scheme; none exists, so this is unavailable by default.

    A receipt is canonical JSON with schema, issuer, kind, subject, evidence,
    sequence, previous_head, head and signature. ``head`` must equal
    sha256(canonical(body without head/signature)); ``previous_head`` must equal the
    caller-pinned head of the immediately preceding accepted receipt.
    """
    SCHEMA = 'hashlab-e002-external-receipt-v1'

    def __init__(self, trust_root, *, previous_head, sequence):
        if type(trust_root) is not TrustRoot:
            raise FinalizationUnavailable('trust root required')
        self.root = trust_root
        self.scheme = APPROVED_SIGNATURE_SCHEMES[trust_root.scheme]
        _hex(previous_head, 64)
        if type(sequence) is not int or sequence < 1:
            raise ValueError('receipt sequence required')
        self.previous_head, self.sequence = previous_head, sequence

    def verify(self, claim, receipt):
        try:
            body = decode(receipt)
            if (type(body) is not dict or set(body) != {'schema', 'issuer', 'kind', 'subject', 'evidence',
                    'sequence', 'previous_head', 'head', 'signature'} or body['schema'] != self.SCHEMA
                    or body['issuer'] != self.root.identity or body['kind'] != claim.kind
                    or body['subject'] != claim.subject_sha256 or body['evidence'] != claim.evidence_sha256
                    or type(body['sequence']) is not int or body['sequence'] != self.sequence
                    or body['previous_head'] != self.previous_head):
                return False
            unsigned = {k: v for k, v in body.items() if k not in ('head', 'signature')}
            head = sha256(canonical(unsigned)).hexdigest()
            if body['head'] != head or type(body['signature']) is not str:
                return False
            return self.scheme.verify(self.root.key_fingerprint, head.encode('ascii'), bytes.fromhex(body['signature'])) is True
        except (ValueError, KeyError, TypeError):
            return False


def default_receipt_verifier():
    raise FinalizationUnavailable('no approved external receipt service, trust root, credential or signature scheme is configured')


def archive_adapter():
    raise FinalizationUnavailable('no approved external archive service or retention receipt exists')


def verify_restored_copy(inventory, restored_root):
    """Narrow R9 restore check: a restored directory must match the retained inventory exactly."""
    if type(inventory) is not dict or not inventory:
        raise ValueError('retained inventory required')
    root = Path(restored_root)
    require_plain(root, directory=True)
    observed = {p.name: file_inventory(p) for p in sorted(root.iterdir())}
    if observed != inventory:
        raise ValueError('restored copy differs from retained inventory')
    return True


# -------------------------------------------------- attempt-state handling

def classify_attempt_evidence(root):
    """Describe, never repair. Failed/incomplete attempts keep every byte and cannot finalize."""
    root = Path(root)
    require_plain(root, directory=True)
    names = {p.name for p in root.iterdir()}
    if 'failure.json' in names:
        state = 'failed'
    elif 'INCOMPLETE' in names or 'complete.json' not in names:
        state = 'incomplete'
    else:
        state = 'complete-candidate'
    return dict(state=state, retained=inspect_partial(root), repaired=False, resumed=False)


# ---------------------------------------------------------- verification report

def parse_verification_report(raw, *, plan, full, completion_sha256):
    """Structural/binding check of the independent verifier's public report.

    The report is a claim. It is not trusted until an external proof of kind
    ``independent-verification`` is bound to its digest by ``authenticate_production_capture``.
    """
    if type(raw) is not bytes or len(raw) > 65536:
        raise ValueError('verification report bytes')
    report = decode(raw)
    keys = {'schema', 'scope', 'mode', 'verification', 'bindings', 'seed', 'coverage', 'independence', 'claims'}
    if (type(report) is not dict or set(report) != keys or report['schema'] != REPORT_SCHEMA
            or report['scope'] != 'production' or report['mode'] != 'full'
            or report['verification'] != 'independent-full-regeneration-and-rehash'):
        raise ValueError('verification report contract')
    b, c, claims = report['bindings'], report['coverage'], report['claims']
    if (type(b) is not dict or b.get('completion_sha256') != completion_sha256 or b.get('plan_sha256') != plan.fingerprint
            or b.get('code_commit') != plan.code_commit or b.get('seed_record_sha256') != full.seed_record_sha256
            or b.get('seedless_sha256') != full.seedless_sha256 or b.get('seeded_config_sha256') != full.resolved_config_sha256
            or b.get('config_sha256') != sha256(canonical(Config().to_dict())).hexdigest()
            or b.get('full_plan_sha256') != full.fingerprint or b.get('c_seed_content') not in ('verified', 'not-verified')
            or type(b.get('c_seed')) is not str or not re.fullmatch('[0-9a-f]{40}', b['c_seed'])
            or type(b.get('c_pre')) is not str or not re.fullmatch('[0-9a-f]{40}', b['c_pre'])
            or type(b.get('seed_commitment_sha256')) is not str or not re.fullmatch('[0-9a-f]{64}', b['seed_commitment_sha256'])
            or type(report['seed']) is not dict or report['seed'].get('kind') != 'beacon'
            or report['seed'].get('c_pre') != b.get('c_pre')
            or type(b.get('bundle_sha256')) is not str or not re.fullmatch('[0-9a-f]{64}', b['bundle_sha256'])
            or report['seed'].get('bundle_sha256') != b.get('bundle_sha256')
            or b.get('c_pre_content') not in ('verified', 'not-verified')
            or any(type(b.get(k)) is not str or not re.fullmatch('[0-9a-f]{64}', b[k]) for k in (
                'accounting_sha256', 'environment_sha256', 'history_sha256', 'index_sha256',
                'source_inventory_sha256', 'runtime_sha256'))):
        raise ValueError('verification report bindings mismatch')
    if (type(c) is not dict or c.get('candidates_rehashed') != PRODUCTION_EVALUATIONS
            or c.get('compression_blocks') != PRODUCTION_BLOCKS
            or type(c.get('attempts_reconstructed')) is not int or c['attempts_reconstructed'] < PRODUCTION_EVALUATIONS):
        raise ValueError('verification report coverage incomplete')
    if (claims != dict(independent_regeneration_and_rehash=True, external_receipt=False, disclosure_authorized=False,
                       execution_authorized=False, g1=False, qa2=False, sampled_audit_absence_claim=False)):
        raise ValueError('verification report claims exceed independent regeneration')
    return report


def _replay(root, report):
    """Local transport + accounting replay against the verified report; no candidate regeneration."""
    root = Path(root)
    completion = decode((root/'complete.json').read_bytes())
    attempts = report['coverage']['attempts_reconstructed']
    if (completion.get('scope') != 'production' or completion.get('format') != FORMAT
            or completion.get('confirmatory_complete') is not False or completion.get('qa2') is not False
            or completion.get('evaluations') != PRODUCTION_EVALUATIONS
            or completion.get('compression_blocks') != PRODUCTION_BLOCKS or completion.get('attempts') != attempts):
        raise ValueError('production completion contract')
    acc, evaluations, blocks = Accumulator(), 0, 0
    for attempt, raw, effective in iter_chunks(root, expected_chunks=completion['chunks'], expected_attempts=attempts):
        if attempt.reasons:
            continue
        mode = attempt.arm if not attempt.arm.startswith('A') else 'N1'
        if bytes.fromhex(ControlEngine(mode).transform(raw)['effective_digest_hex']) != effective:
            raise ValueError('raw/effective transformation mismatch')
        acc.add(attempt.record(), effective)
        evaluations += 1
        blocks += (len(attempt.candidate) + 72) // 64
    accounting = acc.finish()
    validate_accounting(accounting, require_complete=True)
    if ((evaluations, blocks) != (PRODUCTION_EVALUATIONS, PRODUCTION_BLOCKS)
            or (root/'accounting.json').read_bytes() != canonical(accounting)
            or sha256(canonical(accounting)).hexdigest() != report['bindings']['accounting_sha256']):
        raise ValueError('capture accounting/completeness mismatch')
    return accounting


def _journal_heads(journal_root):
    files = sorted(p for p in Path(journal_root).iterdir() if p.name != 'writer.lock')
    return [sha256(p.read_bytes()).hexdigest() for p in files]


def _receipt(raw, proof, kind, evidence):
    if type(raw) is not bytes or sha256(raw).hexdigest() != proof.receipt_sha256:
        raise ValueError('receipt bytes do not match the externally verified proof')
    body = decode(raw)
    if (type(body) is not dict or body.get('schema') != HeadChainReceiptVerifier.SCHEMA or body.get('kind') != kind
            or body.get('evidence') != evidence or type(body.get('sequence')) is not int):
        raise ValueError('receipt contract')
    _hex(body.get('head'), 64)
    _hex(body.get('previous_head'), 64)
    return body


def authenticate_production_capture(root, *, plan, full, completion_sha256, report_bytes, proofs,
                                    journal_root, journal_anchor, started_receipt, result_receipt,
                                    repository_root, audit_root):
    """The only path to a production ``VerifiedCapture`` (official confirmatory eligibility).

    Required, in the protocol order, each as a separate externally verified claim:
      producer completion (local pin + accounting replay) -> independent algorithmic verification
      (report proof) -> outer manifest (sealed, externally proven) -> authenticated C_pre timestamp
      -> pre-execution started-attempt checkpoint -> post-verification result/manifest checkpoint
      with prior-head continuity. Execution authorization and Director acceptance are separate
      claims, neither required nor accepted as substitutes. Bounded, engineering, partial, unsigned
      or synthetic evidence fails a gate, and with no approved receipt service none can be issued.
    """
    if type(plan) is not ProductionPlan or type(full) is not FullPlanBinding:
        raise PermissionError('production plan and full binding required')
    _hex(completion_sha256, 64)
    root = Path(root)
    require_plain(root, directory=True)
    if classify_attempt_evidence(root)['state'] != 'complete-candidate':
        raise ValueError('failed or incomplete evidence cannot become a capture')
    plan.validate_local_inputs(repository_root, audit_root)
    seedless = Plan(plan.code_commit)
    full.validate(seedless)
    if file_inventory(root/'complete.json')['sha256'] != completion_sha256:
        raise ValueError('completion pin mismatch')
    report = parse_verification_report(report_bytes, plan=plan, full=full, completion_sha256=completion_sha256)
    require_verified(proofs, KIND_SEED, full.fingerprint, evidence=full.seed_record_sha256)
    require_verified(proofs, KIND_VERIFICATION, full.fingerprint, evidence=sha256(report_bytes).hexdigest())
    # Outer manifest: sealed, includes exactly the verified report, externally proven.
    manifest = (root/'manifest.sha256').read_bytes().decode('ascii').strip()
    _hex(manifest, 64)
    verify_seal(root, seedless, full, manifest, require_verified(proofs, 'outer-manifest', full.fingerprint, evidence=manifest))
    if (root/'verification.json').read_bytes() != report_bytes:
        raise ValueError('sealed verification report differs from the supplied report')
    # Pre-reveal C_pre timestamp (S3), as its own claim.
    c_pre = report['bindings']['c_pre']
    require_verified(proofs, KIND_TIMESTAMP, full.fingerprint,
                     evidence=timestamp_subject(c_pre, report['bindings']['bundle_sha256']))
    # Journal: exactly one attempt, started then valid result carrying this manifest.
    events, head = AttemptJournal(journal_root).read(anchor=journal_anchor)
    heads = _journal_heads(journal_root)
    if (len(events) != 2 or [e['kind'] for e in events] != ['started', 'result'] or events[0]['attempt'] != 1
            or heads[-1] != head):
        raise ValueError('exactly one started and one result event are required')
    started, result = events[0]['data'], events[1]['data']
    if (started['full_plan'] != full.fingerprint or started['seed_record'] != full.seed_record_sha256
            or started['code_commit'] != plan.code_commit or started['config_sha256'] != full.resolved_config_sha256
            or result['failure'] != 'valid' or result['status'] != 'complete' or result['manifest'] != manifest
            or result['numerical_abort'] is not False):
        raise ValueError('journal attempt does not match the verified binding and manifest')
    # Pre-execution and post-verification checkpoints with prior-head continuity.
    first = _receipt(started_receipt, require_verified(proofs, KIND_CHECKPOINT, full.fingerprint, evidence=heads[0]),
                     KIND_CHECKPOINT, heads[0])
    second = _receipt(result_receipt, require_verified(proofs, KIND_CHECKPOINT, full.fingerprint, evidence=heads[1]),
                      KIND_CHECKPOINT, heads[1])
    if (second['previous_head'] != first['head'] or second['sequence'] != first['sequence'] + 1
            or second.get('issuer') != first.get('issuer')):
        raise ValueError('checkpoint head chain is not continuous')
    accounting = _replay(root, report)
    return VerifiedCapture(accounting, plan, completion_sha256, _token=_CAPTURE)


def require_statistics_for_capture(statistics_report_bytes, verification_report_bytes, *, full, proofs):
    """Bind the independent statistics check to the same verified accounting as the capture.

    Artificial or foreign counts can satisfy the statistics arithmetic but not this binding:
    the statistics' accounting digest must equal the one in the independently verified,
    externally proven regeneration report, and the statistics check itself needs its own
    externally verified proof. Returns the statistics digest; it authorizes no disclosure.
    """
    statistics = decode(statistics_report_bytes)
    verification = decode(verification_report_bytes)
    if (type(statistics) is not dict or statistics.get('schema') != STATISTICS_VERIFICATION_SCHEMA
            or statistics.get('scope') != 'measured-production' or verification.get('schema') != REPORT_SCHEMA
            or verification.get('scope') != 'production'
            or statistics['bindings']['accounting_sha256'] != verification['bindings']['accounting_sha256']
            or statistics['bindings']['completion_sha256'] != verification['bindings']['completion_sha256']
            or statistics['bindings']['plan_sha256'] != verification['bindings']['plan_sha256']
            or statistics['claims'] != dict(numeric_results_disclosed=False, disclosure_authorized=False,
                                            execution_authorized=False)):
        raise ValueError('statistics are not bound to the independently verified accounting')
    require_verified(proofs, KIND_VERIFICATION, full.fingerprint, evidence=sha256(verification_report_bytes).hexdigest())
    digest = statistics['bindings']['statistics_sha256']
    require_verified(proofs, KIND_STATISTICS, full.fingerprint, evidence=digest)
    return digest


# ------------------------------------------------------------ outer sealing

def expected_manifest_pin(root, seedless, full, provenance, *, extra):
    """Pin of the E4 outer manifest that sealing would produce, including files not yet written."""
    files = evidence_inventory(root)
    for name, raw in extra.items():
        if name in files:
            raise FileExistsError(name)
        files[name] = dict(size=len(raw), sha256=sha256(raw).hexdigest())
    body = dict(schema='hashlab-exp002-outer-manifest-v1', seedless=seedless.fingerprint,
                full_plan=full.fingerprint, provenance=provenance, files=dict(sorted(files.items())))
    return sha256(canonical(body)).hexdigest()


def seal_evidence(root, *, seedless, full, report_bytes, attempt, proofs):
    """Persist the independent report, then apply the existing E4 outer seal.

    Preconditions (all checked before any byte is written): complete, unfailed evidence;
    an externally verified ``independent-verification`` proof for this exact report; and an
    externally verified ``evidence-completeness`` proof for the exact manifest pin. A partial
    result is retained and never overwritten, resumed or repaired.
    """
    root = Path(root)
    if classify_attempt_evidence(root)['state'] != 'complete-candidate':
        raise ValueError('failed or incomplete evidence cannot be sealed')
    if type(report_bytes) is not bytes or type(attempt) is not int or attempt < 1:
        raise ValueError('report bytes and attempt required')
    report = decode(report_bytes)
    accounting = file_inventory(root/'accounting.json')['sha256']
    if report.get('schema') != REPORT_SCHEMA or report['bindings']['accounting_sha256'] != accounting:
        raise ValueError('verification report does not describe this evidence')
    require_verified(proofs, KIND_VERIFICATION, full.fingerprint, evidence=sha256(report_bytes).hexdigest())
    provenance = dict(attempt=attempt, source='supplied-evidence', accounting_sha256=accounting)
    pin = expected_manifest_pin(root, seedless, full, provenance, extra={'verification.json': report_bytes})
    require_verified(proofs, 'evidence-completeness', full.fingerprint, evidence=pin)
    durable_create(root/'verification.json', report_bytes)
    if seal(root, seedless, full, provenance, proofs) != pin:
        raise ValueError('sealed manifest differs from the verified pin')
    return pin


# ------------------------------------------------------------ R9 structure

EVIDENCE_ENVELOPE = 'hashlab-exp002-r9-evidence-envelope-v1'


def _ref(raw):
    return dict(schema=EVIDENCE_ENVELOPE, sha256=sha256(raw).hexdigest(), bytes=str(len(raw)))


def r9_algorithmic_record(report_bytes, *, plan, full, artifacts, attempt='E002-A-1', recorded_at,
                          actor_id='independent-verifier'):
    """Structural M1A algorithmic-verification declaration for a verified report.

    Returns (record_bytes, artifact_map). The record is an UntrustedAlgorithmicReport:
    parse/graph checks are structural only and authenticate nothing.
    """
    need = ('policy', 'source_inventory', 'configuration', 'seedless_plan', 'full_plan', 'environment', 'scope',
            'tool_source', 'tool_environment', 'method', 'separation', 'shared_dependencies', 'limitations')
    if type(artifacts) is not dict or set(artifacts) != set(need) or any(type(v) is not bytes or not v for v in artifacts.values()):
        raise ValueError('complete artifact set required')
    report = decode(report_bytes)
    refs = {k: _ref(v) for k, v in artifacts.items()}
    refs['report'] = _ref(report_bytes)
    record = dict(
        schema=r9.ALGORITHMIC_SCHEMA,
        bindings=dict(active_protocol=r9.ACTIVE_PROTOCOL, scientific_baseline=r9.SCIENTIFIC_BASELINE,
            governance=r9.GOVERNANCE, secondary=r9.SECONDARY, policy_ref=refs['policy'],
            source=dict(object_format='sha1', commit=plan.code_commit, inventory_ref=refs['source_inventory']),
            configuration_ref=refs['configuration'], seedless_plan_ref=refs['seedless_plan'],
            full_plan_ref=refs['full_plan'], environment_ref=refs['environment']),
        scope=dict(study='experiment-002', operation='exp002-execution', scope_ref=refs['scope'],
                   attempt=attempt, stage=None),
        producer=dict(actor_id=actor_id, role='algorithmic-verifier', tool_source_ref=refs['tool_source'],
                      tool_environment_ref=refs['tool_environment']),
        recorded_at=recorded_at, predecessor_ref=None, verification_kind='candidate-reconstruction',
        input_refs=sorted([refs['report']], key=lambda r: (r['schema'], r['sha256'])),
        method_ref=refs['method'], reference_refs=[],
        findings=[dict(check_id='independent-regeneration-and-rehash', state='matched',
                       evidence_refs=[refs['report']],
                       reason='Every attempted candidate was independently regenerated and every accepted candidate rehashed.')],
        coverage=dict(unit='records', expected=str(report['coverage']['candidates_rehashed']),
                      checked=str(report['coverage']['candidates_rehashed']), scope_complete='complete'),
        implementation_separation_ref=refs['separation'], shared_dependencies_ref=refs['shared_dependencies'],
        limitations_ref=refs['limitations'], first_mismatch_ref=None)
    raw = canonical(record)
    r9.parse_record(raw)
    graph = {r9.Ref(v['schema'], v['sha256'], int(v['bytes'])): (artifacts[k] if k != 'report' else report_bytes)
             for k, v in refs.items()}
    r9.check_reference_graph(raw, graph, opaque_schemas=frozenset({EVIDENCE_ENVELOPE}))
    return raw, graph


# ------------------------------------------------------------ result record

def finalization_record(destination, *, plan_fingerprint, completion_sha256, ledger, restored=None):
    """Exclusive public finalization record listing each claim separately."""
    if type(ledger) is not dict or set(ledger) != set(ALL_KINDS) or any(type(v) is not bool for v in ledger.values()):
        raise ValueError('complete claim ledger required')
    raw = canonical(dict(schema='hashlab-e002-finalization-record-v1', plan_sha256=plan_fingerprint,
                         completion_sha256=completion_sha256, claims=ledger,
                         note='claims are independent; none implies another', repaired=False, resumed=False))
    durable_create(destination, raw)
    return sha256(raw).hexdigest()
