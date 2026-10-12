"""Review 038 bounded infrastructure, not a historical full-stream provider.

All producer/accounting operations enforce <=4096 SYNTHETIC occurrences.
No candidate SHA-256, dispatcher, automatic retry, recovery or acceptance flag.
"""
from dataclasses import dataclass,asdict
from hashlib import sha256
from itertools import islice
from pathlib import Path
import os
import sqlite3
import struct

from hashlab.candidates import build_generator
from .e001_reconstruction import SOURCE,MANIFEST,CONTRACT
from .exp002 import in_a1,in_a3,HammingPopulation,integer
from .exp002_foundation import canonical,decode,_hex
from .exp002_journal import require_plain,durable_create,file_inventory

KINDS={0:'sequential',2:'uniform',4:'patterned',6:'gray',7:'stride',8:'bit-reversed',9:'random_bytes'}
CONFIG='d8a4f67d2823734a245892c36003207132fc72cc0db0d447f8824e4ca203364b'
ZERO='0'*64
HEADER=struct.Struct('>8sBBII')


def fingerprint(value):return sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class FixturePlan:
    specs: tuple
    discovery: int
    validation: int
    seeds: tuple = (1,2)  # visibly synthetic fixture keys, not historical seeds
    source: str = SOURCE
    manifest: str = MANIFEST
    config: str = CONFIG
    contract: str = CONTRACT
    schema: str = 'e001-reconstruction-fixture-plan-v1'

    def __post_init__(self):
        if type(self.specs) is not tuple or not self.specs or any(type(s) is not tuple or len(s)!=2 for s in self.specs):raise ValueError('typed fixture specs')
        ordinals=[]
        for ordinal,kind in self.specs:
            integer(ordinal,0,9)
            if KINDS.get(ordinal)!=kind:raise ValueError('unsupported generator identity')
            ordinals.append(ordinal)
        if ordinals!=sorted(set(ordinals)):raise ValueError('generator order')
        integer(self.discovery,0,4096);integer(self.validation,0,4096)
        integer(len(self.specs)*(self.discovery+self.validation),1,4096)
        if type(self.seeds) is not tuple or len(self.seeds)!=2:raise ValueError('fixture keys')
        for seed in self.seeds:integer(seed,0,2**64-1)
        if (self.source,self.manifest,self.config,self.contract,self.schema)!=(SOURCE,MANIFEST,CONFIG,CONTRACT,'e001-reconstruction-fixture-plan-v1'):raise ValueError('wrong historical bindings')

    @property
    def fingerprint(self):return fingerprint(asdict(self))

    def positions(self):
        for ordinal,_ in self.specs:
            for phase,count in enumerate((self.discovery,self.validation)):
                for index in range(count):yield ordinal,phase,index


def fixture_rows(plan):
    if type(plan) is not FixturePlan:raise ValueError('fixture plan required')
    for ordinal,kind in plan.specs:
        spec=dict(id='synthetic-fixture',width=8,type=kind)
        if kind in ('gray','stride','bit-reversed'):
            spec.update(type='structured',mode=kind)
            if kind=='stride':spec.update(stride=11400714819323198485,offset=0)
        if kind=='patterned':spec.update(mode='repeated-bytes',max_period=3)
        if kind in ('sequential','uniform'):spec.update(encoding='be-bytes')
        if kind=='sequential':spec['start']=0
        gen=build_generator(spec)
        for phase,count in enumerate((plan.discovery,plan.validation)):
            offset=0 if gen.uses_seed else phase*plan.discovery
            seed=plan.seeds[phase] if gen.uses_seed else None
            for index,raw in enumerate(islice(gen.stream(seed,offset),count)):
                yield ordinal,phase,index,raw


