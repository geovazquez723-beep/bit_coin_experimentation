"""E3 count/record infrastructure, with no generator, hash engine or runner.

SHA-256 here fingerprints metadata and verifies file integrity only. Candidate
digests are supplied by callers; this module never computes them. Versioned
contracts do not authorize execution or assert that supplied records are true.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Callable, Iterable, Protocol

from .exp002 import Config, PROTOCOL_IDENTITY, EXCLUSION_DIGEST, integer

ARMS = ('A1', 'A2', 'A3', 'N1', 'N2', 'P1', 'P2+', 'P2-')
CLUSTERED = ('A2', 'N2')
SECONDARY_ID = 'hashlab-exp002-secondary-statistics-proposal-v2'
SECONDARY_SLOTS = tuple(
    f'{a}:{s}:{test}' for a in ('A1','A2','A3','N1','N2') for s in ('D','V')
    for test in ('leading_zero_bits','first_byte','last_byte')) + tuple(
    f'{a}:{s}:dispersion' for a in ('A2','N2') for s in ('D','V')) + tuple(
    f'A3:{s}:weight_groups' for s in ('D','V'))
LIMITS = tuple((a, s, 200_000 if a == 'P1' else 15_000_000)
               for a in ARMS for s in (('C',) if a.startswith('P') else ('D', 'V')))


def _hex(value, length):
    if type(value) is not str or re.fullmatch('[0-9a-f]{'+str(length)+'}', value) is None:
        raise ValueError('require canonical lowercase hex')
    return value


def _exact(data, keys):
    if type(data) is not dict or set(data) != set(keys):
        raise ValueError('missing or unknown schema fields')


def canonical(data) -> bytes:
    """ASCII JSON, sorted keys, compact separators, no floats/NaN or coercions."""
    def check(value):
        if value is None or type(value) in (str, int, bool):
            return
        if type(value) in (list, tuple):
            for item in value:
                check(item)
            return
        if type(value) is dict and all(type(k) is str for k in value):
            for item in value.values():
                check(item)
            return
        raise ValueError('noncanonical JSON type')
    check(data)
    return json.dumps(data, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def decode(data: bytes):
    """Reject duplicate keys, noncanonical encoding and malformed JSON."""
    if type(data) is not bytes:
        raise ValueError('require bytes')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=pairs)
    if canonical(value) != data:
        raise ValueError('noncanonical JSON bytes')
    return value


@dataclass(frozen=True)
class Plan:
    """Seedless plan: no execution master, round or commitment is accepted."""
    code_commit: str
    config: Config = field(default_factory=Config)
    schema: str = 'hashlab-exp002-seedless-plan-v2'

    def __post_init__(self):
        _hex(self.code_commit, 40)
        if type(self.config) is not Config or self.schema != 'hashlab-exp002-seedless-plan-v2':
            raise ValueError('invalid plan contract')

    def to_dict(self):
        return dict(schema=self.schema, code_commit=self.code_commit,
            config=self.config.to_dict(), streams=[dict(arm=a, stage=s, trials=n) for a,s,n in LIMITS],
            populations={
                'A1': dict(lower=2**20, upper_exclusive=2**32, encoding='8-byte-big-endian',
                           sampling='SRS-without-replacement-then-random-split'),
                'A2': dict(prefix_bytes=76, prefix_count=3000, nonce_start=0, nonce_stop=10000,
                           nonce_encoding='4-byte-little-endian', discovery_clusters=[0,1499],
                           validation_clusters=[1500,2999], sampling='uniform-prefix-complete-nonce-block'),
                'A3': dict(bits=64, maximum_weight=6, require_top32_nonzero=True,
                           class_size=82128984, excluded_count=60721, eligible_size=82068263,
                           exclusion_sha256=EXCLUSION_DIGEST, sampling='SRS-without-replacement-then-random-split')},
            controls=dict(N1='feistel64-blake2b-6-rounds-reject-A1-A3-E001',
                          N2='blake2b-80-byte-stream-reject-A2;10000-per-pseudo-cluster',
                          positive_source='N1-permutation-indices-from-2^63-reject-A1-A3-E001',
                          positive_lifts={'P1':'0.25','P2+':'0.02','P2-':'-0.02'}),
            statistics=dict(difference='two-sided-doubled-tail-Holm-D;flagged-one-sided-Holm-V',
                            margin='pooled-D-V;A1-A3-design-based;A2-CP-t-hull',
                            classification='frozen-revision-8-nine-cells', secondary=dict(
                                identity=SECONDARY_ID, alpha='0.01', correction='Holm',
                                role='exploratory-only', slots=list(SECONDARY_SLOTS),
                                a3_groups=[[1,2,3,4],[5],[6]],
                                a3_group_populations=[631413,7407537,74029313])),
            e001=dict(run_id='20261011T205056Z-exp001-fc1d75fc',
                      manifest_sha256='546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b',
                      a1_intersection=0, a3_excluded=60721),
            prerequisite_status='not-established-by-foundation')

    def serialize(self):
        return canonical(self.to_dict())

    @property
    def fingerprint(self):
        return sha256(b'hashlab-exp002-seedless-plan-v2\0'+self.serialize()).hexdigest()

    @classmethod
    def from_dict(cls, data):
        if type(data) is not dict:
            raise ValueError('require plan object')
        try:
            plan = cls(data['code_commit'], Config.from_mapping(data['config']), data['schema'])
        except KeyError as exc:
            raise ValueError('missing plan fields') from exc
        if canonical(plan.to_dict()) != canonical(data):
            raise ValueError('altered frozen plan')
        return plan


@dataclass(frozen=True)
class CandidateRecord:
    arm: str
    stage: str
    index: int
    candidate_hex: str
    cluster: int | None = None
    schema: str = 'hashlab-exp002-candidate-v1'

    def __post_init__(self):
        limits = {(a,s):n for a,s,n in LIMITS}
        if type(self.arm) is not str or type(self.stage) is not str or (self.arm,self.stage) not in limits:
            raise ValueError('invalid arm/stage')
        integer(self.index, 0, limits[self.arm,self.stage]-1)
        _hex(self.candidate_hex, 160 if self.arm in CLUSTERED else 16)
        if self.schema != 'hashlab-exp002-candidate-v1':
            raise ValueError('unknown candidate schema')
        if self.arm in CLUSTERED:
            expected = self.index//10000 + (1500 if self.stage == 'V' else 0)
            if type(self.cluster) is not int or self.cluster != expected:
                raise ValueError('cluster/stage/index mismatch')
            if self.arm == 'A2' and int.from_bytes(bytes.fromhex(self.candidate_hex[-8:]),'little') != self.index%10000:
                raise ValueError('A2 nonce/index mismatch')
        elif self.cluster is not None:
            raise ValueError('unexpected cluster')
        value = int(self.candidate_hex,16)
        if self.arm == 'A1' and not 2**20 <= value < 2**32:
            raise ValueError('outside A1 population')
        if self.arm == 'A3' and not (value>>32 and value.bit_count()<=6):
            raise ValueError('outside A3 structural class')

    def to_dict(self):
        return asdict(self)

    def serialize(self):
        return canonical(self.to_dict())

    @classmethod
    def deserialize(cls, data):
        value=decode(data)
        _exact(value, cls.__dataclass_fields__)
        return cls(**value)


@dataclass(frozen=True)
class SuccessRecord:
    candidate: CandidateRecord
    digest_hex: str
    schema: str = 'hashlab-exp002-success-v1'

    def __post_init__(self):
        if type(self.candidate) is not CandidateRecord or self.schema != 'hashlab-exp002-success-v1':
            raise ValueError('invalid success record')
        _hex(self.digest_hex,64)
        if int(self.digest_hex,16) >= 2**248:
            raise ValueError('digest does not satisfy strict target')

    def serialize(self):
        return canonical(dict(schema=self.schema,candidate=self.candidate.to_dict(),digest_hex=self.digest_hex))

    @classmethod
    def deserialize(cls,data):
        value=decode(data)
        _exact(value,cls.__dataclass_fields__)
        candidate=value['candidate']
        _exact(candidate,CandidateRecord.__dataclass_fields__)
        return cls(CandidateRecord(**candidate),value['digest_hex'],value['schema'])


class ControlProvider(Protocol):
    """Supplied records/digests only; no generation implementation in E3."""
    def records(self, arm: str) -> Iterable[tuple[CandidateRecord, bytes]]: ...


class E001Reconstruction(Protocol):
    """Future external reconstruction must preserve E001 and match pinned identity."""
    def candidates(self, request: E001ExclusionRequest) -> Iterable[bytes]: ...


@dataclass(frozen=True)
class E001ExclusionRequest:
    """Pinned reconstruction inputs; an external implementation supplies bytes.

    This is a request contract only: construction never enumerates E001.
    """
    run_id: str = '20261011T205056Z-exp001-fc1d75fc'
    manifest_sha256: str = '546d83a2ad5615cfe937e021c2b7097f1997d7f13c8f3326f3d03e6aa60a967b'
    eight_byte_count: int = 7_000_000
    sixteen_byte_count: int = 3_000_000
    a1_intersection: int = 0
    a3_excluded_count: int = 60721
    a3_exclusion_sha256: str = EXCLUSION_DIGEST

    def __post_init__(self):
        for name,definition in self.__dataclass_fields__.items():
            value=getattr(self,name)
            if type(value) is not type(definition.default) or value!=definition.default:
                raise ValueError('altered E001 reconstruction contract')


class OverlapAudit(Protocol):
    def check(self, record: CandidateRecord) -> None:
        """Raise on any unhandled overlap/exclusion failure; never suppress hits."""
        ...


@dataclass(frozen=True)
class AuditResult:
    name: str
    guarantee: str
    checked: int
    hits: int
    rejected: int
    reference: str

    def __post_init__(self):
        if type(self.name) is not str or not self.name or self.guarantee not in ('M','E','D','P','C'):
            raise ValueError('invalid audit identity/guarantee')
        integer(self.checked,0,2**64-1)
        integer(self.hits,0,self.checked)
        integer(self.rejected,0,self.hits)
        if type(self.reference) is not str or not self.reference.strip():
            raise ValueError('require proof, digest, probability bound or assumption reference')
        if self.guarantee in ('P','C') and any((self.checked,self.hits,self.rejected)):
            raise ValueError('unchecked bounds/assumptions cannot report measured counts')


class SuccessIndexCollector:
    """Chunked sink with a hard record cap; sink exceptions poison the collector.

    Sink owns persistence. No retry or truncation. Chunk order follows input
    order; the accounting layer enforces unique consecutive stream indices.
    """
    def __init__(self, sink: Callable[[tuple[tuple[str,str,int],...]],None], capacity=4096):
        integer(capacity,1,65536)
        if not callable(sink):
            raise ValueError('require sink')
        self._sink,self.capacity=sink,capacity
        self._pending=[]
        self._failed=False
        self._closed=False

    def add(self, record: CandidateRecord):
        if self._failed or self._closed:
            raise RuntimeError('index collector unavailable')
        if type(record) is not CandidateRecord:
            self._failed=True
            raise ValueError('require candidate record')
        self._pending.append((record.arm,record.stage,record.index))
        if len(self._pending)==self.capacity:
            self.flush()

    def flush(self):
        if self._failed or self._closed:
            raise RuntimeError('index collector unavailable')
        if self._pending:
            try:
                self._sink(tuple(self._pending))
            except BaseException:
                self._failed=True
                raise
            self._pending.clear()

    def close(self):
        self.flush()
        self._closed=True

    @property
    def buffered(self):
        return len(self._pending)


class Accumulator:
    """Ordered per-stream records; fixed counters, no candidate retention.

    Counts, clusters and raw histograms only: no statistical tests or labels.
    A failed audit/sink/input permanently poisons this instance. Caller must
    disclose failure; this layer does not provide operational retry machinery.
    """
    def __init__(self, *, index_collector=None, success_sink=None, audit=None):
        if index_collector is not None and type(index_collector) is not SuccessIndexCollector:
            raise ValueError('invalid index collector')
        if success_sink is not None and not callable(success_sink):
            raise ValueError('invalid success sink')
        if audit is not None and not callable(getattr(audit,'check',None)):
            raise ValueError('invalid audit interface')
        self._indices=index_collector
        self._success_sink=success_sink
        self._audit=audit
        self._failed=False
        self._closed=False
        self._streams={(a,s):dict(trials=0,successes=0,first_byte=[0]*256,
            last_byte=[0]*256,leading_zero_bits=[0]*257,
            cluster_trials=[0]*1500 if a in CLUSTERED else None,
            cluster_successes=[0]*1500 if a in CLUSTERED else None,
            weight_trials=[0]*6 if a=='A3' else None,
            weight_successes=[0]*6 if a=='A3' else None) for a,s,_ in LIMITS}

    def add(self, record: CandidateRecord, digest: bytes):
        if self._failed or self._closed:
            raise RuntimeError('accumulator unavailable')
        try:
            if type(record) is not CandidateRecord or type(digest) is not bytes or len(digest)!=32:
                raise ValueError('require candidate record and supplied 32-byte digest')
            stream=self._streams[record.arm,record.stage]
            if record.index != stream['trials']:
                raise ValueError('duplicate, gap or out-of-order stream index')
            if self._audit is not None:
                self._audit.check(record)
            success=int.from_bytes(digest,'big')<2**248
            if success:
                sr=SuccessRecord(record,digest.hex())
                if self._success_sink is not None:
                    self._success_sink(sr.serialize())
                if self._indices is not None:
                    self._indices.add(record)
            stream['trials']+=1
            stream['successes']+=int(success)
            stream['first_byte'][digest[0]]+=1
            stream['last_byte'][digest[-1]]+=1
            stream['leading_zero_bits'][256-int.from_bytes(digest,'big').bit_length()]+=1
            if record.arm=='A3':
                weight=int(record.candidate_hex,16).bit_count()-1
                stream['weight_trials'][weight]+=1
                stream['weight_successes'][weight]+=int(success)
            if record.cluster is not None:
                c=record.cluster%1500
                stream['cluster_trials'][c]+=1
                stream['cluster_successes'][c]+=int(success)
        except BaseException:
            self._failed=True
            raise

    def snapshot(self):
        if self._failed:
            raise RuntimeError('failed accumulator cannot publish counts')
        # Detached JSON-safe snapshot, no mutable aliases to internal counters.
        return json.loads(canonical(dict(schema='hashlab-exp002-accounting-v2', secondary_identity=SECONDARY_ID,
            complete=all(v['trials']==dict(((a,s),n) for a,s,n in LIMITS)[k] for k,v in self._streams.items()),
            streams=[dict(arm=a,stage=s,**self._streams[a,s]) for a,s,_ in LIMITS])))

    def finish(self):
        if self._failed or self._closed:
            raise RuntimeError('accumulator unavailable')
        try:
            if not self.snapshot()['complete']:
                raise ValueError('incomplete frozen stream geometry')
            if self._indices is not None:
                self._indices.close()
            self._closed=True
            return self.snapshot()
        except BaseException:
            self._failed=True
            raise


def validate_accounting(data, *, require_complete=False):
    _exact(data,('schema','secondary_identity','complete','streams'))
    if (data['schema']!='hashlab-exp002-accounting-v2' or data['secondary_identity']!=SECONDARY_ID
            or type(data['complete']) is not bool):
        raise ValueError('invalid accounting schema')
    rows=data['streams']
    if type(rows) is not list or len(rows)!=len(LIMITS):
        raise ValueError('missing accounting streams')
    complete=True
    for row,(arm,stage,limit) in zip(rows,LIMITS):
        _exact(row,('arm','stage','trials','successes','first_byte','last_byte','leading_zero_bits',
                    'cluster_trials','cluster_successes','weight_trials','weight_successes'))
        if (row['arm'],row['stage'])!=(arm,stage):
            raise ValueError('noncanonical stream order/identity')
        integer(row['trials'],0,limit)
        integer(row['successes'],0,row['trials'])
        complete &= row['trials']==limit
        for key,size in (('first_byte',256),('last_byte',256),('leading_zero_bits',257)):
            counts=row[key]
            if type(counts) is not list or len(counts)!=size:
                raise ValueError('invalid diagnostic bins')
            for count in counts:
                integer(count,0,row['trials'])
            if sum(counts)!=row['trials']:
                raise ValueError('diagnostic total mismatch')
        if sum(row['leading_zero_bits'][8:])!=row['successes'] or row['first_byte'][0]!=row['successes']:
            raise ValueError('target/diagnostic mismatch')
        for j in range(8):
            if row['leading_zero_bits'][j]!=sum(row['first_byte'][2**(7-j):2**(8-j)]):
                raise ValueError('first-byte/leading-zero mismatch')
        if arm in CLUSTERED:
            ct,cs=row['cluster_trials'],row['cluster_successes']
            if type(ct) is not list or type(cs) is not list or len(ct)!=1500 or len(cs)!=1500:
                raise ValueError('missing clusters')
            for i,(trials,successes) in enumerate(zip(ct,cs)):
                integer(trials,0,10000)
                integer(successes,0,trials)
                if trials!=min(10000,max(0,row['trials']-i*10000)):
                    raise ValueError('cluster accounting order mismatch')
            if sum(ct)!=row['trials'] or sum(cs)!=row['successes']:
                raise ValueError('cluster accounting total mismatch')
        elif row['cluster_trials'] is not None or row['cluster_successes'] is not None:
            raise ValueError('unexpected clusters')
        if arm=='A3':
            wt,ws=row['weight_trials'],row['weight_successes']
            if type(wt) is not list or type(ws) is not list or len(wt)!=6 or len(ws)!=6:
                raise ValueError('missing A3 raw-weight counters')
            for trials,successes in zip(wt,ws):
                integer(trials,0,row['trials'])
                integer(successes,0,trials)
            if sum(wt)!=row['trials'] or sum(ws)!=row['successes']:
                raise ValueError('A3 raw-weight totals mismatch')
            if wt[0]>12:
                raise ValueError('A3 weight one exceeds twelve eligible members')
            if any(n>size for n,size in zip((sum(wt[:4]),wt[4],wt[5]),(631413,7407537,74029313))):
                raise ValueError('A3 grouped count exceeds eligible population')
        elif row['weight_trials'] is not None or row['weight_successes'] is not None:
            raise ValueError('unexpected A3 weight counters')
    if data['complete']!=complete or require_complete and not complete:
        raise ValueError('completion/geometry mismatch')
    a3=[r for r in rows if r['arm']=='A3']
    if sum(r['weight_trials'][0] for r in a3)>12:
        raise ValueError('pooled A3 weight-one count exceeds eligible population')
    pooled=[sum(r['weight_trials'][i] for r in a3) for i in range(6)]
    if any(n>size for n,size in zip((sum(pooled[:4]),pooled[4],pooled[5]),(631413,7407537,74029313))):
        raise ValueError('pooled A3 grouped count exceeds eligible population')


def validate_success_records(records: Iterable[bytes], accounting):
    """Streaming structural consistency, not candidate-digest authentication.

    Each input is canonical SuccessRecord bytes without a newline. Strictly
    increasing per-stream success indices detect repeats without a sample set.
    """
    validate_accounting(accounting)
    rows={(r['arm'],r['stage']):r for r in accounting['streams']}
    previous={k:-1 for k in rows}
    totals={k:0 for k in rows}
    clusters={k:[0]*1500 for k in rows if k[0] in CLUSTERED}
    weights={k:[0]*6 for k in rows if k[0]=='A3'}
    for raw in records:
        success=SuccessRecord.deserialize(raw)
        r=success.candidate
        key=r.arm,r.stage
        if not previous[key]<r.index<rows[key]['trials']:
            raise ValueError('success index repeated, out of order or beyond accounted records')
        previous[key]=r.index
        totals[key]+=1
        if totals[key]>rows[key]['successes']:
            raise ValueError('excess success records')
        if r.cluster is not None:
            clusters[key][r.cluster%1500]+=1
        if r.arm=='A3':
            weights[key][int(r.candidate_hex,16).bit_count()-1]+=1
    for key,row in rows.items():
        if totals[key]!=row['successes']:
            raise ValueError('missing success records')
        if key in clusters and clusters[key]!=row['cluster_successes']:
            raise ValueError('success cluster mismatch')
        if key in weights and weights[key]!=row['weight_successes']:
            raise ValueError('success raw-weight mismatch')


@dataclass(frozen=True)
class EvidenceFile:
    name: str
    bytes: int
    sha256: str

    def __post_init__(self):
        if type(self.name) is not str or re.fullmatch(r'[a-z0-9](?:[a-z0-9_.-]{0,126}[a-z0-9])?',self.name) is None:
            raise ValueError('unsafe evidence basename')
        if self.name.split('.')[0] in {'con','prn','aux','nul',*(f'com{i}' for i in range(10)),*(f'lpt{i}' for i in range(10))}:
            raise ValueError('reserved evidence basename')
        if self.name in ('manifest.json','manifest.sha256'):
            raise ValueError('self-referential payload forbidden')
        integer(self.bytes,0,2**64-1)
        _hex(self.sha256,64)


@dataclass(frozen=True)
class ExecutionManifest:
    """Typed E002 metadata payload; outer hashlab-manifest-v1 is unchanged.

    No timestamp/seed/attempt is selected, no directory created or file sealed.
    Complete validates accounting only, not scientific/operational validity.
    """
    plan_sha256: str
    code_commit: str
    status: str
    payloads: tuple[EvidenceFile,...]
    protocol_identity: str = PROTOCOL_IDENTITY
    schema: str = 'hashlab-exp002-execution-metadata-v1'

    def __post_init__(self):
        _hex(self.plan_sha256,64)
        _hex(self.code_commit,40)
        if self.status not in ('partial','complete','aborted'):
            raise ValueError('invalid execution status')
        if self.schema!='hashlab-exp002-execution-metadata-v1' or self.protocol_identity!=PROTOCOL_IDENTITY:
            raise ValueError('unknown manifest schema/protocol')
        if type(self.payloads) is not tuple or not self.payloads or any(type(p) is not EvidenceFile for p in self.payloads):
            raise ValueError('require typed payload inventory')
        names=[p.name for p in self.payloads]
        if names!=sorted(set(names)) or 'accounting.json' not in names:
            raise ValueError('require unique sorted inventory and accounting payload')

    def serialize(self):
        return canonical(asdict(self))

    @classmethod
    def deserialize(cls,data):
        value=decode(data)
        _exact(value,cls.__dataclass_fields__)
        if type(value['payloads']) is not list:
            raise ValueError('require payload list')
        payloads=[]
        for p in value['payloads']:
            _exact(p,EvidenceFile.__dataclass_fields__)
            payloads.append(EvidenceFile(**p))
        return cls(**dict(value,payloads=tuple(payloads)))


def validate_evidence(root: Path, plan: Plan, manifest: ExecutionManifest,
                      *, pinned_metadata_sha256: str):
    """Read-only, bounded-file-buffer integrity and accounting validation.

    The externally supplied pin must be retained independently by the caller.
    Reject links, missing/unlisted files and locally rewritten metadata/payloads.
    Foundation inventory is flat and excludes the outer seal files.
    """
    if type(plan) is not Plan or type(manifest) is not ExecutionManifest:
        raise ValueError('require typed plan/manifest')
    _hex(pinned_metadata_sha256,64)
    if sha256(manifest.serialize()).hexdigest()!=pinned_metadata_sha256:
        raise ValueError('external metadata pin mismatch')
    if manifest.plan_sha256!=plan.fingerprint or manifest.code_commit!=plan.code_commit:
        raise ValueError('plan/manifest binding mismatch')
    root=Path(root)
    if root.is_symlink() or getattr(root,'is_junction',lambda:False)() or not root.is_dir():
        raise ValueError('invalid evidence root')
    if {p.name for p in root.iterdir()}!={p.name for p in manifest.payloads}:
        raise ValueError('missing or unlisted evidence')
    for entry in manifest.payloads:
        path=root/entry.name
        if path.is_symlink() or not path.is_file() or getattr(path,'is_junction',lambda:False)():
            raise ValueError('non-regular evidence payload')
        digest=sha256()
        size=0
        with path.open('rb') as source:
            for chunk in iter(lambda:source.read(65536),b''):
                size+=len(chunk)
                if size>entry.bytes:
                    raise ValueError('evidence size mismatch')
                digest.update(chunk)
        if size!=entry.bytes or digest.hexdigest()!=entry.sha256:
            raise ValueError('evidence integrity mismatch')
    # Accounting has bounded geometry; reject oversized JSON before loading.
    accounting=root/'accounting.json'
    if accounting.stat().st_size>2_000_000:
        raise ValueError('accounting payload exceeds schema cap')
    counts=decode(accounting.read_bytes())
    validate_accounting(counts,require_complete=manifest.status=='complete')
    successes=root/'successes.jsonl'
    if successes.exists():
        def records():
            with successes.open('rb') as source:
                while line:=source.readline(4097):
                    if len(line)>4096 or not line.endswith(b'\n'):
                        raise ValueError('oversized or truncated success JSONL record')
                    yield line[:-1]
        validate_success_records(records(),counts)
    elif manifest.status=='complete' or any(r['successes'] for r in counts['streams']):
        raise ValueError('missing success record payload')
