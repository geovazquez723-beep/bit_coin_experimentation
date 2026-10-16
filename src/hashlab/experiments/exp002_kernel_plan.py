"""Inert production bindings and fixed engineering adapter; no seed selection."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from .exp002 import Config, arm_seed_labels
from .exp002_foundation import Plan, canonical, decode, _hex
from .exp002_s14 import S14_FILES, load_s14
from .exp002_journal import file_inventory
from .exp002_runtime_identity import observe_hashing_identity, check_hashing_identity_shape
from .exp002_r9_contracts import ACTIVE_PROTOCOL, SCIENTIFIC_BASELINE, GOVERNANCE, SECONDARY

FORMAT = 'hashlab-e002-kernel-chunks-v1'
# Include package initializers and transitive history/serialization dependencies,
# not merely the directly imported scientific functions. Independent verification
# must use the matching checkout; a different package inventory fails closed.
_PACKAGE = Path(__file__).resolve().parents[1]
REQUIRED_SOURCES = tuple(sorted(
    ['src/hashlab/'+p.relative_to(_PACKAGE).as_posix() for p in _PACKAGE.rglob('*.py')]
    + ['src/hashlab/experiments/e001_contract.json']))


def master_material(precommit, round_number, randomness_hex):
    """Approved S4 ASCII bytes. Inputs are calculations, not authenticated receipts."""
    _hex(precommit, 40)
    _hex(randomness_hex, 64)
    if type(round_number) is not int or not 1 <= round_number < 2**64:
        raise ValueError('canonical positive beacon round required')
    return f'hashlab-exp002-master-v1|{precommit}|{round_number}|{randomness_hex}'.encode('ascii')


def derive_master(precommit, round_number, randomness_hex):
    """Pure deterministic derivation; never enables a production action."""
    return int.from_bytes(sha256(master_material(precommit, round_number, randomness_hex)).digest()[:8], 'big')


@dataclass(frozen=True)
class Artifact:
    path: str
    size: int
    sha256: str

    def __post_init__(self):
        if (type(self.path) is not str or not re.fullmatch(r'[A-Za-z0-9_./-]{1,240}', self.path)
                or self.path.startswith('/') or any(p in ('', '.', '..') for p in self.path.split('/'))):
            raise ValueError('relative artifact path required')
        if type(self.size) is not int or self.size <= 0:
            raise ValueError('nonempty artifact required')
        _hex(self.sha256, 64)

    def to_dict(self):
        return dict(path=self.path, size=self.size, sha256=self.sha256)


def source_inventory(repository):
    return tuple(Artifact(p, **file_inventory(Path(repository)/p)) for p in sorted(REQUIRED_SOURCES))


def observe_runtime():
    """Observe actual interpreter and installed dependency bytes; no installation."""
    import sys
    import platform
    import importlib.metadata
    package=importlib.metadata.distribution('PyYAML')
    entries=[]
    for name in sorted(str(p) for p in package.files or () if str(p).startswith(('yaml/','_yaml/','PyYAML-'))):
        path=Path(package.locate_file(name))
        if path.is_file() and not name.endswith(('.pyc','.pyo')):
            entries.append(dict(path=name,**file_inventory(path)))
    if not entries: raise ValueError('dependency artifact inventory unavailable')
    return RuntimeBinding('CPython '+sys.version,platform.platform(),
        file_inventory(sys.executable)['sha256'],
        (('PyYAML',package.version,sha256(canonical(entries)).hexdigest()),),
        hashing=observe_hashing_identity())


@dataclass(frozen=True)
class RuntimeBinding:
    """Exact supplied artifact inventory, not an assertion of runtime approval."""
    python_version: str
    platform: str
    interpreter_sha256: str
    dependencies: tuple[tuple[str, str, str], ...]
    # Loaded SHA-256 implementation identity (G1-B). None only for legacy/engineering bindings.
    hashing: dict | None = None

    def __post_init__(self):
        if (type(self.python_version) is not str or not self.python_version.startswith('CPython ')
                or type(self.platform) is not str or not self.platform.strip()):
            raise ValueError('exact runtime identity required')
        _hex(self.interpreter_sha256, 64)
        if type(self.dependencies) is not tuple or not self.dependencies:
            raise ValueError('dependency artifacts required')
        names = []
        for row in self.dependencies:
            if type(row) is not tuple or len(row) != 3:
                raise ValueError('dependency name/version/artifact digest required')
            name, version, pin = row
            if type(name) is not str or not name or type(version) is not str or not version:
                raise ValueError('dependency identity required')
            _hex(pin, 64)
            names.append(name)
        if names != sorted(set(names)) or 'PyYAML' not in names:
            raise ValueError('unique sorted dependencies including PyYAML required')
        if self.hashing is not None:
            check_hashing_identity_shape(self.hashing)
            if [a['sha256'] for a in self.hashing['artifacts'] if a['role'] == 'interpreter'] != [self.interpreter_sha256]:
                raise ValueError('hashing identity interpreter differs from interpreter_sha256')

    def to_dict(self):
        value = dict(python_version=self.python_version, platform=self.platform,
                     interpreter_sha256=self.interpreter_sha256,
                     dependencies=[list(x) for x in self.dependencies])
        if self.hashing is not None:
            value['hashing'] = self.hashing
        return value


def history_binding():
    return dict(schema='hashlab-e002-kernel-history-binding-v1',
                files={p: dict(size=n, sha256=h) for p, (n, h) in S14_FILES.items()},
                occurrences=7_000_000, distinct_a3=60721, distinct_history=6048573,
                exclusion_sha256=Config().a3_exclusion_sha256,
                original_manifest='546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b')


@dataclass(frozen=True)
class ProductionPlan:
    code_commit: str
    sources: tuple[Artifact, ...]
    runtime: RuntimeBinding
    schema: str = 'hashlab-e002-production-kernel-plan-v1'

    def __post_init__(self):
        _hex(self.code_commit, 40)
        if self.schema != 'hashlab-e002-production-kernel-plan-v1' or type(self.runtime) is not RuntimeBinding:
            raise ValueError('production plan identity required')
        if self.runtime.hashing is None:
            raise ValueError('production plan requires the loaded SHA-256 implementation identity')
        if (type(self.sources) is not tuple or any(type(x) is not Artifact for x in self.sources)
                or [x.path for x in self.sources] != sorted(REQUIRED_SOURCES)):
            raise ValueError('complete exact kernel source inventory required')

    def to_dict(self):
        return dict(schema=self.schema, scope='production-disabled',
            identities=dict(active_protocol=ACTIVE_PROTOCOL, scientific_baseline=SCIENTIFIC_BASELINE,
                            governance=GOVERNANCE, secondary=SECONDARY),
            science=Plan(self.code_commit).to_dict(),
            config_sha256=sha256(canonical(Config().to_dict())).hexdigest(),
            seed=dict(master='authenticated-S4-seed-record-required;not-supplied',
                      master_message='hashlab-exp002-master-v1|C_pre|R_star|randomness_hex',
                      master_conversion='SHA256-first-8-bytes-uint64-big-endian',
                      domain='experiment-002',
                      arm_labels={a: {p: list(arm_seed_labels(a, p)) for p in ('selection', 'stage-allocation')}
                                  for a in ('A1', 'A3')},
                      a2=['experiment-002','A2-prefix-nonce-w80','prefix-key-v1'],
                      n1=['experiment-002','N1-feistel64-w8','permutation-key-v1'],
                      n2=['experiment-002','N2-random-bytes-w80','stream-key-v1']),
            controls=dict(n1_stop_exclusive=30999999, positive_start=str(2**63),
                          thresholds_u32={'P1':2**32//1020,'P2+':2**32//12750,'P2-':2**32//50},
                          n2_uniqueness='approved-probabilistic-assumption;no-deduplication'),
            sources=[x.to_dict() for x in self.sources], runtime=self.runtime.to_dict(),
            history=history_binding(), evidence=dict(format=FORMAT, rows_per_chunk=4096,
                verification='full-independent-regeneration-and-rehash-supported',
                audit_decision='unresolved;approved-minimal-success-plus-sample-option-retained'),
            restrictions=dict(execution_enabled=False, arbitrary_master=False, quota_override=False,
                primary_progress=False, incomplete_primary_disclosure=False,
                validation='restricted', final_disclosure='separate-authorization-required',
                f4='full-failed-statistics-after-control-gate-failure',
                external_receipts='not-provided', resume=False, retry=False))

    def serialize(self):
        return canonical(self.to_dict())

    @property
    def fingerprint(self):
        return sha256(self.serialize()).hexdigest()

    @classmethod
    def from_bytes(cls, raw):
        if type(raw) is not bytes or len(raw) > 131072:
            raise ValueError('plan size/type')
        value = decode(raw)
        try:
            rt = value['runtime']
            plan = cls(value['science']['code_commit'],
                tuple(Artifact(**x) for x in value['sources']),
                RuntimeBinding(rt['python_version'],rt['platform'],rt['interpreter_sha256'],
                               tuple(tuple(x) for x in rt['dependencies']), rt.get('hashing')), value['schema'])
        except (KeyError, TypeError) as exc:
            raise ValueError('missing production binding') from exc
        if plan.serialize() != raw:
            raise ValueError('mismatched frozen production binding')
        return plan

    def validate_local_inputs(self, repository, audit_root):
        # Does not authenticate Git chronology, runtime approval or dependencies by assertion.
        if observe_runtime() != self.runtime:
            raise ValueError('observed runtime/dependency mismatch')
        if source_inventory(repository) != self.sources:
            raise ValueError('source bytes mismatch')
        import subprocess
        commit=subprocess.run(['git','rev-parse','HEAD'],cwd=repository,check=True,
                              capture_output=True,text=True).stdout.strip()
        if commit!=self.code_commit:
            raise ValueError('source commit mismatch')
        subprocess.run(['git','ls-files','--error-unmatch',*sorted(REQUIRED_SOURCES)],
                       cwd=repository,check=True,capture_output=True)
        # New uncommitted source is allowed only for engineering, never a valid
        # production commit binding. Compare LF content with the committed blobs.
        for item in self.sources:
            committed=subprocess.run(['git','show',self.code_commit+':'+item.path],
                cwd=repository,check=True,capture_output=True).stdout
            observed=(Path(repository)/item.path).read_bytes().replace(b'\r\n',b'\n')
            if observed!=committed.replace(b'\r\n',b'\n'):
                raise ValueError('source is not the bound commit')
        return load_s14(audit_root, repository)


@dataclass(frozen=True)
class EngineeringPlan:
    """One fixed I3-compatible fixture. No geometry/key/seed constructor options."""
    schema: str = 'hashlab-e002-kernel-engineering-plan-v1'

    def __post_init__(self):
        if self.schema != 'hashlab-e002-kernel-engineering-plan-v1':
            raise ValueError('engineering identity')

    def to_dict(self):
        from .exp002_integration import fixture_spec
        return dict(schema=self.schema, scope='engineering-only', fixture=fixture_spec(),
                    evidence_format=FORMAT, confirmatory_complete=False, qa2=False)

    def serialize(self):
        return canonical(self.to_dict())

    @property
    def fingerprint(self):
        return sha256(self.serialize()).hexdigest()
