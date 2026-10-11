"""HASHLAB command-line interface.

    python -m hashlab.cli validate [--config CONFIG]
    python -m hashlab.cli plan --config CONFIG [--json]
    python -m hashlab.cli run --config CONFIG [--results-dir results]
    python -m hashlab.cli analyze --run-id RUN_ID [--results-dir results]

``validate`` and ``plan`` never hash candidates for an experiment and never
write to the results directory.

Exit codes: 0 ok, 1 self-check failure, 2 config/plan error, 3 evidence
integrity failure, 130 interrupted.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hashlab import __version__
from hashlab.evidence.manifest import ANALYSES_DIR, verify_manifest
from hashlab.evidence.storage import dumps, read_json, run_path
from hashlab.experiments.analysis import analyze_results, render_report
from hashlab.experiments.baseline import build_plan, describe_plan, run_experiment
from hashlab.experiments.config import ConfigError, load_config_file, resolve_config
from hashlab.experiments.selfcheck import run_selfchecks

DEFAULT_RESULTS_DIR = Path("results")


def _load(path: str) -> tuple[bytes, dict]:
    source, raw = load_config_file(Path(path))
    return source, resolve_config(raw)


def cmd_validate(args: argparse.Namespace) -> int:
    failed = False
    for name, error in run_selfchecks():
        print(f"[{'FAIL' if error else ' OK '}] {name}" + (f": {error}" if error else ""))
        failed = failed or error is not None
    if args.config:
        try:
            _, resolved = _load(args.config)
            plan = build_plan(resolved)
        except (ConfigError, OSError, ValueError) as exc:
            print(f"[FAIL] config {args.config}:\n{exc}")
            return 2
        if plan["errors"]:
            print(f"[FAIL] config {args.config} produces an infeasible plan:")
            for error in plan["errors"]:
                print(f"       {error}")
            return 2
        print(f"[ OK ] config {args.config} is valid ({len(resolved['generators'])} generators)")
    print("validate: no experiment was run; nothing was written.")
    return 1 if failed else 0


def cmd_plan(args: argparse.Namespace) -> int:
    try:
        _, resolved = _load(args.config)
    except (ConfigError, OSError, ValueError) as exc:
        print(f"config error:\n{exc}", file=sys.stderr)
        return 2
    plan = build_plan(resolved)
    print(json.dumps(plan, indent=2) if args.json else describe_plan(plan))
    if not args.json:
        print("plan: dry run only; no hashing was done and nothing was written.")
    return 2 if plan["errors"] else 0


def cmd_run(args: argparse.Namespace) -> int:
    try:
        source, resolved = _load(args.config)
    except (ConfigError, OSError, ValueError) as exc:
        print(f"config error:\n{exc}", file=sys.stderr)
        return 2
    plan = build_plan(resolved)
    if plan["errors"]:
        print(describe_plan(plan), file=sys.stderr)
        return 2
    try:
        run_id, path = run_experiment(resolved, source, Path(args.results_dir))
    except KeyboardInterrupt:
        return 130
    analysis = read_json(path / "analysis.json")
    print(f"run_id: {run_id}")
    print(f"evidence: {path}")
    print(f"verdict: {analysis['verdict']['summary']}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    try:
        path = run_path(Path(args.results_dir), args.run_id)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    problems = verify_manifest(path)
    if problems:
        print("evidence integrity check FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 3
    print(f"[ OK ] evidence integrity verified for {args.run_id}")
    results = read_json(path / "results.json")
    resolved = read_json(path / "config.resolved.json")
    analysis = analyze_results(results, resolved)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out_dir = path / ANALYSES_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=False)
    with open(out_dir / "analysis.json", "x", encoding="utf-8", newline="\n") as handle:
        handle.write(dumps(analysis))
    report = render_report(analysis)
    with open(out_dir / "report.md", "x", encoding="utf-8", newline="\n") as handle:
        handle.write(report)
    print(report)
    print(f"re-analysis written to {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hashlab", description="HASHLAB SHA-256 proof-of-work research harness")
    parser.add_argument("--version", action="version", version=f"hashlab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="run cheap self-checks (and optionally validate a config)")
    p_validate.add_argument("--config", help="config file to validate (no hashing)")
    p_validate.set_defaults(func=cmd_validate)

    p_plan = sub.add_parser("plan", help="show the pre-registered plan for a config (dry run)")
    p_plan.add_argument("--config", required=True)
    p_plan.add_argument("--json", action="store_true", help="print the full plan as JSON")
    p_plan.set_defaults(func=cmd_plan)

    p_run = sub.add_parser("run", help="execute an experiment and seal an evidence directory")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    p_run.set_defaults(func=cmd_run)

    p_analyze = sub.add_parser("analyze", help="verify a run's evidence and re-analyze it")
    p_analyze.add_argument("--run-id", required=True)
    p_analyze.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    p_analyze.set_defaults(func=cmd_analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
