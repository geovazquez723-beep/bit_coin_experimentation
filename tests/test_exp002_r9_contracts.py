"""Synthetic structural qualification: no authority, scientific or execution checks."""
import copy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json

import pytest

from hashlab.experiments import exp002_r9_contracts as r9


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode('ascii')


OPAQUE = 'hashlab-exp002-r9-plan-envelope-v1'
PAYLOAD = b'synthetic opaque bytes; no policy or evidence authority'
REF = dict(schema=OPAQUE, sha256=sha256(PAYLOAD).hexdigest(), bytes=str(len(PAYLOAD)))


def fixture(algorithmic=False):
    value = dict(
        schema=r9.DIRECTOR_SCHEMA,
        bindings=dict(active_protocol=r9.ACTIVE_PROTOCOL, scientific_baseline=r9.SCIENTIFIC_BASELINE,
                      governance=r9.GOVERNANCE, secondary=r9.SECONDARY, policy_ref=REF,
                      source=dict(object_format='sha1', commit='a' * 40, inventory_ref=REF),
                      configuration_ref=None, seedless_plan_ref=None, full_plan_ref=None, environment_ref=None),
        scope=dict(study='experiment-002', operation='migration-implementation', scope_ref=REF, attempt=None, stage=None),
        producer=dict(actor_id='synthetic-actor', role='operator', tool_source_ref=REF, tool_environment_ref=REF),
        recorded_at='2026-10-12T00:00:00Z', predecessor_ref=None)
    if algorithmic:
        value.update(schema=r9.ALGORITHMIC_SCHEMA, verification_kind='qualification', input_refs=[REF],
                     method_ref=REF, reference_refs=[REF], findings=[dict(check_id='synthetic-check', state='matched', evidence_refs=[REF], reason='Unrecomputed assertion')],
                     coverage=dict(unit='checks', expected='1', checked='1', scope_complete='complete'),
                     implementation_separation_ref=REF, shared_dependencies_ref=REF,
                     limitations_ref=REF, first_mismatch_ref=None)
    else:
        value.update(approval_id='synthetic-approval', decision='approved', action='migration-implementation',
                     constraints_ref=REF, subject_refs=[REF], release_ref=None, seed_commitment_ref=None,
                     gate_decision_refs=[], authorization_evidence_ref=REF, not_before='2026-10-12T00:00:00Z',
                     not_after='2026-10-13T00:00:00Z', supersedes_ref=None)
    return copy.deepcopy(value)


def set_path(value, path, replacement):
    parts = path.split('.')
    for key in parts[:-1]:
        value = value[int(key)] if type(value) is list else value[key]
    key = parts[-1]
    value[int(key) if type(value) is list else key] = replacement


@pytest.mark.parametrize('algorithmic', [False, True])
def test_positive_canonical_untrusted(algorithmic):
    record = r9.parse_record(canonical(fixture(algorithmic)))
    expected = r9.UntrustedAlgorithmicReport if algorithmic else r9.UntrustedDirectorApproval
    assert type(record) is expected
    assert not hasattr(record, 'authorize')
    assert not hasattr(record, 'verify')
    with pytest.raises(FrozenInstanceError):
        record.schema = 'changed'
    if algorithmic:
        assert record.coverage.scope_complete == 'complete'  # False claim still untrusted.
    else:
        assert record.decision == 'approved'  # No human origin was authenticated.


@pytest.mark.parametrize('path,replacement', [
    ('schema', 'hashlab-exp002-r9-director-approval-v2'),
    ('bindings.active_protocol', r9.SCIENTIFIC_BASELINE),
    ('bindings.scientific_baseline', r9.ACTIVE_PROTOCOL),
    ('bindings.governance', 'other-governance'),
    ('bindings.secondary', 'hashlab-exp002-secondary-statistics-proposal-v1'),
    ('bindings.source.object_format', 'sha256'),
    ('bindings.source.commit', 'A' * 40), ('bindings.source.commit', 'a' * 39),
    ('bindings.source', {}), ('bindings.policy_ref.sha256', 'A' * 64),
    ('bindings.policy_ref.schema', '../../policy'), ('bindings.policy_ref.bytes', '-1'),
    ('bindings.policy_ref.bytes', '01'), ('bindings.policy_ref.bytes', '1e2'),
    ('bindings.policy_ref.bytes', '65537'), ('bindings.policy_ref.bytes', True),
    ('bindings.policy_ref.bytes', 1), ('bindings.policy_ref.bytes', 1.0),
    ('recorded_at', '2026-02-30T00:00:00Z'), ('recorded_at', '2026-10-12T00:00:00+00:00'),
    ('recorded_at', '2026-10-12T00:00:00.0Z'), ('producer.actor_id', '../actor'),
    ('producer.actor_id', 'C:\\actor'), ('producer.actor_id', 'CON'),
    ('producer.actor_id', 'actor:stream'), ('scope.attempt', '../../attempt'),
    ('scope.stage', 'X'), ('scope.study', 'e001-historical-reconstruction'),
    ('action', 'exp002-execution'), ('subject_refs', [REF, REF]),
    ('not_after', '2026-10-11T00:00:00Z'), ('supersedes_ref', REF),
    ('authorization_evidence_ref', None),
])
def test_invalid_structure(path, replacement):
    value = fixture()
    set_path(value, path, replacement)
    with pytest.raises(ValueError):
        r9.parse_record(canonical(value))


