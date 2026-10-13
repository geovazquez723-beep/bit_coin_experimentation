"""Read-only authenticated S1.4 exclusion adapter. Never reconstructs E001.

Pins transcribed from the retained, accepted S1.4 result report. Authentication
means exact local bytes against these accepted pins, not a signature or human
replication. The A3 intersection is not the complete historical population.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import struct

from .e001_reconstruction import validate_history, strict_json, SOURCE, CONTRACT, MANIFEST
from .e001_phase_b import CONFIG
from .exp002 import Exclusions, HammingPopulation, EXCLUSION_DIGEST
from .exp002_journal import file_inventory, require_plain

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


@dataclass(frozen=True)
class VerifiedS14:
    exclusions: Exclusions

    def identity(self):
        return dict(source=SOURCE, config=CONFIG, contract=CONTRACT, manifest=MANIFEST,
                    producer_sha256=S14_FILES['producer/complete.json'][1],
                    verifier_sha256=S14_FILES['verifier/verified.json'][1],
                    exclusion_sha256=EXCLUSION_DIGEST, distinct_exclusions=60721)


def load_s14(audit_root, repository_root):
    """Hash all eight retained files and original sealed/source identities first."""
    root = Path(audit_root)
    for path in (root, root/'producer', root/'verifier'):
        require_plain(path, directory=True)
    if {p.name for p in root.iterdir()} != {'producer', 'verifier'}:
        raise ValueError('unexpected S1.4 directory')
    for role in ('producer', 'verifier'):
        if {p.name for p in (root/role).iterdir()} != {
                Path(name).name for name in S14_FILES if name.startswith(role+'/')}:
            raise ValueError('S1.4 inventory mismatch')
    for name, (size, digest) in S14_FILES.items():
        if file_inventory(root/name) != dict(size=size, sha256=digest):
            raise ValueError('S1.4 pin mismatch: '+name)
    repository = Path(repository_root)
    validate_history(repository/'results/20261011T205056Z-exp001-fc1d75fc', repository)
    producer = strict_json((root/'producer/complete.json').read_bytes())
    verifier = strict_json((root/'verifier/verified.json').read_bytes())
    plan = strict_json((root/'producer/plan.json').read_bytes())
    if any(plan[k] != v for k, v in dict(source=SOURCE, config=CONFIG,
                                       contract=CONTRACT, manifest=MANIFEST).items()):
        raise ValueError('S1.4 historical identity mismatch')
    common = dict(scope='historical', historical_complete=True, final_acceptance=False,
                  raw_attempted=7000000, unique_evaluated=7000000, qualifying_a1=0,
                  distinct_excluded_a3=60721, exclusion_sha256=EXCLUSION_DIGEST)
    if any(p[k] != v for p in (producer, verifier) for k, v in common.items()):
        raise ValueError('S1.4 incomplete or inconsistent reports')
    if (verifier['verification'] != 'independent-stream-replay'
            or verifier['evidence_report_sha256'] != S14_FILES['producer/complete.json'][1]
            or producer['accounting'] != verifier['accounting']
            or producer['accounting'] != plan['sealed_counts']):
        raise ValueError('S1.4 producer/verifier disagreement')
    expected = {Path(n).name: dict(bytes=s, sha256=h) for n, (s, h) in S14_FILES.items()
                if n.startswith('producer/') and not n.endswith('/complete.json')}
    if producer['files'] != expected:
        raise ValueError('S1.4 recorded evidence hashes disagree')
    population = HammingPopulation()
    values, pair_ranks = [], []
    digest = sha256()
    with (root/'producer/exclusions.bin').open('rb') as source:
        for _ in range(60721):
            raw = source.read(16)
            if len(raw) != 16:
                raise ValueError('truncated exclusions')
            value, rank = struct.unpack('>QQ', raw)
            if values and value <= values[-1] or population.rank(value) != rank:
                raise ValueError('noncanonical exclusion values/ranks')
            values.append(value)
            pair_ranks.append(rank)
            digest.update(raw[:8])
        if source.read(1) or digest.hexdigest() != EXCLUSION_DIGEST:
            raise ValueError('canonical exclusion digest/count mismatch')
    raw = (root/'producer/ranks.bin').read_bytes()
    ranks = tuple(r for r, in struct.iter_unpack('>Q', raw))
    exclusions = Exclusions(ranks, population)
    if len(ranks) != 60721 or sorted(pair_ranks) != list(ranks):
        raise ValueError('retained ranks differ from exclusion values')
    return VerifiedS14(exclusions)
