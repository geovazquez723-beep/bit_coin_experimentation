"""Bounded binary attempt/evaluation chunks. Integrity is relative to a retained pin.

No completion is issued by the writer. Observation correctness requires independent
regeneration/rehashing, not a transport hash. All files are exclusive creations.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
import struct

from .exp002_foundation import ARMS, CandidateRecord, canonical, decode
from .exp002_journal import durable_create, file_inventory, require_plain

MAGIC = b'E002KRN1'
HEADER = struct.Struct('>8sIQQ')
ROW = struct.Struct('>QBBBBQQQQI')
TRAILER = struct.Struct('>QQ32s')
NONE = 2**64-1
NO_CLUSTER = 2**32-1
REASONS = ('C1','C3','E001','A2')
STAGES = ('D','V','C')
CHUNK_ROWS = 4096
MAX_ROW_BYTES = ROW.size + 80 + 64


def _uint(value, maximum=NONE-1):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('invalid binary integer')
    return value


@dataclass(frozen=True)
class Attempt:
    arm: str
    stage: str
    candidate: bytes
    accepted_index: int | None
    source_index: int | None = None
    population_rank: int | None = None
    byte_offset: int | None = None
    cluster: int | None = None
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if self.arm not in ARMS or self.stage not in STAGES or type(self.candidate) is not bytes:
            raise ValueError('invalid attempt')
        if len(self.candidate) != (80 if self.arm in ('A2','N2') else 8):
            raise ValueError('candidate width')
        for value in (self.accepted_index,self.source_index,self.population_rank,self.byte_offset):
            if value is not None: _uint(value)
        if self.cluster is not None: _uint(self.cluster,2999)
        if (type(self.reasons) is not tuple or self.reasons != tuple(r for r in REASONS if r in self.reasons)
                or bool(self.reasons) != (self.accepted_index is None)):
            raise ValueError('rejection/acceptance mismatch')
        if self.accepted_index is not None:
            self.record()

    def record(self):
        if self.reasons:
            raise ValueError('rejected attempt has no record')
        return CandidateRecord(self.arm,self.stage,self.accepted_index,self.candidate.hex(),self.cluster)

    @classmethod
    def from_provider(cls, row):
        return cls(row['arm'],row['stage'],bytes.fromhex(row['candidate_hex']),row['accepted_index'],
                   row.get('source_index',row.get('raw_index')),row.get('population_rank'),
                   row.get('byte_offset'),row.get('cluster'),tuple(row['reasons']))


def encode_row(sequence, attempt, raw=None, effective=None):
    if type(attempt) is not Attempt: raise ValueError('typed attempt required')
    _uint(sequence)
    if attempt.reasons:
        if raw is not None or effective is not None: raise ValueError('rejected evaluation')
    elif type(raw) is not bytes or type(effective) is not bytes or len(raw)!=32 or len(effective)!=32:
        raise ValueError('accepted evaluation requires two digests')
    values = (attempt.source_index,attempt.accepted_index,attempt.population_rank,attempt.byte_offset)
    head = ROW.pack(sequence,ARMS.index(attempt.arm),STAGES.index(attempt.stage),
                    sum(1<<REASONS.index(r) for r in attempt.reasons),len(attempt.candidate),
                    *(NONE if x is None else x for x in values),
                    NO_CLUSTER if attempt.cluster is None else attempt.cluster)
    return head + attempt.candidate + (b'' if attempt.reasons else raw+effective)


def decode_row(source):
    head = source.read(ROW.size)
    if len(head)!=ROW.size: raise ValueError('torn row header')
    seq,arm,stage,mask,width,src,accepted,rank,offset,cluster = ROW.unpack(head)
    if arm>=len(ARMS) or stage>=len(STAGES) or mask>=16 or width not in (8,80):
        raise ValueError('invalid row tags')
    candidate = source.read(width)
    reasons = tuple(r for i,r in enumerate(REASONS) if mask&(1<<i))
    digests = b'' if reasons else source.read(64)
    if len(candidate)!=width or (not reasons and len(digests)!=64): raise ValueError('torn row body')
    attempt = Attempt(ARMS[arm],STAGES[stage],candidate,
        None if accepted==NONE else accepted,None if src==NONE else src,
        None if rank==NONE else rank,None if offset==NONE else offset,
        None if cluster==NO_CLUSTER else cluster,reasons)
    raw,effective = (None,None) if reasons else (digests[:32],digests[32:])
    return seq,attempt,raw,effective,head+candidate+digests


class ChunkWriter:
    """One row at a time, <=4096 rows/chunk; no growing inventory in memory."""
    def __init__(self, root):
        self.root = Path(root)
        self.index = (self.root/'chunks.jsonl').open('xb')
        self.handle = None
        self.sequence = self.chunk_count = self.row_count = self.body_bytes = 0
        self.failed = self.closed = False

    def _start(self):
        self.name = f'chunk-{self.chunk_count:08d}.bin'
        self.handle = (self.root/self.name).open('xb')
        self.handle.write(HEADER.pack(MAGIC,1,self.chunk_count,self.sequence))
        self.body_hash = sha256()
        self.row_count = self.body_bytes = 0

    def add(self, attempt, raw=None, effective=None):
        if self.failed or self.closed: raise RuntimeError('writer unavailable')
        try:
            data = encode_row(self.sequence,attempt,raw,effective)
            if self.handle is None: self._start()
            self.handle.write(data); self.body_hash.update(data)
            self.sequence += 1; self.row_count += 1; self.body_bytes += len(data)
            if self.row_count==CHUNK_ROWS: self._finish_chunk()
        except BaseException:
            self.failed = True
            raise

    def _finish_chunk(self):
        self.handle.write(TRAILER.pack(self.row_count,self.body_bytes,self.body_hash.digest()))
        self.handle.flush(); os.fsync(self.handle.fileno()); self.handle.close(); self.handle=None
        entry = dict(sequence=self.chunk_count,name=self.name,first=self.sequence-self.row_count,
                     rows=self.row_count,**file_inventory(self.root/self.name))
        self.index.write(canonical(entry)+b'\n')
        self.chunk_count += 1

    def finish(self):
        if self.failed or self.closed: raise RuntimeError('writer unavailable')
        try:
            if self.handle is not None: self._finish_chunk()
            self.index.flush(); os.fsync(self.index.fileno()); self.index.close(); self.closed=True
            return dict(chunks=self.chunk_count,attempts=self.sequence,
                        index=file_inventory(self.root/'chunks.jsonl'))
        except BaseException:
            self.failed=True
            raise

    def abandon(self):
        # Close, retain bytes; do not remove or repair the torn last chunk/index.
        self.failed=True
        if self.handle is not None: self.handle.close(); self.handle=None
        if not self.index.closed: self.index.close()


def iter_chunks(root, *, expected_chunks, expected_attempts):
    """Stream checks; caller must exhaust the iterator before accepting completion."""
    root=Path(root); require_plain(root,directory=True)
    count=chunks=0
    with (root/'chunks.jsonl').open('rb') as index:
        while line:=index.readline(1025):
            if len(line)>1024 or not line.endswith(b'\n'): raise ValueError('torn chunk index')
            entry=decode(line[:-1])
            if (type(entry) is not dict or set(entry)!={'sequence','name','first','rows','size','sha256'}
                    or type(entry['sequence']) is not int or entry['sequence']!=chunks
                    or entry['name']!=f'chunk-{chunks:08d}.bin'
                    or type(entry['first']) is not int or entry['first']!=count
                    or type(entry['rows']) is not int or not 1<=entry['rows']<=CHUNK_ROWS):
                raise ValueError('chunk sequence/length mismatch')
            if chunks>=expected_chunks: raise ValueError('extra chunk')
            if chunks<expected_chunks-1 and entry['rows']!=CHUNK_ROWS:
                raise ValueError('nonterminal short chunk')
            path=root/entry['name']
            if (type(entry['size']) is not int or not HEADER.size+TRAILER.size <= entry['size']
                    <= HEADER.size+TRAILER.size+MAX_ROW_BYTES*entry['rows']):
                raise ValueError('chunk size bound')
            if file_inventory(path)!=dict(size=entry['size'],sha256=entry['sha256']):
                raise ValueError('chunk hash/size mismatch')
            with path.open('rb') as source:
                if source.read(HEADER.size)!=HEADER.pack(MAGIC,1,chunks,count):
                    raise ValueError('chunk header mismatch')
                body=sha256(); length=0
                for _ in range(entry['rows']):
                    seq,attempt,raw,effective,encoded=decode_row(source)
                    if seq!=count or count>=expected_attempts: raise ValueError('row continuity')
                    body.update(encoded);length+=len(encoded);count+=1
                    yield attempt,raw,effective
                if source.read(TRAILER.size)!=TRAILER.pack(entry['rows'],length,body.digest()) or source.read(1):
                    raise ValueError('chunk trailer/extra bytes')
            chunks+=1
    if (chunks,count)!=(expected_chunks,expected_attempts): raise ValueError('incomplete chunks')


def create_root(destination, *, repository, audit_root, minimum_free_bytes=None):
    root=Path(destination).absolute()
    if root.resolve().is_relative_to(Path(repository).resolve()/'results') or root.resolve().is_relative_to(Path(audit_root).resolve()):
        raise ValueError('output beneath retained evidence')
    for parent in root.parents:
        require_plain(parent,directory=True)
        if (parent/'complete.json').exists() or (parent/'manifest.sha256').exists():
            raise ValueError('output beneath completed evidence')
    if minimum_free_bytes is not None:
        from .exp002_resource_preflight import check_free_space
        check_free_space(root,minimum_free_bytes)       # fails before any file is created
    root.mkdir()
    durable_create(root/'INCOMPLETE',b'incomplete\n')
    return root
