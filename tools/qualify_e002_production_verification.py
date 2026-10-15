"""Bounded production-format fixture producer and independent production-evidence verifier.

Roles: ``produce-bounded`` (fixed 78-evaluation public fixture) and ``verify``. There is no
production, QA2 or quota/seed role. ``verify --geometry production`` verifies future evidence
only; it never produces, enables, resumes or repairs anything.
"""
import argparse
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('produce-bounded', 'verify'))
    parser.add_argument('destination', type=Path)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--pin')
    parser.add_argument('--seed-record', type=Path)
    parser.add_argument('--geometry', choices=('bounded-fixture', 'production'), default='bounded-fixture')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--backend', choices=('hacl', 'cng', 'reference'), default='hacl',
                        help='independent candidate-evaluation SHA-256 backend (never hashlib)')
    args = parser.parse_args()
    if args.role == 'verify' and not (args.pin and args.seed_record):
        parser.error('verify requires a retained --pin and --seed-record')
    sys.path.insert(0, str(args.repository/'src'))
    audit = args.audit or args.repository/'results/e001-s14-audit-20261012-01'
    started = time.perf_counter()
    if args.role == 'produce-bounded':
        from hashlab.experiments.exp002_kernel_bounded import run_bounded
        result = run_bounded(args.destination, audit_root=audit, repository_root=args.repository).to_dict()
    else:
        from e002_verify.production_evidence import verify_evidence
        result = verify_evidence(args.destination, completion_sha256=args.pin, geometry_name=args.geometry,
                                 seed_record=args.seed_record.read_bytes(), audit_root=audit,
                                 repository_root=args.repository, candidate_backend=args.backend)
    from qualify_e002_i3 import peak_rss
    report = dict(result=result, elapsed_seconds=time.perf_counter()-started, peak_rss_bytes=peak_rss())
    if args.report:
        with args.report.open('x', encoding='utf-8') as output:
            json.dump(report, output, sort_keys=True, indent=2)
            output.write('\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
