"""R9-M1A strict structural declarations. No authentication or authorization.

Only standard-library parsing/value utilities are imported. Reference checking
consumes an explicitly supplied in-memory graph; it never retrieves artifacts.
"""
from dataclasses import dataclass, fields
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Final

PARSER_ID: Final = 'hashlab-exp002-r9-strict-parser-v1'
REFERENCE_POLICY_ID: Final = 'hashlab-exp002-r9-bounded-references-v1'
ACTIVE_PROTOCOL: Final = 'proposal-revision-9|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1'
SCIENTIFIC_BASELINE: Final = 'proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1'
GOVERNANCE: Final = 'hashlab-exp002-solo-governance-v1'
SECONDARY: Final = 'hashlab-exp002-secondary-statistics-proposal-v2'
DIRECTOR_SCHEMA: Final = 'hashlab-exp002-r9-director-approval-v1'
ALGORITHMIC_SCHEMA: Final = 'hashlab-exp002-r9-algorithmic-verification-v1'
PROPOSED_SCHEMAS: Final = frozenset(
    'hashlab-exp002-r9-' + name + '-v1' for name in (
        'director-approval', 'algorithmic-verification', 'external-timestamp',
        'history-checkpoint', 'solo-archive', 'restore-verification', 'human-audit',
        'g1-decision', 'qa2-decision', 'g2-decision', 'plan-envelope',
        'evidence-envelope', 'compatibility-decision')) | frozenset({
            'hashlab-e001-r9-solo-audit-acceptance-v1'})
MAX_RECORD_BYTES: Final = 65536
MAX_NESTING_DEPTH: Final = 16
MAX_REFERENCES: Final = 128
MAX_RESOLUTION_DEPTH: Final = 8
MAX_AGGREGATE_BYTES: Final = 1048576
MAX_COUNT: Final = 2**64 - 1
ACTIONS: Final = frozenset(('policy-adoption migration-implementation protocol-freeze '
    'g1-acceptance qa2-execution e001-enumeration e001-audit-acceptance '
    'release-creation commitment-publication seed-procedure exp002-execution '
    'retry interpretation publication').split())


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _shape(value, names):
    _require(type(value) is dict and set(value) == set(names), 'incorrect object fields')


def _enum(value, choices):
    _require(type(value) is str and value in choices, 'unsupported identity/enum')
    return value


def _hex(value, size):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % size, value), 'invalid hex identity')
    return value


def _uint(value, maximum=MAX_COUNT):
    _require(type(value) is str and len(value) <= 20 and
             re.fullmatch(r'0|[1-9][0-9]*', value), 'invalid decimal integer')
    number = int(value)
    _require(number <= maximum, 'integer out of bounds')
    return number


def _id(value):
    # Flat identifiers only: no paths, traversal, Windows devices or ADS.
    _require(type(value) is str and len(value) <= 128 and
             re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', value), 'unsafe identifier')
    _require(value.upper() not in {'CON', 'PRN', 'AUX', 'NUL'} |
             {p + str(n) for p in ('COM', 'LPT') for n in range(1, 10)}, 'reserved identifier')
    return value


def _time(value):
    _require(type(value) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value), 'invalid UTC time')
    datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    return value


@dataclass(frozen=True)
class Ref:
    schema: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class Source:
    object_format: str
    commit: str
    inventory_ref: Ref


@dataclass(frozen=True)
class Bindings:
    active_protocol: str
    scientific_baseline: str
    governance: str
    secondary: str
    policy_ref: Ref
    source: Source
    configuration_ref: Ref | None
    seedless_plan_ref: Ref | None
    full_plan_ref: Ref | None
    environment_ref: Ref | None


@dataclass(frozen=True)
class Scope:
    study: str
    operation: str
    scope_ref: Ref
    attempt: str | None
    stage: str | None


@dataclass(frozen=True)
class Producer:
    actor_id: str
    role: str
    tool_source_ref: Ref
    tool_environment_ref: Ref


