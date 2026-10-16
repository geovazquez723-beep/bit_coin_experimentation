"""Present-baseline comparison of the local E001 qualification snapshots (G1-C).

The snapshots under ``results-smoke/`` are point-in-time working-checkout inventories (not
historical provenance).  The sealed E001 evidence must still match them exactly; the wider
protected working-tree inventory legitimately evolved, so each file must be unchanged, differ only
by CRLF/LF checkout conversion, or appear in ``fixtures/e001-present-baseline-v1.json`` with its
exact current LF-normalised hash.  Any other change is reported.
"""
from hashlib import sha256
from pathlib import Path
import json

BASELINE = Path(__file__).parent / "fixtures" / "e001-present-baseline-v1.json"


def compare_snapshot(before: dict, baseline: dict, root: Path = Path(".")) -> list[str]:
    problems = []
    for name, entry in before["sealed"].items():
        path = root / name
        if not path.is_file():
            problems.append(f"sealed missing: {name}")
            continue
        st = path.stat()
        if (st.st_size != entry["size"] or st.st_mtime_ns != entry["mtime_ns"]
                or sha256(path.read_bytes()).hexdigest() != entry["sha256"]):
            problems.append(f"sealed changed: {name}")
    superseded = baseline["superseded_since_snapshot"]
    for name, entry in before["protected"].items():
        path = root / name
        if not path.is_file():
            problems.append(f"protected missing: {name}")
            continue
        raw = path.read_bytes()
        if sha256(raw).hexdigest() == entry["sha256"]:
            continue
        lf = sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        if lf == entry["sha256"]:
            continue
        pinned = superseded.get(name.replace("\\", "/"))
        if pinned is None or pinned["current_lf_sha256"] != lf:
            problems.append(f"protected changed outside present baseline: {name}")
    return problems


def check_snapshot_file(snapshot: Path) -> list[str]:
    if not snapshot.exists():
        return []
    return compare_snapshot(json.loads(snapshot.read_text()), json.loads(BASELINE.read_text()))
