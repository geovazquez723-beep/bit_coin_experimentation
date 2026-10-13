# E002-I2 control byte specification — decision proposal

Status: **Director-approved for D1–D5**, by the human Research Director's
subsequent E002-I2 implementation request supplied in this chat. The approval
authorizes implementation and bounded synthetic qualification only. Binding
clarifications: C1 is exactly `2^20 <= x < 2^32`; C3 remains the complete
structural class. N1 source indices must be strictly below 30,999,999, with
fail-closed exhaustion. The proposed transformations and exact floor-quantized
effects are approved. No protocol freeze, research execution, QA2, historical
reconstruction or production seed selection is authorized.

Original proposal prepared 2026-10-12 against branch
`feat/e002-i2-controls`, HEAD `3167c4ce66adabcc22743d99fc76e4f57316a711`.
This document resolves specification questions only; it authorizes no implementation,
protocol freeze, QA2, historical reconstruction or experiment execution.

## Authority and what is already fixed

Repository-relative sources below identify authority separately from precedent:

| Source | Relevant requirements/status |
|---|---|
| [Rev8](experiment-002-research-design.md), §3.2 “Null and positive controls”, §§3.3, 3.7, 3.8 S4, 3.12 | Scientific authority: N1 six-round keyed 64-bit BLAKE2b Feistel and inverse; reject structural classes and E001; first 15M accepted D, next 15M V. N2 keyed 80-byte stream, reject A2, 1,500 pseudo-clusters of 10,000 per stage. P use the same permutation, indices starting at 2^63, same rejections, biased engine: P1 +25%/200,000; P2+ +2%/15M; P2− −2%/15M. |
| [Rev9 policy](experiment-002-solo-governance-revision-9.md), I05–I08, I14, M06/M11; [Director adoption](../reviews/architecture-review-043-director-revision-9-adoption.md) | Rev9 was adopted by the separate Director record; the policy's preserved proposal-era header is historical. Scientific baseline remains Rev8. No scientific substitution, reduced counts or synthetic replacement of controls. |
| [Approved A1/A3 encoding](experiment-002-a1-a3-seed-encoding-proposal.md); Rev8 §3.2 A2 encoding and [addendum](../reviews/experiment-002-protocol-readiness-addendum.md) §9 | Their exact labels/bytes are approved **for those arms**. They do not freeze N1/N2/P labels or keys. Rev8 S4 preserves `hashlab-seed-v1` derivation. |
| `src/hashlab/candidates/base.py::derive_seed`; `src/hashlab/candidates/random.py::RandomBytesGenerator.stream` | Accepted implementation precedent: ASCII decimal master and pipe-separated labels; SHA-256 first eight raw bytes interpreted BE. Random-byte generator uses BE128 key and counter, 64-byte keyed BLAKE2b blocks, continuous width-byte slicing. Its generic runner deduplication and phase restart are not E002 requirements. |
| `src/hashlab/experiments/exp002.py::{in_a1,in_a3,a2_key,a2_prefix}` | Accepted arm predicates and A2 bytes; A2's LE64 key is a precedent, not authority for a control key. No control-specific seed binding or Feistel exists here. |
| `src/hashlab/experiments/controls.py::BiasedControlEngine` | Existing positive-only transformation and floor-quantized U32 selector are completely derivable; negative lift is rejected. No accepted P2− transformation. |
| `src/hashlab/experiments/exp002_foundation.py::{Plan,CandidateRecord,LIMITS}`; `src/hashlab/statistics/exp002.py::controls` | Accepted sample/record and count-only statistical contracts. Records use stage-local accepted indices and global A2/N2 cluster numbers. These are not implementations of the control generators. |

