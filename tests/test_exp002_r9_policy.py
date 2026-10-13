"""Deterministic synthetic B1 tests; no experiment or real authority fixtures."""
import ast
import copy
from dataclasses import fields
from hashlib import sha256
import json
from pathlib import Path

import pytest

from hashlab.experiments import exp002_r9_policy as p
from hashlab.experiments import exp002_r9_contracts as m


def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii')


def fixture(director=False, kind='qualification', operation='migration-implementation'):
    artifacts = {}

    def ref(schema, data):
        r = dict(schema=schema, sha256=sha256(data).hexdigest(), bytes=str(len(data)))
        artifacts[m.Ref(schema, r['sha256'], len(data))] = data
        return r

    policy = canonical(p._policy_document())
    catalog = canonical(p._catalog_document())
    source = canonical(dict(schema=p.SOURCE_SCHEMA, entries=[dict(
        id='synthetic-source', sha256='b' * 64, bytes='7')], object_format='sha1', commit='a' * 40))
    environment = canonical(dict(schema=p.ENVIRONMENT_SCHEMA, entries=[dict(
        id='synthetic-environment', sha256='c' * 64, bytes='9')]))
    sr = ref(p.SOURCE_SCHEMA, source)
    er = ref(p.ENVIRONMENT_SCHEMA, environment)
    human = ref(p.HUMAN_SCHEMA, b'SYNTHETIC approved PASS complete https://invalid.example; unauthenticated')
    refs = {'bindings.policy_ref': ref(p.POLICY_SCHEMA, policy),
            'synthetic.catalog_ref': ref(p.CATALOG_SCHEMA, catalog),
            'bindings.source.inventory_ref': sr, 'producer.tool_source_ref': sr,
            'producer.tool_environment_ref': er, 'bindings.environment_ref': er}
    if director:
        refs['authorization_evidence_ref'] = human
    v = dict(qualification_only='synthetic-b1',
             record_schema=m.DIRECTOR_SCHEMA if director else m.ALGORITHMIC_SCHEMA,
             identities=dict(p.IDENTITIES), scope=dict(study='experiment-002',
             operation=operation, attempt=None, stage=None), verification_kind=None if director else kind,
             decision='approved' if director else None, scope_complete=None if director else 'complete',
             references=refs, findings=[] if director else [
                 dict(check_id='synthetic-required', state='matched', evidence_refs=[human], reason='Unrecomputed claim'),
                 dict(check_id='synthetic-optional', state='missing', evidence_refs=[], reason='Synthetic unavailable evidence'),
                 dict(check_id='synthetic-na', state='not-applicable', evidence_refs=[], reason=p.CHECKS[2][3])])
    return v, policy, catalog, artifacts


def check(v, policy, catalog, artifacts):
    return p.check_structural_policy(p.parse_synthetic_declaration(canonical(v)),
        p.parse_structural_policy(policy), p.parse_reference_catalog(catalog), artifacts)


@pytest.mark.parametrize('director,kind,operation', [
    (True, None, 'policy-adoption'), (True, None, 'migration-implementation'),
    (False, 'qualification', 'migration-implementation'),
    (False, 'evidence-integrity', 'migration-implementation')])
def test_positive_untrusted(director, kind, operation):
    result = check(*fixture(director, kind, operation))
    assert result.schema == p.FINDINGS_SCHEMA
    assert result.completeness == 'structural-scope-only'
    assert result.trust == 'untrusted'
    assert any(r[2] == 'bytes-matched-content-unverified' for r in result.references)
    assert {f.name for f in fields(result)} == {'schema', 'completeness', 'trust', 'checks', 'references', 'limitations'}
    assert 'No authenticated approval' in result.limitations[0]
    assert 'No G1/QA2/G2' in result.limitations[1]


@pytest.mark.parametrize('factory,parser', [(p._policy_document, p.parse_structural_policy),
                                           (p._catalog_document, p.parse_reference_catalog)])
def test_exact_profiles(factory, parser):
    original = factory()
    assert parser(canonical(original)).canonical_bytes == canonical(original)
    for key in original:
        bad = copy.deepcopy(original)
        del bad[key]
        with pytest.raises(ValueError):
            parser(canonical(bad))
    for key in dict(p.IDENTITIES):
        bad = copy.deepcopy(original)
        bad['identities'][key] = 'wrong'
        with pytest.raises(ValueError):
            parser(canonical(bad))
    bad = copy.deepcopy(original)
    bad['self-appointed-authority'] = 'trusted'
    with pytest.raises(ValueError):
        parser(canonical(bad))


