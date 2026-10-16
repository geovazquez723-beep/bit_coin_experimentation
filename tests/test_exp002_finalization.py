"""Finalization, claim separation, receipt adapters, capture gating and statistics verification.

Everything marked synthetic/unit-only is a test double. No approved external service,
trust root, credential or signature scheme exists; none is fabricated for production use.
"""
from hashlib import sha256
from pathlib import Path
import hashlib
import hmac
import json
import shutil

import pytest

from hashlab.experiments import exp002_finalization as fin
from hashlab.experiments import exp002_governance as gov
from hashlab.experiments import exp002_journal as journal_module
from hashlab.experiments import exp002_kernel as kernel
from hashlab.experiments import exp002_kernel_bounded as bounded
from hashlab.experiments import exp002_kernel_inference as inference
from hashlab.experiments import exp002_kernel_plan as plans
from hashlab.experiments import exp002_kernel_statistics as statistics
from hashlab.experiments import exp002_integration as i3
from hashlab.experiments import exp002_r9_contracts as r9
from hashlab.experiments.exp002_foundation import canonical
from hashlab.experiments.exp002_kernel_disclosure import KernelFailure
from e002_verify import production_statistics as ref_statistics

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO/'results/e001-s14-audit-20261012-01'
H = 'a'*64


class SyntheticVerifier:
    """Unit-only stand-in for an external verifier; accepts only exact claim-bound bytes."""
    def verify(self, claim, receipt):
        return receipt == canonical(dict(kind=claim.kind, subject=claim.subject_sha256, evidence=claim.evidence_sha256))


def proof(kind, subject, evidence):
    claim = gov.Claim(kind, subject, evidence, True)
    return gov.verify_claim(claim, canonical(dict(kind=kind, subject=subject, evidence=evidence)), SyntheticVerifier())


class SyntheticJournal(journal_module.AttemptJournal):
    pin = journal_module.ZERO

    def append(self, *args, **kwargs):
        if self.pin is not None:
            kwargs['anchor'] = proof('registry-history', self.pin, self.pin)
        self.pin = super().append(*args, **kwargs)
        return self.pin


def production_plan():
    runtime = plans.RuntimeBinding('CPython 3.13.0 engineering identity', 'unit-platform', '1'*64, (('PyYAML', '6.0.3', '2'*64),))
    return plans.ProductionPlan('16f8b30ae30a9ef3ffc0f2868e9508e70c8007cd',
        tuple(plans.Artifact(p, 1, '3'*64) for p in sorted(plans.REQUIRED_SOURCES)), runtime)


PLAN = production_plan()
SIGNATURE = 'ab'*48                                  # synthetic bytes; no BLS signature is verified anywhere
SCHEDULED = 1692803367 + 999*3                       # genesis + (R*-1)*3 for R* = 1000
PROD_SEEDLESS = fin.Plan(PLAN.code_commit)
BUNDLE = fin.preregistration_bundle(PLAN, 1000)
BUNDLE_SHA = sha256(BUNDLE).hexdigest()
SEED = fin.beacon_seed_record('0'*40, 1000, SIGNATURE, witness_receipt_sha256='9'*64, witnessed_unix=SCHEDULED-90000,
                              preregistration_bundle_sha256=BUNDLE_SHA)
FULL = fin.full_binding(PLAN, SEED)
COUNTS = i3.count_fixtures(REPO)['cases'][0]['accounting']       # artificial counts, never measured evidence


def synthetic_report(**changes):
    """Stand-in for the independent verifier's report; production evidence cannot exist yet."""
    from hashlab.experiments.exp002 import Config
    report = dict(schema=fin.REPORT_SCHEMA, scope='production', mode='full',
        verification='independent-full-regeneration-and-rehash',
        bindings=dict(completion_sha256='c'*64, plan_sha256=PLAN.fingerprint, accounting_sha256=sha256(canonical(COUNTS)).hexdigest(),
                      environment_sha256='e'*64, history_sha256='f'*64, index_sha256='1'*64,
                      seed_record_sha256=FULL.seed_record_sha256, source_inventory_sha256='2'*64, runtime_sha256='3'*64,
                      code_commit=PLAN.code_commit, seedless_sha256=FULL.seedless_sha256,
                      config_sha256=sha256(canonical(Config().to_dict())).hexdigest(),
                      seeded_config_sha256=FULL.resolved_config_sha256, full_plan_sha256=FULL.fingerprint,
                      seed_commitment_sha256=sha256(fin.seed_commitment(PLAN, SEED)).hexdigest(),
                      c_pre='0'*40, c_seed='5'*40, c_seed_content='not-verified', bundle_sha256=BUNDLE_SHA,
                      c_pre_content='not-verified'),
        seed=dict(kind='beacon', c_pre='0'*40, round='1000', scheduled_unix=str(SCHEDULED), witness_receipt_sha256='9'*64,
                  bundle_sha256=BUNDLE_SHA, master=json.loads(SEED)['master'], beacon_signature='not-verified;requires-pinned-bls-client',
                  witness_receipt='not-verified;requires-authenticated-timestamp-service'),
        coverage=dict(attempts_reconstructed=fin.PRODUCTION_EVALUATIONS, candidates_rehashed=fin.PRODUCTION_EVALUATIONS,
                      compression_blocks=fin.PRODUCTION_BLOCKS, chunks=44000, rejections={}, history_occurrences=7000000,
                      a3_exclusion_ranks=60721),
        independence=dict(candidate_sha256=dict(role='candidate-evaluation', backend='hacl', known_answers='passed',
                                                independent_of_producer=True, shared_with_producer=False)),
        claims=dict(independent_regeneration_and_rehash=True, external_receipt=False,
                      disclosure_authorized=False, execution_authorized=False, g1=False, qa2=False,
                      sampled_audit_absence_claim=False))
    for path, value in changes.items():
        target = report
        *parents, leaf = path.split('.')
        for q in parents:
            target = target[q]
        target[leaf] = value
    return report


def started(**changes):
    data = dict(full_plan=FULL.fingerprint, seed_record=FULL.seed_record_sha256, code_commit=PLAN.code_commit,
                config_sha256=FULL.resolved_config_sha256, command='synthetic-only',
                utc='2000-01-01T00:00:00.000000Z', retry_evidence=None)
    data.update(changes)
    return data


