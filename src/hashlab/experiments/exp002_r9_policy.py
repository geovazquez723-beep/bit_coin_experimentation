"""B1 synthetic structural qualification only; no authentication or permission.

This is an explicit, separately selected boundary, never a fallback record parser.
Policy/catalog bytes are untrusted exact code-defined profiles. Inventories are
bounded declarations, not observations of source or execution provenance.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import re

from . import exp002_r9_contracts as m1a

POLICY_SCHEMA = 'hashlab-exp002-r9-structural-policy-profile-v1'
CATALOG_SCHEMA = 'hashlab-exp002-r9-reference-catalog-v1'
FINDINGS_SCHEMA = 'hashlab-exp002-r9-structural-policy-findings-v1'
SOURCE_SCHEMA = 'hashlab-exp002-r9-source-inventory-v1'
ENVIRONMENT_SCHEMA = 'hashlab-exp002-r9-environment-inventory-v1'
HUMAN_SCHEMA = 'hashlab-exp002-r9-human-channel-export-opaque-v1'
LEGACY_SCHEMAS = (
    'hashlab-exp002-seedless-plan-v2', 'hashlab-exp002-full-plan-binding-v1',
    'hashlab-exp002-accounting-v2', 'hashlab-exp002-outer-manifest-v1',
    'hashlab-manifest-v1')
TYPED_SCHEMAS = (POLICY_SCHEMA, CATALOG_SCHEMA, SOURCE_SCHEMA, ENVIRONMENT_SCHEMA,
                 m1a.DIRECTOR_SCHEMA, m1a.ALGORITHMIC_SCHEMA)
OPAQUE_SCHEMAS = (HUMAN_SCHEMA,) + LEGACY_SCHEMAS
IDENTITIES = (
    ('active_protocol', m1a.ACTIVE_PROTOCOL),
    ('scientific_baseline', m1a.SCIENTIFIC_BASELINE),
    ('governance', m1a.GOVERNANCE), ('secondary', m1a.SECONDARY))
# Tuple rules cannot be expanded by an input policy. All omitted fields fail.
FIELD_RULES = (
    ('bindings.policy_ref', (POLICY_SCHEMA,)),
    ('bindings.source.inventory_ref', (SOURCE_SCHEMA,)),
    ('producer.tool_source_ref', (SOURCE_SCHEMA,)),
    ('bindings.environment_ref', (ENVIRONMENT_SCHEMA,)),
    ('producer.tool_environment_ref', (ENVIRONMENT_SCHEMA,)),
    ('authorization_evidence_ref', (HUMAN_SCHEMA,)),
    ('bindings.seedless_plan_ref', (LEGACY_SCHEMAS[0],)),
    ('bindings.full_plan_ref', (LEGACY_SCHEMAS[1],)),
    ('synthetic.catalog_ref', (CATALOG_SCHEMA,)),
    ('findings.synthetic-required.evidence_refs', (HUMAN_SCHEMA,)),
    ('findings.synthetic-optional.evidence_refs', LEGACY_SCHEMAS),
    ('findings.synthetic-na.evidence_refs', ()),
)
SCOPES = (
    (m1a.DIRECTOR_SCHEMA, 'policy-adoption', None),
    (m1a.DIRECTOR_SCHEMA, 'migration-implementation', None),
    (m1a.ALGORITHMIC_SCHEMA, 'migration-implementation', 'qualification'),
    (m1a.ALGORITHMIC_SCHEMA, 'migration-implementation', 'evidence-integrity'))
CHECKS = (
    ('synthetic-required', 'required', (HUMAN_SCHEMA,), ''),
    ('synthetic-optional', 'optional', LEGACY_SCHEMAS, 'Synthetic optional evidence is not supplied.'),
    ('synthetic-na', 'not-applicable', (), 'Synthetic design scope excludes execution.'),
)
LIMITS = (('artifact_bytes', 65536), ('json_nesting', 16), ('references', 128),
          ('artifact_map_entries', 128), ('resolution_depth', 8),
          ('aggregate_bytes', 1048576))


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def _catalog_document():
    return dict(schema=CATALOG_SCHEMA, identities=dict(IDENTITIES),
                schemas=[dict(schema=s, treatment=('typed-structural' if s in TYPED_SCHEMAS
                          else 'bytes-matched-content-unverified'))
                         for s in sorted(TYPED_SCHEMAS + OPAQUE_SCHEMAS)],
                fields=[dict(field=f, schemas=list(s)) for f, s in FIELD_RULES])


def _policy_document():
    return dict(schema=POLICY_SCHEMA, identities=dict(IDENTITIES),
                catalog_schema=CATALOG_SCHEMA, resource_policy=m1a.REFERENCE_POLICY_ID,
                bounds={k: str(v) for k, v in LIMITS},
                reference_fields=[dict(field=f, schemas=list(s)) for f, s in FIELD_RULES],
                opaque_terminals=[dict(schema=s, result='bytes-matched-content-unverified')
                                  for s in OPAQUE_SCHEMAS],
                scopes=[dict(record_schema=s, study='experiment-002', operation=o,
                             verification_kind=k, attempt=None, stage=None,
                             checks=[] if s == m1a.DIRECTOR_SCHEMA else [
                                 dict(check_id=c, position=str(i), applicability=a,
                                      evidence_schemas=list(e), rationale=r)
                                 for i, (c, a, e, r) in enumerate(CHECKS)])
                        for s, o, k in SCOPES])


@dataclass(frozen=True)
class UntrustedStructuralPolicy:
    canonical_bytes: bytes


@dataclass(frozen=True)
class UntrustedReferenceCatalog:
    canonical_bytes: bytes


@dataclass(frozen=True)
class UntrustedSyntheticDeclaration:
    """A B1 test declaration, deliberately not an M1A v1 record or upgrade."""
    canonical_bytes: bytes


@dataclass(frozen=True)
class StructuralPolicyFindings:
    schema: str
    completeness: str
    trust: str
    checks: tuple[tuple[str, str], ...]
    references: tuple[tuple[str, m1a.Ref, str], ...]
    limitations: tuple[str, ...]


def parse_structural_policy(data: bytes) -> UntrustedStructuralPolicy:
    """Require the exact synthetic profile; authenticate no policy adoption."""
    m1a._require(m1a._decode(data) == _policy_document(), 'unsupported structural policy')
    return UntrustedStructuralPolicy(data)


def parse_reference_catalog(data: bytes) -> UntrustedReferenceCatalog:
    """Require the compiled catalog; authenticate neither identity nor content."""
    m1a._require(m1a._decode(data) == _catalog_document(), 'unsupported reference catalog')
    return UntrustedReferenceCatalog(data)


def recognize_attempt_id(study: str, label: str) -> tuple[str, int]:
    """Recognize syntax only; allocate no attempt, registry entry or retry right."""
    m1a._require(type(label) is str and len(label) <= 17, 'invalid attempt ID')
    match = re.fullmatch(r'(E002-[SQA]|E001-H)-([1-9][0-9]{0,9})', label)
    m1a._require(match is not None, 'invalid attempt ID')
    prefix, number = match.groups()
    m1a._require(study == ('experiment-002' if prefix.startswith('E002-')
                          else 'e001-historical-reconstruction'), 'attempt study mismatch')
    m1a._require(int(number) <= 4294967295, 'attempt number limit')
    return prefix, int(number)


def _reference(value):
    m1a._shape(value, ('schema', 'sha256', 'bytes'))
    return m1a.Ref(m1a._enum(value['schema'], TYPED_SCHEMAS + OPAQUE_SCHEMAS),
                   m1a._hex(value['sha256'], 64), m1a._uint(value['bytes'], 65536))


def _declaration(data):
    v = m1a._decode(data)
    m1a._shape(v, ('qualification_only', 'record_schema', 'identities', 'scope',
                   'verification_kind', 'decision', 'scope_complete', 'references', 'findings'))
    m1a._enum(v['qualification_only'], ('synthetic-b1',))
    m1a._require(v['identities'] == dict(IDENTITIES), 'identity mismatch')
    s = v['scope']
    m1a._shape(s, ('study', 'operation', 'attempt', 'stage'))
    m1a._require(s['study'] == 'experiment-002' and s['attempt'] is None and
                 s['stage'] is None, 'out-of-profile scope')
    m1a._require((v['record_schema'], s['operation'], v['verification_kind']) in SCOPES,
                 'out-of-profile operation/kind')
    director = v['record_schema'] == m1a.DIRECTOR_SCHEMA
    if director:
        m1a._enum(v['decision'], ('approved', 'denied', 'withdrawn'))
        m1a._require(v['scope_complete'] is None, 'Director coverage must be null')
    else:
        m1a._require(v['decision'] is None, 'algorithmic decision must be null')
        m1a._enum(v['scope_complete'], ('complete', 'partial', 'unknown'))
    refs = v['references']
    m1a._require(type(refs) is dict, 'reference fields required')
    required = {'bindings.policy_ref', 'bindings.source.inventory_ref',
                'producer.tool_source_ref', 'producer.tool_environment_ref', 'synthetic.catalog_ref'}
    permitted = required | {'bindings.environment_ref'}
    if director:
        required |= {'authorization_evidence_ref'}
        permitted |= {'authorization_evidence_ref'}
    else:
        permitted |= {'bindings.seedless_plan_ref', 'bindings.full_plan_ref'}
    m1a._require(required <= set(refs) <= permitted, 'missing/unsupported reference fields')
    occurrences = []

    def add(field, values):
        m1a._require(type(values) is list and len(values) <= 128, 'reference array limit')
        parsed = [_reference(r) for r in values]
        keys = [(r.schema, r.sha256) for r in parsed]
        m1a._require(keys == sorted(set(keys)), 'unsorted/duplicate references')
        for ref in parsed:
            m1a._require(ref.schema in dict(FIELD_RULES)[field], 'field/reference type mismatch')
            occurrences.append((field, ref))
            m1a._require(len(occurrences) <= 128, 'reference count limit')

    for field in sorted(refs):
        add(field, [refs[field]])
    findings = v['findings']
    m1a._require(type(findings) is list and len(findings) <= 128, 'findings limit')
    expected = () if director else CHECKS
    m1a._require(len(findings) == len(expected), 'omitted/extra checks')
    for f, (check, applicability, schemas, rationale) in zip(findings, expected):
        m1a._shape(f, ('check_id', 'state', 'evidence_refs', 'reason'))
        m1a._require(f['check_id'] == check, 'unknown/duplicate/reordered checks')
        m1a._enum(f['state'], ('matched', 'mismatched', 'missing', 'unverifiable', 'not-applicable'))
        reason = f['reason']
        m1a._require(type(reason) is str and len(reason) <= 2048 and
                     all(ord(c) >= 32 and not 0xD800 <= ord(c) <= 0xDFFF for c in reason),
                     'invalid finding reason')
        add('findings.' + check + '.evidence_refs', f['evidence_refs'])
        if applicability == 'required':
            m1a._require(f['state'] != 'not-applicable', 'required check not applicable')
        if applicability == 'not-applicable':
            m1a._require(f['state'] == 'not-applicable' and reason == rationale and
                         not f['evidence_refs'], 'fixed not-applicable rationale')
        elif applicability == 'optional' and f['state'] == 'not-applicable':
            m1a._require(not f['evidence_refs'] and reason == rationale,
                         'optional not-applicable rationale')
        elif not f['evidence_refs']:
            m1a._require(f['state'] == 'missing', 'absent evidence must be explicit missing')
        else:
            m1a._require(f['state'] not in ('missing', 'not-applicable'), 'evidence/state mismatch')
    return v, occurrences


def parse_synthetic_declaration(data: bytes) -> UntrustedSyntheticDeclaration:
    """Explicit synthetic format only; no v1 fallback or human/scientific validation."""
    _declaration(data)
    return UntrustedSyntheticDeclaration(data)


def _inventory(data, schema):
    v = m1a._decode(data)
    names = ('schema', 'entries', 'object_format', 'commit') if schema == SOURCE_SCHEMA else ('schema', 'entries')
    m1a._shape(v, names)
    m1a._require(v['schema'] == schema, 'inventory schema mismatch')
    if schema == SOURCE_SCHEMA:
        m1a._enum(v['object_format'], ('sha1',))
        m1a._hex(v['commit'], 40)
    entries = v['entries']
    m1a._require(type(entries) is list and len(entries) <= 128, 'inventory entry limit')
    ids = []
    for entry in entries:
        m1a._shape(entry, ('id', 'sha256', 'bytes'))
        ids.append(m1a._id(entry['id']))
        m1a._hex(entry['sha256'], 64)
        m1a._uint(entry['bytes'])
    m1a._require(ids == sorted(set(ids)), 'unsorted/duplicate inventory IDs')
    # Entries describe byte pins, not Ref edges; no filesystem resolution exists.


def check_structural_policy(record, profile, catalog, supplied_artifacts) -> StructuralPolicyFindings:
    """Check only synthetic consistency and supplied bytes, never authenticate.

    M1A instances fail explicitly: v1 cannot represent B1 refs. Missing graph
    bytes fail; missing check evidence must be declared as a missing finding.
    Inventories validate declarations only; opaque content is never decoded.
    """
    m1a._require(type(profile) is UntrustedStructuralPolicy and
                 type(catalog) is UntrustedReferenceCatalog, 'explicit B1 profile/catalog required')
    parse_structural_policy(profile.canonical_bytes)
    parse_reference_catalog(catalog.canonical_bytes)
    m1a._require(type(record) is UntrustedSyntheticDeclaration,
                 'M1A v1 cannot represent B1 bindings; no implicit upgrade')
    v, occurrences = _declaration(record.canonical_bytes)
    m1a._require(type(supplied_artifacts) is dict and len(supplied_artifacts) <= 128,
                 'artifact map limit')
    total = len(record.canonical_bytes)
    seen = set()
    results = []
    for field, ref in occurrences:
        m1a._require(ref in supplied_artifacts, 'missing referenced bytes')
        data = supplied_artifacts[ref]
        m1a._require(type(data) is bytes and len(data) <= 65536 and len(data) == ref.bytes,
                     'referenced size mismatch')
        m1a._require(sha256(data).hexdigest() == ref.sha256, 'referenced digest mismatch')
        if ref not in seen:
            total += len(data)
            m1a._require(total <= 1048576, 'aggregate byte limit')
            seen.add(ref)
        if ref.schema == POLICY_SCHEMA:
            m1a._require(data == profile.canonical_bytes, 'policy binding mismatch')
            parse_structural_policy(data)
        elif ref.schema == CATALOG_SCHEMA:
            m1a._require(data == catalog.canonical_bytes, 'catalog binding mismatch')
            parse_reference_catalog(data)
        elif ref.schema in (SOURCE_SCHEMA, ENVIRONMENT_SCHEMA):
            _inventory(data, ref.schema)
        elif ref.schema in (m1a.DIRECTOR_SCHEMA, m1a.ALGORITHMIC_SCHEMA):
            # No field admits these until a versioned complete content contract exists.
            raise ValueError('implemented v1 records unsupported in B1 evidence fields')
        results.append((field, ref, 'bytes-matched-content-unverified' if ref.schema in
                        OPAQUE_SCHEMAS else 'untrusted-structure-matched'))
    return StructuralPolicyFindings(FINDINGS_SCHEMA, 'structural-scope-only', 'untrusted',
        tuple((f['check_id'], f['state']) for f in v['findings']), tuple(results),
        ('No authenticated approval, scientific PASS, external receipt or execution capability.',
         'No G1/QA2/G2 result, provenance, chronology or dependency completeness.',
         'Synthetic declarations only; M1A v1 binding incompatibility remains.'))
