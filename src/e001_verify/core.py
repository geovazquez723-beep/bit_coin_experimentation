"""Independent MT specification: 624 words, int seed little-endian 32-bit limbs.

init_by_array constants 19650218,1664525,1566083941; twist M=397 and
0x9908b0df; temper 11,7/0x9d2c5680,15/0xefc60000,18. getrandbits uses
high bits for short words and little-endian word assembly for multiword draws.
Compatibility with original CPython binaries remains unqualified.
"""
from hashlib import blake2b, sha256
from itertools import product, islice
from math import comb

MASK=(1<<32)-1

class MT19937:
    def __init__(self,seed):
        if type(seed) is not int or not 0<=seed<2**64:raise ValueError('fixture integer seed')
        key=[seed&MASK]
        if seed>>32:key.append(seed>>32)
        a=[19650218]
        for i in range(1,624):a.append((1812433253*(a[-1]^(a[-1]>>30))+i)&MASK)
        i=1;j=0
        for _ in range(max(624,len(key))):
            a[i]=((a[i]^((a[i-1]^(a[i-1]>>30))*1664525))+key[j]+j)&MASK
            i+=1;j+=1
            if i>=624:a[0]=a[623];i=1
            if j>=len(key):j=0
        for _ in range(623):
            a[i]=((a[i]^((a[i-1]^(a[i-1]>>30))*1566083941))-i)&MASK
            i+=1
            if i>=624:a[0]=a[623];i=1
        a[0]=0x80000000
        self.a=a;self.index=624

    def word(self):
        if self.index==624:
            for i in range(624):
                y=(self.a[i]&0x80000000)|(self.a[(i+1)%624]&0x7fffffff)
                self.a[i]=self.a[(i+397)%624]^(y>>1)^(0x9908b0df if y&1 else 0)
            self.index=0
        y=self.a[self.index];self.index+=1
        y^=y>>11;y^=(y<<7)&0x9d2c5680;y^=(y<<15)&0xefc60000;y^=y>>18
        return y&MASK

    def getrandbits(self,k):
        if type(k) is not int or not 0<=k<=128:raise ValueError('fixture bit width')
        out=0
        for shift in range(0,k,32):
            bits=min(32,k-shift)
            out|=(self.word()>>(32-bits))<<shift
        return out


def _stream(kind,seed=None):
    """Eight-byte synthetic streams matching the historical algorithms."""
    if kind=='uniform':
        rng=MT19937(seed)
        while True:yield rng.getrandbits(64).to_bytes(8,'big')
    elif kind=='random_bytes':
        counter=0
        while True:
            block=blake2b(counter.to_bytes(16,'big'),key=seed.to_bytes(16,'big'),digest_size=64).digest()
            for i in range(0,64,8):yield block[i:i+8]
            counter+=1
    elif kind=='patterned':
        for length in (1,2,3):
            for motif in product(range(256),repeat=length):
                raw=(bytes(motif)*8)[:8]
                if all(any(raw[j]!=raw[j%p] for j in range(8)) for p in range(1,length)):
                    yield raw
    else:
        for i in range(2**64):
            if kind=='sequential':v=i
            elif kind=='gray':v=i^(i//2)
            elif kind=='stride':v=(11400714819323198485*i)%(2**64)
            elif kind=='bit-reversed':v=sum(((i>>j)&1)<<(63-j) for j in range(64))
            else:raise ValueError('unsupported independent stream')
            yield v.to_bytes(8,'big')


def classify(values):
    a1=0;eligible=set();a1_values=set();a3_occurrences=0
    for i,raw in enumerate(values):
        if i>=4096 or type(raw) is not bytes or len(raw)!=8:raise ValueError('fixture limit/width')
        v=int.from_bytes(raw,'big');a1+=int(2**20<=v<2**32)
        if 2**20<=v<2**32:a1_values.add(v)
        if v>>32 and 1<=v.bit_count()<=6:eligible.add(v);a3_occurrences+=1
    ranks=[]
    for v in eligible:
        w=v.bit_count();rank=sum(comb(64,k)-comb(32,k) for k in range(1,w))-comb(32,w)
        remaining=w
        for b in range(63,-1,-1):
            if (v>>b)&1:
                if b>=remaining:rank+=comb(b,remaining)
                remaining-=1
        ranks.append(rank)
    digest=sha256()
    for v in sorted(eligible):digest.update(v.to_bytes(8,'big'))
    return dict(a1=a1,a1_distinct=len(a1_values),a3_occurrences=a3_occurrences,a3_distinct=len(eligible),ranks=sorted(ranks),exclusion_sha256=digest.hexdigest())


def verify_rows(specs,discovery,validation,seeds,rows):
    if type(discovery) is not int or type(validation) is not int or min(discovery,validation)<0 or not 1<=len(specs)*(discovery+validation)<=4096:
        raise ValueError('independent fixture geometry')
    allowed={0:'sequential',2:'uniform',4:'patterned',6:'gray',7:'stride',8:'bit-reversed',9:'random_bytes'}
    if type(specs) is not tuple or any(type(s) is not tuple or len(s)!=2 or type(s[0]) is not int or allowed.get(s[0])!=s[1] for s in specs):raise ValueError('independent identities')
    ordinals=[s[0] for s in specs]
    if ordinals!=sorted(set(ordinals)):raise ValueError('independent ordering')
    if type(seeds) is not tuple or len(seeds)!=2 or any(type(v) is not int or not 0<=v<2**64 for v in seeds):raise ValueError('independent fixture keys')
    rows=iter(rows);values=[];accounting=[];provenance={}
    for ordinal,kind in specs:
        seen={};continuing=None
        if kind not in ('uniform','random_bytes'):continuing=_stream(kind)
        for phase,count in enumerate((discovery,validation)):
            source=_stream(kind,seeds[phase]) if continuing is None else continuing
            within=cross=unique=0
            for index,expected in enumerate(islice(source,count)):
                try:row=next(rows)
                except StopIteration:raise ValueError('missing independent occurrence') from None
                if type(row) is not tuple or len(row)!=4 or any(type(v) is not int for v in row[:3]) or type(row[3]) is not bytes or row!=(ordinal,phase,index,expected):raise ValueError('independent bytes/order mismatch')
                previous=seen.get(expected)
                if previous is None:seen[expected]=(phase,index);unique+=1
                elif previous[0]!=phase:cross+=1
                else:within+=1
                values.append(expected)
                v=int.from_bytes(expected,'big')
                if v>>32 and 1<=v.bit_count()<=6:
                    if v not in provenance:provenance[v]=dict(value_hex=expected.hex(),ordinal=ordinal,phase=phase,index=index,occurrences=0)
                    provenance[v]['occurrences']+=1
            accounting.append(dict(ordinal=ordinal,phase=phase,attempted=count,unique=unique,within=within,cross=cross))
    if next(rows,None) is not None:raise ValueError('extra independent occurrence')
    return dict(schema='e001-independent-fixture-report-v1',scope='synthetic-only',
                accounting=accounting,membership=classify(values),a3_provenance=[provenance[v] for v in sorted(provenance)],final_acceptance=False)
