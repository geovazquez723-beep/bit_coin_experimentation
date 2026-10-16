"""Q-2 second-host replay of retained bounded production-format engineering evidence (G1-D).

    python second_host_replay.py package EVIDENCE_DIR SEED_RECORD PIN AUDIT_DIR OUT_DIR
    python second_host_replay.py replay PACKAGE_DIR --repository FRESH_CHECKOUT --audit AUDIT_DIR --out REPORT.json

``package`` (run on the producing host) copies the evidence byte for byte into a NEW directory with a
manifest of every file, the required repository commit, the producer runtime identity and a host
fingerprint.  The retained S1.4 audit inputs are hash-listed, not copied (transfer them separately).
``replay`` (run on the candidate second host) verifies the package inventory and the audit inputs,
requires a clean checkout at the pinned commit, runs the independent verifier with the independent
HACL* SHA-256 backend, and compares the result with the producer-side expected report.  It records
host, runtime and native hashing identities and states whether the replay host has the same
fingerprint as the producing host; a same-host run is reported ``q2_qualifying: false`` and exits 2.
No seed is generated, nothing is produced, repaired or resumed, and no evidence is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = "hashlab-e002-q2-package-v1"
COMPARED = ("bindings", "claims", "coverage", "mode", "schema", "scope", "seed", "verification")
AUDIT_FILES = ("producer/accounting.sqlite", "producer/complete.json", "producer/exclusions.bin",
               "producer/occurrences.bin", "producer/plan.json", "producer/ranks.bin",
               "verifier/reference.sqlite", "verifier/verified.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def host_fingerprint() -> dict:
    guid = None
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                                0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                guid = winreg.QueryValueEx(key, "MachineGuid")[0]
        except OSError:
            guid = None
    return {"node_sha256": hashlib.sha256(platform.node().encode()).hexdigest(),
            "machine_guid_sha256": hashlib.sha256(guid.encode()).hexdigest() if guid else None,
            "platform": platform.platform(), "processor": platform.processor(), "machine": platform.machine()}


def same_host(a: dict, b: dict) -> bool:
    if a.get("machine_guid_sha256") and a.get("machine_guid_sha256") == b.get("machine_guid_sha256"):
        return True
    return a.get("node_sha256") == b.get("node_sha256")


def inventory(root: Path, names=None) -> dict:
    names = sorted(names if names is not None else (p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()))
    return {n: {"size": (root / n).stat().st_size, "sha256": sha256_file(root / n)} for n in names}


def git(repository: Path, *args) -> str:
    return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()


def package(args) -> int:
    out = args.out_dir
    if out.exists():
        raise SystemExit("refusing to overwrite an existing package directory")
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "src"))
    out.mkdir(parents=True)
    shutil.copytree(args.evidence, out / "evidence")
    (out / "seed-record.json").write_bytes(args.seed_record.read_bytes())
    (out / "pin.txt").write_text(args.pin + "\n", encoding="ascii")
    from e002_verify.production_evidence import verify_evidence
    expected = verify_evidence(out / "evidence", completion_sha256=args.pin, geometry_name="bounded-fixture",
                               seed_record=(out / "seed-record.json").read_bytes(), audit_root=args.audit,
                               repository_root=repo, candidate_backend="hacl")
    (out / "expected-report.json").write_text(json.dumps(expected, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    env = json.loads((out / "evidence" / "environment.json").read_text(encoding="utf-8"))
    manifest = {"schema": SCHEMA, "required_commit": git(repo, "rev-parse", "HEAD"),
                "repository_clean_at_packaging": git(repo, "status", "--porcelain", "--untracked-files=no") == "",
                "completion_sha256": args.pin, "producer_runtime": env["runtime"], "producer_host": host_fingerprint(),
                "files": inventory(out), "audit_inputs": inventory(args.audit, AUDIT_FILES)}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"package": str(out), "files": len(manifest["files"]), "commit": manifest["required_commit"]}))
    return 0


def replay(args) -> int:
    pkg = args.package
    manifest = json.loads((pkg / "MANIFEST.json").read_text(encoding="utf-8"))
    problems = []
    if manifest.get("schema") != SCHEMA:
        raise SystemExit("unsupported package schema")
    observed = inventory(pkg)
    observed.pop("MANIFEST.json", None)
    if observed != manifest["files"]:
        problems.append("package inventory differs from the manifest")
    try:
        audit_ok = inventory(args.audit, AUDIT_FILES) == manifest["audit_inputs"]
    except OSError:
        audit_ok = False
    if not audit_ok:
        problems.append("S1.4 audit inputs missing or different from the manifest")
    repo = args.repository.resolve()
    head = git(repo, "rev-parse", "HEAD")
    if head != manifest["required_commit"]:
        problems.append(f"checkout is {head}, manifest requires {manifest['required_commit']}")
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        problems.append("checkout has tracked modifications")
    if args.out.exists():
        raise SystemExit("refusing to overwrite an existing report")
    host = host_fingerprint()
    qualifying = not same_host(host, manifest["producer_host"])
    report = {"schema": "hashlab-e002-q2-replay-report-v1", "package_commit": manifest["required_commit"],
              "replay_commit": head, "replay_host": host, "producer_host": manifest["producer_host"],
              "q2_qualifying": qualifying, "package_problems": problems, "python": sys.version,
              "executable": sys.executable, "executable_sha256": sha256_file(Path(sys.executable)),
              "observe_hashing": bool(args.observe_hashing), "result": None, "differences": None, "matches_expected": False}
    if not problems:
        sys.path.insert(0, str(repo / "src"))
        from e002_verify.production_evidence import verify_evidence
        result = verify_evidence(pkg / "evidence", completion_sha256=manifest["completion_sha256"],
                                 geometry_name="bounded-fixture", seed_record=(pkg / "seed-record.json").read_bytes(),
                                 audit_root=args.audit, repository_root=repo, candidate_backend="hacl",
                                 observe_hashing=args.observe_hashing)
        expected = json.loads((pkg / "expected-report.json").read_text(encoding="utf-8"))
        result = json.loads(json.dumps(result))
        differences = [k for k in COMPARED if result.get(k) != expected.get(k)]
        report.update(result=result, differences=differences, matches_expected=not differences)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("q2_qualifying", "package_problems", "differences", "matches_expected")}))
    if problems or report["differences"]:
        return 1
    return 0 if qualifying else 2


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("package")
    a.add_argument("evidence", type=Path)
    a.add_argument("seed_record", type=Path)
    a.add_argument("pin")
    a.add_argument("audit", type=Path)
    a.add_argument("out_dir", type=Path)
    b = sub.add_parser("replay")
    b.add_argument("package", type=Path)
    b.add_argument("--repository", type=Path, required=True)
    b.add_argument("--audit", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--observe-hashing", action="store_true")
    args = p.parse_args()
    return package(args) if args.cmd == "package" else replay(args)


if __name__ == "__main__":
    raise SystemExit(main())
