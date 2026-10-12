"""Synthetic-testable outer evidence seals; no experiment or operational runner."""
from hashlib import sha256
from pathlib import Path
import re

from .exp002_foundation import canonical, decode, _hex
from .exp002_governance import FullPlanBinding, require_verified
from .exp002_journal import durable_create, require_plain, file_inventory


def inventory(root, *, sealed=False):
    require_plain(root,directory=True)
    result={}
    for p in sorted(Path(root).iterdir()):
        require_plain(p)
        if sealed and p.name in ('manifest.json','manifest.sha256'):
            continue
        if (not re.fullmatch('[a-z0-9][a-z0-9_.-]*',p.name)
                or p.name in ('manifest.json','manifest.sha256')
                or p.name.split('.')[0] in ('con','prn','aux','nul')
                or re.fullmatch('(com|lpt)[1-9]',p.name.split('.')[0])):
            raise ValueError('unsafe evidence name')
        result[p.name]=file_inventory(p)
    if not result:
        raise ValueError('empty evidence')
    return result


def seal(root, plan, full, provenance, proofs):
    """Seal supplied evidence only after independently verified completeness.

    This is a versioned E4 outer contract, not E001's manifest implementation.
    A partial seal is retained and cannot be overwritten.
    """
    if type(full) is not FullPlanBinding:
        raise ValueError('missing full binding')
    full.validate(plan)
    if type(provenance) is not dict or set(provenance)!={'attempt','source','accounting_sha256'}:
        raise ValueError('invalid provenance')
    if type(provenance['attempt']) is not int or provenance['attempt']<1 or provenance['source']!='supplied-evidence':
        raise ValueError('invalid attempt/source')
    _hex(provenance['accounting_sha256'],64)
    files=inventory(root)
    body=dict(schema='hashlab-exp002-outer-manifest-v1',seedless=plan.fingerprint,
              full_plan=full.fingerprint,provenance=provenance,files=files)
    raw=canonical(body); pin=sha256(raw).hexdigest()
    require_verified(proofs,'evidence-completeness',full.fingerprint,evidence=pin)
    durable_create(Path(root)/'manifest.json',raw)
    durable_create(Path(root)/'manifest.sha256',(pin+'\n').encode('ascii'))
    return pin


def verify_seal(root, plan, full, pin, external_proof):
    """Independent read-only inventory/hash verification against external pin."""
    _hex(pin,64); full.validate(plan)
    require_verified((external_proof,),'outer-manifest',full.fingerprint,evidence=pin)
    files=inventory(root,sealed=True)
    raw=(Path(root)/'manifest.json').read_bytes()
    if sha256(raw).hexdigest()!=pin or (Path(root)/'manifest.sha256').read_bytes()!=(pin+'\n').encode('ascii'):
        raise ValueError('seal digest mismatch')
    body=decode(raw)
    if (set(body)!={'schema','seedless','full_plan','provenance','files'}
            or body['schema']!='hashlab-exp002-outer-manifest-v1'
            or body['seedless']!=plan.fingerprint or body['full_plan']!=full.fingerprint
            or body['files']!=files):
        raise ValueError('evidence provenance/inventory mismatch')
    return body