class Setup:
    """Every capture gate satisfied by synthetic doubles; individual tests remove or corrupt one.

    Order modeled: producer completion -> independent verification report -> outer manifest ->
    journal result (carries the manifest) -> started and result checkpoint receipts -> capture.
    """
    def __init__(self, tmp_path, monkeypatch, *, started_changes=None, result_changes=None, receipt2_previous=None,
                 omit_result=False, **report_changes):
        monkeypatch.setitem(fin.APPROVED_SIGNATURE_SCHEMES, 'test-hmac', TestHmacScheme())
        self.root = tmp_path/'evidence'
        self.root.mkdir()
        (self.root/'complete.json').write_bytes(b'synthetic-completion')
        (self.root/'accounting.json').write_bytes(canonical(COUNTS))
        self.pin = sha256(b'synthetic-completion').hexdigest()
        self.report = canonical(synthetic_report(**{'bindings.completion_sha256': self.pin}, **report_changes))
        verification = proof(fin.KIND_VERIFICATION, FULL.fingerprint, sha256(self.report).hexdigest())
        provenance = dict(attempt=1, source='supplied-evidence', accounting_sha256=sha256(canonical(COUNTS)).hexdigest())
        expected = fin.expected_manifest_pin(self.root, PROD_SEEDLESS, FULL, provenance, extra={'verification.json': self.report})
        self.manifest = fin.seal_evidence(self.root, seedless=PROD_SEEDLESS, full=FULL, report_bytes=self.report, attempt=1,
                                          proofs=[verification, proof('evidence-completeness', FULL.fingerprint, expected)])
        self.journal = SyntheticJournal(tmp_path/'journal')
        self.journal.root.mkdir()
        self.journal.append('started', 1, started(**(started_changes or {})))
        if not omit_result:
            self.journal.append('result', 1, dict(dict(failure='valid', manifest=self.manifest, disclosure=H,
                numerical_abort=False, run_id='unit-run', status='complete'), **(result_changes or {})))
        self.anchor = proof('registry-history', self.journal.pin, self.journal.pin)
        heads = fin._journal_heads(self.journal.root)
        trust = fin.TrustRoot('checkpoint-service', 'test-hmac', H, 'b'*64)
        first_raw, first_head = receipt(fin.KIND_CHECKPOINT, FULL.fingerprint, heads[0], 1, '0'*64, issuer='checkpoint-service')
        previous = receipt2_previous or first_head
        second_raw, _ = receipt(fin.KIND_CHECKPOINT, FULL.fingerprint, heads[-1], 2, previous, issuer='checkpoint-service')
        first = gov.verify_claim(gov.Claim(fin.KIND_CHECKPOINT, FULL.fingerprint, heads[0], True), first_raw,
                                 fin.HeadChainReceiptVerifier(trust, previous_head='0'*64, sequence=1))
        second = gov.verify_claim(gov.Claim(fin.KIND_CHECKPOINT, FULL.fingerprint, heads[-1], True), second_raw,
                                  fin.HeadChainReceiptVerifier(trust, previous_head=previous, sequence=2))
        self.receipts = (first_raw, second_raw)
        self.named = dict(
            seed=proof(fin.KIND_SEED, FULL.fingerprint, FULL.seed_record_sha256), verification=verification,
            manifest=proof('outer-manifest', FULL.fingerprint, self.manifest),
            timestamp=proof(fin.KIND_TIMESTAMP, FULL.fingerprint, fin.timestamp_subject('0'*40, BUNDLE_SHA)),
            started=first, result=second)
        self.proofs = list(self.named.values())
        monkeypatch.setattr(plans.ProductionPlan, 'validate_local_inputs', lambda *a: None)
        monkeypatch.setattr(fin, '_replay', lambda root, report: COUNTS)   # unit-only: bypasses chunk replay

    def issue(self, **overrides):
        args = dict(plan=PLAN, full=FULL, completion_sha256=self.pin, report_bytes=self.report, proofs=self.proofs,
                    journal_root=self.journal.root, journal_anchor=self.anchor, started_receipt=self.receipts[0],
                    result_receipt=self.receipts[1], repository_root=REPO, audit_root=AUDIT)
        args.update(overrides)
        return fin.authenticate_production_capture(self.root, **args)

    def without(self, *names):
        return [v for k, v in self.named.items() if k not in names]


# ------------------------------------------------------------ seed/full binding

def test_full_binding_requires_exact_beacon_record_and_never_a_master():
    assert FULL.seedless_sha256 == fin.Plan(PLAN.code_commit).fingerprint
    assert FULL.seed_record_sha256 == sha256(SEED).hexdigest()
    record = json.loads(SEED)
    assert record['master'] == str(plans.derive_master('0'*40, 1000, record['beacon']['randomness_hex']))
    assert record['beacon']['randomness_hex'] == sha256(bytes.fromhex(SIGNATURE)).hexdigest()
    assert FULL.resolved_config_sha256 == sha256(canonical(dict(__import__('hashlab.experiments.exp002', fromlist=['Config']).Config().to_dict(), master=record['master']))).hexdigest()
    for bad in (SEED.replace(b'"master":"', b'"master":"9'), canonical(dict(schema=fin.SEED_RECORD_SCHEMA, kind='public-engineering',
                master='0', domain='experiment-002-kat')), b'{}', b'x',
                canonical(dict(record, beacon=dict(record['beacon'], randomness_hex='0'*64))),
                canonical(dict(record, beacon=dict(record['beacon'], chain_hash='0'*64))),
                canonical(dict(record, beacon=dict(record['beacon'], scheduled_unix='1'))),
                canonical(dict(record, witness=dict(record['witness'], witnessed_unix=str(SCHEDULED-3600)))),
                canonical(dict(record, c_pre='A'*40))):
        with pytest.raises(ValueError):
            fin.full_binding(PLAN, bad)
    with pytest.raises(ValueError):
        fin.full_binding(plans.EngineeringPlan(), SEED)
    for args in (('0'*40, 0, SIGNATURE), ('0'*40, 1000, 'ab'*47), ('g'*40, 1000, SIGNATURE)):
        with pytest.raises(ValueError):
            fin.beacon_seed_record(*args, witness_receipt_sha256='9'*64, witnessed_unix=SCHEDULED-90000,
                                   preregistration_bundle_sha256=BUNDLE_SHA)
    with pytest.raises(ValueError):                         # witness inside the 24 h lead is ineligible
        fin.beacon_seed_record('0'*40, 1000, SIGNATURE, witness_receipt_sha256='9'*64, witnessed_unix=SCHEDULED-86399,
                               preregistration_bundle_sha256=BUNDLE_SHA)


def test_seed_commitment_is_derived_outside_the_seed_record_so_no_digest_is_circular():
    commitment = json.loads(fin.seed_commitment(PLAN, SEED))
    assert commitment['full_plan_sha256'] == FULL.fingerprint and commitment['seed_record_sha256'] == FULL.seed_record_sha256
    assert commitment['seeded_config_sha256'] == FULL.resolved_config_sha256 != commitment['config_sha256']
    assert commitment['c_pre'] == '0'*40 and commitment['seedless_plan_sha256'] == FULL.seedless_sha256
    assert FULL.fingerprint.encode() not in SEED and commitment['full_plan_sha256'].encode() not in SEED


