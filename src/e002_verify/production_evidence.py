"""Independent streaming verifier for ``hashlab-e002-kernel-chunks-v1`` evidence.

No HASHLAB imports. Reconstructs every attempted candidate from the seed record,
frozen/bounded geometry and authenticated retained history; checks framing,
ordering, rejections, raw/effective digests (full rehash of every accepted
candidate), exact accounting and completion claims. The public report contains no
successes, histograms or primary/validation values.

Only the ``full`` mode exists. A sampled "success-plus-sample" audit cannot
establish absence of omitted successes, and because candidate reconstruction
already dominates cost it would save little, so it is deliberately unimplemented.
Passing this verifier is an independent-reconstruction claim. It is not an
external receipt, disclosure authorization or execution authorization.
"""
from hashlib import sha256
from pathlib import Path
import re
import struct
import subprocess

from . import core as arms
from . import controls
from . import production as prod
from .core import encode, empty_accounting, _plain, _file_hash
from .integration import read_json
from .sha256_independent import CandidateHasher, BackendUnavailable, file_integrity_backend


def candidate_hasher(backend):
    """The only route to candidate-evaluation SHA-256 in the verifier."""
    return CandidateHasher(backend)

FORMAT = 'hashlab-e002-kernel-chunks-v1'
HEAD = struct.Struct('>8sIQQ')
ROW = struct.Struct('>QBBBBQQQQI')
END = struct.Struct('>QQ32s')
ABSENT, NO_CLUSTER = 2**64 - 1, 2**32 - 1
ROWS_PER_CHUNK = 4096
SEED_RECORD_SCHEMA = 'hashlab-e002-seed-record-v1'
REPORT_SCHEMA = 'hashlab-e002-production-verification-v1'
SCOPES = {'production': 'hashlab-e002-kernel-production-environment-v1',
          'bounded-fixture': 'hashlab-e002-kernel-bounded-environment-v1'}
ACTIVE = 'proposal-revision-9|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1'
BASELINE = 'proposal-revision-8|hashlab-exp002-a2-encoding-v1|hashlab-exp002-a1-a3-subseed-encoding-v1'
GOVERNANCE = 'hashlab-exp002-solo-governance-v1'
SECONDARY = 'hashlab-exp002-secondary-statistics-proposal-v2'
EXCLUSION = '7c946a93c8e6476ced765b49fd9e5b7f89748bd4825111d94cc305c279a3585c'
MANIFEST = '546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b'
S14_FILES = {
    'producer/accounting.sqlite': (37801984, '14bc1c75950284a1d514568207e7bbccea86706b44b118f95e42fa861e0b9803'),
    'producer/complete.json': (2104, 'c4fe9ba89f1c4390c5300a7a5512aaf20f2bc6fcbbfcbe2292b1af564f70ddc1'),
    'producer/exclusions.bin': (971536, '39d09046325a41dd36d1bc0390e15a1d35a64f649d20f144b9025ccda4395268'),
    'producer/occurrences.bin': (133000000, 'dc27fca46c57a8c02aaa50584af1783e1f4e6dbfedb48231847415c509d9695f'),
    'producer/plan.json': (3464, '19d6396493fc9b8aa9559fd8ddab65f219b920a13b447bb9fb00c04da782054b'),
    'producer/ranks.bin': (485768, '124d6722591d81c9739e63d2702d67dcc3f889fb297a55fd52d7c7c800ee320a'),
    'verifier/reference.sqlite': (37789696, 'e024010e7585a019487fc47c1afcbc22ae1d7c7c497f1fc7e6a9cbf25f31970c'),
    'verifier/verified.json': (1881, '3ed80c4d663614fb5245902f88037573776889dc3c3afc47e32018add11d42eb'),
}
CAPS = dict(plan=131072, history=131072, environment=262144, accounting=2_000_000, index=None, complete=8192)


# ------------------------------------------------- independent frozen plan text

def config():
    return dict(schema='hashlab-exp002-config-v1', proposal_revision=8,
        a2_encoding='hashlab-exp002-a2-encoding-v1', a1_a3_seed_encoding='hashlab-exp002-a1-a3-subseed-encoding-v1',
        protocol_identity=BASELINE, engine='sha256', target=2**248, per_stage=15_000_000, prefixes=3000,
        nonces=10_000, a1_population=prod.A1_SIZE, a3_population=82_068_263, a3_exclusion_sha256=EXCLUSION,
        seed_derivation='hashlab-seed-v1', alpha_difference='0.005', alpha_margin='0.005',
        relative_margin='0.02', a2_t_df=2999, a2_t_critical='2.9376', within_low_count=115839,
        within_high_count=118519, beyond_low_count=113851, beyond_high_count=120546, master='derived-from-beacon')


