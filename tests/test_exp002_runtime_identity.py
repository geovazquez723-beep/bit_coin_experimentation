"""G1-B: producer/verifier binding of the loaded SHA-256 implementation (synthetic substitution tests)."""
import copy
import sys

import pytest

import e002_verify.production_evidence as ev
from e002_verify import runtime_identity as vri
from hashing_fixture import synthetic_hashing_identity
from hashlab.experiments import exp002_runtime_identity as pri
from hashlab.experiments import exp002_kernel_plan as plans

win = pytest.mark.skipif(sys.platform != 'win32', reason='loaded-module observation is Windows only')


@pytest.fixture(scope='module')
def observed():
    return pri.observe_hashing_identity()


@win
def test_producer_identity_names_the_loaded_implementation(observed):
    roles = [a['role'] for a in observed['artifacts']]
    for role in ('interpreter', 'python_dll', 'hashlib_extension', 'libcrypto'):
        assert roles.count(role) == 1
    by = {a['role']: a for a in observed['artifacts']}
    assert by['python_dll']['path'].lower().endswith('python%d%d.dll' % sys.version_info[:2])
    assert by['libcrypto']['path'].lower().rsplit('\\', 1)[-1].startswith('libcrypto')
    import _hashlib
    assert by['hashlib_extension']['path'].lower() == _hashlib.__file__.lower()
    assert observed['libcrypto_version'].startswith('OpenSSL 3.')
    pri.check_hashing_identity_shape(observed)


@win
def test_verifier_observes_independently_and_agrees(observed):
    local = vri.observe_local()
    assert vri.compare(observed, local) == ([], True)
    assert local == observed        # different enumeration API, same facts


@win
def test_observation_ignores_guessed_locations(monkeypatch):
    real = pri._loaded_modules()
    monkeypatch.setattr(pri, '_loaded_modules', lambda: [p for p in real if 'libcrypto' not in p.lower()])
    with pytest.raises(ValueError, match='libcrypto'):
        pri.observe_hashing_identity()
    monkeypatch.setattr(pri, '_loaded_modules', lambda: real + ['C:/x/libcrypto-3-other.dll'])
    with pytest.raises(ValueError, match='libcrypto'):
        pri.observe_hashing_identity()


@win
@pytest.mark.parametrize('role', ['python_dll', 'hashlib_extension', 'libcrypto'])
def test_substituted_artifact_bytes_change_the_identity(role, observed, monkeypatch, tmp_path):
    """A one-bit-altered copy at the enumerated path is reported as different."""
    victim = next(a['path'] for a in observed['artifacts'] if a['role'] == role)
    copy_path = tmp_path / victim.rsplit('\\', 1)[-1]
    raw = bytearray(open(victim, 'rb').read())
    raw[len(raw) // 2] ^= 1
    copy_path.write_bytes(raw)
    swapped = [str(copy_path) if p == victim else p for p in pri._loaded_modules()]
    monkeypatch.setattr(pri, '_loaded_modules', lambda: swapped)
    monkeypatch.setattr(pri, '_openssl_version', lambda path: observed['libcrypto_version'])   # never load the altered copy
    if role == 'hashlib_extension':
        import _hashlib
        monkeypatch.setattr(_hashlib, '__file__', str(copy_path))
    altered = pri.observe_hashing_identity()
    assert [a['sha256'] for a in altered['artifacts']] != [a['sha256'] for a in observed['artifacts']]
    assert vri.compare(observed, altered)[0] == ['artifact bytes']


def test_shape_rejections():
    good = synthetic_hashing_identity()
    pri.check_hashing_identity_shape(good)
    vri.check_declared(good)
    mutations = (lambda h: h['artifacts'].pop(),
                 lambda h: h['artifacts'].append(dict(h['artifacts'][0])),
                 lambda h: h['artifacts'][0].update(sha256='G' * 64),
                 lambda h: h['artifacts'][0].update(role='libssl'),
                 lambda h: h['artifacts'][0].update(size=0),
                 lambda h: h.update(sha256_provider='sha256_c'),
                 lambda h: h.update(libcrypto_version='LibreSSL'),
                 lambda h: h.update(extra=1))
    for mutate in mutations:
        value = copy.deepcopy(good)
        mutate(value)
        with pytest.raises(ValueError):
            pri.check_hashing_identity_shape(value)
        with pytest.raises(ValueError):
            vri.check_declared(value)


def test_runtime_binding_requires_matching_interpreter_and_production_requires_hashing():
    h = synthetic_hashing_identity()
    plans.RuntimeBinding('CPython 3.13.0 x', 'p', '1' * 64, (('PyYAML', '1', '2' * 64),), hashing=h)
    with pytest.raises(ValueError, match='interpreter'):
        plans.RuntimeBinding('CPython 3.13.0 x', 'p', '9' * 64, (('PyYAML', '1', '2' * 64),), hashing=h)
    legacy = plans.RuntimeBinding('CPython 3.13.0 x', 'p', '1' * 64, (('PyYAML', '1', '2' * 64),))
    assert 'hashing' not in legacy.to_dict()          # legacy serialization unchanged
    with pytest.raises(ValueError, match='SHA-256'):
        plans.ProductionPlan('16f8b30ae30a9ef3ffc0f2868e9508e70c8007cd',
                             tuple(plans.Artifact(p, 1, '3' * 64) for p in sorted(plans.REQUIRED_SOURCES)), legacy)


def test_verifier_rejects_production_runtime_without_or_with_wrong_hashing():
    rt = {'python_version': 'CPython 3.13.0 t', 'platform': 'unit', 'interpreter_sha256': '1' * 64,
          'dependencies': [['PyYAML', '6.0.3', '2' * 64]]}
    ev._runtime_shape(rt)                                    # legacy shape accepted for bounded scopes
    with pytest.raises(ValueError, match='production runtime'):
        ev._runtime_shape(rt, production=True)
    rt['hashing'] = synthetic_hashing_identity()
    ev._runtime_shape(rt, production=True)
    rt['hashing']['artifacts'][1]['sha256'] = '8' * 64       # interpreter row != interpreter_sha256
    with pytest.raises(ValueError, match='interpreter'):
        ev._runtime_shape(rt, production=True)


@win
def test_check_binding_observation_fails_on_altered_declaration(observed, monkeypatch):
    """The verifier's observe_hashing path: matching declaration passes, altered libcrypto digest is refused."""
    declared = copy.deepcopy(observed)
    assert vri.compare(declared, vri.observe_local())[0] == []
    next(a for a in declared['artifacts'] if a['role'] == 'libcrypto')['sha256'] = 'a' * 64
    assert vri.compare(declared, vri.observe_local())[0] == ['artifact bytes']
    declared = copy.deepcopy(observed)
    declared['libcrypto_version'] = 'OpenSSL 3.0.0 substituted'
    assert vri.compare(declared, vri.observe_local())[0] == ['libcrypto version']


@win
def test_identity_is_stable_across_processes_with_different_imports(observed):
    """Incidental modules (e.g. VCRUNTIME140_1.dll pulled in by other extensions) must not change the identity."""
    import json
    import subprocess
    code = ("import sys, json; sys.path[:0] = %r\n"
            "import yaml, ssl, sqlite3, decimal\n"                      # load unrelated native extensions first
            "from hashlab.experiments.exp002_runtime_identity import observe_hashing_identity as o\n"
            "print(json.dumps(o()))" % ([p for p in sys.path if p],))
    other = json.loads(subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, check=True).stdout)
    assert other == observed
    assert vri.compare(other, vri.observe_local()) == ([], True)
