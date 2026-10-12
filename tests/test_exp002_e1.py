"""Small non-confirmatory engineering fixtures; no candidate SHA-256 evaluation."""
import itertools
import tracemalloc
from collections import Counter
from hashlib import sha256

import pytest

from hashlab.experiments.exp002 import (
    Config, Exclusions, HammingPopulation, RegistryState, RegistryRecord, SeedCommitment,
    A1_SIZE, A3_CLASS_SIZE, a1_value, in_a1, in_a3, a2_key, a2_prefix,
    a2_candidate, a2_stage, a2_stream, validate_prefixes, le32,
    sample_ranks, engineering_arm_stream, audit_e001,
    arm_seed_labels, arm_seed_material, arm_subseed, ARM_SEED_ENCODING, PROTOCOL_IDENTITY,
)


@pytest.mark.parametrize('index,nonce,expected', [
    (0, 1, '063d1eb37b1f102e2a56bdb3a953bfe07ed19b3ccd3df65d66128ec6da2f41d2324136bf6da3495cbb3a95b080fcbc1690084cfa69a1511f80ffd68c6e138413bf91cf4d4b7c7c3821600caa'),
    (1499, 256, 'ca0ca6c86f2c0ba42b1bc47371b637236bebe9f939252692a8262671320a87273bfc147042516522ba06551cf59070032e33aff3ad423fab24cad2ec7efd2bc41eb9de669aeebd5967ab0145'),
    (1500, 9999, '25c9fbc1593fea7dfc4d6fca5ce4cb842665f9e6a6966a8566f2c74bc344b65df1f38fff5428703b83809cfddbecbe3c5cebcdb46f3d9c6cd796defe38d72e620d7355370310e8fe865fd9e8'),
])
def test_a2_kat(index, nonce, expected):
    key = a2_key(0, 'experiment-002-kat')
    assert key.hex() == '0f57b91a27beb8f9'
    prefix = a2_prefix(key, index)
    assert prefix.hex() == expected
    assert a2_candidate(prefix, nonce) == bytes.fromhex(expected) + nonce.to_bytes(4, 'little')


@pytest.mark.parametrize('bits,split,weight', [(8,4,3), (12,6,3), (10,3,4)])
def test_hamming_exhaustive(bits, split, weight):
    population = HammingPopulation(bits, split, weight)
    expected = sorted((v for v in range(2**bits) if v >> split and v.bit_count() <= weight),
                      key=lambda v: (v.bit_count(), v))
    assert population.size == len(expected)
    assert [population.unrank(r) for r in range(population.size)] == expected
    assert [population.rank(v) for v in expected] == list(range(population.size))


def test_populations():
    p = HammingPopulation()
    assert p.size == A3_CLASS_SIZE
    assert a1_value(0) == (2**20).to_bytes(8, 'big')
    assert a1_value(A1_SIZE-1) == (2**32-1).to_bytes(8, 'big')
    for rank in [0, 31, 32, 1551, p.size-1]:
        value = p.unrank(rank)
        assert p.rank(value) == rank
        assert in_a3(value.to_bytes(8, 'big'))
        assert not in_a1(value.to_bytes(8, 'big'))
    assert not in_a1((2**20-1).to_bytes(8, 'big'))
    assert not in_a1((2**32).to_bytes(8, 'big'))
    assert not in_a3((1).to_bytes(8, 'big'))
    assert not in_a3(((1<<32) | 63).to_bytes(8, 'big'))


@pytest.mark.parametrize('bad', [-1, True, 1.0, '1', 2**32])
def test_integer_rejection(bad):
    with pytest.raises(ValueError):
        le32(bad)


@pytest.mark.parametrize('field', list(Config.__dataclass_fields__))
def test_frozen_config(field):
    data = Config().to_dict()
    data[field] = None
    with pytest.raises(ValueError):
        Config.from_mapping(data)


def test_config_shape():
    data = Config().to_dict()
    assert Config.from_mapping(data) == Config()
    for bad in [{}, dict(data, extra=1), [], dict(data, proposal_revision=True)]:
        with pytest.raises(ValueError):
            Config.from_mapping(bad)


def draw(**kwargs):
    return list(sample_ranks(100, 12, 13, selection_seed=7, stage_seed=8, **kwargs))


def test_replay_partition_exclusion():
    rows = draw(excluded=(0, 5, 99))
    assert rows == draw(excluded=(0, 5, 99))
    assert Counter(stage for stage, _ in rows) == {'D':12, 'V':13}
    assert len({rank for _, rank in rows}) == 25
    assert not {rank for _, rank in rows} & {0, 5, 99}
    assert [r for _, r in rows] == sorted(r for _, r in rows)
    assert list(sample_ranks(20,3,3,selection_seed=7,stage_seed=8,excluded=(0,5))) == [
        ('D',2), ('V',6), ('V',7), ('D',9), ('D',11), ('V',13)]