@pytest.mark.parametrize('path,replacement', [
    ('coverage.expected', '18446744073709551616'), ('coverage.expected', '9' * 5000),
    ('coverage.checked', True), ('coverage.checked', '2'), ('coverage.scope_complete', True),
    ('findings.0.state', 'verified'), ('findings.0.reason', '\ud800'),
    ('findings.0.reason', 'x' * 2049), ('verification_kind', 'authorization'),
    ('findings', [dict(check_id='x', state='matched', evidence_refs=[], reason='x')] * 2),
])
def test_invalid_algorithmic(path, replacement):
    value = fixture(True)
    set_path(value, path, replacement)
    with pytest.raises(ValueError):
        r9.parse_record(canonical(value))


@pytest.mark.parametrize('transform', [
    lambda b: b + b'\n', lambda b: b' ' + b, lambda b: b'\xef\xbb\xbf' + b,
    lambda b: b.replace(b':', b': ', 1),
    lambda b: b.replace(b'"approved"', b'"approv\\u0065d"'),
    lambda b: b.replace(b'"decision":"approved"', b'"decision":"approved","decision":"denied"'),
    lambda b: b.replace(b'"commit":"' + b'a' * 40 + b'"', b'"commit":"' + b'a' * 40 + b'","commit":"' + b'a' * 40 + b'"'),
    lambda b: b.replace(b'"decision":"approved"', b'"decision":NaN'),
    lambda b: b.replace(b'"decision":"approved"', b'"decision":Infinity'),
    lambda b: b.replace(b'"decision":"approved"', b'"decision":-Infinity'),
    lambda b: b.replace(b'"decision":"approved"', b'"decision":1e300'),
    lambda b: b'\xff' + b,
])
def test_noncanonical(transform):
    with pytest.raises(ValueError):
        r9.parse_record(transform(canonical(fixture())))


@pytest.mark.parametrize('algorithmic', [False, True])
def test_exact_shapes(algorithmic):
    original = fixture(algorithmic)
    def objects(v):
        if type(v) is dict:
            yield v
            for child in v.values():
                yield from objects(child)
        elif type(v) is list:
            for child in v:
                yield from objects(child)
    for index in range(len(list(objects(original)))):
        for unknown in (False, True):
            value = copy.deepcopy(original)
            obj = list(objects(value))[index]
            if unknown:
                obj['unknown'] = None
            else:
                del obj[next(iter(obj))]
            with pytest.raises(ValueError):
                r9.parse_record(canonical(value))


def test_resource_preflight():
    for data in (b' ' * (r9.MAX_RECORD_BYTES + 1), b'[' * 17 + b']' * 17):
        with pytest.raises(ValueError):
            r9.parse_record(data)
    value = fixture()
    value['subject_refs'] = [REF] * 129
    with pytest.raises(ValueError):
        r9.parse_record(canonical(value))
    value = fixture(True)
    value['findings'] = [dict(check_id=f'x{i}', state='matched', evidence_refs=[REF], reason='x') for i in range(128)]
    with pytest.raises(ValueError, match='reference count'):
        r9.parse_record(canonical(value))


def test_execution_declaration_cannot_be_incomplete():
    value = fixture()
    value['action'] = value['scope']['operation'] = 'exp002-execution'
    with pytest.raises(ValueError, match='incomplete execution'):
        r9.parse_record(canonical(value))


def test_graph_exact_bytes_and_explicit_terminal_policy():
    ref = r9.Ref(OPAQUE, REF['sha256'], len(PAYLOAD))
    root = canonical(fixture())
    assert r9.check_reference_graph(root, {ref: PAYLOAD}, opaque_schemas=frozenset({OPAQUE})) == (ref,)
    for artifacts in ({}, {ref: b'x'}, {ref: b'x' * len(PAYLOAD)}):
        with pytest.raises(ValueError):
            r9.check_reference_graph(root, artifacts, opaque_schemas=frozenset({OPAQUE}))
    with pytest.raises(ValueError):
        r9.check_reference_graph(root, {ref: PAYLOAD})
    with pytest.raises(ValueError):
        r9.check_reference_graph(root, {}, opaque_schemas=frozenset({r9.DIRECTOR_SCHEMA}))