@dataclass(frozen=True)
class Finding:
    check_id: str
    state: str
    evidence_refs: tuple[Ref, ...]
    reason: str


@dataclass(frozen=True)
class RecordCommon:
    schema: str
    bindings: Bindings
    scope: Scope
    producer: Producer
    recorded_at: str
    predecessor_ref: Ref | None


@dataclass(frozen=True)
class UntrustedDirectorApproval(RecordCommon):
    """Parsed declaration only, including when decision says approved."""
    approval_id: str
    decision: str
    action: str
    constraints_ref: Ref
    subject_refs: tuple[Ref, ...]
    release_ref: Ref | None
    seed_commitment_ref: Ref | None
    gate_decision_refs: tuple[Ref, ...]
    authorization_evidence_ref: Ref
    not_before: str
    not_after: str
    supersedes_ref: Ref | None


@dataclass(frozen=True)
class Coverage:
    unit: str
    expected: int
    checked: int
    scope_complete: str


@dataclass(frozen=True)
class UntrustedAlgorithmicReport(RecordCommon):
    """Coverage and findings are assertions, never verified scientific evidence."""
    verification_kind: str
    input_refs: tuple[Ref, ...]
    method_ref: Ref
    reference_refs: tuple[Ref, ...]
    findings: tuple[Finding, ...]
    coverage: Coverage
    implementation_separation_ref: Ref
    shared_dependencies_ref: Ref
    limitations_ref: Ref
    first_mismatch_ref: Ref | None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _forbidden(value):
    raise ValueError('JSON numbers/constants unsupported; use decimal strings')


def _decode(data):
    _require(type(data) is bytes and len(data) <= MAX_RECORD_BYTES, 'record bytes/type limit')
    # Lexical preflight before JSON allocation; ignore brackets inside strings.
    depth = 0
    quoted = escaped = False
    for byte in data:
        _require(byte < 128, 'canonical ASCII required')
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            _require(depth <= MAX_NESTING_DEPTH, 'nesting limit')
        elif byte in (93, 125):
            depth -= 1
            _require(depth >= 0, 'invalid nesting')
    value = json.loads(data, object_pairs_hook=_pairs, parse_int=_forbidden,
                       parse_float=_forbidden, parse_constant=_forbidden)
    _require(json.dumps(value, sort_keys=True, ensure_ascii=True,
                        separators=(',', ':'), allow_nan=False).encode('ascii') == data,
             'noncanonical bytes')
    return value