class ExactDedup:
    """New exclusive SQLite store; failed transactions permanently poison this object."""
    def __init__(self,path,*,max_bytes=8*1024*1024,cache_kib=64,max_records=4096):
        integer(max_bytes,65536,64*1024*1024);integer(cache_kib,8,1024);integer(max_records,1,4096)
        self.path=Path(path);require_plain(self.path.parent,directory=True)
        descriptor=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        os.close(descriptor)
        self.failed=False;self.records=0;self.max_records=max_records;self.max_bytes=max_bytes
        self.db=sqlite3.connect(self.path)
        try:
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('PRAGMA journal_mode=DELETE')
            self.db.execute(f'PRAGMA cache_size=-{cache_kib}')
            self.db.execute('PRAGMA temp_store=FILE')
            self.db.execute(f'PRAGMA max_page_count={max_bytes//4096}')
            self.db.execute('CREATE TABLE seen (generator INTEGER NOT NULL, candidate BLOB NOT NULL CHECK(typeof(candidate)=\'blob\' AND length(candidate)=8), phase INTEGER NOT NULL, idx INTEGER NOT NULL, PRIMARY KEY(generator,candidate)) WITHOUT ROWID')
            self.db.commit()
        except BaseException:
            self.failed=True;self.db.close();raise

    def _commit(self):self.db.commit()

    def observe(self,ordinal,phase,index,raw):
        if self.failed:raise ValueError('poisoned store; no retry')
        try:
            integer(ordinal,0,9);integer(phase,0,1);integer(index,0,4095)
            if type(raw) is not bytes or len(raw)!=8:raise ValueError('BLOB width')
            if self.records>=self.max_records:raise ValueError('configured record limit')
            if sum(p.stat().st_size for p in self.path.parent.glob(self.path.name+'*'))>self.max_bytes:raise ValueError('disk reservation exceeded')
            previous=self.db.execute('SELECT phase,idx FROM seen WHERE generator=? AND candidate=?',(ordinal,raw)).fetchone()
            if previous is not None and previous[0]>phase:raise ValueError('phase reversal')
            if previous is None:self.db.execute('INSERT INTO seen VALUES (?,?,?,?)',(ordinal,raw,phase,index))
            self._commit()
            self.records+=1
            return dict(outcome='unique' if previous is None else 'cross' if previous[0]!=phase else 'within',
                        first_phase=phase if previous is None else previous[0],first_index=index if previous is None else previous[1])
        except BaseException:
            self.failed=True
            self.db.rollback()
            raise

    def close(self):self.db.close()


def account_rows(plan,rows,store):
    try:
        return _account_rows(plan,rows,store)
    except BaseException:
        store.failed=True
        store.db.rollback()
        raise


def _account_rows(plan,rows,store):
    rows=iter(rows);values=set();a1=0;a1_values=set();a3_occurrences=0;provenance={};accounting=[]
    for ordinal,_ in plan.specs:
        for phase,count in enumerate((plan.discovery,plan.validation)):
            counts=dict(ordinal=ordinal,phase=phase,attempted=0,unique=0,within=0,cross=0)
            for index in range(count):
                row=next(rows,None)
                if type(row) is not tuple or len(row)!=4 or row[:3]!=(ordinal,phase,index):raise ValueError('missing/order/provenance')
                
                for value,upper in zip(row[:3],(9,1,4095)):integer(value,0,upper)
                raw=row[3];out=store.observe(ordinal,phase,index,raw)
                counts['attempted']+=1;counts[out['outcome']]+=1
                a1+=int(in_a1(raw))
                if in_a1(raw):a1_values.add(raw)
                if in_a3(raw):
                    v=int.from_bytes(raw,'big');values.add(v);a3_occurrences+=1
                    if v not in provenance:provenance[v]=dict(value_hex=raw.hex(),ordinal=ordinal,phase=phase,index=index,occurrences=0)
                    provenance[v]['occurrences']+=1
            accounting.append(counts)
    if next(rows,None) is not None:raise ValueError('extra occurrence')
    digest=sha256()
    for v in sorted(values):digest.update(v.to_bytes(8,'big'))
    return dict(schema='e001-producer-fixture-accounting-v1',plan=plan.fingerprint,
        producer_complete=True,accounting=accounting,a3_provenance=[provenance[v] for v in sorted(provenance)],membership=dict(a1=a1,a1_distinct=len(a1_values),a3_occurrences=a3_occurrences,a3_distinct=len(values),
        ranks=sorted(HammingPopulation().rank(v) for v in values),exclusion_sha256=digest.hexdigest()),final_acceptance=False)


