"""Fixed nonhistorical S1.3 resource probes, never a historical runner.

Fixed synthetic geometries include balanced seven-family workloads, period-three
patterned continuation and larger seeded state. Maximum 262,144 raw occurrences,
keys 1/2. Separate processes measure whole-process peak RSS.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time

CASES = {'balanced-small': ((0,2,4,6,7,8,9),4096),
         'balanced-medium': ((0,2,4,6,7,8,9),8192),
         'balanced-large': ((0,2,4,6,7,8,9),16384),
         'patterned-period-three': ((4,),65536),
         'seeded-state': ((2,9),65536)}


def peak_rss():
    if os.name == 'nt':
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)] + [
                (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
                'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi',use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource
    scale = 1 if sys.platform == 'darwin' else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*scale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--worker',choices=('producer','verifier'))
    parser.add_argument('--case',choices=tuple(CASES))
    args = parser.parse_args()
    if args.worker:
        if args.case is None: parser.error('worker requires fixed synthetic case')
        ordinals,n = CASES[args.case]
        # Imports are included in whole-process peak memory, but excluded from wall
        # throughput timing to measure the scientific pipeline itself.
        if args.worker == 'producer':
            from hashlab.experiments.e001_historical import SyntheticGeometry,run_synthetic
            start = time.perf_counter()
            report = run_synthetic(SyntheticGeometry(n,n,ordinals),args.output/'producer')
        else:
            from e001_stream_verify.streaming import verify_synthetic
            start = time.perf_counter()
            report = verify_synthetic(args.output/'producer',args.output/'verifier',ordinals,n,n)
        elapsed = time.perf_counter()-start
        count = 2*n*len(ordinals)
        result = dict(role=args.worker,case=args.case,scope='synthetic-qualification',phase_attempts=n,
                      occurrences=count,seconds=elapsed,occurrences_per_second=count/elapsed,
                      whole_process_peak_rss_bytes=peak_rss(),resources=report['resources'],
                      raw_attempted=report['raw_attempted'],historical_complete=report['historical_complete'],
                      evidence_bytes=sum(p.stat().st_size for p in (args.output/args.worker).iterdir()))
        print(json.dumps(result,sort_keys=True))
        return
    if args.case is not None: parser.error('case is only for fixed workers')
    from hashlab.experiments.e001_historical import _new_output
    args.output = _new_output(args.output)  # sealed-path checks before any mkdir
    measurements = []
    for name in CASES:
        case = args.output/name
        case.mkdir()
        for role in ('producer','verifier'):
            completed = subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),str(case),
                                        '--worker',role,'--case',name],
                                       check=True,capture_output=True,text=True)
            measurements.append(json.loads(completed.stdout))
    result = dict(scope='synthetic-qualification',measurements=measurements,
                  runtime=dict(python=sys.version,sqlite=sqlite3.sqlite_version,platform=platform.platform()),
                  historical_execution=False,provisional_estimates=True)
    with open(args.output/'measurements.json','x') as out:
        json.dump(result,out,indent=2)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