Preserve SHA-256, digest BE integer `v < T = 2^248`, `p0 = 1/256`, all
sample counts, and all approved effects. P1 detection is one-sided `p < .001`;
at least one P2 must be detected and neither P2 may be `WITHIN` under the
15M Clopper–Pearson margin rule. Accepted detection boundaries are P1 `k >= 870`,
P2+ `k >= 59343`, P2− `k <= 57848`. Null D/V procedures and replicated-null
failure remain unchanged; N2 retains A2's CP/t hull with 2,999 df. Nothing here
replaces the frozen nine-cell rules or changes alpha allocation.

## Proposed byte definitions

`BEw(x)`/`LEw(x)` denote exactly w-byte unsigned encodings; reject out-of-range
values rather than truncate. Hex denotes raw bytes, not ASCII hex. BLAKE2b below
always means keyed BLAKE2b-512: digest_size=64, fanout=1, depth=1, leaf_size=0,
node_offset=0, node_depth=0, inner_size=0, last_node=false, zero salt and
personalization. No HMAC, implicit NUL, newline or key-prepending.

### D1 — control labels, keys and domain separation

**Fixed:** existing `hashlab-seed-v1` derivation. **Missing:** control labels,
purpose labels, key bytes and whether P has separate keys. **Recommendation:**

```text
H(m,d,a,p) = SHA256(ASCII("hashlab-seed-v1|" + decimal(m) + "|" + d + "|" + a + "|" + p))
s(m,d,a,p) = unsigned-BE-integer(H(m,d,a,p)[0:8])
K_N = LE8(s(m,d,"N1-feistel64-w8","permutation-key-v1"))
K_2 = BE16(s(m,d,"N2-random-bytes-w80","stream-key-v1"))
```

Master range is `[0,2^64)`; decimal is canonical with no sign/leading zeros
(zero is `0`). Production d is exactly `experiment-002`; fixture d is exactly
`experiment-002-kat`. No caller-selected production labels or per-stage keys.
P1/P2+/P2− reuse **K_N and the same permutation**; separate P keys would destroy
the approved disjoint-index bijection argument. The two key widths deliberately
follow different precedents and are newly proposed control bindings.

Alternative: BE8 for K_N or LE8 for K_2; equally deterministic, different KATs
and candidates. Impact: new control replay identity; no change to existing
A1/A2/A3 keys, master derivation, commitments or frozen configuration. Director
approval required for labels/domain/key bindings; no production seed is chosen.

### D2 — N1 Feistel and inverse

**Fixed:** 64-bit permutation, six BLAKE2b rounds and a real inverse.
**Missing:** halves, round numbering, message, digest extraction and output swap.
**Recommendation:** for `0 <= i < 2^64`, initialize
`L0 = i >> 32`, `R0 = i mod 2^32`. For r=0,...,5:

```text
M_r(R) = ASCII("hashlab-exp002-feistel-round-v1") || BE1(r) || BE4(R)   # 36 bytes
F_r(R) = unsigned-BE-integer(BLAKE2b-512(key=K_N, message=M_r(R))[0:4])
(L_(r+1), R_(r+1)) = (R_r, L_r XOR F_r(R_r))
pi_N(i) = 2^32 * L6 + R6
candidate(i) = BE8(pi_N(i))
```

No final swap, cycle walking, round-key derivation or reduction of the 64-bit
domain. Inverse starts with `(L6,R6)` from the value's high/low halves and, for
r=5,...,0, replaces `(L,R)` with `(R XOR F_r(L), L)`, then returns `2^32*L+R`.
Each round is bijective by this equation, regardless of PRP quality.

Alternative: LE halves/messages, a final swap, or BLAKE2b digest_size=4 instead
of truncating the 64-byte digest. All change the permutation; digest_size=4 is
not an equivalent BLAKE2b call. Impact: fixes candidate replay and inverse audit
bytes while preserving the approved construction/PRP assumption. Director
approval required; no accepted Feistel code resolves these choices.

### D3 — N1/P exclusions and index allocation