# --------------------------------------------------------- claim separation

def test_five_claims_are_independent_and_exact():
    expected = {fin.KIND_CAPTURE: 'c'*64, fin.KIND_VERIFICATION: 'd'*64, fin.KIND_STATISTICS: 'e'*64,
                fin.KIND_RECEIPTS[0]: '1'*64, fin.KIND_DISCLOSURE: '2'*64, fin.KIND_EXECUTION: '3'*64}
    everything = [proof(k, FULL.fingerprint, e) for k, e in expected.items()]
    assert all(fin.claim_ledger(FULL, everything, expected=expected)[k] for k in expected)
    for kind in expected:
        only = [proof(kind, FULL.fingerprint, expected[kind])]
        ledger = fin.claim_ledger(FULL, only, expected=expected)
        assert [k for k, ok in ledger.items() if ok] == [kind]
    ledger = fin.claim_ledger(FULL, [proof(fin.KIND_VERIFICATION, FULL.fingerprint, 'd'*64)], expected=expected)
    assert not ledger[fin.KIND_DISCLOSURE] and not ledger[fin.KIND_EXECUTION] and not any(ledger[k] for k in fin.KIND_RECEIPTS)
    stale = [proof(fin.KIND_VERIFICATION, FULL.fingerprint, 'f'*64)]
    assert not fin.claim_ledger(FULL, stale, expected=expected)[fin.KIND_VERIFICATION]
    other = [proof(fin.KIND_VERIFICATION, 'b'*64, 'd'*64)]
    assert not fin.claim_ledger(FULL, other, expected=expected)[fin.KIND_VERIFICATION]
    duplicate = [proof(fin.KIND_VERIFICATION, FULL.fingerprint, 'd'*64)]*2
    assert not fin.claim_ledger(FULL, duplicate, expected=expected)[fin.KIND_VERIFICATION]
    assert not any(fin.claim_ledger(FULL, [gov.Claim(k, FULL.fingerprint, expected[k], True) for k in expected], expected=expected).values())
    with pytest.raises(ValueError):
        fin.claim_ledger(FULL, [], expected={'invented': H})


def test_finalization_record_lists_every_claim_separately_and_is_exclusive(tmp_path):
    ledger = {k: False for k in fin.ALL_KINDS}
    ledger[fin.KIND_VERIFICATION] = True
    pin = fin.finalization_record(tmp_path/'finalization.json', plan_fingerprint=PLAN.fingerprint,
                                  completion_sha256='c'*64, ledger=ledger)
    body = json.loads((tmp_path/'finalization.json').read_bytes())
    assert sha256((tmp_path/'finalization.json').read_bytes()).hexdigest() == pin
    assert body['claims'][fin.KIND_VERIFICATION] and not body['claims'][fin.KIND_DISCLOSURE] and not body['claims'][fin.KIND_EXECUTION]
    assert body['repaired'] is False and body['resumed'] is False
    with pytest.raises(FileExistsError):
        fin.finalization_record(tmp_path/'finalization.json', plan_fingerprint=PLAN.fingerprint, completion_sha256='c'*64, ledger=ledger)
    for bad in ({}, {**ledger, 'extra': True}, {**ledger, fin.KIND_DISCLOSURE: 1}):
        with pytest.raises(ValueError):
            fin.finalization_record(tmp_path/'other.json', plan_fingerprint=H, completion_sha256=H, ledger=bad)


# ---------------------------------------------------- receipt adapter / chain

def test_no_receipt_service_trust_root_scheme_archive_or_signature_exists_by_default():
    assert fin.APPROVED_SIGNATURE_SCHEMES == {}
    with pytest.raises(fin.FinalizationUnavailable):
        fin.default_receipt_verifier()
    with pytest.raises(fin.FinalizationUnavailable):
        fin.archive_adapter()
    with pytest.raises(fin.FinalizationUnavailable):
        fin.TrustRoot('service', 'ed25519', H, H)
    with pytest.raises(fin.FinalizationUnavailable):
        fin.HeadChainReceiptVerifier(None, previous_head=H, sequence=1)


class TestHmacScheme:
    """Unit-only symmetric double; production code registers no scheme."""
    name = 'test-hmac'

    def verify(self, fingerprint, message, signature):
        return hmac.compare_digest(hmac.new(bytes.fromhex(fingerprint), message, hashlib.sha256).digest(), signature)


def receipt(kind, subject, evidence, sequence, previous, *, issuer='service-1', key=H, tamper=None):
    body = dict(schema=fin.HeadChainReceiptVerifier.SCHEMA, issuer=issuer, kind=kind, subject=subject, evidence=evidence,
                sequence=sequence, previous_head=previous)
    head = sha256(canonical(body)).hexdigest()
    signature = hmac.new(bytes.fromhex(key), head.encode('ascii'), hashlib.sha256).hexdigest()
    body.update(head=head, signature=signature)
    if tamper:
        body.update(tamper)
    return canonical(body), head


@pytest.fixture
def scheme(monkeypatch):
    monkeypatch.setitem(fin.APPROVED_SIGNATURE_SCHEMES, 'test-hmac', TestHmacScheme())
    return fin.TrustRoot('service-1', 'test-hmac', H, 'b'*64)