@pytest.mark.parametrize('excluded', [(1,1), (2,1), (-1,), (100,), (True,), []])
def test_exclusion_rejection(excluded):
    with pytest.raises(ValueError):
        draw(excluded=excluded)


def test_exhaustion_and_empty():
    rows = list(sample_ranks(10, 4, 4, selection_seed=1, stage_seed=2, excluded=(1,3)))
    assert {r for _, r in rows} == set(range(10)) - {1,3}
    assert not list(sample_ranks(10, 0, 0, selection_seed=1, stage_seed=2))
    with pytest.raises(ValueError):
        list(sample_ranks(10, 6, 5, selection_seed=1, stage_seed=2))


def test_prefix_uniqueness_and_overlap():
    # Eight engineering prefixes only; never build the confirmatory population.
    key = a2_key(0, 'experiment-002-qa2')
    prefixes = tuple(a2_prefix(key, j) for j in range(8))
    validate_prefixes(prefixes, 8)
    assert len(set(prefixes)) == 8
    candidates = {a2_candidate(p, n) for p in prefixes for n in range(4)}
    assert len(candidates) == 32
    assert all(len(c) == 80 and not in_a1(c) and not in_a3(c) for c in candidates)
    with pytest.raises(ValueError):
        validate_prefixes((prefixes[0], prefixes[0]), 2)
    with pytest.raises(ValueError):
        next(a2_stream(prefixes))
    for bad in [-1, 10_000, True, 2**32]:
        with pytest.raises(ValueError):
            a2_candidate(prefixes[0], bad)
    assert le32(2**32-1) == b'\xff'*4


@pytest.mark.parametrize('index,stage', [(0,'D'), (1499,'D'), (1500,'V'), (2999,'V')])
def test_stages(index, stage):
    assert a2_stage(index) == stage


def test_stream_adapter():
    population = HammingPopulation(12,6,3)
    excluded = Exclusions((0,3,5), population)
    rows = list(engineering_arm_stream('A3', population.size, 10, 11,
        selection_seed=1, stage_seed=2, exclusions=excluded))
    assert len({c for _, c in rows}) == 21
    assert not {int.from_bytes(c,'big') for _, c in rows} & {population.unrank(r) for r in excluded.ranks}
    with pytest.raises(ValueError):
        excluded.verify_protocol()
    with pytest.raises(ValueError):
        list(engineering_arm_stream('A3', 10, 1, 1, selection_seed=1, stage_seed=2))


def test_e001_audit_small_fixture():
    population = HammingPopulation()
    exclusions = Exclusions((0, 1), population)
    rows = [population.unrank(r).to_bytes(8,'big') for r in exclusions.ranks]
    audit_e001(iter(rows), exclusions, 2)
    for bad in [rows[:1], rows + [a1_value(0)], [b'x'*80]]:
        with pytest.raises(ValueError):
            audit_e001(iter(bad), exclusions, 2)


