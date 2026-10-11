"""Evidence directories: unique, never reused, made read-only after writing.

Layout of results/<run_id>/ (all listed in manifest.json):

    config.source.yaml      exact bytes of the config file used
    config.resolved.json    the normalized config the run actually used
    plan.json               the pre-registered plan (computed before any hashing)
    environment.json        git revision, Python/package versions, machine details
    seeds.json              master seed and every derived sub-seed
    batches.jsonl           one JSON line per bounded batch (streamed during the run)
    successes.jsonl         optional successful candidates (capped), if enabled
    results.json            final counters per generator and phase
    analysis.json           statistical analysis
    report.md               human-readable report
    manifest.json + manifest.sha256

Re-analyses go into results/<run_id>/analyses/<timestamp>/ and never touch
the sealed files.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from hashlab.evidence.manifest import (
    MANIFEST_DIGEST_NAME,
    MANIFEST_NAME,
    build_manifest,
    file_sha256,
)

RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9_.-]{1,40}-[0-9a-f]{8}$")


def new_run_id(experiment_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "-", experiment_id)[:40] or "run"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-exp{safe}-{secrets.token_hex(4)}"


def validate_run_id(run_id: str) -> str:
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"invalid run id {run_id!r}")
    return run_id


def dumps(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def make_read_only(path: Path) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


class RunDirectory:
    """Write-once evidence directory for a single run."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.files: list[str] = []
        self.sealed = False

    @classmethod
    def create(cls, results_root: Path, run_id: str) -> "RunDirectory":
        validate_run_id(run_id)
        results_root.mkdir(parents=True, exist_ok=True)
        path = results_root / run_id
        path.mkdir(exist_ok=False)  # never reuse or overwrite a run
        return cls(path)

    def _claim(self, name: str) -> Path:
        if self.sealed:
            raise RuntimeError("run directory is sealed")
        if name in self.files or name in (MANIFEST_NAME, MANIFEST_DIGEST_NAME) or "/" in name or "\\" in name:
            raise ValueError(f"cannot write evidence file {name!r}")
        target = self.path / name
        if target.exists():
            raise FileExistsError(target)
        self.files.append(name)
        return target

    def write_bytes(self, name: str, data: bytes) -> Path:
        target = self._claim(name)
        with open(target, "xb") as handle:
            handle.write(data)
        return target

    def write_json(self, name: str, data: object) -> Path:
        return self.write_bytes(name, dumps(data).encode("utf-8"))

    def write_text(self, name: str, text: str) -> Path:
        return self.write_bytes(name, text.encode("utf-8"))

    def open_stream(self, name: str) -> IO[str]:
        """Open an append-only text stream (JSON Lines) that becomes part of the evidence."""
        target = self._claim(name)
        return open(target, "x", encoding="utf-8", newline="\n")

    def seal(self, metadata_fields: dict) -> dict:
        """Hash every file, write the manifest and its digest, and make everything read-only."""
        manifest = build_manifest(self.path, self.files, metadata_fields)
        manifest_path = self.path / MANIFEST_NAME
        with open(manifest_path, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(dumps(manifest))
        digest_path = self.path / MANIFEST_DIGEST_NAME
        with open(digest_path, "x", encoding="ascii", newline="\n") as handle:
            handle.write(f"{file_sha256(manifest_path)}  {MANIFEST_NAME}\n")
        for name in [*self.files, MANIFEST_NAME, MANIFEST_DIGEST_NAME]:
            make_read_only(self.path / name)
        self.sealed = True
        return manifest


def run_path(results_root: Path, run_id: str) -> Path:
    path = results_root / validate_run_id(run_id)
    if not path.is_dir():
        raise FileNotFoundError(f"no evidence directory for run {run_id!r} under {results_root}")
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
