"""E5 Phase A: pinned historical occurrences, not a full E audit or hash run.

Only bounded fixture windows are exposed. Raw occurrences are retained; seeded
validation dedup against all discovery values is explicitly unresolved here.
SHA-256 below authenticates metadata/source and exclusion-set encoding only.
"""
from dataclasses import dataclass
from hashlib import sha256
from itertools import islice
from pathlib import Path
import json

from hashlab.candidates import build_generator
from .exp002 import HammingPopulation, in_a1, in_a3, integer
from .exp002_foundation import E001ExclusionRequest
from .exp002_journal import file_inventory, require_plain

SOURCE = 'ef595f5c2f2166923fd277def39708409f564419'
MANIFEST = '546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b'
CONTRACT = '008103689ed9a9d2b9ec4a68dc21801602cf59d8b0bc009d2e7c97c9dba31d04'
LIMIT = 4096
PHASES = ('discovery','validation')


def strict_json(raw):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d: raise ValueError('duplicate historical key')
            d[k]=v
        return d
    def invalid(value): raise ValueError('nonfinite historical number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def contract():
    raw=Path(__file__).with_name('e001_contract.json').read_bytes().replace(b'\r\n',b'\n')
    if sha256(raw).hexdigest()!=CONTRACT:
        raise ValueError('historical contract identity mismatch')
    return strict_json(raw)


def validate_history(root, source_root):
    """Read-only pin check of all eleven files and actual generator source bytes."""
    root=Path(root); source_root=Path(source_root)
    require_plain(root,directory=True)
    paths=list(root.iterdir())
    for p in paths: require_plain(p)
    raw=(root/'manifest.json').read_bytes()
    if sha256(raw).hexdigest()!=MANIFEST:
        raise ValueError('unaccepted E001 manifest')
    manifest=strict_json(raw)
    if (manifest['schema']!='hashlab-manifest-v1' or manifest['status']!='complete'
            or manifest['run_id']!=E001ExclusionRequest().run_id):
        raise ValueError('invalid historical manifest')
    if {p.name for p in paths}!=set(manifest['files'])|{'manifest.json','manifest.sha256'}:
        raise ValueError('historical inventory mismatch')
    if (root/'manifest.sha256').read_text('ascii')!=MANIFEST+'  manifest.json\n':
        raise ValueError('historical self hash mismatch')
    for name,expected in manifest['files'].items():
        actual=file_inventory(root/name)
        if actual!=dict(size=expected['bytes'],sha256=expected['sha256']):
            raise ValueError('historical payload mismatch: '+name)
    c=contract()
    for name,key in (('config.resolved.json','config'),('seeds.json','seeds'),('environment.json','environment')):
        if strict_json((root/name).read_bytes())!=c[key]:
            raise ValueError('unsupported historical configuration/provenance')
    if c['environment']['git']['revision']!=SOURCE or c['environment']['git']['dirty']:
        raise ValueError('missing immutable historical source')
    for name,pin in c['source_sha256_lf'].items():
        path=source_root/name
        require_plain(path)
        if sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=pin:
            raise ValueError('source differs from historical revision: '+name)
        # A pinned source directory cannot excuse running a different checkout.
        loaded=Path(__file__).resolve().parents[3]/name
        require_plain(loaded)
        if sha256(loaded.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=pin:
            raise ValueError('loaded checkout differs from historical source')
    results=strict_json((root/'results.json').read_bytes())
    for gid,phases in c['counts'].items():
        for phase,counts in phases.items():
            actual=results['generators'][gid]['phases'][phase]
            if any(actual[k]!=v or type(actual[k]) is not type(v) for k,v in counts.items()):
                raise ValueError('historical counts mismatch')
    return c


@dataclass(frozen=True)
class Occurrence:
    generator: str
    ordinal: int
    phase: str
    index: int  # attempted occurrence within phase, not unique-output ordinal
    enumeration_index: int
    candidate: bytes
    scope: str = 'synthetic-fixture'
    source: str = SOURCE
    manifest: str = MANIFEST

    def __post_init__(self):
        specs=contract()['config']['generators']
        integer(self.ordinal,0,len(specs)-1)
        spec=specs[self.ordinal]
        if self.generator!=spec['id'] or self.phase not in PHASES:
            raise ValueError('missing or inconsistent occurrence provenance')
        integer(self.index,0,499999)
        seeded=spec['type'] in ('uniform','random_bytes')
        expected=self.index+(500000 if self.phase=='validation' and not seeded else 0)
        if type(self.enumeration_index) is not int or self.enumeration_index!=expected:
            raise ValueError('invalid enumeration index')
        if type(self.candidate) is not bytes or len(self.candidate)!=spec['width']:
            raise ValueError('invalid historical candidate width')
        if self.source!=SOURCE or self.manifest!=MANIFEST or self.scope not in ('synthetic-fixture','historical-prefix'):
            raise ValueError('unaccepted historical provenance')


class BoundedE001Reconstruction:
    """E001Reconstruction provider deliberately limited to fixture prefixes.

    candidates(request) emits only 7*prefix discovery occurrences (8-byte sets),
    never seven million. records exposes provenance and bounded raw windows.
    No dedup claim is made for a seeded validation window without discovery.
    """
    def __init__(self, root, source_root, *, prefix=8):
        integer(prefix,1,LIMIT//10)
        self.root=Path(root); self.source_root=Path(source_root); self.prefix=prefix
        validate_history(root,source_root)

    def records(self, generator, phase, *, start=0, count=None):
        c=validate_history(self.root,self.source_root)
        specs=c['config']['generators']
        matches=[(i,s) for i,s in enumerate(specs) if s['id']==generator]
        if len(matches)!=1 or phase not in PHASES: raise ValueError('unsupported stream')
        ordinal,spec=matches[0]
        count=self.prefix if count is None else count
        integer(start,0,499999); integer(count,0,LIMIT)
        if start+count>500000: raise ValueError('window beyond sealed attempted count')
        gen=build_generator(spec)
        offset=c['counts'][generator][phase]['start_index']
        # No hidden large islice replay. Sequential/structured are direct-index.
        if spec['type'] in ('uniform','random_bytes','patterned') and start+offset+count>LIMIT:
            raise ValueError('window requires unauthorized prefix enumeration')
        seed=c['counts'][generator][phase]['seed']
        if gen.uses_seed or spec['type']=='patterned':
            stream=islice(gen.stream(seed,offset),start,start+count)
        else:
            stream=islice(gen.stream(seed,offset+start),count)
        for index,raw in enumerate(stream,start):
            yield Occurrence(generator,ordinal,phase,index,index+offset,raw,'historical-prefix')

    def candidates(self, request):
        if type(request) is not E001ExclusionRequest or request!=E001ExclusionRequest():
            raise ValueError('unaccepted reconstruction request')
        for spec in contract()['config']['generators']:
            if spec['width']==8:
                for record in self.records(spec['id'],'discovery'):
                    yield record.candidate


def exclusion_representation(values):
    """Bounded unique weight/colex ranks; digest sorts NUMERIC values, eight-byte BE."""
    population=HammingPopulation(); distinct=set()
    for i,raw in enumerate(values):
        if i>=LIMIT: raise ValueError('fixture exclusion resource limit')
        if type(raw) is not bytes or len(raw)!=8 or not in_a3(raw):
            raise ValueError('non-A3 exclusion')
        distinct.add(int.from_bytes(raw,'big'))
    digest=sha256()
    for value in sorted(distinct): digest.update(value.to_bytes(8,'big'))
    return dict(ranks=tuple(sorted(population.rank(v) for v in distinct)),
                distinct=len(distinct),sha256=digest.hexdigest())


def validate_exclusion_representation(data):
    """Validate supplied bounded ranks/count/digest; never assume production X3."""
    if type(data) is not dict or set(data)!={'ranks','distinct','sha256'}:
        raise ValueError('malformed exclusion representation')
    ranks=data['ranks']
    if type(ranks) is not tuple or len(ranks)>LIMIT:
        raise ValueError('bounded immutable exclusion ranks required')
    population=HammingPopulation(); previous=-1; values=[]
    for rank in ranks:
        integer(rank,0,population.size-1)
        if rank<=previous: raise ValueError('unordered or duplicate exclusion rank')
        previous=rank
        values.append(population.unrank(rank).to_bytes(8,'big'))
    if type(data['distinct']) is not int or exclusion_representation(values)!=data:
        raise ValueError('exclusion count/digest mismatch')
    return data


class InterruptedAudit(RuntimeError):
    def __init__(self, summary):
        super().__init__('fixture audit interrupted; no E claim')
        self.summary=summary


def fixture_audit(records, expected):
    """Exact bounded occurrence-key schedule; all summaries are nonproduction.

    expected entries: (generator, ordinal, phase, index). Duplicated values are
    retained as occurrences, collapsed only in the exclusion representation.
    Repeated/out-of-order provenance is rejected, never silently deduplicated.
    """
    if type(expected) is not tuple or len(expected)>LIMIT or len(set(expected))!=len(expected):
        raise ValueError('invalid fixture audit schedule')
    keys=[]
    for gid,ordinal,phase,index in expected:
        # Validate schedule even if the input stream is empty.
        spec=contract()['config']['generators'][integer(ordinal,0,9)]
        if gid!=spec['id'] or phase not in PHASES: raise ValueError('bad schedule provenance')
        integer(index,0,499999)
        keys.append((ordinal,PHASES.index(phase),index))
    if keys!=sorted(keys): raise ValueError('out-of-order fixture schedule')
    n=0; a1=0; values=[]; seen=set(); duplicates=0
    def summary(status):
        return dict(schema='hashlab-e001-fixture-audit-v1',status=status,scope='bounded-fixture-only',
                    source=SOURCE,manifest=MANIFEST,expected=len(expected),checked=n,
                    duplicate_occurrences=duplicates,a1_occurrences=a1,
                    exclusions=exclusion_representation(values),e_audit_passed=False)
    try:
        for record in records:
            if type(record) is not Occurrence: raise ValueError('missing typed provenance')
            key=(record.generator,record.ordinal,record.phase,record.index)
            if n>=len(expected) or key!=expected[n]: raise ValueError('count/order/provenance mismatch')
            n+=1
            if record.candidate in seen: duplicates+=1
            seen.add(record.candidate)
            if len(record.candidate)==8:
                a1+=int(in_a1(record.candidate))
                if in_a3(record.candidate): values.append(record.candidate)
    except ValueError:
        raise
    except Exception as exc:
        raise InterruptedAudit(summary('incomplete')) from exc
    return summary('fixture-complete' if n==len(expected) and not a1 else 'incomplete' if n<len(expected) else 'fixture-a1-hit')