def encode_chunk(rows):
    if type(rows) is not tuple or not 1<=len(rows)<=4096:raise ValueError('chunk bound')
    ordinal,phase,start,_=rows[0]
    integer(ordinal,0,9);integer(phase,0,1);integer(start,0,4095)
    if ordinal not in KINDS:raise ValueError('ordinal')
    body=[]
    for offset,row in enumerate(rows):
        if type(row) is not tuple or len(row)!=4 or row[:3]!=(ordinal,phase,start+offset):raise ValueError('chunk order')
        integer(row[2],0,4095)
        if type(row[3]) is not bytes or len(row[3])!=8:raise ValueError('chunk width')
        body.append(struct.pack('>I',row[2])+row[3])
    return HEADER.pack(b'HLE1OCC1',ordinal,phase,start,len(rows))+b''.join(body)


def decode_chunk(raw):
    if type(raw) is not bytes or not HEADER.size+12<=len(raw)<=HEADER.size+4096*12:raise ValueError('chunk size')
    magic,ordinal,phase,start,count=HEADER.unpack(raw[:HEADER.size])
    if magic!=b'HLE1OCC1' or not 1<=count<=4096 or len(raw)!=HEADER.size+12*count:raise ValueError('chunk header')
    rows=tuple((ordinal,phase,struct.unpack('>I',raw[i:i+4])[0],raw[i+4:i+12]) for i in range(HEADER.size,len(raw),12))
    if encode_chunk(rows)!=raw:raise ValueError('noncanonical chunk')
    return rows


class ChunkWriter:
    def __init__(self,root,plan,*,chunk_limit=64,max_bytes=128*1024):
        integer(chunk_limit,1,4096);integer(max_bytes,1,1024*1024)
        self.root=Path(root);require_plain(root,directory=True)
        if list(self.root.iterdir()):raise ValueError('new empty output required')
        self.plan=plan;self.chunk_limit=chunk_limit;self.max_bytes=max_bytes;self.failed=False;self.used=False

    def write(self,rows):
        if self.failed or self.used:raise ValueError('failed or already used writer')
        self.used=True
        durable_create(self.root/'writer.lock',b'incomplete')
        try:
            expected=iter(self.plan.positions());buffer=[];inventory={};used=0
            def flush():
                nonlocal used
                if not buffer:return
                raw=encode_chunk(tuple(buffer));used+=len(raw)
                if used>self.max_bytes:raise ValueError('output reservation exceeded')
                name=f'occ-{len(inventory)+1:08d}.bin'
                durable_create(self.root/name,raw)
                inventory[name]=dict(size=len(raw),sha256=sha256(raw).hexdigest());buffer.clear()
            for row in rows:
                if type(row) is not tuple or len(row)!=4 or row[:3]!=next(expected,None):raise ValueError('fixture ordering')
                if buffer and (row[:2]!=buffer[0][:2] or len(buffer)==self.chunk_limit):flush()
                buffer.append(row)
            if next(expected,None) is not None:raise ValueError('incomplete output')
            flush()
            manifest=dict(schema='e001-fixture-outer-manifest-v1',plan=self.plan.fingerprint,files=inventory,producer_complete=True,final_acceptance=False)
            durable_create(self.root/'manifest.json',canonical(manifest))
            self.root.joinpath('writer.lock').unlink()
            return fingerprint(manifest)
        except BaseException:
            self.failed=True;raise


