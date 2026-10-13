"""One fixed engineering fixture, with producer/reference in separate processes."""
import argparse
import json
from pathlib import Path
import time


def peak_rss():
    """Whole-process peak working set on Windows; peak RSS on Unix."""
    import sys
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
                (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
                'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        api=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
        api.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        api.restype=wintypes.BOOL
        if not api(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource
    size=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return size if sys.platform=='darwin' else size*1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('produce','verify'))
    parser.add_argument('destination', type=Path)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--pin')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    audit = args.audit or args.repository/'results/e001-s14-audit-20261012-01'
    if args.role=='verify' and not args.pin:
        parser.error('verify requires externally retained --pin')
    start = time.perf_counter()
    if args.role=='produce':
        from hashlab.experiments.exp002_synthetic import run_fixture
        result = dict(complete_sha256=run_fixture(args.destination,audit_root=audit,
                                                repository_root=args.repository))
    else:
        from e002_verify.core import verify_fixture
        result = verify_fixture(args.destination,complete_sha256=args.pin,audit_root=audit,
                                repository_root=args.repository)
    if args.report:
        with args.report.open('x',encoding='utf-8') as out:
            json.dump(result,out,sort_keys=True,indent=2)
            out.write('\n')
    print(json.dumps(dict(result=result,elapsed_seconds=time.perf_counter()-start,
                          peak_rss_bytes=peak_rss()),sort_keys=True))


if __name__=='__main__':
    main()
