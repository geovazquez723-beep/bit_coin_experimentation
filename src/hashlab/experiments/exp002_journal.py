"""Append-only governance journal. Never dispatches work or accepts a seed.

An interrupted writer leaves its lock and bytes intact. Recovery is read-only;
operator/Architect resolution and an externally anchored history are required.
Filesystem durability is bounded by the platform's fsync guarantees.
"""
from hashlib import sha256
from pathlib import Path
import os
import stat
from datetime import datetime

from .exp002_foundation import canonical, decode, _hex
from .exp002_governance import require_verified

SCHEMA = 'hashlab-exp002-attempt-event-v1'
ZERO = '0'*64
BUFFER_SIZE = 64*1024


def require_plain(path, *, directory=False):
    """Reject all reparse points (including junctions), links and special files."""
    info=Path(path).lstat()
    if (getattr(info,'st_file_attributes',0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError('unsupported filesystem entry')


def file_inventory(path):
    require_plain(path)
    digest=sha256(); size=0
    with open(path,'rb') as handle:
        while chunk:=handle.read(BUFFER_SIZE):
            digest.update(chunk)
            size+=len(chunk)
    return dict(size=size,sha256=digest.hexdigest())


def durable_create(path, raw):
    with open(path, 'xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def inspect_partial(root):
    """Preserve and describe every byte, including lock and torn records."""
    root=Path(root)
    require_plain(root,directory=True)
    # Unexpected entries must never disappear from a purported complete disclosure.
    return {p.name:file_inventory(p) for p in sorted(root.iterdir())}


class AttemptJournal:
    def __init__(self, root):
        self.root=Path(root)

    def read(self, *, anchor=None, allow_lock=False):
        if not self.root.is_dir() or self.root.is_symlink():
            raise ValueError('missing or unsafe journal')
        paths=sorted(self.root.iterdir())
        if any(p.is_symlink() or not p.is_file() for p in paths):
            raise ValueError('unsafe journal entry')
        if not allow_lock and (self.root/'writer.lock').exists():
            raise ValueError('interrupted/concurrent writer; read-only recovery required')
        paths=[p for p in paths if p.name!='writer.lock']
        events=[]
        previous=ZERO
        for i,p in enumerate(paths,1):
            if p.name!=f'{i:08d}.json':
                raise ValueError('gap or unknown journal artifact')
            raw=p.read_bytes()
            event=decode(raw)
            if (type(event) is not dict or set(event)!={'schema','sequence','previous','kind','attempt','data'}
                    or event['schema']!=SCHEMA or type(event['sequence']) is not int
                    or event['sequence']!=i or event['previous']!=previous):
                raise ValueError('rewritten or malformed event')
            self._validate(events,event)
            events.append(event)
            previous=sha256(raw).hexdigest()
        if anchor is not None:
            require_verified((anchor,), 'registry-history', previous, evidence=previous)
        return tuple(events),previous

    @staticmethod
    def _validate(events,event):
        attempt=event['attempt']; data=event['data']
        if type(attempt) is not int or attempt<1 or type(data) is not dict:
            raise ValueError('invalid attempt')
        starts=[e for e in events if e['kind']=='started']
        if event['kind']=='started':
            if set(data)!={'full_plan','seed_record','code_commit','config_sha256','command','utc','retry_evidence'}:
                raise ValueError('missing started disclosure')
            for key in ('full_plan','seed_record','config_sha256'):
                _hex(data[key],64)
            _hex(data['code_commit'],40)
            if any(type(data[k]) is not str or not data[k] for k in ('command','utc')):
                raise ValueError('missing command/time')
            try:
                datetime.strptime(data['utc'],'%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                raise ValueError('require explicit UTC timestamp') from None
            if attempt!=len(starts)+1:
                raise ValueError('duplicate or skipped attempt')
            if starts:
                if not events or events[-1]['kind']!='result':
                    raise ValueError('unresolved previous attempt')
                prev=starts[-1]['data']; result=events[-1]['data']
                if data['seed_record']!=prev['seed_record']:
                    raise ValueError('seed replacement prohibited')
                if result['failure']=='valid':
                    raise ValueError('valid final attempt cannot be retried')
                unchanged=all(data[k]==prev[k] for k in ('code_commit','full_plan','config_sha256'))
                needs_review=(not unchanged or result['failure'] in ('F3','F4') or len(starts)>=3)
                if result['failure']=='F4' and data['code_commit']==prev['code_commit']:
                    raise ValueError('same-code F4 retry prohibited')
                if needs_review and data['retry_evidence'] is None:
                    raise ValueError('verified retry review required')
                if data['retry_evidence'] is not None:
                    _hex(data['retry_evidence'],64)
            elif data['retry_evidence'] is not None:
                raise ValueError('initial attempt cannot claim retry')
        elif event['kind']=='result':
            if not events or events[-1]['kind']!='started' or events[-1]['attempt']!=attempt:
                raise ValueError('result without unresolved start')
            if set(data)!={'failure','manifest','disclosure','numerical_abort','run_id','status'}:
                raise ValueError('incomplete result disclosure')
            if data['failure'] not in ('valid','F1','F2','F3','F4') or type(data['numerical_abort']) is not bool:
                raise ValueError('invalid result')
            _hex(data['disclosure'],64)
            if type(data['run_id']) is not str or not data['run_id'] or data['status'] not in ('complete','incomplete','aborted'):
                raise ValueError('missing run identity/status')
            if data['manifest'] is not None:
                _hex(data['manifest'],64)
            if (data['failure']=='valid' and (data['manifest'] is None or data['numerical_abort'] or data['status']!='complete')):
                raise ValueError('impossible valid result')
        else:
            raise ValueError('invalid event kind')

    def append(self, kind, attempt, data, *, retry_proof=None, anchor=None):
        # Lock acquisition is exclusive; no lock stealing or automatic repair.
        lock=self.root/'writer.lock'
        durable_create(lock,b'write-in-progress')
        events,previous=self.read(allow_lock=True)
        require_verified((anchor,), 'registry-history', previous, evidence=previous)
        event=dict(schema=SCHEMA,sequence=len(events)+1,previous=previous,kind=kind,attempt=attempt,data=data)
        self._validate(events,event)
        if kind=='started' and data['retry_evidence'] is not None:
            require_verified((retry_proof,), 'retry-review', data['full_plan'], evidence=data['retry_evidence'])
        durable_create(self.root/f'{len(events)+1:08d}.json',canonical(event))
        lock.unlink()
        return sha256(canonical(event)).hexdigest()


def disclose_failure(destination, journal, *, failure, numerical_abort):
    """Exclusive durable sidecar; failure to disclose propagates, never retries."""
    if failure not in ('F1','F2','F3','F4') or type(numerical_abort) is not bool:
        raise ValueError('invalid failure disclosure')
    raw=canonical(dict(schema='hashlab-exp002-failure-disclosure-v1',failure=failure,
                       numerical_abort=numerical_abort,partial_evidence=inspect_partial(journal)))
    durable_create(destination,raw)
    return sha256(raw).hexdigest()