def test_memory_does_not_retain_samples():
    def peak(n):
        tracemalloc.start()
        for _ in sample_ranks(20_000, n//2, n//2, selection_seed=1, stage_seed=2):
            pass
        _, result = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return result
    small, large = peak(100), peak(18_000)
    assert large < small + 32_768
    assert large < 100_000


def test_small_uniformity_fixture():
    # Fixed deterministic seeds; broad engineering check, not scientific inference.
    frequencies = Counter()
    for seed in range(2000):
        frequencies.update((stage, rank) for stage, rank in sample_ranks(
            10, 2, 2, selection_seed=seed, stage_seed=seed+2000))
    assert all(300 < frequencies[stage,rank] < 500 for stage in ('D','V') for rank in range(10))


def test_commitment_registry_interfaces():
    SeedCommitment('a'*40, 'b'*64, 'c'*64)
    with pytest.raises(ValueError):
        SeedCommitment('bad', 'b'*64, 'c'*64)
    state = RegistryState().append('S').append('Q').append('Q')
    assert state.entries == ('S1','Q1','Q2')
    with pytest.raises(ValueError):
        state.append('A')
    frozen = RegistryState(state.entries, precommitted=True)
    for kind in ('S','Q'):
        with pytest.raises(ValueError):
            frozen.append(kind)
    assert frozen.append('Q', approved_amendment=True).entries[-1] == 'Q3'
    seeded = RegistryState(state.entries, True, True)
    assert seeded.append('A').entries[-1] == 'A1'
    for bad in [lambda: RegistryState(('A1',)), lambda: RegistryState(('Q2',)),
                lambda: RegistryState(final=True).append('S')]:
        with pytest.raises(ValueError):
            bad()


def test_registry_record_binding():
    fields = dict(entry_id='Q1', utc='2026-10-12T00:00:00Z', code_commit='a'*40,
                  configuration_sha256='b'*64, plan_sha256='c'*64, command='engineering-fixture')
    RegistryRecord(**fields)
    RegistryRecord(**fields, phase='result', run_id='fixture', status='incomplete', failure_class='F1')
    RegistryRecord(**fields, phase='result', run_id='fixture', status='complete', failure_class='valid', manifest_sha256='d'*64)
    for changes in [dict(utc='bad'), dict(utc='2026-10-12Z'), dict(entry_id='A0'), dict(command=''),
                    dict(phase='result'), dict(manifest_sha256='d'*64)]:
        with pytest.raises(ValueError):
            RegistryRecord(**(fields | changes))


def test_additional_foundation_rejections():
    with pytest.raises(ValueError):
        Exclusions((), None)
    for domain in ('experiment-001', 'unknown', ''):
        with pytest.raises(ValueError):
            a2_key(0,domain)
    for master in (True,-1,2**64,0.0):
        with pytest.raises(ValueError):
            a2_key(master,'experiment-002-kat')
    for index in (-1,3000,True):
        with pytest.raises(ValueError):
            a2_stage(index)
    with pytest.raises(ValueError):
        a2_prefix(b'12345678',3000)
    assert len(a2_prefix(b'12345678',2999)) == 76
    with pytest.raises(ValueError):
        validate_prefixes((b'x'*75,),1)
    p = HammingPopulation()
    for rank in (-1,p.size,True):
        with pytest.raises(ValueError):
            p.unrank(rank)
    for value in (0,1,2**64,True):
        with pytest.raises(ValueError):
            p.rank(value)


@pytest.mark.parametrize('arm,purpose,length,message,digest,expected', [
    ('A1','selection',58,
     b'hashlab-seed-v1|0|experiment-002|A1-lowint-w8|selection-v1',
     'ff02f20338ea39cb98778affa607d272f9c979516c76361421901fbdab97849b',18375515525278742987),
    ('A1','stage-allocation',65,
     b'hashlab-seed-v1|0|experiment-002|A1-lowint-w8|stage-allocation-v1',
     'b116da691b775b41c60880fd0f895223b0959373ef21966b585df9d0574d45f3',12760626739168107329),
    ('A3','selection',57,
     b'hashlab-seed-v1|0|experiment-002|A3-lowhw-w8|selection-v1',
     'c12b68881535433f5bbeced6a56b7e5b2a368b522b391eb597fc0c490028ea1b',13919334006999302975),
    ('A3','stage-allocation',64,
     b'hashlab-seed-v1|0|experiment-002|A3-lowhw-w8|stage-allocation-v1',
     '971224204ac801c38c554a7ea25b660c4cd0a0d3dcfbc8953c66edb0af3e05e2',10885802970420085187),
])
def test_approved_arm_complete_kats(arm,purpose,length,message,digest,expected):
    # Public master zero is a KAT input, never a selected execution master.
    actual = arm_seed_material(0,arm,purpose)
    assert actual == message
    assert len(actual) == length
    assert sha256(actual).hexdigest() == digest
    assert int.from_bytes(bytes.fromhex(digest)[:8],'big') == expected
    assert arm_subseed(0,arm,purpose) == expected
    assert arm_seed_labels(arm,purpose) == tuple(message.decode('ascii').split('|')[2:])


@pytest.mark.parametrize('bad', [True,-1,2**64,0.0,'0',None])
def test_arm_master_rejections(bad):
    for interface in (arm_seed_material,arm_subseed):
        with pytest.raises(ValueError):
            interface(bad,'A1','selection')


@pytest.mark.parametrize('arm,purpose', [('A2','selection'),('a1','selection'),
    ('A1','discovery'),('A3','Selection'),([], 'selection'), ('A1',None)])
def test_arm_domain_rejections(arm,purpose):
    for interface in (arm_seed_material,arm_subseed):
        with pytest.raises(ValueError):
            interface(0,arm,purpose)


def test_approved_identity_and_seed_algorithm_binding(monkeypatch):
    expected_identity = ('proposal-revision-8|hashlab-exp002-a2-encoding-v1|'
                         'hashlab-exp002-a1-a3-subseed-encoding-v1')
    assert PROTOCOL_IDENTITY == expected_identity
    config = Config().to_dict()
    assert config['protocol_identity'] == expected_identity
    assert config['a1_a3_seed_encoding'] == ARM_SEED_ENCODING
    config.pop('a1_a3_seed_encoding')
    with pytest.raises(ValueError):
        Config.from_mapping(config)
    message = arm_seed_material(2**64-1,'A3','selection')
    assert message.startswith(b'hashlab-seed-v1|18446744073709551615|')
    assert message.isascii() and not message.endswith(b'\n')
    calls = []
    def frozen_derivation(master,*labels):
        calls.append((master,labels))
        return 123
    monkeypatch.setattr('hashlab.experiments.exp002.derive_seed',frozen_derivation)
    assert arm_subseed(0,'A1','selection') == 123
    assert calls == [(0,('experiment-002','A1-lowint-w8','selection-v1'))]
