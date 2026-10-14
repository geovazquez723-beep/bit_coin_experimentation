"""Fixed 206-evaluation engineering producer/verifier; no production or QA2 role."""
import argparse
import json
from pathlib import Path
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=('produce','verify'))
    parser.add_argument('destination',type=Path)
    parser.add_argument('--repository',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--audit',type=Path)
    parser.add_argument('--pin')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.role=='verify' and not args.pin:parser.error('verify requires retained --pin')
    sys.path.insert(0,str(args.repository/'src'))
    audit=args.audit or args.repository/'results/e001-s14-audit-20261012-01'
    started=time.perf_counter()
    if args.role=='produce':
        from hashlab.experiments.exp002_kernel import run_engineering
        result=run_engineering(args.destination,audit_root=audit,repository_root=args.repository).to_dict()
    else:
        from e002_verify.kernel import verify_engineering
        result=verify_engineering(args.destination,completion_sha256=args.pin,audit_root=audit,
                                  repository_root=args.repository)
    from qualify_e002_i3 import peak_rss
    report=dict(result=result,elapsed_seconds=time.perf_counter()-started,peak_rss_bytes=peak_rss())
    if args.report:
        with args.report.open('x',encoding='utf-8') as output:
            json.dump(report,output,sort_keys=True,indent=2);output.write('\n')
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