**Fixed:** structural predicate rejection, inverse-index E001 check over every
one of the 7M historical 8-byte candidates, ascending N1 indices, accepted-order
D/V split, shared P permutation and disjoint indices at/above 2^63.
**Ambiguity:** Rev8 calls the low-integer reject class `C1` without defining that
symbol elsewhere; §3.2 defines `U1`, and accepted `in_a1` tests U1. **Recommend
explicit Director clarification** that the predicate is `2^20 <= x < 2^32`,
with x read from BE8. C3 is exactly `x >> 32 != 0 and HW(x) <= 6`, including
the full class, not only the eligible A3 population after historical exclusions.
The alternative `x < 2^32` excludes additional candidates and must not be
silently substituted. This clarification can change control bytes, not arm sets.

For each historical raw 8-byte candidate h, use `x = unsigned-BE-integer(h)`
and store/compare `j = pi_N_inverse(x)` as an unsigned 64-bit **source index**.
Do not compare x with an index, reinterpret historical bytes as LE, or regenerate
history under this proposal. Repeated historical occurrences map to the same
skip index; retain occurrence/audit counts separately from unique skip indices.
For every attempted source i, reject if its inverse skip index is present or
its output meets either structural predicate; accept otherwise. Record all
applicable reasons (and count each rejected attempt once). An unhandled hit
retains the frozen failure behavior.

**Missing:** exact P-to-P allocation. **Recommend:** one ascending cursor starting
at b=2^63: fill P1 with 200,000 accepted values, then P2+ with 15M, then P2− with
15M. Every attempted index, including rejection, advances the cursor; the next
control starts after the last attempted index of its predecessor. This proves
pairwise P uniqueness and disjointness without guessing a rejection allowance.
Use the same skip-index set for N1 and all P. N1 starts at zero, fills 15M D
then 15M V, and never resets between stages. Rejections consume no accepted
index. Record indices remain stage-local accepted ordinals as in CandidateRecord;
source indices/cursor and rejection totals are separate replay/audit information.

Rev8 states N1 uses fewer than 31M indices. Recommend fail closed before consuming
the 31,000,000th index: index 30,999,999 or later is forbidden (maximum allowed
attempted index is 30,999,998), reporting failure rather than extending/reseeding. P fails closed
at 2^64 without wrap; neither failure reduces the required sample sizes. Treat
this enforcement of the stated N1 bound as an approval item, not a new guarantee
that every key fills the quota. Alternative: predefined P subranges with explicit
exhaustion handling; changes candidates and needs separately approved bounds.
Impact: preserves bijection guarantees and counts; fills missing cursor/failure
semantics. Director approval required for C1, P ordering and bound handling.

### D4 — N2 stream, rejection and pseudo-clusters

**Fixed:** 80-byte keyed BLAKE2b stream, A2 membership rejection, stream-order
clusters and 15M accepted per stage. **Missing:** expansion/counter/key and
restart/buffer boundaries. **Recommend adopting the existing generator bytes**:

```text
B_c = BLAKE2b-512(key=K_2, message=BE16(c)),  c=0,1,...,2^128-1
S = B_0 || B_1 || ...
raw_candidate(t) = S[80*t : 80*(t+1)]
```

There is no block padding between candidates, discarded block tail, stage
restart or separate cluster stream. Reject counter exhaustion before an
incomplete candidate; never wrap. Seek/replay by byte offset 80*t; an accepted
ordinal alone does not identify that offset after rejections.

For every complete raw candidate z, reject iff `z[0:76]` belongs to the complete
approved set of 3,000 A2 prefixes **and** `unsigned-LE-integer(z[76:80]) < 10000`.
This predicate is already derivable from approved A2 encoding. Rejects consume
the entire 80-byte raw candidate, are counted and do not consume an accepted
ordinal. Continue the same stream until 30M accepted. For global accepted ordinal
q: D iff q<15M, else V; stage-local index `q mod 15M`, global cluster `q // 10000`,
within-cluster position `q mod 10000`. Thus the cluster rule is derivable from
the accepted record contract; no random allocation is needed.

