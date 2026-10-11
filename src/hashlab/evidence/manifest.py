"""Evidence manifests: environment capture and file-integrity hashes.

A run's manifest.json lists every evidence file with its SHA-256 and size.
manifest.sha256 holds the SHA-256 of manifest.json itself. Verification
catches accidental edits, truncation or missing files. It is NOT tamper-proof
against someone who rewrites both files; for that, archive or sign the
digests outside the run directory (an open question in the README).

The hostname and user name are deliberately left out of the environment record.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

MANIFEST_NAME = "manifest.json"
MANIFEST_DIGEST_NAME = "manifest.sha256"
MANIFEST_SCHEMA = "hashlab-manifest-v1"
#: Sub-directory for later re-analyses. It is created after sealing, so it is excluded from the manifest.
ANALYSES_DIR = "analyses"
REPO_ROOT = Path(__file__).resolve().parents[3]
TRACKED_PACKAGES = ("hashlab", "PyYAML", "pytest")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_info(repo: Path = REPO_ROOT) -> dict:
    revision = _git(["rev-parse", "HEAD"], repo)
    if revision is None:
        return {"available": False, "note": "not a git repository, no commits yet, or git unavailable"}
    status = _git(["status", "--porcelain"], repo) or ""
    changed = [line for line in status.splitlines() if line.strip()]
    return {
        "available": True,
        "revision": revision,
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"], repo),
        "dirty": bool(changed),
        "changed_paths": len(changed),
        "note": "a dirty tree means the run used uncommitted code; the results may not reproduce from the revision alone",
    }


def package_versions() -> dict:
    versions: dict[str, str | None] = {}
    for name in TRACKED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def collect_environment() -> dict:
    return {
        "captured_at_utc": utc_now_iso(),
        "python": {
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "hash_randomization": sys.flags.hash_randomization,
        },
        "openssl": ssl.OPENSSL_VERSION,
        "packages": package_versions(),
        "machine": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "git": git_info(),
    }


def build_manifest(run_dir: Path, files: list[str], metadata_fields: dict) -> dict:
    entries = {}
    for name in sorted(files):
        path = run_dir / name
        entries[name] = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
    return {"schema": MANIFEST_SCHEMA, "sealed_at_utc": utc_now_iso(), **metadata_fields, "files": entries}


def verify_manifest(run_dir: Path) -> list[str]:
    """Return a list of integrity problems (an empty list means the evidence is intact)."""
    problems: list[str] = []
    manifest_path = run_dir / MANIFEST_NAME
    digest_path = run_dir / MANIFEST_DIGEST_NAME
    if not manifest_path.is_file():
        return [f"missing {MANIFEST_NAME}"]
    if not digest_path.is_file():
        problems.append(f"missing {MANIFEST_DIGEST_NAME}")
    elif digest_path.read_text(encoding="ascii").split()[0] != file_sha256(manifest_path):
        problems.append(f"{MANIFEST_NAME} does not match {MANIFEST_DIGEST_NAME}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return problems + [f"{MANIFEST_NAME} is not valid JSON: {exc}"]
    if manifest.get("schema") != MANIFEST_SCHEMA:
        problems.append(f"unexpected manifest schema {manifest.get('schema')!r}")
    listed = manifest.get("files", {})
    for name, entry in listed.items():
        path = run_dir / name
        if not path.is_file():
            problems.append(f"missing evidence file {name}")
            continue
        if path.stat().st_size != entry.get("bytes"):
            problems.append(f"size mismatch for {name}")
        if file_sha256(path) != entry.get("sha256"):
            problems.append(f"hash mismatch for {name}")
    allowed = set(listed) | {MANIFEST_NAME, MANIFEST_DIGEST_NAME, ANALYSES_DIR}
    for child in run_dir.iterdir():
        if child.name not in allowed:
            problems.append(f"unlisted file in evidence directory: {child.name}")
    return problems