def slots():
    return ([f'{a}:{s}:{t}' for a in ('A1', 'A2', 'A3', 'N1', 'N2') for s in ('D', 'V')
             for t in ('leading_zero_bits', 'first_byte', 'last_byte')]
            + [f'{a}:{s}:dispersion' for a in ('A2', 'N2') for s in ('D', 'V')]
            + [f'A3:{s}:weight_groups' for s in ('D', 'V')])


def streams():
    return [dict(arm=a, stage=s, trials=200_000 if a == 'P1' else 15_000_000)
            for a in prod.ARMS for s in (('C',) if a.startswith('P') else ('D', 'V'))]


def science(code_commit):
    return dict(schema='hashlab-exp002-seedless-plan-v2', code_commit=code_commit, config=config(),
        streams=streams(), populations={
            'A1': dict(lower=2**20, upper_exclusive=2**32, encoding='8-byte-big-endian',
                       sampling='SRS-without-replacement-then-random-split'),
            'A2': dict(prefix_bytes=76, prefix_count=3000, nonce_start=0, nonce_stop=10000,
                       nonce_encoding='4-byte-little-endian', discovery_clusters=[0, 1499],
                       validation_clusters=[1500, 2999], sampling='uniform-prefix-complete-nonce-block'),
            'A3': dict(bits=64, maximum_weight=6, require_top32_nonzero=True, class_size=82128984,
                       excluded_count=60721, eligible_size=82068263, exclusion_sha256=EXCLUSION,
                       sampling='SRS-without-replacement-then-random-split')},
        controls=dict(N1='feistel64-blake2b-6-rounds-reject-A1-A3-E001',
                      N2='blake2b-80-byte-stream-reject-A2;10000-per-pseudo-cluster',
                      positive_source='N1-permutation-indices-from-2^63-reject-A1-A3-E001',
                      positive_lifts={'P1': '0.25', 'P2+': '0.02', 'P2-': '-0.02'}),
        statistics=dict(difference='two-sided-doubled-tail-Holm-D;flagged-one-sided-Holm-V',
            margin='pooled-D-V;A1-A3-design-based;A2-CP-t-hull', classification='frozen-revision-8-nine-cells',
            secondary=dict(identity=SECONDARY, alpha='0.01', correction='Holm', role='exploratory-only',
                           slots=slots(), a3_groups=[[1, 2, 3, 4], [5], [6]],
                           a3_group_populations=[631413, 7407537, 74029313])),
        e001=dict(run_id='20261011T205056Z-exp001-fc1d75fc', manifest_sha256=MANIFEST,
                  a1_intersection=0, a3_excluded=60721),
        prerequisite_status='not-established-by-foundation')


def seedless_sha256(code_commit):
    return sha256(b'hashlab-exp002-seedless-plan-v2\0' + encode(science(code_commit))).hexdigest()