class _Parser:
    def __init__(self):
        self.references = []

    def ref(self, value, nullable=False):
        if nullable and value is None:
            return None
        _shape(value, ('schema', 'sha256', 'bytes'))
        result = Ref(_enum(value['schema'], PROPOSED_SCHEMAS),
                     _hex(value['sha256'], 64), _uint(value['bytes'], MAX_RECORD_BYTES))
        self.references.append(result)
        _require(len(self.references) <= MAX_REFERENCES, 'reference count limit')
        return result

    def refs(self, value):
        _require(type(value) is list and len(value) <= MAX_REFERENCES, 'reference array limit')
        result = tuple(self.ref(v) for v in value)
        keys = [(r.schema, r.sha256) for r in result]
        _require(keys == sorted(set(keys)), 'unsorted/duplicate references')
        return result

    def record(self, v):
        _require(type(v) is dict, 'record object required')
        schema = v.get('schema')
        _enum(schema, (DIRECTOR_SCHEMA, ALGORITHMIC_SCHEMA))
        cls = UntrustedDirectorApproval if schema == DIRECTOR_SCHEMA else UntrustedAlgorithmicReport
        _shape(v, (f.name for f in fields(cls)))
        b = v['bindings']
        _shape(b, (f.name for f in fields(Bindings)))
        for name, expected in (('active_protocol', ACTIVE_PROTOCOL),
                               ('scientific_baseline', SCIENTIFIC_BASELINE),
                               ('governance', GOVERNANCE), ('secondary', SECONDARY)):
            _enum(b[name], (expected,))
        s = b['source']
        _shape(s, ('object_format', 'commit', 'inventory_ref'))
        source = Source(_enum(s['object_format'], ('sha1',)), _hex(s['commit'], 40), self.ref(s['inventory_ref']))
        bindings = Bindings(*(b[k] for k in ('active_protocol', 'scientific_baseline', 'governance', 'secondary')),
                            self.ref(b['policy_ref']), source,
                            *(self.ref(b[k], True) for k in ('configuration_ref', 'seedless_plan_ref', 'full_plan_ref', 'environment_ref')))
        s = v['scope']
        _shape(s, (f.name for f in fields(Scope)))
        scope = Scope(_enum(s['study'], ('experiment-002', 'e001-historical-reconstruction')),
                      _enum(s['operation'], ACTIONS), self.ref(s['scope_ref']),
                      None if s['attempt'] is None else _id(s['attempt']),
                      None if s['stage'] is None else _enum(s['stage'], ('D', 'V', 'C')))
        _require((scope.operation.startswith('e001-')) == (scope.study == 'e001-historical-reconstruction'), 'study/operation mismatch')
        p = v['producer']
        _shape(p, (f.name for f in fields(Producer)))
        producer = Producer(_id(p['actor_id']), _enum(p['role'], ('director', 'operator', 'algorithmic-verifier', 'external-service', 'human-auditor', 'archive-operator', 'gate-evaluator')),
                            self.ref(p['tool_source_ref']), self.ref(p['tool_environment_ref']))
        common = dict(schema=schema, bindings=bindings, scope=scope, producer=producer,
                      recorded_at=_time(v['recorded_at']), predecessor_ref=self.ref(v['predecessor_ref'], True))
        if cls is UntrustedDirectorApproval:
            _require(v['action'] == scope.operation, 'action/scope mismatch')
            before, after = _time(v['not_before']), _time(v['not_after'])
            _require(before <= after, 'reversed time interval')
            extra = dict(approval_id=_id(v['approval_id']), decision=_enum(v['decision'], ('approved', 'denied', 'withdrawn')),
                         action=_enum(v['action'], ACTIONS), not_before=before, not_after=after,
                         subject_refs=self.refs(v['subject_refs']), gate_decision_refs=self.refs(v['gate_decision_refs']))
            for key in ('constraints_ref', 'release_ref', 'seed_commitment_ref', 'authorization_evidence_ref', 'supersedes_ref'):
                extra[key] = self.ref(v[key], key in ('release_ref', 'seed_commitment_ref', 'supersedes_ref'))
            _require(extra['supersedes_ref'] is None or extra['supersedes_ref'].schema == DIRECTOR_SCHEMA, 'wrong supersedes schema')
            if scope.operation in ('exp002-execution', 'retry'):
                _require(all(getattr(bindings, k) is not None for k in ('configuration_ref', 'seedless_plan_ref', 'full_plan_ref', 'environment_ref')) and
                         extra['release_ref'] is not None and extra['seed_commitment_ref'] is not None and
                         {r.schema for r in extra['gate_decision_refs']} ==
                         {'hashlab-exp002-r9-' + g + '-decision-v1' for g in ('g1', 'qa2', 'g2')}, 'incomplete execution declaration')
            return cls(**common, **extra)
        c = v['coverage']
        _shape(c, (f.name for f in fields(Coverage)))
        coverage = Coverage(_enum(c['unit'], ('occurrences', 'records', 'files', 'checks')),
                            _uint(c['expected']), _uint(c['checked']), _enum(c['scope_complete'], ('complete', 'partial', 'unknown')))
        _require(coverage.checked <= coverage.expected, 'coverage exceeds expected')
        _require(type(v['findings']) is list and len(v['findings']) <= MAX_REFERENCES, 'findings limit')
        findings = []
        for f in v['findings']:
            _shape(f, (field.name for field in fields(Finding)))
            _require(type(f['reason']) is str and len(f['reason']) <= 2048 and
                     all(ord(ch) >= 32 and not 0xD800 <= ord(ch) <= 0xDFFF for ch in f['reason']), 'invalid reason')
            findings.append(Finding(_id(f['check_id']), _enum(f['state'], ('matched', 'mismatched', 'missing', 'unverifiable', 'not-applicable')), self.refs(f['evidence_refs']), f['reason']))
        _require(len({f.check_id for f in findings}) == len(findings), 'duplicate checks')
        extra = {k: self.ref(v[k], k == 'first_mismatch_ref') for k in ('method_ref', 'implementation_separation_ref', 'shared_dependencies_ref', 'limitations_ref', 'first_mismatch_ref')}
        return cls(**common, **extra, verification_kind=_enum(v['verification_kind'], ('statistical', 'candidate-reconstruction', 'evidence-integrity', 'historical-compatibility', 'overlap', 'qualification', 'combined')),
                   input_refs=self.refs(v['input_refs']), reference_refs=self.refs(v['reference_refs']), findings=tuple(findings), coverage=coverage)