def test_head_chain_receipts_validate_trust_root_identity_sequence_and_head(scheme):
    chain, previous = [], '0'*64
    for sequence, kind in enumerate(fin.KIND_RECEIPTS, 1):
        raw, head = receipt(kind, FULL.fingerprint, 'e'*64, sequence, previous)
        verifier = fin.HeadChainReceiptVerifier(scheme, previous_head=previous, sequence=sequence)
        evidence = gov.verify_claim(gov.Claim(kind, FULL.fingerprint, 'e'*64, True), raw, verifier)
        assert evidence.claim.kind == kind
        chain.append((raw, previous, sequence))
        previous = head
    # Replay, reordering and every bound field fail closed.
    raw, prev, seq = chain[0]
    claim = gov.Claim(fin.KIND_RECEIPTS[0], FULL.fingerprint, 'e'*64, True)
    cases = {
        'replayed-as-next': fin.HeadChainReceiptVerifier(scheme, previous_head=chain[1][1], sequence=2),
        'wrong-previous-head': fin.HeadChainReceiptVerifier(scheme, previous_head='9'*64, sequence=1),
        'wrong-sequence': fin.HeadChainReceiptVerifier(scheme, previous_head=prev, sequence=2),
        'other-issuer': fin.HeadChainReceiptVerifier(fin.TrustRoot('service-2', 'test-hmac', H, 'b'*64), previous_head=prev, sequence=1),
        'other-key': fin.HeadChainReceiptVerifier(fin.TrustRoot('service-1', 'test-hmac', 'c'*64, 'b'*64), previous_head=prev, sequence=1)}
    for name, verifier in cases.items():
        with pytest.raises(ValueError):
            gov.verify_claim(claim, raw, verifier)
    verifier = fin.HeadChainReceiptVerifier(scheme, previous_head=prev, sequence=1)
    for tamper in ({'evidence': 'f'*64}, {'subject': 'f'*64}, {'kind': 'solo-archive'}, {'head': 'f'*64}, {'signature': '00'*32},
                   {'issuer': 'service-2'}, {'sequence': 2}, {'previous_head': 'f'*64}, {'schema': 'other'}):
        bad, _ = receipt(fin.KIND_RECEIPTS[0], FULL.fingerprint, 'e'*64, 1, prev, tamper=tamper)
        with pytest.raises(ValueError):
            gov.verify_claim(claim, bad, verifier)
    for bad in (b'', b'{}', b'unsigned', canonical(dict(kind=claim.kind))):
        with pytest.raises(ValueError):
            gov.verify_claim(claim, bad, verifier)
    with pytest.raises(ValueError):                         # fabricated unauthenticated receipt shape
        gov.verify_claim(claim, canonical(dict(kind=claim.kind, subject=claim.subject_sha256, evidence=claim.evidence_sha256)), verifier)


# ----------------------------------------------- capture gating (all gates)