@pytest.mark.parametrize('parser,good', [
    (p.parse_structural_policy, canonical(p._policy_document())),
    (p.parse_reference_catalog, canonical(p._catalog_document())),
    (p.parse_synthetic_declaration, canonical(fixture()[0]))])
@pytest.mark.parametrize('mutation', [lambda b: b + b'\n', lambda b: b' ' + b,
    lambda b: b'\xef\xbb\xbf' + b, lambda b: b'{"x":null,"x":null}',
    lambda b: b'{"n":1}', lambda b: b'{"n":1.5}', lambda b: b'{"n":NaN}',
    lambda b: b'{' , lambda b: b'x' * 65537,
    lambda b: b'[' * 17 + b']' * 17])
def test_strict_inputs(parser, good, mutation):
    with pytest.raises(ValueError):
        parser(mutation(good))


def test_self_expanding_catalog_and_profile():
    v = p._catalog_document()
    v['schemas'].append(dict(schema='hashlab-arbitrary-v1', treatment='bytes-matched-content-unverified'))
    with pytest.raises(ValueError):
        p.parse_reference_catalog(canonical(v))
    v = p._policy_document()
    v['scopes'][2]['checks'][0]['applicability'] = 'optional'
    with pytest.raises(ValueError):
        p.parse_structural_policy(canonical(v))


@pytest.mark.parametrize('mutation', [
    lambda v: v['scope'].update(attempt='E002-Q-1'),
    lambda v: v['scope'].update(stage='D'),
    lambda v: v['scope'].update(operation='qa2-execution'),
    lambda v: v['scope'].update(operation='exp002-execution'),
    lambda v: v['scope'].update(study='e001-historical-reconstruction'),
    lambda v: v.update(verification_kind='statistical'),
    lambda v: v.update(qualification_only='real'),
    lambda v: v['findings'].pop(),
    lambda v: v['findings'].reverse(),
    lambda v: v['findings'].append(copy.deepcopy(v['findings'][0])),
    lambda v: v['findings'][1].update(check_id='synthetic-required'),
    lambda v: v['findings'][0].update(check_id='unknown'),
    lambda v: v['findings'][0].update(state='not-applicable'),
    lambda v: v['findings'][0].update(evidence_refs=[]),
    lambda v: v['findings'][1].update(state='matched'),
    lambda v: v['findings'][2].update(reason='self exemption'),
    lambda v: v['references'].pop('bindings.policy_ref'),
    lambda v: v['references'].update(scope_ref=v['references']['bindings.policy_ref']),
    lambda v: v['references'].update(predecessor_ref=v['references']['bindings.policy_ref']),
    lambda v: v['references']['bindings.policy_ref'].update(schema=p.HUMAN_SCHEMA),
    lambda v: v['references']['bindings.source.inventory_ref'].update(schema=p.HUMAN_SCHEMA),
    lambda v: v['references']['producer.tool_environment_ref'].update(schema=p.SOURCE_SCHEMA),
    lambda v: v['findings'][0]['evidence_refs'][0].update(schema=m.DIRECTOR_SCHEMA),
    lambda v: v['findings'][0]['evidence_refs'][0].update(schema='hashlab-unknown-v1'),
    lambda v: v['findings'][0]['evidence_refs'].append(copy.deepcopy(v['findings'][0]['evidence_refs'][0])),
])
def test_negative_declarations(mutation):
    v, *rest = fixture()
    mutation(v)
    with pytest.raises(ValueError):
        check(v, *rest)


@pytest.mark.parametrize('key', dict(p.IDENTITIES))
def test_declaration_identity(key):
    v, *rest = fixture()
    v['identities'][key] = 'wrong'
    with pytest.raises(ValueError):
        check(v, *rest)