def production_plan(code_commit, sources, runtime):
    return dict(schema='hashlab-e002-production-kernel-plan-v1', scope='production-disabled',
        identities=dict(active_protocol=ACTIVE, scientific_baseline=BASELINE, governance=GOVERNANCE,
                        secondary=SECONDARY),
        science=science(code_commit), config_sha256=sha256(encode(config())).hexdigest(),
        seed=dict(master='authenticated-S4-seed-record-required;not-supplied',
                  master_message='hashlab-exp002-master-v1|C_pre|R_star|randomness_hex',
                  master_conversion='SHA256-first-8-bytes-uint64-big-endian', domain='experiment-002',
                  arm_labels={'A1': {'selection': ['experiment-002', 'A1-lowint-w8', 'selection-v1'],
                                     'stage-allocation': ['experiment-002', 'A1-lowint-w8', 'stage-allocation-v1']},
                              'A3': {'selection': ['experiment-002', 'A3-lowhw-w8', 'selection-v1'],
                                     'stage-allocation': ['experiment-002', 'A3-lowhw-w8', 'stage-allocation-v1']}},
                  a2=['experiment-002', 'A2-prefix-nonce-w80', 'prefix-key-v1'],
                  n1=['experiment-002', 'N1-feistel64-w8', 'permutation-key-v1'],
                  n2=['experiment-002', 'N2-random-bytes-w80', 'stream-key-v1']),
        controls=dict(n1_stop_exclusive=30999999, positive_start=str(2**63),
                      thresholds_u32={'P1': 2**32//1020, 'P2+': 2**32//12750, 'P2-': 2**32//50},
                      n2_uniqueness='approved-probabilistic-assumption;no-deduplication'),
        sources=sources, runtime=runtime,
        history=dict(schema='hashlab-e002-kernel-history-binding-v1',
                     files={p: dict(size=n, sha256=h) for p, (n, h) in S14_FILES.items()},
                     occurrences=7_000_000, distinct_a3=60721, distinct_history=6048573,
                     exclusion_sha256=EXCLUSION, original_manifest=MANIFEST),
        evidence=dict(format=FORMAT, rows_per_chunk=4096,
                      verification='full-independent-regeneration-and-rehash-supported',
                      audit_decision='unresolved;approved-minimal-success-plus-sample-option-retained'),
        restrictions=dict(execution_enabled=False, arbitrary_master=False, quota_override=False,
                          primary_progress=False, incomplete_primary_disclosure=False, validation='restricted',
                          final_disclosure='separate-authorization-required',
                          f4='full-failed-statistics-after-control-gate-failure',
                          external_receipts='not-provided', resume=False, retry=False))


def bounded_plan():
    g = prod.BOUNDED
    return dict(schema='hashlab-e002-bounded-kernel-plan-v1', scope='bounded-fixture',
        seed=dict(kind='public-engineering', master='0', domain=g.domain, a1_a3_labels='experiment-002'),
        geometry=dict(a1_size=g.a1_size, a1_stage=g.a1_stage, a2_clusters=list(g.a2_clusters),
                      a2_nonces=g.a2_nonces, a3_size=g.a3_size, a3_stage=g.a3_stage,
                      control_stage=g.control_stage, p1=g.p1, p2=g.p2),
        evidence_format=FORMAT, confirmatory_complete=False, qa2=False)


# ----------------------------------------------------------- bindings/helpers

def _require(condition, message):
    if not condition:
        raise ValueError('reference: ' + message)


def _hex(value, n):
    _require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % n, value), 'hex identity')
    return value


def _json(path, cap):
    _plain(path)
    _require(path.stat().st_size <= cap, 'metadata size cap ' + path.name)
    return read_json(path)


# Revision 8 section 3.8.1 pinned beacon tuple (decision D5, still proposed; never fetched here).
BEACON = dict(chain_hash='52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971',
              scheme='bls-unchained-g1-rfc9380', beacon_id='quicknet', period='3', genesis_unix='1692803367',
              public_key_hex='83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a')
WITNESS_LEAD_SECONDS = 24 * 3600
SEED_COMMITMENT_SCHEMA = 'hashlab-e002-seed-commitment-v1'
PREREGISTRATION_SCHEMA = 'hashlab-e002-preregistration-bundle-v1'


def _decimal(value, low=0):
    _require(type(value) is str and re.fullmatch('0|[1-9][0-9]{0,19}', value) and int(value) >= low, 'canonical decimal')
    return int(value)


def seeded_config_sha256(master):
    """Configuration digest with the derived master inserted (S5); the seedless value is `config_sha256`."""
    return sha256(encode(dict(config(), master=str(master)))).hexdigest()


def full_plan_sha256(seedless, seed_record_sha, resolved_config_sha):
    """FullPlanBinding fingerprint, independently restated."""
    return sha256(encode(dict(schema='hashlab-exp002-full-plan-binding-v1', seedless_sha256=seedless,
        seed_record_sha256=seed_record_sha, resolved_config_sha256=resolved_config_sha,
        protocol_identity=BASELINE, secondary_identity=SECONDARY))).hexdigest()