def parse_record(data: bytes) -> UntrustedDirectorApproval | UntrustedAlgorithmicReport:
    """Validate canonical structure only; return an immutable untrusted claim."""
    return _Parser().record(_decode(data))


def check_reference_graph(root: bytes, artifacts: dict[Ref, bytes], *,
                          opaque_schemas: frozenset[str] = frozenset()) -> tuple[Ref, ...]:
    """Check a caller-supplied graph, never resolve paths or authenticate claims.

    Only the two implemented schemas can be traversed. The caller may explicitly
    designate other proposed schemas as opaque terminal bytes. Their internal
    structure/dependencies are NOT checked. Default traversal fails closed.
    Count limits apply to edge occurrences; aggregate bytes count unique content.
    """
    _require(type(artifacts) is dict and len(artifacts) <= MAX_REFERENCES, 'artifact map limit')
    _require(type(opaque_schemas) is frozenset and opaque_schemas <= PROPOSED_SCHEMAS -
             {DIRECTOR_SCHEMA, ALGORITHMIC_SCHEMA}, 'invalid opaque schema policy')
    _require(type(root) is bytes and len(root) <= MAX_RECORD_BYTES, 'record bytes/type limit')
    total = len(root)
    _require(total <= MAX_AGGREGATE_BYTES, 'aggregate byte limit')
    active = set()
    visited = set()
    result = []
    edges = 0

    def walk(data, depth):
        nonlocal total, edges
        _require(depth <= MAX_RESOLUTION_DEPTH, 'resolution depth limit')
        fingerprint = sha256(data).hexdigest()
        _require(fingerprint not in active, 'reference cycle')
        active.add(fingerprint)
        parser = _Parser()
        parser.record(_decode(data))
        for ref in parser.references:
            _require(depth + 1 <= MAX_RESOLUTION_DEPTH, 'resolution depth limit')
            edges += 1
            _require(edges <= MAX_REFERENCES, 'graph reference count limit')
            _require(ref in artifacts, 'missing referenced bytes')
            child = artifacts[ref]
            _require(type(child) is bytes and len(child) == ref.bytes and len(child) <= MAX_RECORD_BYTES, 'referenced size mismatch')
            _require(sha256(child).hexdigest() == ref.sha256, 'referenced digest mismatch')
            _require(ref.sha256 not in active, 'reference cycle')
            if ref not in visited:
                total += len(child)
                _require(total <= MAX_AGGREGATE_BYTES, 'aggregate byte limit')
                visited.add(ref)
                result.append(ref)
            # Revisit shared subgraphs along every path so a shallower earlier
            # visit cannot hide a later excessive-depth path. Edge budget bounds it.
            if ref.schema not in opaque_schemas:
                decoded = _decode(child)
                _require(type(decoded) is dict and decoded.get('schema') == ref.schema, 'referenced schema mismatch')
                walk(child, depth + 1)
        active.remove(fingerprint)

    walk(root, 0)
    return tuple(result)
