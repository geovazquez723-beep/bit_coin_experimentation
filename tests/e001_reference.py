"""Independent bounded historical references; no adapter or HASHLAB imports."""
import hashlib
import itertools
import random

SEEDS={
 'uniform-be-w8':(11563638942429927757,17448145370022348540),
 'uniform-dec-w16':(4510579110814029430,7646975460325050960),
 'random-bytes-w8':(710289665967761509,8231496708541735395),
}

def reference(gid,phase,start,count):
    pi=('discovery','validation').index(phase)
    offset=500000*pi if gid not in SEEDS else 0
    if gid in SEEDS:
        seed=SEEDS[gid][pi]
        if gid=='random-bytes-w8':
            first=start//8; last=(start+count+7)//8
            raw=b''.join(hashlib.blake2b(i.to_bytes(16,'big'),key=seed.to_bytes(16,'big'),digest_size=64).digest() for i in range(first,last))
            shift=(start%8)*8
            return [raw[shift+8*i:shift+8*(i+1)] for i in range(count)]
        rng=random.Random(seed)
        draws=[rng.getrandbits(64).to_bytes(8,'big') if gid=='uniform-be-w8'
               else str(rng.randrange(10**16)).zfill(16).encode('ascii') for _ in range(start+count)]
        return draws[start:]
    def encode(i):
        if gid=='seq-be-w8': return i.to_bytes(8,'big')
        if gid=='seq-dec-w16': return str(i).zfill(16).encode('ascii')
        if gid=='struct-gray-w8': return (i^(i//2)).to_bytes(8,'big')
        if gid=='struct-stride-w8': return ((11400714819323198485*i)%(2**64)).to_bytes(8,'big')
        if gid=='struct-bitrev-w8': return sum(((i>>k)&1)<<(63-k) for k in range(64)).to_bytes(8,'big')
        raise ValueError(gid)
    if not gid.startswith('pattern-'): return [encode(i) for i in range(offset+start,offset+start+count)]
    alphabet=range(256) if gid=='pattern-bytes-w8' else range(32,127)
    width=8 if gid=='pattern-bytes-w8' else 16
    result=[]; ordinal=0
    for period in range(1,4 if width==8 else 5):
        for motif in itertools.product(alphabet,repeat=period):
            raw=(bytes(motif)*width)[:width]
            # Direct definition, independent of production KMP and Mobius code.
            minimum=next(p for p in range(1,width+1) if all(raw[j]==raw[j%p] for j in range(width)))
            if minimum!=period: continue
            if start<=ordinal<start+count: result.append(raw)
            ordinal+=1
            if ordinal==start+count:return result
    return result


def rank_reference(raw):
    """Independent count of eligible values earlier in (weight,numeric) order."""
    from math import comb
    v=int.from_bytes(raw,'big'); weight=v.bit_count()
    assert len(raw)==8 and v>>32 and 1<=weight<=6
    prior=sum(comb(64,k)-comb(32,k) for k in range(1,weight))
    # Combinatorial count of same-weight values numerically below v.
    lower=0; remaining=weight
    for bit in range(63,-1,-1):
        if (v>>bit)&1:
            lower+=comb(bit,remaining) if bit>=remaining else 0
            remaining-=1
    # All same-weight values confined to low 32 bits precede v.
    return prior+lower-comb(32,weight)
