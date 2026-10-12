# Approved A1/A3 sub-seed encoding v1

Proposed in Architecture Review 026; **APPROVED in Architecture Review 027**.
Encoding identity: `hashlab-exp002-a1-a3-subseed-encoding-v1`. The original filename
is retained to preserve the review artifact. The exact labels and KATs below are
unchanged; production derivation interfaces now bind them to protocol identity.
No execution seed or beacon round is selected. The public integer zero below is
only a known-answer input. The frozen scientific design and `hashlab-seed-v1`
algorithm remain unchanged. This approved encoding amendment augments proposal
revision 8's protocol identity without changing its scientific design.

## Exact ordered labels

Each purpose has three ordered ASCII labels. Case, hyphens and spelling are exact.

| Purpose | Label 1 | Label 2 | Label 3 |
|---|---|---|---|
| A1 selection | `experiment-002` | `A1-lowint-w8` | `selection-v1` |
| A1 stage allocation | `experiment-002` | `A1-lowint-w8` | `stage-allocation-v1` |
| A3 selection | `experiment-002` | `A3-lowhw-w8` | `selection-v1` |
| A3 stage allocation | `experiment-002` | `A3-lowhw-w8` | `stage-allocation-v1` |

The arm labels match the existing proposal's illustrative arm ids. The two
purposes isolate selection draws from stage-allocation draws. Distinct messages
do not mathematically guarantee distinct finite 64-bit outputs, nor prove
independence of MT19937 streams; the protocol's ideal-RNG assumption remains.

## Byte and integer contract

For `m` an actual integer in `[0, 2^64-1]`, excluding booleans, define

```text
M = ASCII("hashlab-seed-v1|" + decimal(m) + "|" + label1 + "|" + label2 + "|" + label3)
H = SHA-256(M)
s = int.from_bytes(H[0:8], "big", signed=False)
```

`decimal(m)` is unsigned canonical base-ten ASCII: `0`, or digits starting with
`1`–`9`, without leading zeros, sign, exponent or separators. Reject floats,
strings, booleans and out-of-range values before calling the existing derivation.
Pipes are single byte `0x7c`; there is no BOM, NUL, whitespace or final newline.
The ASCII prefix `hashlab-seed-v1` has hex `686173686c61622d736565642d7631`.
ASCII is a subset of UTF-8, so these messages exactly reuse the existing
`derive_seed(m, label1, label2, label3)` algorithm without modifying that function.

Pass `s` as the unsigned Python integer to a local `random.Random(s)` instance.
Do not serialize it as an A2 LE64 key, truncate it, use Python `hash()`, add
another hash, or replace it with a string seed. Selection and allocation use
separate RNG instances. Production `arm_seed_labels`, `arm_seed_material` and
`arm_subseed` in `src/hashlab/experiments/exp002.py` bind this approved contract.
Sampling primitives still accept explicit engineering sub-seeds. These pure
interfaces do not choose an execution master or verify later beacon commitments.

## Complete known-answer vectors

All four use public documentation input `m=0`, never a selected execution master.

### A1 selection — 58 message bytes

```text
hashlab-seed-v1|0|experiment-002|A1-lowint-w8|selection-v1
SHA-256: ff02f20338ea39cb98778affa607d272f9c979516c76361421901fbdab97849b
H[0:8]: ff02f20338ea39cb
s: 18375515525278742987
```

### A1 stage allocation — 65 message bytes

```text
hashlab-seed-v1|0|experiment-002|A1-lowint-w8|stage-allocation-v1
SHA-256: b116da691b775b41c60880fd0f895223b0959373ef21966b585df9d0574d45f3
H[0:8]: b116da691b775b41
s: 12760626739168107329
```

### A3 selection — 57 message bytes

```text
hashlab-seed-v1|0|experiment-002|A3-lowhw-w8|selection-v1
SHA-256: c12b68881535433f5bbeced6a56b7e5b2a368b522b391eb597fc0c490028ea1b
H[0:8]: c12b68881535433f
s: 13919334006999302975
```

### A3 stage allocation — 64 message bytes

```text
hashlab-seed-v1|0|experiment-002|A3-lowhw-w8|stage-allocation-v1
SHA-256: 971224204ac801c38c554a7ea25b660c4cd0a0d3dcfbc8953c66edb0af3e05e2
H[0:8]: 971224204ac801c3
s: 10885802970420085187
```

## Independent reproduction

Reference Python, standard library only, no HASHLAB imports:

```python
from hashlib import sha256

for arm in ("A1-lowint-w8", "A3-lowhw-w8"):
    for purpose in ("selection-v1", "stage-allocation-v1"):
        message = f"hashlab-seed-v1|0|experiment-002|{arm}|{purpose}".encode("ascii")
        digest = sha256(message).digest()
        print(message.decode("ascii"), len(message), digest.hex(),
              int.from_bytes(digest[:8], "big"))
```

Independent PowerShell/.NET implementation, no HASHLAB or Python imports:

```powershell
foreach ($armLabel in @('A1-lowint-w8', 'A3-lowhw-w8')) {
    foreach ($purposeLabel in @('selection-v1', 'stage-allocation-v1')) {
        $material = "hashlab-seed-v1|0|experiment-002|$armLabel|$purposeLabel"
        $engine = [System.Security.Cryptography.SHA256]::Create()
        $digest = $engine.ComputeHash([Text.Encoding]::ASCII.GetBytes($material))
        $engine.Dispose()
        $firstEight = [byte[]]$digest[0..7]
        if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($firstEight) }
        $value = [BitConverter]::ToUInt64($firstEight, 0)
        $hex = [BitConverter]::ToString($digest).Replace('-', '').ToLowerInvariant()
        "$material $hex $value"
    }
}
```

Both implementations were run during Review 026 and agree on all four full
digests and unsigned integers. A separate check against existing `derive_seed`
also agrees. No candidate hashes were evaluated. Architecture Review 027 approves
binding the exact contract into production identity. Regression tests now verify
all four complete messages, lengths, full digests and derived integers against
the bound interfaces. No execution master or beacon value was selected.