def test_missing_explicit_and_opaque_legacy():
    v, *rest = fixture()
    v['findings'][0].update(state='missing', evidence_refs=[])
    result = check(v, *rest)
    assert result.checks[0] == ('synthetic-required', 'missing')
    policy, catalog, artifacts = rest
    for schema in p.LEGACY_SCHEMAS:
        data = b'SYNTHETIC legacy bytes: dependencies unresolved'
        ref = m.Ref(schema, sha256(data).hexdigest(), len(data))
        artifacts[ref] = data
        v['findings'][1].update(state='matched', evidence_refs=[dict(schema=schema,
            sha256=ref.sha256, bytes=str(ref.bytes))])
        assert check(v, policy, catalog, artifacts).references[-1][2] == 'bytes-matched-content-unverified'


@pytest.mark.parametrize('mode', ['missing', 'size', 'digest', 'map', 'typed-opaque', 'inventory-refs'])
def test_reference_failures(mode):
    v, policy, catalog, artifacts = fixture()
    ref = next(r for r in artifacts if r.schema == p.SOURCE_SCHEMA)
    if mode == 'missing':
        del artifacts[ref]
    elif mode == 'size':
        artifacts[ref] += b'x'
    elif mode == 'digest':
        artifacts[ref] = b'x' * ref.bytes
    elif mode == 'map':
        artifacts.update({i: b'' for i in range(129)})
    else:
        data = b'SYNTHETIC opaque source' if mode == 'typed-opaque' else canonical(dict(
            schema=p.SOURCE_SCHEMA, entries=[], object_format='sha1', commit='a'*40,
            references=[v['references']['bindings.source.inventory_ref']]))
        new = m.Ref(p.SOURCE_SCHEMA, sha256(data).hexdigest(), len(data))
        artifacts[new] = data
        for field in ('bindings.source.inventory_ref', 'producer.tool_source_ref'):
            v['references'][field] = dict(schema=new.schema, sha256=new.sha256, bytes=str(new.bytes))
    with pytest.raises(ValueError):
        check(v, policy, catalog, artifacts)


@pytest.mark.parametrize('study,prefix', [('experiment-002', 'E002-S'), ('experiment-002', 'E002-Q'),
    ('experiment-002', 'E002-A'), ('e001-historical-reconstruction', 'E001-H')])
@pytest.mark.parametrize('number', [1, 4294967295])
def test_future_attempts(study, prefix, number):
    assert p.recognize_attempt_id(study, f'{prefix}-{number}') == (prefix, number)


@pytest.mark.parametrize('label', ['E002-Q-0', 'E002-Q-01', 'E002-Q-+1', 'E002-Q--1',
    'E002-Q-0x1', 'E002-Q-1.0', 'E002-Q-4294967296', 'E002-Q-999999999999999999999',
    'E002-X-1', 'E001-H-1', 'S1', 'S5', 'A1', 'A3', 'e002-q-1', 'E002-Q-\u0661', None])
def test_invalid_attempts(label):
    with pytest.raises(ValueError):
        p.recognize_attempt_id('experiment-002', label)


def test_m1a_boundary_no_fallback():
    data = Path('tests/fixtures/exp002-r9-director-synthetic-v1.json').read_bytes()
    record = m.parse_record(data)
    _, policy, catalog, artifacts = fixture()
    with pytest.raises(ValueError, match='M1A v1'):
        p.check_structural_policy(record, p.parse_structural_policy(policy),
                                  p.parse_reference_catalog(catalog), artifacts)
    with pytest.raises(ValueError):
        p.parse_synthetic_declaration(data)
    v = json.loads(data)
    v['bindings']['policy_ref']['schema'] = p.POLICY_SCHEMA
    with pytest.raises(ValueError):
        m.parse_record(canonical(v))
    with pytest.raises(ValueError):
        m.parse_record(canonical(fixture()[0]))


def test_no_graph_expansion_or_opaque_typed_records():
    # B1 has no recursive fields: cycles/deep graphs fail at their first edge.
    for schema in p.TYPED_SCHEMAS:
        v, *rest = fixture()
        v['findings'][0]['evidence_refs'][0]['schema'] = schema
        with pytest.raises(ValueError):
            check(v, *rest)
    v, *rest = fixture()
    v['findings'][0]['evidence_refs'] *= 129
    with pytest.raises(ValueError):
        check(v, *rest)