def test_cycle_detection_with_synthetic_digest_oracle(monkeypatch):
    # A real content-addressed cycle needs a SHA-256 fixed point. Replace only the
    # digest oracle to exercise the active-stack check, not an authority verifier.
    value = fixture()
    value['predecessor_ref'] = dict(schema=r9.DIRECTOR_SCHEMA, sha256='b' * 64, bytes='0')
    for _ in range(4):
        value['predecessor_ref']['bytes'] = str(len(canonical(value)))
    data = canonical(value)
    class Digest:
        def hexdigest(self):
            return 'b' * 64
    monkeypatch.setattr(r9, 'sha256', lambda data: sha256(data) if data == PAYLOAD else Digest())
    ref = r9.Ref(r9.DIRECTOR_SCHEMA, 'b' * 64, len(data))
    with pytest.raises(ValueError, match='cycle'):
        opaque_ref = r9.Ref(OPAQUE, REF['sha256'], len(PAYLOAD))
        r9.check_reference_graph(data, {ref: data, opaque_ref: PAYLOAD}, opaque_schemas=frozenset({OPAQUE}))


def test_graph_depth_and_aggregate_bounds(monkeypatch):
    ref = r9.Ref(OPAQUE, REF['sha256'], len(PAYLOAD))
    data = canonical(fixture())
    monkeypatch.setattr(r9, 'MAX_AGGREGATE_BYTES', len(data) + len(PAYLOAD) - 1)
    with pytest.raises(ValueError, match='aggregate'):
        r9.check_reference_graph(data, {ref: PAYLOAD}, opaque_schemas=frozenset({OPAQUE}))
    monkeypatch.setattr(r9, 'MAX_AGGREGATE_BYTES', 1048576)
    child = canonical(fixture())
    child_ref = dict(schema=r9.DIRECTOR_SCHEMA, sha256=sha256(child).hexdigest(), bytes=str(len(child)))
    value = fixture()
    value['predecessor_ref'] = child_ref
    monkeypatch.setattr(r9, 'MAX_RESOLUTION_DEPTH', 0)
    with pytest.raises(ValueError, match='resolution depth'):
        r9.check_reference_graph(canonical(value), {ref: PAYLOAD, r9.Ref(r9.DIRECTOR_SCHEMA, child_ref['sha256'], len(child)): child}, opaque_schemas=frozenset({OPAQUE}))


def test_import_boundary():
    import ast
    from pathlib import Path
    tree = ast.parse(Path(r9.__file__).read_text())
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports == {'dataclasses', 'datetime', 'hashlib', 'json', 're', 'typing'}


@pytest.mark.parametrize('kind,algorithmic', [('director', False), ('algorithmic', True)])
def test_checked_in_canonical_fixture(kind, algorithmic):
    from pathlib import Path
    data = (Path(__file__).parent / 'fixtures' / f'exp002-r9-{kind}-synthetic-v1.json').read_bytes()
    assert data == canonical(fixture(algorithmic))
    r9.parse_record(data)


def test_uint64_exact_upper_boundary():
    value = fixture(True)
    value['coverage']['expected'] = value['coverage']['checked'] = str(2**64 - 1)
    assert r9.parse_record(canonical(value)).coverage.checked == 2**64 - 1


def test_reference_depth_real_limit_and_shared_graph():
    opaque_ref = r9.Ref(OPAQUE, REF['sha256'], len(PAYLOAD))
    artifacts = {opaque_ref: PAYLOAD}
    data = canonical(fixture())
    for level in range(9):
        if level <= 7:
            r9.check_reference_graph(data, artifacts, opaque_schemas=frozenset({OPAQUE}))
        else:
            with pytest.raises(ValueError, match='resolution depth'):
                r9.check_reference_graph(data, artifacts, opaque_schemas=frozenset({OPAQUE}))
        ref = dict(schema=r9.DIRECTOR_SCHEMA, sha256=sha256(data).hexdigest(), bytes=str(len(data)))
        artifacts[r9.Ref(r9.DIRECTOR_SCHEMA, ref['sha256'], len(data))] = data
        value = fixture()
        value['predecessor_ref'] = ref
        data = canonical(value)


def test_graph_edge_budget():
    ref = r9.Ref(OPAQUE, REF['sha256'], len(PAYLOAD))
    artifacts = {ref: PAYLOAD}
    subjects = []
    for index in range(16):
        child = fixture()
        child['approval_id'] = f'synthetic-{index}'
        data = canonical(child)
        item = dict(schema=r9.DIRECTOR_SCHEMA, sha256=sha256(data).hexdigest(), bytes=str(len(data)))
        artifacts[r9.Ref(r9.DIRECTOR_SCHEMA, item['sha256'], len(data))] = data
        subjects.append(item)
    root = fixture()
    root['subject_refs'] = sorted(subjects, key=lambda v: (v['schema'], v['sha256']))
    with pytest.raises(ValueError, match='graph reference count'):
        r9.check_reference_graph(canonical(root), artifacts, opaque_schemas=frozenset({OPAQUE}))