Do **not** deduplicate N2 within/across stages or against itself: Rev8 §3.3
explicitly leaves uniqueness unverified with birthday bound
`C(30,000,000,2)/2^640 ≈ 2^-591`, under the stated random-stream model. The
required A2 rejection remains; the pseudorandomness and negligible-collision
statements remain assumptions, not exact guarantees. Generic runner deduplication
would change this contract. Alternative: two blocks per candidate with tails
discarded, or per-stage streams; different bytes without current approval.
Impact: new deterministic binding of existing design, no new deduplication rule.
Director approval required for stream/key/boundary adoption; membership and
accepted cluster mapping need no new scientific decision.

### D5 — P1/P2+ lift and P2− suppression

Let supplied base digest d be exactly 32 bytes, `v = unsigned-BE-integer(d)`,
`u = unsigned-BE-integer(d[28:32])`, `U=2^32`. Base engine remains SHA-256;
the following definitions act on its digest, not on candidate generation.

**Positive precedent, recommend adoption unchanged:** for lift l=1/4 or 1/50,
`a = floor(U*l/255)`. If `v >= T and u < a`, return `BE32(v mod T)`;
otherwise return d unchanged. Existing `Fraction(relative_lift).limit_denominator(10^12)`
recovers these rationals for .25 and .02; specifying rational arithmetic avoids
port-dependent floating comparisons. Existing successes are never modified.

**Negative gap, new recommendation:** for suppression fraction l=1/50,
`a_minus = floor(U/50)`. If `v < T and u < a_minus`, return `BE32(v+T)`;
otherwise return d unchanged. At this T the suppressed digest's first byte changes
from 00 to 01 and the remaining 31 bytes are preserved. No overflow, reroll,
extra hash, candidate edit or change to already unsuccessful digests. `v=T`
is unsuccessful and remains unchanged in P2−. Selector equality never transforms.

Under the ideal uniform base-digest model, top-byte success and the low U32
selector are independent at this power-of-two T. Exact quantized probabilities:

| Control | Selector threshold a (decimal / BE4 hex) | Success probability | Realized relative effect |
|---|---|---|---|
| P1 | 4210752 / `00404040` | `83886079/17179869184` | `16777215/67108864` |
| P2+ | 336860 / `000523dc` | `1095216649/274877906944` | `21474825/1073741824` |
| P2− | 85899345 / `051eb851` | `4209067951/1099511627776` | `-85899345/4294967296` |

For positives `p = p0+(1-p0)*a/U`; for negative `p=p0*(1-a_minus/U)`.
Requested effects remain +25%, +2%, −2%. Realized magnitudes fall short by,
respectively, `1/67108864`, `287/26843545600`, `23/107374182400` in relative
probability units. Do not report these quantized values as exact rational lifts
of 1/4 or ±1/50. Positive quantization is existing precedent; adopting it for
E002 and accepting negative quantization requires explicit Director compatibility
approval. Do not alter the frozen margin endpoints to match these tiny offsets.

Alternatives requiring a decision: suppress to a fixed failing digest (same
success count, different digest diagnostics), ceil/nearest threshold (different
probability), or a larger/exact selector (changes the engine and positive
precedent; exact 1/50 cannot be represented by a fixed binary threshold).
Impact: new negative engine semantics, preserved nominal effects and statistical
gates; this proposal does not authorize changing the existing positive-only API.

## Proposed known-answer vectors

These are specification KATs, not experiment evidence. Only public fixture zero
in the existing `experiment-002-kat` domain was used. SHA-256 below derives
fixture key material only; BLAKE2b calculates these small byte fixtures. No
research-candidate SHA-256, production seed, history enumeration or QA2 was run.

### Key derivation and N1

Exact ASCII messages (no newline), full derivation digest, subseed and key:

