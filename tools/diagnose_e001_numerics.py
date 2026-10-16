"""Read-only diagnostic of the 86 E001 secondary-test numerical differences (G1-C).

Re-runs the pure historical analysis on the sealed ``results.json``/``config.resolved.json``
(no candidate generation, no hashing, no E001 enumeration) and compares every float in the
result with the sealed ``analysis.json`` by exact IEEE-754 bit pattern.  No tolerance is used.

    python diagnose_e001_numerics.py run --src SRC_ROOT --out OUT.json [--naive-sum] [--config-order]
    python diagnose_e001_numerics.py compare --run OUT.json [--run OUT2.json ...]

``--naive-sum`` shadows ``sum`` inside ``hashlab.statistics.distribution`` with a strict left
fold (the CPython <= 3.11 float ``sum`` algorithm).  It exists only to test the cause hypothesis;
it changes nothing on disk.  Output is refused if it would be written inside ``results/``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
import sys
from pathlib import Path

SEALED = Path(__file__).resolve().parents[1] / "results" / "20261011T205056Z-exp001-fc1d75fc"


def _naive_sum(iterable, start=0):
    total = start
    for item in iterable:
        total = total + item
    return total


def _bits(x: float) -> str:
    return struct.pack(">d", x).hex()


def _keyed(analysis: dict) -> tuple[dict, list]:
    """Return a copy with ``secondary_tests`` keyed by (generator, phase, test) and the original order."""
    rows = analysis.get("secondary_tests", [])
    keys = [f'{r["generator"]}|{r["phase"]}|{r["test"]}' for r in rows]
    if len(set(keys)) != len(keys):
        raise SystemExit("duplicate secondary-test keys")
    copy = dict(analysis)
    copy["secondary_tests"] = dict(zip(keys, rows))
    return copy, keys


def _flatten(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{path}[{i}]")
    else:
        yield path, obj


def run(args) -> int:
    out = Path(args.out).resolve()
    if SEALED.parent in out.parents or SEALED in out.parents:
        raise SystemExit("refusing to write inside results/")
    if out.exists():
        raise SystemExit("refusing to overwrite an existing output")
    sys.path.insert(0, str(Path(args.src).resolve()))
    from hashlab.experiments.analysis import analyze_results  # noqa: E402
    from hashlab.statistics import distribution  # noqa: E402

    if args.naive_sum:
        distribution.sum = _naive_sum
    raw_results = (SEALED / "results.json").read_bytes()
    raw_config = (SEALED / "config.resolved.json").read_bytes()
    results, resolved = json.loads(raw_results), json.loads(raw_config)
    if args.config_order:
        # results.json is stored with sorted keys; the original in-memory results followed config order.
        order = [spec["id"] for spec in resolved["generators"]]
        results["generators"] = {gid: results["generators"][gid] for gid in order}
    analysis = analyze_results(results, resolved)
    from hashlab.evidence.storage import dumps as canonical_json  # noqa: E402
    record = {
        "python": sys.version,
        "executable": sys.executable,
        "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "platform": platform.platform(),
        "src": str(Path(args.src).resolve()),
        "naive_sum": bool(args.naive_sum),
        "config_order": bool(args.config_order),
        "serialized": canonical_json(analysis),
        "inputs_sha256": {"results.json": hashlib.sha256(raw_results).hexdigest(),
                          "config.resolved.json": hashlib.sha256(raw_config).hexdigest()},
        "analysis": analysis,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def compare(args) -> int:
    sealed = json.loads((SEALED / "analysis.json").read_text(encoding="utf-8"))
    sealed_keyed, sealed_order = _keyed(sealed)
    sealed_flat = dict(_flatten(sealed_keyed))
    summary = []
    for run_path in args.run:
        rec = json.loads(Path(run_path).read_text(encoding="utf-8"))
        run_keyed, run_order = _keyed(rec["analysis"])
        flat = dict(_flatten(run_keyed))
        keys = set(flat) | set(sealed_flat)
        diffs = []
        for key in sorted(keys):
            a, b = sealed_flat.get(key, "<missing>"), flat.get(key, "<missing>")
            if type(a) is not type(b) or a != b or (isinstance(a, float) and _bits(a) != _bits(b)):
                diffs.append((key, a, b))
        numeric = [d for d in diffs if isinstance(d[1], float) and isinstance(d[2], float)]
        other = [d for d in diffs if d not in numeric]
        sealed_text = (SEALED / "analysis.json").read_bytes().decode("utf-8")
        mask = lambda t: "\n".join(l if "analyzed_at_utc" not in l else "<masked>" for l in t.splitlines())
        full = rec.get("serialized") == sealed_text
        masked = rec.get("serialized") is not None and mask(rec["serialized"]) == mask(sealed_text)
        item = {"full_serialized_bytes_equal": full, "serialized_equal_except_timestamp_line": masked,
                "config_order": rec.get("config_order"), "python": rec["python"].split()[0], "executable_sha256": rec["executable_sha256"],
                "naive_sum": rec["naive_sum"], "paths_compared": len(keys),
                "secondary_order_identical": run_order == sealed_order,
                "secondary_rows_keyed": len(run_order),
                "float_bit_differences": len(numeric),
                "other_differences": [d[0] for d in other],
                "max_abs_float_difference": max((abs(d[1] - d[2]) for d in numeric), default=0.0),
                "float_difference_paths": [d[0] for d in numeric]}
        summary.append(item)
        print(json.dumps({k: v for k, v in item.items() if k != "float_difference_paths"}))
    if args.dump:
        Path(args.dump).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--src", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--naive-sum", action="store_true")
    r.add_argument("--config-order", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("--run", action="append", required=True)
    c.add_argument("--dump")
    a = p.parse_args()
    return run(a) if a.cmd == "run" else compare(a)


if __name__ == "__main__":
    raise SystemExit(main())
