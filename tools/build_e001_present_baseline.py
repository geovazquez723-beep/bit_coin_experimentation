"""Build tests/fixtures/e001-present-baseline-v1.json from a local qualification snapshot (G1-C).

Records, for every protected-inventory file whose current content differs from the
snapshot beyond CRLF/LF, the CURRENT LF-normalised SHA-256.  The snapshot itself is only read.
Run from the repository root:  python tools/build_e001_present_baseline.py SNAPSHOT.json OUT.json
"""
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys


def main(snapshot: str, out: str) -> int:
    before = json.loads(Path(snapshot).read_text())
    superseded = {}
    for name, entry in before["protected"].items():
        raw = Path(name).read_bytes()
        if sha256(raw).hexdigest() == entry["sha256"]:
            continue
        lf = sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        if lf != entry["sha256"]:
            superseded[name.replace("\\", "/")] = {"snapshot_sha256": entry["sha256"], "current_lf_sha256": lf}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    doc = {"schema": "hashlab-e001-present-baseline-v1", "recorded_at_head": head,
           "snapshot": Path(snapshot).as_posix(), "snapshot_sha256": sha256(Path(snapshot).read_bytes()).hexdigest(),
           "superseded_since_snapshot": dict(sorted(superseded.items()))}
    Path(out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
