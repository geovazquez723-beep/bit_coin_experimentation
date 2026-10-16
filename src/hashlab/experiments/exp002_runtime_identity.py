"""Observed identity of the code that evaluates the producer's SHA-256 (G1-B runtime binding).

``python.exe`` alone does not pin the hashing code: on Windows ``hashlib.sha256`` is ``_hashlib.pyd``
over ``libcrypto-3-x64.dll``, and the interpreter itself lives in ``python3XY.dll``. This module reads
the *loaded* module list of the running process (never a guessed path), hashes each relevant file and
cross-checks that ``hashlib.sha256`` really is the loaded ``_hashlib`` extension. Windows only; any
other platform, or any inconsistency, fails closed with ``ValueError``.
"""
import hashlib
import sys
from pathlib import Path

SCHEMA = 'hashlab-e002-runtime-hashing-identity-v1'
ROLES = ('crt', 'hashlib_extension', 'interpreter', 'libcrypto', 'python_dll')
_KAT = ('abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')


def _hex64(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _loaded_modules():
    if sys.platform != 'win32':
        raise ValueError('loaded-module observation is implemented for Windows only')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    handles = (wintypes.HMODULE * 4096)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcessModules(kernel.GetCurrentProcess(), handles, ctypes.sizeof(handles), ctypes.byref(needed)):
        raise ValueError('loaded-module enumeration failed')
    paths = []
    for i in range(needed.value // ctypes.sizeof(wintypes.HMODULE)):
        buffer = ctypes.create_unicode_buffer(2048)
        if not kernel.GetModuleFileNameW(handles[i], buffer, 2048):
            raise ValueError('loaded-module path unavailable')
        paths.append(buffer.value)
    return paths


def _norm(path):
    return str(Path(path).resolve()).lower()


def _file_pin(path):
    digest = hashlib.sha256()
    size = 0
    with open(path, 'rb') as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def _openssl_version(libcrypto_path):
    """Ask the *already loaded* library; never load a file (GetModuleHandle, not LoadLibrary)."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    handle = kernel.GetModuleHandleW(libcrypto_path)
    if not handle:
        raise ValueError('libcrypto is not a loaded module at the observed path')
    lib = ctypes.CDLL('libcrypto-loaded', handle=handle)
    lib.OpenSSL_version.restype = ctypes.c_char_p
    lib.OpenSSL_version.argtypes = [ctypes.c_int]
    return lib.OpenSSL_version(0).decode('ascii')


def observe_hashing_identity():
    """Identity of the interpreter, interpreter DLL, ``_hashlib`` and the loaded OpenSSL crypto library."""
    import _hashlib
    # Force the provider to be loaded and exercised before the module list is read.
    if hashlib.sha256(_KAT[0].encode()).hexdigest() != _KAT[1]:
        raise ValueError('sha256 known answer failed')
    if type(hashlib.sha256()).__module__ != '_hashlib' or hashlib.sha256 is not _hashlib.openssl_sha256:
        raise ValueError('hashlib.sha256 is not the _hashlib implementation')
    loaded = _loaded_modules()
    by_name = {}
    for path in loaded:
        by_name.setdefault(Path(path).name.lower(), []).append(path)
    dll_name = 'python%d%d.dll' % sys.version_info[:2]
    found = {}

    def one(role, paths):
        if len(paths) != 1:
            raise ValueError(f'{role}: expected exactly one loaded module, found {len(paths)}')
        found[role] = paths[0]

    one('interpreter', [p for p in loaded if _norm(p) == _norm(sys.executable)])
    one('python_dll', by_name.get(dll_name, []))
    hashlib_file = getattr(_hashlib, '__file__', None)
    if not hashlib_file:
        raise ValueError('_hashlib has no file; implementation not an extension module')
    one('hashlib_extension', [p for p in loaded if _norm(p) == _norm(hashlib_file)])
    one('libcrypto', [p for n, ps in by_name.items() if n.startswith('libcrypto') for p in ps])
    crt = [p for n, ps in by_name.items() if n == 'vcruntime140.dll' for p in ps]
    artifacts = []
    for role, path in sorted(found.items()):
        size, digest = _file_pin(path)
        artifacts.append(dict(role=role, path=path, size=size, sha256=digest))
    for path in sorted(crt):
        size, digest = _file_pin(path)
        artifacts.append(dict(role='crt', path=path, size=size, sha256=digest))
    artifacts.sort(key=lambda a: (a['role'], a['path'].lower()))
    version = _openssl_version(found['libcrypto'])
    return dict(schema=SCHEMA, sha256_provider='_hashlib', libcrypto_version=version,
                python_version=sys.version.split()[0], artifacts=artifacts)


def check_hashing_identity_shape(value):
    """Structural validation of a declared identity (no observation)."""
    if (type(value) is not dict or set(value) != {'schema', 'sha256_provider', 'libcrypto_version',
                                                   'python_version', 'artifacts'}
            or value['schema'] != SCHEMA or value['sha256_provider'] != '_hashlib'
            or type(value['libcrypto_version']) is not str or not value['libcrypto_version'].startswith('OpenSSL ')
            or type(value['python_version']) is not str or type(value['artifacts']) is not list):
        raise ValueError('hashing identity shape')
    roles = []
    for a in value['artifacts']:
        if (type(a) is not dict or set(a) != {'role', 'path', 'size', 'sha256'} or a['role'] not in ROLES
                or type(a['path']) is not str or not a['path'] or type(a['size']) is not int
                or a['size'] <= 0 or not _hex64(a['sha256'])):
            raise ValueError('hashing identity artifact')
        roles.append(a['role'])
    for required in ('interpreter', 'python_dll', 'hashlib_extension', 'libcrypto'):
        if roles.count(required) != 1:
            raise ValueError('hashing identity role: ' + required)
    return value