def parse_seed_record(raw, geometry):
    """Strict seed record (S1-S5, 3.8.1). Returns (master, record_sha256, facts).

    Checked: C_pre git id, pinned chain tuple, R* canonical decimal, scheduled time
    genesis+(R*-1)*period, witness lead >= 24 h before that time, 48-byte signature encoding,
    randomness == SHA-256(signature), exact S4 derivation and master. NOT checked here (an
    operational dependency): the BLS signature itself, and the witness timestamp receipt.
    """
    _require(type(raw) is bytes and len(raw) <= 4096, 'seed record size')
    record = read_json_bytes(raw)
    _require(type(record) is dict and record.get('schema') == SEED_RECORD_SCHEMA, 'seed record schema')
    kind = record.get('kind')
    if kind == 'beacon':
        _require(set(record) == {'schema', 'kind', 'c_pre', 'beacon', 'witness', 'master', 'domain'},
                 'beacon seed record fields')
        _hex(record['c_pre'], 40)
        b, w = record['beacon'], record['witness']
        _require(type(b) is dict and set(b) == set(BEACON) | {'round', 'scheduled_unix', 'signature_hex', 'randomness_hex'},
                 'beacon fields')
        _require(all(b[k] == v for k, v in BEACON.items()), 'beacon tuple differs from the pinned chain')
        number = _decimal(b['round'], 1)
        _require(number < 2**64, 'round range')
        scheduled = int(BEACON['genesis_unix']) + (number - 1) * int(BEACON['period'])
        _require(_decimal(b['scheduled_unix']) == scheduled, 'scheduled time is not genesis+(R*-1)*period')
        _hex(b['signature_hex'], 96)
        _hex(b['randomness_hex'], 64)
        _require(sha256(bytes.fromhex(b['signature_hex'])).hexdigest() == b['randomness_hex'],
                 'randomness is not SHA-256 of the signature')
        _require(type(w) is dict and set(w) == {'receipt_sha256', 'witnessed_unix', 'bundle_sha256'}, 'witness fields')
        _hex(w['receipt_sha256'], 64)
        _hex(w['bundle_sha256'], 64)
        _require(_decimal(w['witnessed_unix']) + WITNESS_LEAD_SECONDS <= scheduled,
                 'C_pre witness is not at least 24 h before R*')
        master = prod.master_from_beacon(record['c_pre'], number, b['randomness_hex'])
        _require(record['master'] == str(master), 'seed record master does not match beacon derivation')
        facts = dict(kind='beacon', c_pre=record['c_pre'], round=b['round'], scheduled_unix=b['scheduled_unix'],
                     witness_receipt_sha256=w['receipt_sha256'], bundle_sha256=w['bundle_sha256'], master=str(master),
                     beacon_signature='not-verified;requires-pinned-bls-client',
                     witness_receipt='not-verified;requires-authenticated-timestamp-service')
    elif kind == 'public-engineering':
        _require(set(record) == {'schema', 'kind', 'master', 'domain'}, 'engineering seed record fields')
        _require(geometry.name == 'bounded-fixture' and record['master'] == '0',
                 'engineering seed record is valid only for the bounded public fixture')
        master, facts = 0, dict(kind='public-engineering', master='0')
    else:
        raise ValueError('reference: seed record kind')
    _require(record['domain'] == geometry.domain, 'seed record domain does not match geometry')
    return master, sha256(raw).hexdigest(), facts


def parse_seed_commitment(raw, *, seed_record_sha, facts, master, code_commit):
    """C_seed content (S5): everything derived from, but not part of, the seed record bytes."""
    _require(type(raw) is bytes and len(raw) <= 4096, 'seed commitment size')
    doc = read_json_bytes(raw)
    seedless = seedless_sha256(code_commit)
    resolved = seeded_config_sha256(master)
    expected = dict(schema=SEED_COMMITMENT_SCHEMA, c_pre=facts['c_pre'], seed_record_sha256=seed_record_sha,
                    preregistration_bundle_sha256=facts['bundle_sha256'],
                    master=str(master), seedless_plan_sha256=seedless,
                    config_sha256=sha256(encode(config())).hexdigest(), seeded_config_sha256=resolved,
                    full_plan_sha256=full_plan_sha256(seedless, seed_record_sha, resolved))
    _require(doc == expected, 'seed commitment differs from the independently derived bindings')
    return expected