def test_unit_only_gates_issue_a_capture_that_reaches_measured_inference(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    capture = setup.issue()
    assert isinstance(capture, kernel.VerifiedCapture) and 'withheld' in repr(capture)
    result = inference.infer_measured(capture, plan=PLAN)       # artificial counts: dispatch only
    assert result.inspect()['validation'] == 'withheld'
    with pytest.raises(PermissionError):
        result.disclose_final()
    # Execution authorization, disclosure and Director acceptance are neither used nor implied.
    assert not any(fin.claim_ledger(FULL, setup.proofs, expected={fin.KIND_DISCLOSURE: H, fin.KIND_EXECUTION: H}).values())


@pytest.mark.parametrize('missing', ['seed', 'verification', 'manifest', 'timestamp', 'started', 'result'])
def test_each_required_claim_is_separately_necessary(tmp_path, monkeypatch, missing):
    setup = Setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        setup.issue(proofs=setup.without(missing))


def test_extra_or_substituted_claims_do_not_help(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    full_set = setup.proofs
    report_digest = sha256(setup.report).hexdigest()
    wrong = (proof(fin.KIND_DISCLOSURE, FULL.fingerprint, report_digest), proof(fin.KIND_EXECUTION, FULL.fingerprint, report_digest),
             proof('director-acceptance', FULL.fingerprint, report_digest))
    for kind, replacement in (('verification', wrong[0]), ('verification', wrong[1]), ('timestamp', wrong[2]),
                              ('started', wrong[1]), ('manifest', wrong[0])):
        with pytest.raises(ValueError):
            setup.issue(proofs=setup.without(kind) + [replacement])
    with pytest.raises(ValueError):
        setup.issue(proofs=full_set + [setup.named['verification']])               # duplicate proof
    with pytest.raises(ValueError):
        setup.issue(proofs=setup.without('verification') + [proof(fin.KIND_VERIFICATION, 'b'*64, report_digest)])
    with pytest.raises(ValueError):
        setup.issue(proofs=setup.without('verification') + [proof(fin.KIND_VERIFICATION, FULL.fingerprint, 'f'*64)])
    with pytest.raises(ValueError):                                                  # declarations are not verified evidence
        setup.issue(proofs=setup.without('seed') + [gov.Claim(fin.KIND_SEED, FULL.fingerprint, FULL.seed_record_sha256, True)])


def test_bindings_report_receipts_and_types_are_enforced(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    for overrides in (dict(completion_sha256='d'*64), dict(report_bytes=setup.report+b' '), dict(report_bytes=b'{}'),
                      dict(journal_anchor=proof('registry-history', 'b'*64, 'b'*64)),
                      dict(started_receipt=setup.receipts[1]), dict(result_receipt=setup.receipts[0]),
                      dict(started_receipt=b'unsigned'), dict(result_receipt=setup.receipts[1]+b' ')):
        with pytest.raises((ValueError, PermissionError)):
            setup.issue(**overrides)
    for wrong in (plans.EngineeringPlan(), bounded.BoundedPlan(), None):
        with pytest.raises(PermissionError):
            setup.issue(plan=wrong)
    with pytest.raises(PermissionError):
        setup.issue(full=None)
    with pytest.raises((ValueError, TypeError)):
        setup.issue(journal_root=None)


@pytest.mark.parametrize('kwargs', [
    dict(started_changes=dict(full_plan='b'*64)), dict(started_changes=dict(seed_record='b'*64)),
    dict(started_changes=dict(code_commit='b'*40)), dict(started_changes=dict(config_sha256='b'*64)),
    dict(result_changes=dict(manifest='f'*64)), dict(result_changes=dict(failure='F1', manifest=None, status='incomplete')),
    dict(omit_result=True), dict(receipt2_previous='f'*64)])
def test_journal_binding_manifest_and_checkpoint_chain_are_enforced(tmp_path, monkeypatch, kwargs):
    with pytest.raises(ValueError):
        Setup(tmp_path, monkeypatch, **kwargs).issue()


def test_unsealed_or_modified_roots_are_refused(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    (setup.root/'accounting.json').write_bytes(canonical(COUNTS) + b' ')
    with pytest.raises(ValueError):
        setup.issue()
    other = Setup(tmp_path/'other', monkeypatch) if (tmp_path/'other').mkdir() is None else None
    (other.root/'verification.json').write_bytes(b'{}')
    with pytest.raises(ValueError):
        other.issue()
    third = Setup(tmp_path/'third', monkeypatch) if (tmp_path/'third').mkdir() is None else None
    (third.root/'manifest.json').unlink()
    (third.root/'manifest.sha256').unlink()
    with pytest.raises((ValueError, OSError)):
        third.issue()


@pytest.mark.parametrize('field,value', [
    ('bindings.completion_sha256', 'd'*64), ('bindings.plan_sha256', 'd'*64), ('bindings.code_commit', 'b'*40),
    ('bindings.seed_record_sha256', 'd'*64), ('bindings.seedless_sha256', 'd'*64), ('bindings.config_sha256', 'd'*64),
    ('bindings.seeded_config_sha256', 'd'*64), ('bindings.full_plan_sha256', 'd'*64), ('bindings.c_seed', 'x'),
    ('bindings.c_pre', 'd'*40), ('bindings.seed_commitment_sha256', 'x'), ('bindings.bundle_sha256', 'd'*64),
    ('bindings.bundle_sha256', 'x'), ('seed.bundle_sha256', 'd'*64), ('bindings.c_pre_content', 'maybe'),
    ('bindings.seeded_config_sha256', sha256(canonical(__import__('hashlab.experiments.exp002', fromlist=['Config']).Config().to_dict())).hexdigest()),
    ('bindings.config_sha256', FULL.resolved_config_sha256), ('bindings.c_seed_content', 'maybe'),
    ('seed.kind', 'public-engineering'), ('seed.c_pre', 'd'*40),
    ('independence.candidate_sha256.backend', 'openssl'), ('independence.candidate_sha256.backend', 'hashlib'),
    ('independence.candidate_sha256.independent_of_producer', False), ('independence.candidate_sha256.shared_with_producer', True),
    ('independence.candidate_sha256.known_answers', 'failed'), ('independence.candidate_sha256.role', 'file-integrity'),
    ('independence', {}), ('independence', None),
    ('bindings.accounting_sha256', 'x'), ('scope', 'bounded-fixture'), ('mode', 'success-plus-sample'),
    ('verification', 'sampled'), ('coverage.candidates_rehashed', 1000), ('coverage.compression_blocks', 1),
    ('coverage.attempts_reconstructed', 5), ('claims.execution_authorized', True), ('claims.disclosure_authorized', True),
    ('claims.external_receipt', True), ('claims.sampled_audit_absence_claim', True), ('claims.g1', True), ('claims.qa2', True),
    ('schema', 'other')])
def test_verification_report_binding_and_overclaim_rejections(field, value):
    changes = {'bindings.completion_sha256': 'c'*64}
    changes[field] = value
    report = synthetic_report(**changes)
    with pytest.raises(ValueError):
        fin.parse_verification_report(canonical(report), plan=PLAN, full=FULL, completion_sha256='c'*64)


def test_report_valid_baseline_parses_and_extra_fields_fail():
    report = synthetic_report(**{'bindings.completion_sha256': 'c'*64})
    assert fin.parse_verification_report(canonical(report), plan=PLAN, full=FULL, completion_sha256='c'*64)
    with pytest.raises(ValueError):
        fin.parse_verification_report(canonical(dict(report, extra=1)), plan=PLAN, full=FULL, completion_sha256='c'*64)
    with pytest.raises(ValueError):
        fin.parse_verification_report(b'x'*70000, plan=PLAN, full=FULL, completion_sha256='c'*64)


def test_failed_or_incomplete_evidence_never_becomes_a_capture_and_is_retained(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    for marker in ('failure.json', 'INCOMPLETE'):
        (setup.root/marker).write_bytes(b'retained')
        before = fin.classify_attempt_evidence(setup.root)
        assert before['state'] in ('failed', 'incomplete') and before['repaired'] is False and before['resumed'] is False
        with pytest.raises(ValueError):
            setup.issue()
        assert (setup.root/marker).read_bytes() == b'retained' and fin.classify_attempt_evidence(setup.root) == before
        (setup.root/marker).unlink()
    assert fin.classify_attempt_evidence(setup.root)['state'] == 'complete-candidate'
    empty = tmp_path/'empty'
    empty.mkdir()
    assert fin.classify_attempt_evidence(empty)['state'] == 'incomplete'


def test_claim_order_has_no_circular_dependency(tmp_path, monkeypatch):
    """Each artifact's pin depends only on earlier artifacts; later claims are never inputs to earlier pins."""
    setup = Setup(tmp_path, monkeypatch)
    manifest = json.loads((setup.root/'manifest.json').read_bytes())
    sealed_names = set(manifest['files'])
    assert sealed_names == {'complete.json', 'accounting.json', 'verification.json'}      # no receipts, journal or acceptance inside
    assert manifest['full_plan'] == FULL.fingerprint
    events = setup.journal.read(anchor=setup.anchor)[0]
    assert events[1]['data']['manifest'] == setup.manifest                                 # result entry carries the manifest
    heads = fin._journal_heads(setup.journal.root)
    started = json.loads(setup.receipts[0]); result = json.loads(setup.receipts[1])
    assert started['evidence'] == heads[0] and result['evidence'] == heads[1] and result['previous_head'] == started['head']
    assert heads[0] not in setup.manifest and setup.manifest not in json.dumps(started)    # checkpoint 1 predates the manifest
    assert FULL.seed_record_sha256 not in json.dumps(json.loads(SEED))                      # record digest is not inside the record
    ledger_inputs = dict(setup.named)
    assert 'disclosure' not in ledger_inputs and 'execution' not in ledger_inputs and 'acceptance' not in ledger_inputs


def test_real_chunk_replay_rejects_bounded_and_engineering_evidence(tmp_path):
    from test_exp002_production_verification import unit_inputs, AUDIT as audit
    with pytest.MonkeyPatch.context() as mp:
        unit_inputs(mp)
        root = tmp_path/'bounded'
        pin = bounded.run_bounded(root, audit_root=audit, repository_root=REPO).completion_sha256
    report = synthetic_report()
    with pytest.raises(ValueError, match='production completion contract'):
        fin._replay(root, report)
    # The kernel's engineering authenticator likewise cannot be pointed at a production plan or promoted.
    with pytest.raises(PermissionError):
        kernel.authenticate_capture(root, plan=PLAN, completion_sha256=pin)
    with pytest.raises(ValueError):
        kernel.authenticate_capture(root, plan=plans.EngineeringPlan(), completion_sha256=pin)
    with pytest.raises(ValueError):
        kernel.VerifiedCapture(COUNTS, PLAN, pin)


def test_synthetic_counts_and_engineering_captures_cannot_reach_production_inference(tmp_path, monkeypatch):
    for supplied in (COUNTS, {}, None, 'capture'):
        with pytest.raises(KernelFailure):
            inference.infer_measured(supplied, plan=PLAN)
    with pytest.raises(KernelFailure):
        statistics.commit_statistics(COUNTS, plan=PLAN, destination=tmp_path/'s.json')
    assert not (tmp_path/'s.json').exists()


# -------------------------------------------------------- statistics evidence

def promote_one_failure_to_success(row):
    """Internally consistent single-count change (a leading-zero-0 failure becomes a success)."""
    row['successes'] += 1
    row['first_byte'][255] -= 1
    row['first_byte'][0] += 1
    row['leading_zero_bits'][0] -= 1
    row['leading_zero_bits'][8] += 1



def unit_capture(pin='0'*64):
    # Private unit-only injection of artificial counts; not issued by any authenticator.
    return kernel.VerifiedCapture(COUNTS, PLAN, pin, _token=kernel._CAPTURE)


def test_private_statistics_commitment_and_independent_recalculation(tmp_path):
    restricted, pin = statistics.commit_statistics(unit_capture(), plan=PLAN, destination=tmp_path/'statistics.json')
    raw = (tmp_path/'statistics.json').read_bytes()
    assert sha256(raw).hexdigest() == pin and 'withheld' in repr(restricted)
    report = ref_statistics.verify_statistics(raw, canonical(COUNTS))
    assert report['claims']['numeric_results_disclosed'] is False and report['claims']['disclosure_authorized'] is False
    assert report['bindings']['statistics_sha256'] == pin
    text = json.dumps(report)
    assert 'p_value' not in text and 'discovery_p' not in text
    with pytest.raises(KernelFailure):                       # exclusive: never replaced
        statistics.commit_statistics(unit_capture(), plan=PLAN, destination=tmp_path/'statistics.json')
    assert (tmp_path/'statistics.json').read_bytes() == raw


@pytest.mark.parametrize('mutation', ['primary-p', 'classification', 'secondary', 'gate', 'control-p', 'accounting'])
def test_statistics_corruption_is_detected_independently(tmp_path, mutation):
    statistics.commit_statistics(unit_capture(), plan=PLAN, destination=tmp_path/'statistics.json')
    document = json.loads((tmp_path/'statistics.json').read_bytes())
    accounting = json.loads(canonical(COUNTS))
    result = document['result']
    if mutation == 'primary-p':
        result['primary'][0]['discovery_p'] = '0.5'
    elif mutation == 'classification':
        result['primary'][1]['classification'] = 'replicated-deviation-beyond-margin'
    elif mutation == 'secondary':
        result['secondary']['outcomes'][3]['p_value'] = '0.123'
    elif mutation == 'gate':
        result['controls']['statistical_gate_passed'] = not result['controls']['statistical_gate_passed']
    elif mutation == 'control-p':
        result['controls']['positives'][0]['p'] = '0.5'
    else:
        promote_one_failure_to_success(accounting['streams'][0])
    document['accounting_sha256'] = sha256(canonical(accounting)).hexdigest() if mutation == 'accounting' else document['accounting_sha256']
    with pytest.raises(ValueError):
        ref_statistics.verify_statistics(canonical(document), canonical(accounting))


def test_independent_statistics_check_rejects_incomplete_or_foreign_accounting():
    document = dict(schema=ref_statistics.SCHEMA, scope='measured-production', accounting_sha256=sha256(b'{}').hexdigest(), result={})
    with pytest.raises(ValueError):
        ref_statistics.verify_statistics(canonical(document), b'{}')
    partial = json.loads(canonical(COUNTS))
    partial['complete'] = False
    with pytest.raises(ValueError):
        ref_statistics.check_accounting(partial)
    partial = json.loads(canonical(COUNTS))
    partial['streams'][5]['trials'] -= 1
    with pytest.raises(ValueError):
        ref_statistics.check_accounting(partial)


# ------------------------------------------------------------- R9 / restore

def artifacts():
    names = ('policy', 'source_inventory', 'configuration', 'seedless_plan', 'full_plan', 'environment', 'scope',
             'tool_source', 'tool_environment', 'method', 'separation', 'shared_dependencies', 'limitations')
    return {n: canonical(dict(artifact=n)) for n in names}


def test_r9_algorithmic_record_is_structural_untrusted_and_bound_to_the_report():
    report = canonical(synthetic_report())
    raw, graph = fin.r9_algorithmic_record(report, plan=PLAN, full=FULL, artifacts=artifacts(), recorded_at='2026-10-14T00:00:00Z')
    record = r9.parse_record(raw)
    assert isinstance(record, r9.UntrustedAlgorithmicReport) and record.coverage.scope_complete == 'complete'
    assert record.coverage.expected == record.coverage.checked == fin.PRODUCTION_EVALUATIONS
    assert record.scope.operation == 'exp002-execution' and record.producer.role == 'algorithmic-verifier'
    assert r9.check_reference_graph(raw, graph, opaque_schemas=frozenset({fin.EVIDENCE_ENVELOPE}))
    with pytest.raises(ValueError):                          # default traversal fails closed on opaque schemas
        r9.check_reference_graph(raw, graph)
    smaller = dict(graph)
    smaller.pop(next(iter(smaller)))
    with pytest.raises(ValueError):
        r9.check_reference_graph(raw, smaller, opaque_schemas=frozenset({fin.EVIDENCE_ENVELOPE}))
    with pytest.raises(ValueError):
        r9.parse_record(raw.replace(b'"matched"', b'"matchedX"'))
    with pytest.raises(ValueError):
        fin.r9_algorithmic_record(report, plan=PLAN, full=FULL, artifacts=artifacts(), recorded_at='yesterday')
    short = artifacts()
    short.pop('method')
    with pytest.raises(ValueError):
        fin.r9_algorithmic_record(report, plan=PLAN, full=FULL, artifacts=short, recorded_at='2026-10-14T00:00:00Z')


def test_restore_verification_is_exact_and_narrow(tmp_path):
    source = tmp_path/'evidence'
    source.mkdir()
    (source/'a.bin').write_bytes(b'1')
    (source/'b.bin').write_bytes(b'22')
    inventory = journal_module.inspect_partial(source)
    restored = tmp_path/'restored'
    shutil.copytree(source, restored)
    assert fin.verify_restored_copy(inventory, restored)
    (restored/'b.bin').write_bytes(b'23')
    with pytest.raises(ValueError):
        fin.verify_restored_copy(inventory, restored)
    (restored/'b.bin').write_bytes(b'22')
    (restored/'c.bin').write_bytes(b'')
    with pytest.raises(ValueError):
        fin.verify_restored_copy(inventory, restored)
    with pytest.raises(ValueError):
        fin.verify_restored_copy({}, restored)


# ------------------------------------------- sealing and failure on bounded evidence

SEEDLESS = fin.Plan('a'*40)
ENGINEERING_FULL = gov.FullPlanBinding(SEEDLESS.fingerprint, H, 'b'*64)      # synthetic non-production binding


@pytest.fixture(scope='module')
def bounded_evidence(tmp_path_factory):
    from test_exp002_production_verification import unit_inputs
    root = tmp_path_factory.mktemp('sealing')/'run'
    with pytest.MonkeyPatch.context() as mp:
        unit_inputs(mp)
        pin = bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO).completion_sha256
    return root, pin


def independent_report(root, pin):
    from test_exp002_production_verification import SEED as bounded_seed
    from e002_verify import production_evidence as ev
    return canonical(ev.verify_evidence(root, completion_sha256=pin, geometry_name='bounded-fixture', seed_record=bounded_seed,
                                        audit_root=AUDIT, repository_root=REPO, allowed_extra=('verification.json', 'manifest.json', 'manifest.sha256')))


def test_outer_seal_requires_report_and_completeness_proofs_and_is_never_repaired(tmp_path, bounded_evidence, monkeypatch):
    from test_exp002_production_verification import unit_inputs
    unit_inputs(monkeypatch)
    root = tmp_path/'copy'
    shutil.copytree(bounded_evidence[0], root)
    pin = bounded_evidence[1]
    report = independent_report(root, pin)
    verification = proof(fin.KIND_VERIFICATION, ENGINEERING_FULL.fingerprint, sha256(report).hexdigest())
    provenance = dict(attempt=1, source='supplied-evidence', accounting_sha256=json.loads(report)['bindings']['accounting_sha256'])
    expected = fin.expected_manifest_pin(root, SEEDLESS, ENGINEERING_FULL, provenance, extra={'verification.json': report})
    completeness = proof('evidence-completeness', ENGINEERING_FULL.fingerprint, expected)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    for proofs in ([completeness], [verification], [verification, proof('evidence-completeness', ENGINEERING_FULL.fingerprint, 'f'*64)],
                   [verification, completeness, completeness]):
        with pytest.raises(ValueError):
            fin.seal_evidence(root, seedless=SEEDLESS, full=ENGINEERING_FULL, report_bytes=report, attempt=1, proofs=proofs)
        assert {p.name: p.read_bytes() for p in root.iterdir()} == before         # nothing written before all proofs hold
    with pytest.raises(ValueError):                                                 # report for different accounting
        altered = canonical(dict(json.loads(report), bindings=dict(json.loads(report)['bindings'], accounting_sha256='f'*64)))
        fin.seal_evidence(root, seedless=SEEDLESS, full=ENGINEERING_FULL, report_bytes=altered, attempt=1,
                          proofs=[proof(fin.KIND_VERIFICATION, ENGINEERING_FULL.fingerprint, sha256(altered).hexdigest()), completeness])
    sealed = fin.seal_evidence(root, seedless=SEEDLESS, full=ENGINEERING_FULL, report_bytes=report, attempt=1,
                               proofs=[verification, completeness])
    assert sealed == expected and (root/'manifest.sha256').read_bytes() == (sealed+'\n').encode('ascii')
    from hashlab.experiments import exp002_provenance as provenance_module
    assert provenance_module.verify_seal(root, SEEDLESS, ENGINEERING_FULL, sealed,
                                         proof('outer-manifest', ENGINEERING_FULL.fingerprint, sealed))['full_plan'] == ENGINEERING_FULL.fingerprint
    from e002_verify import production_evidence as ev
    from test_exp002_production_verification import SEED as bounded_seed
    again = ev.verify_evidence(root, completion_sha256=pin, geometry_name='bounded-fixture', seed_record=bounded_seed,
                               audit_root=AUDIT, repository_root=REPO, allowed_extra=('verification.json', 'manifest.json', 'manifest.sha256'))
    assert again['coverage']['candidates_rehashed'] == 78
    with pytest.raises((ValueError, FileExistsError)):                              # no re-seal, replacement or repair
        fin.seal_evidence(root, seedless=SEEDLESS, full=ENGINEERING_FULL, report_bytes=report, attempt=1, proofs=[verification, completeness])
    (root/'chunk-00000000.bin').write_bytes(b'tampered')
    with pytest.raises(ValueError):
        provenance_module.verify_seal(root, SEEDLESS, ENGINEERING_FULL, sealed, proof('outer-manifest', ENGINEERING_FULL.fingerprint, sealed))


def test_failed_attempt_is_disclosed_journaled_retained_and_never_finalized(tmp_path, monkeypatch):
    from test_exp002_production_verification import unit_inputs
    unit_inputs(monkeypatch)
    real = bounded.SHA256Engine.digest
    state = {'n': 0}

    def failing(self, raw):
        state['n'] += 1
        if state['n'] == 20:
            raise RuntimeError('unit-only injected failure')
        return real(self, raw)
    monkeypatch.setattr(bounded.SHA256Engine, 'digest', failing)
    root = tmp_path/'failed'
    with pytest.raises(KernelFailure):
        bounded.run_bounded(root, audit_root=AUDIT, repository_root=REPO)
    retained = {p.name: p.read_bytes() for p in root.iterdir()}
    assert 'failure.json' in retained and 'INCOMPLETE' in retained and 'complete.json' not in retained
    sidecar = tmp_path/'failure-disclosure.json'
    disclosure = journal_module.disclose_failure(sidecar, root, failure='F1', numerical_abort=False)
    listed = json.loads(sidecar.read_bytes())['partial_evidence']
    assert set(listed) == set(retained) and all(listed[n]['sha256'] == sha256(b).hexdigest() for n, b in retained.items())
    journal_root = tmp_path/'journal'
    journal_root.mkdir()
    journal = SyntheticJournal(journal_root)
    journal.append('started', 1, started())
    journal.append('result', 1, dict(failure='F1', manifest=None, disclosure=disclosure, numerical_abort=False,
                                     run_id='bounded-failure', status='incomplete'))
    with pytest.raises(ValueError):                         # a valid final attempt cannot be fabricated from failed evidence
        journal.append('started', 2, started(full_plan='b'*64))
    report = canonical(synthetic_report())
    with pytest.raises(ValueError):
        fin.seal_evidence(root, seedless=SEEDLESS, full=ENGINEERING_FULL, report_bytes=report, attempt=1, proofs=[])
    assert {p.name: p.read_bytes() for p in root.iterdir()} == retained
    with pytest.raises(FileExistsError):
        journal_module.disclose_failure(sidecar, root, failure='F1', numerical_abort=False)


def test_statistics_check_must_bind_to_the_independently_verified_accounting(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    statistics.commit_statistics(unit_capture(setup.pin), plan=PLAN, destination=tmp_path/'statistics.json')
    public = canonical(ref_statistics.verify_statistics((tmp_path/'statistics.json').read_bytes(), canonical(COUNTS)))
    digest = json.loads(public)['bindings']['statistics_sha256']
    proofs = setup.proofs + [proof(fin.KIND_STATISTICS, FULL.fingerprint, digest)]
    assert fin.require_statistics_for_capture(public, setup.report, full=FULL, proofs=proofs) == digest
    for bad_proofs in (setup.proofs, proofs[:1] + proofs[2:], proofs[1:2], []):
        with pytest.raises(ValueError):
            fin.require_statistics_for_capture(public, setup.report, full=FULL, proofs=bad_proofs)
    foreign = json.loads(canonical(COUNTS))
    promote_one_failure_to_success(foreign['streams'][0])
    other = tmp_path/'other'
    other.mkdir()
    foreign_capture = kernel.VerifiedCapture(foreign, PLAN, setup.pin, _token=kernel._CAPTURE)
    statistics.commit_statistics(foreign_capture, plan=PLAN, destination=other/'statistics.json')
    foreign_public = canonical(ref_statistics.verify_statistics((other/'statistics.json').read_bytes(), canonical(foreign)))
    foreign_digest = json.loads(foreign_public)['bindings']['statistics_sha256']
    with pytest.raises(ValueError):                     # arithmetically valid statistics for other counts are not promoted
        fin.require_statistics_for_capture(foreign_public, setup.report, full=FULL,
                                           proofs=setup.proofs + [proof(fin.KIND_STATISTICS, FULL.fingerprint, foreign_digest)])
    with pytest.raises(ValueError):
        fin.require_statistics_for_capture(canonical(dict(json.loads(public), claims=dict(numeric_results_disclosed=True,
                                          disclosure_authorized=False, execution_authorized=False))), setup.report, full=FULL, proofs=proofs)


# ------------------------------------------ D1 identities and D2 timestamp subjects

def test_timestamp_must_bind_both_c_pre_and_the_bundle_digest(tmp_path, monkeypatch):
    setup = Setup(tmp_path, monkeypatch)
    assert fin.timestamp_subject('0'*40, BUNDLE_SHA) not in (sha256(b'0'*40).hexdigest(), BUNDLE_SHA)
    assert fin.timestamp_subject('0'*40, BUNDLE_SHA) != fin.timestamp_subject('1'*40, BUNDLE_SHA)
    assert fin.timestamp_subject('0'*40, BUNDLE_SHA) != fin.timestamp_subject('0'*40, 'd'*64)
    for subject in (sha256(b'0'*40).hexdigest(),                       # the former C_pre-only binding
                    BUNDLE_SHA,                                         # bundle only
                    fin.timestamp_subject('1'*40, BUNDLE_SHA), fin.timestamp_subject('0'*40, 'd'*64)):
        with pytest.raises(ValueError):
            setup.issue(proofs=setup.without('timestamp') + [proof(fin.KIND_TIMESTAMP, FULL.fingerprint, subject)])
    for bad in ('x', '0'*39):
        with pytest.raises(ValueError):
            fin.timestamp_subject(bad, BUNDLE_SHA)
    with pytest.raises(ValueError):
        fin.timestamp_subject('0'*40, 'x')
    assert setup.issue()


def test_preregistration_bundle_is_frozen_seedless_and_named_round_only():
    body = json.loads(BUNDLE)
    assert body['reveal_round'] == '1000' and body['seedless_plan_sha256'] == FULL.seedless_sha256
    assert body['config_sha256'] != FULL.resolved_config_sha256          # seeded configuration is not in C_pre
    assert FULL.resolved_config_sha256.encode() not in BUNDLE and FULL.seed_record_sha256.encode() not in BUNDLE
    assert json.loads(SEED)['witness']['bundle_sha256'] == BUNDLE_SHA
    with pytest.raises(ValueError):
        fin.preregistration_bundle(plans.EngineeringPlan(), 1000)
    with pytest.raises(ValueError):
        fin.preregistration_bundle(PLAN, 0)


def test_seeded_and_seedless_configuration_identities_cannot_be_substituted(tmp_path, monkeypatch):
    from hashlab.experiments.exp002 import Config
    seedless = sha256(canonical(Config().to_dict())).hexdigest()
    seeded = FULL.resolved_config_sha256
    assert seedless != seeded and json.loads(fin.seed_commitment(PLAN, SEED))['config_sha256'] == seedless
    assert json.loads(fin.seed_commitment(PLAN, SEED))['seeded_config_sha256'] == seeded
    # full-plan binding built from the seedless digest has a different fingerprint and is refused everywhere
    swapped = gov.FullPlanBinding(FULL.seedless_sha256, FULL.seed_record_sha256, seedless)
    assert swapped.fingerprint != FULL.fingerprint
    with pytest.raises(ValueError):
        fin.parse_verification_report(canonical(synthetic_report(**{'bindings.completion_sha256': 'c'*64})), plan=PLAN,
                                      full=swapped, completion_sha256='c'*64)
    # the report cannot present one identity in the other's field
    for changes in ({'bindings.seeded_config_sha256': seedless}, {'bindings.config_sha256': seeded},
                    {'bindings.seeded_config_sha256': seedless, 'bindings.config_sha256': seeded}):
        with pytest.raises(ValueError):
            fin.parse_verification_report(canonical(synthetic_report(**{'bindings.completion_sha256': 'c'*64}, **changes)),
                                          plan=PLAN, full=FULL, completion_sha256='c'*64)
    # attempt journal: only the seeded digest passes; the seedless digest is refused at capture
    with pytest.raises(ValueError):
        Setup(tmp_path, monkeypatch, started_changes=dict(config_sha256=seedless)).issue()
    assert Setup(tmp_path/'ok', monkeypatch, started_changes=dict(config_sha256=seeded)).issue() if (tmp_path/'ok').mkdir() is None else True
    # a seed record whose master differs produces a different seeded digest, so a replaced seed cannot reuse the binding
    other = fin.beacon_seed_record('0'*40, 1000, 'cd'*48, witness_receipt_sha256='9'*64, witnessed_unix=SCHEDULED-90000,
                                   preregistration_bundle_sha256=BUNDLE_SHA)
    assert fin.full_binding(PLAN, other).resolved_config_sha256 != seeded and fin.full_binding(PLAN, other).fingerprint != FULL.fingerprint
    assert fin.full_binding(PLAN, other).seedless_sha256 == FULL.seedless_sha256


def test_s4_s5_records_are_acyclic_and_match_the_frozen_derivation():
    record = json.loads(SEED)
    commitment = json.loads(fin.seed_commitment(PLAN, SEED))
    randomness = sha256(bytes.fromhex(SIGNATURE)).hexdigest()
    message = f"hashlab-exp002-master-v1|{'0'*40}|1000|{randomness}".encode('ascii')
    assert record['master'] == str(int.from_bytes(sha256(message).digest()[:8], 'big'))
    assert record['master'] == commitment['master'] == str(plans.derive_master('0'*40, 1000, randomness))
    blob = json.dumps(record) + BUNDLE.decode()
    for downstream in (FULL.fingerprint, commitment['full_plan_sha256'], commitment['seeded_config_sha256'],
                       sha256(fin.seed_commitment(PLAN, SEED)).hexdigest()):
        assert downstream not in blob                                   # nothing earlier contains a later digest
    assert record['witness']['bundle_sha256'] == commitment['preregistration_bundle_sha256'] == BUNDLE_SHA
