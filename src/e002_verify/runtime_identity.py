"""Independent check of the producer's declared SHA-256 runtime identity (G1-B).

No ``hashlab`` imports and no shared code with the producer's observer. The producer enumerates
loaded modules with ``EnumProcessModules``; this module uses a ToolHelp32 module snapshot, so the
two observations do not share a Windows API path. The verifier's *own* candidate-hashing identity
stays in ``sha256_independent``; this module only validates the producer's declaration and,
on request, compares it with what this process has loaded.
"""
import hashlib
import sys

SCHEMA = 'hashlab-e002-runtime-hashing-identity-v1'
_REQUIRED = ('hashlib_extension', 'interpreter', 'libcrypto', 'python_dll')
_ALL_ROLES = _REQUIRED + ('crt',)
_FIELDS = {'schema', 'sha256_provider', 'libcrypto_version', 'python_version', 'artifacts'}


def _is_hex64(text):
    return isinstance(text, str) and len(text) == 64 and set(text) <= set('0123456789abcdef')


def check_declared(declared):
    """Fail closed unless the declared identity is well-formed. Returns it unchanged."""
    ok = (type(declared) is dict and set(declared) == _FIELDS and declared['schema'] == SCHEMA
          and declared['sha256_provider'] == '_hashlib' and type(declared['artifacts']) is list
          and type(declared['libcrypto_version']) is str and declared['libcrypto_version'].startswith('OpenSSL ')
          and type(declared['python_version']) is str)
    if not ok:
        raise ValueError('producer hashing identity shape')
    roles = []
    for item in declared['artifacts']:
        if (type(item) is not dict or set(item) != {'role', 'path', 'size', 'sha256'}
                or item['role'] not in _ALL_ROLES or type(item['path']) is not str or not item['path']
                or type(item['size']) is not int or item['size'] <= 0 or not _is_hex64(item['sha256'])):
            raise ValueError('producer hashing identity artifact')
        roles.append(item['role'])
    if any(roles.count(role) != 1 for role in _REQUIRED):
        raise ValueError('producer hashing identity lacks a required role')
    return declared


def _snapshot_paths():
    if sys.platform != 'win32':
        raise ValueError('loaded-module observation is implemented for Windows only')
    import ctypes
    from ctypes import wintypes

    class ModuleEntry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('GlblcntUsage', wintypes.DWORD), ('ProccntUsage', wintypes.DWORD),
                    ('modBaseAddr', ctypes.c_void_p), ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HMODULE),
                    ('szModule', ctypes.c_wchar * 256), ('szExePath', ctypes.c_wchar * 260)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ModuleEntry)]
    kernel.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ModuleEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(0x8 | 0x10, 0)      # SNAPMODULE | SNAPMODULE32 (this process)
    if snapshot in (None, wintypes.HANDLE(-1).value):
        raise ValueError('module snapshot failed')
    paths = []
    try:
        entry = ModuleEntry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Module32FirstW(snapshot, ctypes.byref(entry))
        while more:
            paths.append(entry.szExePath)
            more = kernel.Module32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    if not paths:
        raise ValueError('module snapshot empty')
    return paths


def _same(a, b):
    import os
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def _pin(path):
    digest, size = hashlib.sha256(), 0
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
            size += len(block)
    return size, digest.hexdigest()


def observe_local():
    """What this process actually has loaded for the producer-equivalent hashing stack."""
    import os
    import _hashlib
    if type(hashlib.sha256()).__module__ != '_hashlib' or not getattr(_hashlib, '__file__', None):
        raise ValueError('hashlib.sha256 is not a loaded _hashlib extension')
    paths = _snapshot_paths()
    base = lambda p: os.path.basename(p).lower()
    wanted = dict(
        interpreter=[p for p in paths if _same(p, sys.executable)],
        python_dll=[p for p in paths if base(p) == 'python%d%d.dll' % sys.version_info[:2]],
        hashlib_extension=[p for p in paths if _same(p, _hashlib.__file__)],
        libcrypto=[p for p in paths if base(p).startswith('libcrypto')])
    artifacts = []
    for role, hits in wanted.items():
        if len(hits) != 1:
            raise ValueError('role %s: %d loaded modules' % (role, len(hits)))
        artifacts.append((role, hits[0]))
    artifacts += [('crt', p) for p in paths if base(p) == 'vcruntime140.dll']
    rows = []
    for role, path in artifacts:
        size, digest = _pin(path)
        rows.append(dict(role=role, path=path, size=size, sha256=digest))
    rows.sort(key=lambda r: (r['role'], r['path'].lower()))
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    handle = kernel.GetModuleHandleW(next(r['path'] for r in rows if r['role'] == 'libcrypto'))
    if not handle:
        raise ValueError('libcrypto is not a loaded module at the observed path')
    lib = ctypes.CDLL('libcrypto-loaded', handle=handle)
    lib.OpenSSL_version.restype = ctypes.c_char_p
    lib.OpenSSL_version.argtypes = [ctypes.c_int]
    return dict(schema=SCHEMA, sha256_provider='_hashlib', libcrypto_version=lib.OpenSSL_version(0).decode('ascii'),
                python_version=sys.version.split()[0], artifacts=rows)


def compare(declared, observed):
    """Differences, comparing byte identity (role, size, sha256) and versions; paths reported separately."""
    def key(value):
        return [(a['role'], a['size'], a['sha256']) for a in value['artifacts']]
    problems = []
    if key(declared) != key(observed):
        problems.append('artifact bytes')
    if declared['libcrypto_version'] != observed['libcrypto_version']:
        problems.append('libcrypto version')
    if declared['python_version'] != observed['python_version']:
        problems.append('python version')
    paths = declared['artifacts'] and [a['path'] for a in declared['artifacts']] == [a['path'] for a in observed['artifacts']]
    return problems, bool(paths)