def parse_preregistration_bundle(raw, *, facts, commitment):
    """The retained C_pre bundle: its digest is the second timestamp subject (R9 M19).

    It must be canonical, hash to the witnessed digest, name the predetermined round R* and the
    pinned chain, and carry exactly the frozen seedless identities that the later commitment
    repeats. The seeded configuration is never part of it, so it cannot change after reveal.
    """
    _require(type(raw) is bytes and len(raw) <= 8192, 'preregistration bundle size')
    _require(sha256(raw).hexdigest() == facts['bundle_sha256'], 'bundle digest differs from the witnessed digest')
    doc = read_json_bytes(raw)
    expected = dict(schema=PREREGISTRATION_SCHEMA, reveal_round=facts['round'], chain_hash=BEACON['chain_hash'],
                    seedless_plan_sha256=commitment['seedless_plan_sha256'], config_sha256=commitment['config_sha256'])
    _require(doc == expected, 'bundle differs from the predetermined round and frozen seedless identities')
    _require(commitment['seeded_config_sha256'] != commitment['config_sha256'], 'seeded and seedless configurations must differ')
    return doc


def verify_c_seed(repository, c_seed, files):
    """C_seed must be a git commit whose tree contains exactly the supplied document bytes."""
    _hex(c_seed, 40)
    for path, raw in files.items():
        shown = subprocess.run(['git', 'show', c_seed + ':' + path], cwd=repository, check=True,
                               capture_output=True).stdout
        _require(shown.replace(b'\r\n', b'\n') == raw.replace(b'\r\n', b'\n'), 'C_seed content differs: ' + path)


def read_json_bytes(raw):
    import json

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate field')
            result[key] = value
        return result

    def invalid(*_):
        raise ValueError('reference: nonfinite JSON')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError('reference: invalid JSON') from None
    _require(encode(value) == raw, 'noncanonical JSON')
    return value


def source_paths(repository):
    base = Path(repository) / 'src/hashlab'
    return sorted(['src/hashlab/' + p.relative_to(base).as_posix() for p in base.rglob('*.py')]
                  + ['src/hashlab/experiments/e001_contract.json'])


def observe_sources(repository):
    return [dict(path=p, size=h['bytes'], sha256=h['sha256'])
            for p in source_paths(repository) for h in [_file_hash(Path(repository) / p)]]


def verify_git_commit(repository, code_commit, sources):
    """Every bound source must equal its committed blob (LF-normalized); HEAD must be the commit."""
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repository, check=True,
                          capture_output=True, text=True).stdout.strip()
    _require(head == code_commit, 'checkout HEAD is not the bound code commit')
    for item in sources:
        committed = subprocess.run(['git', 'show', code_commit + ':' + item['path']], cwd=repository,
                                   check=True, capture_output=True).stdout
        observed = (Path(repository) / item['path']).read_bytes()
        _require(observed.replace(b'\r\n', b'\n') == committed.replace(b'\r\n', b'\n'),
                 'source differs from the bound commit: ' + item['path'])


def _runtime_shape(rt):
    _require(type(rt) is dict and set(rt) == {'python_version', 'platform', 'interpreter_sha256', 'dependencies'}
             and type(rt['python_version']) is str and rt['python_version'].startswith('CPython ')
             and type(rt['platform']) is str and rt['platform'] and _hex(rt['interpreter_sha256'], 64)
             and type(rt['dependencies']) is list and rt['dependencies'], 'runtime binding')
    names = []
    for row in rt['dependencies']:
        _require(type(row) is list and len(row) == 3 and all(type(x) is str and x for x in row)
                 and _hex(row[2], 64), 'dependency binding')
        names.append(row[0])
    _require(names == sorted(set(names)) and 'PyYAML' in names, 'dependency names')


def _stage_index(s):
    return prod.STAGES.index(s)


def _new_accounting():
    return empty_accounting()


def check_binding(geometry, plan_raw, environment, repository, expected_runtime=None):
    """Plan/environment/source/runtime contract. Returns (code_commit or None, sources)."""
    production = geometry.name == 'production'
    _require(type(environment) is dict and set(environment) == {'schema', 'scope', 'runtime', 'sources',
                                  'source_commit_correspondence', 'runtime_approval'}
             and environment['schema'] == SCOPES[geometry.name] and environment['scope'] == geometry.name
             and environment['runtime_approval'] == 'not-claimed', 'environment contract')
    _runtime_shape(environment['runtime'])
    if expected_runtime is not None:
        _require(environment['runtime'] == expected_runtime, 'observed runtime differs from evidence runtime')
    sources = environment['sources']
    _require(sources == observe_sources(repository), 'bound source inventory differs from the checkout')
    if production:
        plan = read_json_bytes(plan_raw)
        _require(type(plan) is dict and type(plan.get('science')) is dict
                 and type(plan['science'].get('code_commit')) is str, 'production plan shape')
        commit = plan['science']['code_commit']
        _hex(commit, 40)
        _require(plan_raw == encode(production_plan(commit, sources, environment['runtime'])),
                 'production plan differs from the independently restated frozen plan')
        _require(environment['source_commit_correspondence'] == 'committed;git-verified', 'source correspondence')
        verify_git_commit(repository, commit, sources)
        return commit, sources
    _require(plan_raw == encode(bounded_plan()), 'bounded plan')
    _require(environment['source_commit_correspondence'] == 'unqualified;engineering-working-copy',
             'bounded source correspondence')
    return None, sources


