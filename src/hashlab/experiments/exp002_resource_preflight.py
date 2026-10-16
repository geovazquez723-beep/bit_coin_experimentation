"""Free-space preflight for the E002 evidence directory (G1-B). Reads only; creates nothing.

The byte model is derived from the frozen binary row layout in ``exp002_kernel_evidence`` so it cannot
drift from the writer. It is a requirement estimate, not a reservation: the writer still fails closed on
ENOSPC and retains whatever was written.
"""
from pathlib import Path
import shutil

from .exp002_foundation import LIMITS
from .exp002_kernel_evidence import CHUNK_ROWS, HEADER, ROW, TRAILER

DIGESTS = 64                        # raw + effective SHA-256 digest of an accepted row
INDEX_LINE_CAP = 1024               # reader-enforced maximum line length of chunks.jsonl
REJECTION_ALLOWANCE_ROWS = 2_000_000
FIXED_OVERHEAD = 2 * 2**30          # plan/history/environment/accounting/completion JSON, slack
SAFETY_FRACTION = 0.10


def _width(arm):
    return 80 if arm in ('A2', 'N2') else 8


def accepted_rows():
    return {arm: sum(n for a, _, n in LIMITS if a == arm) for arm in dict.fromkeys(a for a, _, _ in LIMITS)}


def evidence_bytes(rejection_rows=REJECTION_ALLOWANCE_ROWS):
    """Upper-bound bytes of rows + chunk framing + index for the frozen geometry."""
    accepted = sum(n * (ROW.size + _width(a) + DIGESTS) for a, n in accepted_rows().items())
    total_rows = sum(accepted_rows().values()) + rejection_rows
    chunks = -(-total_rows // CHUNK_ROWS)
    return accepted + rejection_rows * (ROW.size + 80) + chunks * (HEADER.size + TRAILER.size + INDEX_LINE_CAP)


def required_free_bytes(rejection_rows=REJECTION_ALLOWANCE_ROWS):
    base = evidence_bytes(rejection_rows) + FIXED_OVERHEAD
    return int(base * (1 + SAFETY_FRACTION))


def check_free_space(destination, required, *, usage=None):
    """Raise ValueError (before anything is created) unless the destination volume has ``required`` bytes free."""
    if type(required) is not int or required <= 0:
        raise ValueError('positive byte requirement expected')
    probe = Path(destination).absolute()
    while not probe.exists():
        if probe.parent == probe:
            raise ValueError('no existing ancestor of the evidence destination')
        probe = probe.parent
    free = (usage or shutil.disk_usage)(probe).free
    if free < required:
        raise ValueError(f'insufficient free space: {free} bytes free, {required} required; nothing was created')
    return free