def test_import_and_api_isolation():
    source = Path(p.__file__).read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imports == {'dataclasses', 'hashlib', None}
    assert {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} == {'json', 're'}
    assert not {'open', 'eval', 'exec', '__import__'} & {n.func.id for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')} == {
        'parse_structural_policy', 'parse_reference_catalog', 'parse_synthetic_declaration',
        'recognize_attempt_id', 'check_structural_policy'}


def test_reference_occurrence_and_aggregate_limits():
    v, policy, catalog, artifacts = fixture()
    refs = []
    for i in range(123):
        data = ('SYNTHETIC-%03d-' % i).encode('ascii').ljust(65536, b'x')
        ref = m.Ref(p.LEGACY_SCHEMAS[2], sha256(data).hexdigest(), len(data))
        artifacts[ref] = data
        refs.append(dict(schema=ref.schema, sha256=ref.sha256, bytes=str(ref.bytes)))
    refs.sort(key=lambda r: (r['schema'], r['sha256']))
    v['findings'][1].update(state='matched', evidence_refs=refs)
    with pytest.raises(ValueError, match='reference count limit'):
        p.parse_synthetic_declaration(canonical(v))
    v['findings'][1]['evidence_refs'] = refs[:17]
    used = {m.Ref(r['schema'], r['sha256'], int(r['bytes'])) for r in refs[:17]}
    artifacts = {r: data for r, data in artifacts.items() if r.schema not in p.LEGACY_SCHEMAS or r in used}
    with pytest.raises(ValueError, match='aggregate byte limit'):
        check(v, policy, catalog, artifacts)


@pytest.mark.parametrize('schema', [p.SOURCE_SCHEMA, p.ENVIRONMENT_SCHEMA])
@pytest.mark.parametrize('mode', ['duplicate', 'unsafe', 'unknown', 'numeric', 'nested', 'overflow'])
def test_typed_inventory_contracts(schema, mode):
    v, policy, catalog, artifacts = fixture()
    old = next(r for r in artifacts if r.schema == schema)
    document = json.loads(artifacts[old])
    if mode == 'duplicate':
        document['entries'] *= 2
    elif mode == 'unsafe':
        document['entries'][0]['id'] = '../source'
    elif mode == 'unknown':
        document['extra'] = None
    elif mode == 'numeric':
        document['entries'][0]['bytes'] = True
    elif mode == 'nested':
        document['entries'][0]['dependencies'] = [dict(schema=old.schema, sha256=old.sha256, bytes=str(old.bytes))]
    else:
        document['entries'][0]['bytes'] = str(2**64)
    data = canonical(document)
    new = m.Ref(schema, sha256(data).hexdigest(), len(data))
    artifacts[new] = data
    for field, r in v['references'].items():
        if r['schema'] == schema:
            v['references'][field] = dict(schema=schema, sha256=new.sha256, bytes=str(new.bytes))
    with pytest.raises(ValueError):
        check(v, policy, catalog, artifacts)


def test_direct_constructed_profiles_and_declarations_are_revalidated():
    v, policy, catalog, artifacts = fixture()
    for profile, cat in [(p.UntrustedStructuralPolicy(b'{}'), p.parse_reference_catalog(catalog)),
                         (p.parse_structural_policy(policy), p.UntrustedReferenceCatalog(b'{}'))]:
        with pytest.raises(ValueError):
            p.check_structural_policy(p.parse_synthetic_declaration(canonical(v)), profile, cat, artifacts)
    with pytest.raises(ValueError):
        p.check_structural_policy(p.UntrustedSyntheticDeclaration(b'{}'),
            p.parse_structural_policy(policy), p.parse_reference_catalog(catalog), artifacts)


def test_m1a_fixture_masquerades_rejected_in_every_typed_field():
    v, *rest = fixture()
    for field in v['references']:
        bad = copy.deepcopy(v)
        bad['references'][field]['schema'] = 'hashlab-exp002-r9-plan-envelope-v1'
        with pytest.raises(ValueError):
            check(bad, *rest)


def test_optional_not_applicable_is_explicit_and_preserved():
    v, *rest = fixture()
    v['findings'][1].update(state='not-applicable', reason=p.CHECKS[1][3])
    assert check(v, *rest).checks[1] == ('synthetic-optional', 'not-applicable')
    v['findings'][1]['reason'] = 'arbitrary exemption'
    with pytest.raises(ValueError):
        check(v, *rest)