```text
hashlab-seed-v1|0|experiment-002-kat|N1-feistel64-w8|permutation-key-v1
H = 7dc843c837e35f21e983a668b40bf73fa32c5b6689757f5f90befce993f6396e
s = 9063568777293291297
K_N = 215fe337c843c87d

hashlab-seed-v1|0|experiment-002-kat|N2-random-bytes-w80|stream-key-v1
H = 256aba5e63d013c139d364eb1aaf8d33b244229077005fa7ec5dcd1ccf83419b
s = 2696172241498936257
K_2 = 0000000000000000256aba5e63d013c1
```

For N1 round r=0, R=0:

```text
M = 686173686c61622d6578703030322d6665697374656c2d726f756e642d76310000000000
BLAKE2b = 22c4ea33018741ff7a99241949a892d44e8060d567f467099379b15356a74ccea43b566d7eb9951001a5e1b315e455709c0c751d0c850826bee607ae02c0cb93
F = 22c4ea33
```

| Source i as BE8 hex | Candidate BE8 hex | Inverse of candidate (BE8 hex) |
|---|---|---|
| `0000000000000000` | `91e3cb22ac8c8eef` | `0000000000000000` |
| `0000000000000001` | `88cc10e00103efb3` | `0000000000000001` |
| `0123456789abcdef` | `edc1a6ceb00cf3f5` | `0123456789abcdef` |
| `8000000000000000` | `2169c0539d09e12a` | `8000000000000000` |
| `ffffffffffffffff` | `b5e9d7a3edc0b59e` | `ffffffffffffffff` |

For i=0, `(L_r||R_r)` after each round in order:
`0000000022c4ea33`, `22c4ea33f353df1f`, `f353df1fa8d9106b`,
`a8d9106be4b86d5d`, `e4b86d5d91e3cb22`, `91e3cb22ac8c8eef`.
These five inverse results were checked by reversing all six rounds.

Injected-history KAT: a fixture containing raw candidate `2169c0539d09e12a`
must yield skip index 2^63, including when that fixture candidate occurs twice;
P rejects source 2^63 once, while audit occurrence count is two. This is not a
claim that the byte string occurs in E001. Predicate KATs: BE8(2^20−1) is not
C1, BE8(2^20) is C1, BE8(2^32−1) is C1, BE8(2^32) is C3, and
`ffffffffffffffff` is neither. This distinguishes the unresolved C1 alternative.

Allocation KAT (injected small quotas 2/2/2, sole rejection b+1): P1 accepts
sources b,b+2; P2+ b+3,b+4; P2− b+5,b+6; next cursor b+7. For N1 quotas
2 D/2 V with sole rejection 1: D sources 0,2; V sources 3,4. These are cursor
fixtures, not production count overrides or measured rejection outcomes.

### N2 expansion, membership and allocation

With K_2 above, counter messages 0 and 1 are respectively
`00000000000000000000000000000000` and `00000000000000000000000000000001`.
The first three complete raw 80-byte candidates are:

```text
t=0
38e16fae6d0d050bae5563bb522d74bc271ebff447debfb20132bc3cb71f4e9bf3e306906421786de857521aaf56d957689efae9308419fc2c2fbdd8db5c376e5d891954273eff8476e73caf6b59fcfe
t=1
d00a2761d537388a0f57bc4cddbba3c29f90f69c35e1d572c1a4fb0af27e472279bcddfaae653abd4f7419417e69f97f86799ec7d3a9385c64fed68e1089ea860ad2fb64ecd27c4a85dcbc74d62b0d56
t=2
c2b5825914d5b1f9d35046e2ad9c10f7030282029bf5b440db294fb6282f2fe32cafb1abd632cdcf63cf67b36c8d96f631d10f4dccbc8ddc87f968a1d19ed8fccb5477eb33652d9a9b8d570e31d24fd5
```