def tally(row, effective, candidate, arm, cluster):
    """Success classification (strict effective < 2**248) and E3 counters for one accepted candidate."""
    value = int.from_bytes(effective, 'big')
    success = value < prod.TARGET
    row['trials'] += 1
    row['successes'] += success
    row['first_byte'][effective[0]] += 1
    row['last_byte'][effective[-1]] += 1
    row['leading_zero_bits'][256 - value.bit_length()] += 1
    if cluster is not None:
        j = cluster % 1500
        row['cluster_trials'][j] += 1
        row['cluster_successes'][j] += success
    if arm == 'A3':
        w = int.from_bytes(candidate, 'big').bit_count() - 1
        row['weight_trials'][w] += 1
        row['weight_successes'][w] += success
    return success


def verify_evidence(root, *, completion_sha256, geometry_name, seed_record, audit_root, repository_root,
                    mode='full', expected_runtime=None, cross_check=None, allowed_extra=(),
                    seed_commitment=None, c_seed=None, c_seed_files=None, preregistration_bundle=None,
                    c_pre_files=None, candidate_backend='hacl'):
    """Complete independent verification; returns a public report with no outcomes."""
    _require(mode == 'full', 'only full regeneration/rehash verification is defined; sampled audits are unsupported')
    geometry = prod.GEOMETRIES.get(geometry_name)
    _require(geometry is not None, 'unknown geometry')
    production = geometry.name == 'production'
    hasher = candidate_hasher(candidate_backend)      # fails closed before any evidence is read
    evaluate = hasher.evaluator()
    master, seed_sha, seed_facts = parse_seed_record(seed_record, geometry)
    root, repository = Path(root), Path(repository_root)
    _plain(root, directory=True)
    _hex(completion_sha256, 64)
    if production:
        _require(seed_facts['kind'] == 'beacon' and seed_commitment is not None and c_seed is not None,
                 'production verification requires the beacon seed record, C_seed content and C_seed')
    _require((root/'INCOMPLETE').exists() is False and (root/'failure.json').exists() is False,
             'incomplete or failed attempt evidence cannot be verified as complete')
    _require(_file_hash(root/'complete.json')['sha256'] == completion_sha256, 'completion pin')
    report = _json(root/'complete.json', CAPS['complete'])
    quotas = geometry.quotas()
    accepted_total = sum(quotas.values())
    max_attempts = accepted_total + max(1000, accepted_total // 100)
    _require(set(report) == {'schema', 'scope', 'format', 'plan_sha256', 'confirmatory_complete', 'qa2',
                             'evaluations', 'compression_blocks', 'successes', 'rejections', 'chunks',
                             'attempts', 'index', 'plan', 'history', 'environment', 'accounting'}
             and report['schema'] == 'hashlab-e002-kernel-completion-v1' and report['scope'] == geometry.name
             and report['format'] == FORMAT and report['confirmatory_complete'] is False and report['qa2'] is False
             and type(report['attempts']) is int and type(report['chunks']) is int
             and accepted_total <= report['attempts'] <= max_attempts
             and report['chunks'] == -(-report['attempts'] // ROWS_PER_CHUNK), 'completion contract')
    names = {'plan.json', 'history.json', 'environment.json', 'accounting.json', 'chunks.jsonl', 'complete.json'}
    names |= {f'chunk-{i:08d}.bin' for i in range(report['chunks'])}
    present = {p.name for p in root.iterdir()}
    _require(names <= present and present - names <= set(allowed_extra), 'evidence inventory')
    for p in root.iterdir():
        _plain(p)
    pins = {}
    for filename, key in (('plan.json', 'plan'), ('history.json', 'history'), ('environment.json', 'environment'),
                          ('accounting.json', 'accounting'), ('chunks.jsonl', 'index')):
        info = _file_hash(root/filename)
        _require(report[key] == dict(size=info['bytes'], sha256=info['sha256']), 'payload pin ' + filename)
        pins[key] = info['sha256']
    _require(report['plan_sha256'] == pins['plan'], 'plan identity in completion')
    # --- plan, source, runtime
    plan_raw = (root/'plan.json').read_bytes()
    environment = _json(root/'environment.json', CAPS['environment'])
    commit, sources = check_binding(geometry, plan_raw, environment, repository, expected_runtime)
    commitment = None
    if production:
        commitment = parse_seed_commitment(seed_commitment, seed_record_sha=seed_sha, facts=seed_facts,
                                           master=master, code_commit=commit)
        _require(preregistration_bundle is not None, 'production verification requires the retained preregistration bundle')
        parse_preregistration_bundle(preregistration_bundle, facts=seed_facts, commitment=commitment)
        if c_pre_files is not None:
            verify_c_seed(repository, seed_facts['c_pre'], c_pre_files)
        _hex(c_seed, 40)
        if c_seed_files is not None:
            verify_c_seed(repository, c_seed, c_seed_files)
    # --- authenticated retained history
    excluded, identity = arms.load_history(audit_root, repository)
    values, identity, occurrence_count = controls.load_history(audit_root, repository)
    _require(not any(2**20 <= v < 2**32 for v in values), 'historical occurrence intersects the A1 population')
    seeds = prod.seeds(master, geometry.domain)
    summary = dict(identity, historical_occurrences=occurrence_count, distinct_inverse_skip_indices=len(values),
                   complete_occurrence_evidence=True, permutation_key_hex=seeds['n1_key'].hex())
    _require((root/'history.json').read_bytes() == encode(summary), 'history binding')
    # --- every attempt
    expected = prod.attempts(geometry, master, values, sorted(excluded),
                             cross_check=cross_check if cross_check is not None else (1 if not production else 4099))
    accounting = _new_accounting()
    rows = {(r['arm'], r['stage']): r for r in accounting['streams']}
    rejected = {a: 0 for a in prod.ARMS}
    evaluations = blocks = successes = sequence = chunk_count = 0
    index = (root/'chunks.jsonl').read_bytes()
    _require(len(index) <= 1024 * (report['chunks'] + 1), 'index size')
    lines = index.split(b'\n')
    _require(lines.pop() == b'' and len(lines) == report['chunks'], 'chunk index framing')
    for number, line in enumerate(lines):
        entry = read_json_bytes(line)
        rows_in_chunk = ROWS_PER_CHUNK if number < report['chunks'] - 1 else report['attempts'] - ROWS_PER_CHUNK * number
        _require(set(entry) == {'sequence', 'name', 'first', 'rows', 'size', 'sha256'}
                 and all(type(entry[k]) is int for k in ('sequence', 'first', 'rows', 'size'))
                 and entry['sequence'] == number and entry['first'] == sequence
                 and entry['name'] == f'chunk-{number:08d}.bin' and entry['rows'] == rows_in_chunk, 'index continuity')
        data = (root/entry['name']).read_bytes()
        _require(len(data) == entry['size'] and sha256(data).hexdigest() == entry['sha256'], 'chunk identity')
        _require(data[:HEAD.size] == HEAD.pack(b'E002KRN1', 1, number, sequence), 'chunk header')
        position = HEAD.size
        for _ in range(entry['rows']):
            attempt = next(expected, None)
            _require(attempt is not None, 'evidence contains an extra attempt')
            arm, stage, mask, candidate, source, accepted, rank, offset, cluster = attempt
            width = len(candidate)
            head = ROW.pack(sequence, prod.ARMS.index(arm), _stage_index(stage), mask, width,
                            ABSENT if source is None else source, ABSENT if accepted is None else accepted,
                            ABSENT if rank is None else rank, ABSENT if offset is None else offset,
                            NO_CLUSTER if cluster is None else cluster)
            stop = position + ROW.size + width
            _require(data[position:stop] == head + candidate, 'candidate/source/rejection/stage mismatch at attempt %d' % sequence)
            sequence += 1
            if mask:
                rejected[arm] += 1
                position = stop
                continue
            raw = evaluate(candidate)       # independent candidate-evaluation backend, never hashlib
            mode_name = arm if arm[0] in 'NP' else 'N1'
            effective = raw if mode_name in ('N1', 'N2') else prod.transform(mode_name, raw)
            _require(data[stop:stop + 64] == raw + effective, 'raw/effective digest mismatch at attempt %d' % (sequence - 1))
            position = stop + 64
            row = rows[arm, stage]
            _require(accepted == row['trials'], 'accepted index continuity')
            success = tally(row, effective, candidate, arm, cluster)
            evaluations += 1
            blocks += (width + 72) // 64
            successes += success
        trailer = data[position:]
        _require(trailer == END.pack(entry['rows'], position - HEAD.size, sha256(data[HEAD.size:position]).digest()),
                 'chunk trailer/extra bytes')
        chunk_count += 1
    _require(next(expected, None) is None, 'evidence omits expected attempts')
    _require(sequence == report['attempts'] and chunk_count == report['chunks'], 'attempt/chunk totals')
    _require({k: r['trials'] for k, r in rows.items()} == quotas, 'incomplete exact stream quotas')
    accounting['complete'] = all(r['trials'] == n for r, n in ((rows[k], quotas[k]) for k in rows)) \
        and geometry.name == 'production'
    _require((root/'accounting.json').read_bytes() == encode(accounting), 'measured accounting disagreement')
    exact = dict(schema='hashlab-e002-kernel-completion-v1', scope=geometry.name, format=FORMAT,
                 plan_sha256=pins['plan'], confirmatory_complete=False, qa2=False, evaluations=evaluations,
                 compression_blocks=blocks, successes=successes, rejections=rejected, chunks=chunk_count,
                 attempts=sequence, **{k: report[k] for k in ('index', 'plan', 'history', 'environment', 'accounting')})
    _require(encode(report) == encode(exact), 'false completion claims')
    _require((evaluations, blocks) == (geometry.evaluations(), geometry.blocks()), 'evaluation/block totals')
    return dict(
        schema=REPORT_SCHEMA, scope=geometry.name, mode='full',
        verification='independent-full-regeneration-and-rehash',
        bindings=dict(completion_sha256=completion_sha256, plan_sha256=pins['plan'],
                      accounting_sha256=pins['accounting'], environment_sha256=pins['environment'],
                      history_sha256=pins['history'], index_sha256=pins['index'], seed_record_sha256=seed_sha,
                      source_inventory_sha256=sha256(encode(sources)).hexdigest(),
                      runtime_sha256=sha256(encode(environment['runtime'])).hexdigest(),
                      code_commit=commit, seedless_sha256=seedless_sha256(commit) if production else None,
                      config_sha256=sha256(encode(config())).hexdigest() if production else None,
                      seeded_config_sha256=commitment['seeded_config_sha256'] if production else None,
                      full_plan_sha256=commitment['full_plan_sha256'] if production else None,
                      seed_commitment_sha256=sha256(seed_commitment).hexdigest() if production else None,
                      c_pre=seed_facts.get('c_pre'), bundle_sha256=seed_facts.get('bundle_sha256'),
                      c_pre_content='verified' if production and c_pre_files is not None
                      else 'not-verified' if production else None, c_seed=c_seed if production else None,
                      c_seed_content='verified' if production and c_seed_files is not None
                      else 'not-verified' if production else None),
        seed=seed_facts,
        coverage=dict(attempts_reconstructed=sequence, candidates_rehashed=evaluations,
                      compression_blocks=blocks, chunks=chunk_count, rejections=rejected,
                      history_occurrences=occurrence_count, a3_exclusion_ranks=len(excluded)),
        independence=dict(candidate_sha256=hasher.identity(), file_integrity_sha256=file_integrity_backend(),
                          shared_dependencies=['CPython random MT19937', 'hashlib BLAKE2b (Feistel, N2, A2 prefixes)',
                                               'hashlib SHA-256 for file pins and seed derivation (not candidate evaluation)',
                                               'accepted independent S1.4/E001 loaders'],
                          producer_imports=False, runtime_independently_observed=expected_runtime is not None,
                          beacon_authenticity='not-established', ambiguity_policy='fail-closed'),
        claims=dict(independent_regeneration_and_rehash=True, external_receipt=False,
                    disclosure_authorized=False, execution_authorized=False, g1=False, qa2=False,
                    sampled_audit_absence_claim=False),
    )