def read_chunks(root,plan,pin):
    root=Path(root);require_plain(root,directory=True)
    for path in root.iterdir():require_plain(path)
    if (root/'manifest.json').stat().st_size>1024*1024:raise ValueError('manifest cap')
    raw=(root/'manifest.json').read_bytes()
    if sha256(raw).hexdigest()!=pin:raise ValueError('manifest pin mismatch')
    m=decode(raw)
    if set(m)!={'schema','plan','files','producer_complete','final_acceptance'} or m['schema']!='e001-fixture-outer-manifest-v1' or m['plan']!=plan.fingerprint or m['producer_complete'] is not True or m['final_acceptance'] is not False:raise ValueError('manifest binding/schema')
    if type(m['files']) is not dict or set(p.name for p in root.iterdir())!=set(m['files'])|{'manifest.json'}:raise ValueError('missing/unlisted evidence')
    positions=iter(plan.positions())
    for i,(name,entry) in enumerate(sorted(m['files'].items()),1):
        if name!=f'occ-{i:08d}.bin' or file_inventory(root/name)!=entry:raise ValueError('chunk identity/integrity')
        if entry['size']>HEADER.size+4096*12:raise ValueError('oversized chunk')
        for row in decode_chunk((root/name).read_bytes()):
            if row[:3]!=next(positions,None):raise ValueError('duplicate/missing/reordered occurrence')
            yield row
    if next(positions,None) is not None:raise ValueError('incomplete occurrence evidence')


class Checkpoints:
    """Immutable diagnostic checkpoints, not resumable state or acceptance."""
    def __init__(self,root,plan):self.root=Path(root);self.plan=plan
    def read(self,head=ZERO):
        require_plain(self.root,directory=True);previous=ZERO;rows=[]
        for i,path in enumerate(sorted(self.root.iterdir()),1):
            require_plain(path)
            if path.name!=f'{i:08d}.json':raise ValueError('checkpoint gap/lock/artifact')
            raw=path.read_bytes();row=decode(raw)
            if set(row)!={'schema','plan','sequence','previous','checked','status'} or row['schema']!='e001-fixture-checkpoint-v1' or row['plan']!=self.plan.fingerprint or row['sequence']!=i or type(row['sequence']) is not int or row['previous']!=previous or row['status']!='incomplete':raise ValueError('checkpoint chain')
            integer(row['checked'],0,len(self.plan.specs)*(self.plan.discovery+self.plan.validation))
            if rows and row['checked']<rows[-1]['checked']:raise ValueError('checkpoint rollback')
            rows.append(row);previous=sha256(raw).hexdigest()
        if previous!=head:raise ValueError('external checkpoint head mismatch')
        return rows
    def append(self,checked,head=ZERO):
        rows=self.read(head);integer(checked,0,len(self.plan.specs)*(self.plan.discovery+self.plan.validation))
        if rows and checked<rows[-1]['checked']:raise ValueError('checkpoint rollback')
        durable_create(self.root/'writer.lock',b'incomplete-checkpoint')
        row=dict(schema='e001-fixture-checkpoint-v1',plan=self.plan.fingerprint,sequence=len(rows)+1,previous=head,checked=checked,status='incomplete')
        raw=canonical(row);durable_create(self.root/f'{len(rows)+1:08d}.json',raw)
        self.root.joinpath('writer.lock').unlink()
        return sha256(raw).hexdigest()


def incomplete_attempt(plan,checked,error,partial_inventory):
    integer(checked,0,4096)
    if type(error) is not str or not error or type(partial_inventory) is not dict:raise ValueError('incomplete disclosure')
    for name,entry in partial_inventory.items():
        if type(name) is not str or '/' in name or '\\' in name or name in ('','.','..') or type(entry) is not dict or set(entry)!={'size','sha256'}:raise ValueError('partial inventory schema')
        integer(entry['size'],0,2**64-1);_hex(entry['sha256'],64)
    return canonical(dict(schema='e001-fixture-incomplete-v1' ,plan=plan.fingerprint,checked=checked,error=error,
                          partial_inventory=partial_inventory,status='incomplete',retry_authorized=False,final_acceptance=False))