The slices are `B0||B1[0:16]`, `B1[16:64]||B2[0:32]`, and
`B2[32:64]||B3[0:48]`. Thus the vectors test retained block tails, not just a
single-block digest. With an injected prefix set containing `00` repeated 76
times: that prefix followed by `00000000` or `0f270000` rejects; followed by
`10270000` accepts; `01 || 00*75 || 00000000` accepts (prefix absent).

Accepted q=9999 maps to D/index9999/cluster0/position9999; q=10000 to
D/index10000/cluster1/position0; q=14,999,999 to D/index14,999,999/cluster1499/
position9999; q=15,000,000 to V/index0/cluster1500/position0; q=29,999,999 to
V/index14,999,999/cluster2999/position9999. A rejected raw draw at any boundary
leaves that accepted assignment pending. Injecting A2 membership for t=0 makes
t=1 the first accepted candidate, D/index0/cluster0; its raw offset stays 80.

### Digest transformation boundaries

Exact byte KAT notation: `00^n` means n zero bytes, concatenation is `||`, and
`BE4(a)` is the four-byte hex threshold from the probability table. Supply
these digests directly; no candidate hashing is needed.

| Mode | Supplied 32-byte digest | Returned digest |
|---|---|---|
| Each positive, its own a | `01 || 00^27 || BE4(a−1)` | `00^28 || BE4(a−1)` |
| Each positive, its own a | `01 || 00^27 || BE4(a)` | unchanged |
| Each positive | `00^32` (v=0) | unchanged |
| Each positive | `01 || 00^31` (v=T,u=0) | `00^32` |
| Each positive | `00 || ff^31` (v=T−1) | unchanged |
| P2− | `00^28 || 051eb850` | `01 || 00^27 || 051eb850` |
| P2− | `00^28 || 051eb851` | unchanged |
| P2− | `00^32` | `01 || 00^31` (exactly T, fails strict target) |
| P2− | `00 || ff^31` (v=T−1,u=U−1) | unchanged |
| P2− | `01 || 00^31` (v=T) | unchanged |
| All modes | `ff^32` | unchanged |

## Approval table and remaining alternatives

The table below retains the original decision questions and alternatives as
historical context. **D1–D5 are now approved**, including the two binding
clarifications in the status above. Approval establishes these control byte
conventions and authorizes only the separately scoped I2 implementation and
bounded qualification; it grants no research execution permission.

| Decision | Director approval required | What remains open until recorded |
|---|---|---|
| D1 control seed labels/domains and LE8/BE16 keys; shared P key | Yes | Exact bindings; alternative key encodings |
| D2 six-round half/message/extraction/output layout and inverse | Yes | Recommended Feistel versus alternate byte layouts |
| D3 C1 clarification, sequential P1/P2+/P2− cursor and bound handling | Yes | U1 predicate versus broader low-int class; sequential versus bounded subranges; explicit failure at stated N1 bound |
| D4 continuous N2 BE128 counter stream and stage boundary retention | Yes | Adopt generic generator bytes versus per-candidate expansion; no stage restart |
| D5 adopt existing positive transformation/quantization; negative v+T suppression and floor quantization | Yes | Exact failing-digest construction; compatibility of realized quantized effects with nominal approved lifts |
| A2 membership, accepted-order stage/cluster record mapping, unchanged counts/target/gates; no N2 deduplication | No new choice | Already approved or directly derivable; must be preserved |

At original proposal delivery, no control implementation, source/test/statistical edit, historical work, new
seed/beacon/commitment, QA2 or E002 execution accompanies this proposal. KATs
were calculated only for the proposed conventions, using standard-library
hashlib and exact integer/Fraction arithmetic. They qualify neither production
control integration nor experiment readiness. Leave this document unstaged and
uncommitted for Research Director review. Subsequent implementation/qualification
is separately documented; the frozen Rev8/Rev9 protocols remain unchanged.
