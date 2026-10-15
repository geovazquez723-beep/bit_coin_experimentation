"""SHA-256 for research *candidate evaluation* in the independent E002 verifier (Revision 8 section 3.9).

This is deliberately separate from SHA-256 used for file integrity and pins (which stays on
``hashlib``/OpenSSL in ``core``/``production_evidence``). The producer evaluates candidates with
``hashlib.sha256`` (OpenSSL 3.x in this runtime). The verifier must not.

Backends (all produce the exact 32-byte FIPS 180-4 digest of the raw candidate bytes):

* ``hacl``      CPython's built-in ``_sha2`` module: HACL* (Project Everest) formally verified C,
                compiled into the interpreter. A different implementation lineage from OpenSSL, no
                new dependency, native speed. This is the default.
* ``cng``       Windows CNG (``bcrypt.dll`` ``BCryptHash``, Microsoft lineage), via ctypes; a second
                independent native implementation, Windows only.
* ``reference`` Pure-Python FIPS 180-4 (``sha256_reference``). Correct but far too slow for the
                full audit; a bounded correctness oracle and bounded-replay backend.

``hashlib`` is never a candidate-evaluation backend here. A backend is used only after passing
published known-answer vectors; any problem raises ``BackendUnavailable`` (fail closed).
"""
import hashlib
import sys

from . import sha256_reference

BACKENDS = ('hacl', 'cng', 'reference')
LINEAGE = {
    'hacl': 'HACL* (Project Everest) verified C, built into CPython (_sha2); independent of OpenSSL',
    'cng': 'Microsoft Windows CNG bcrypt.dll BCryptHash; independent of OpenSSL and HACL*',
    'reference': 'pure-Python FIPS 180-4 written in this repository; shares no code with any native library',
}
# FIPS 180-4 / NIST CAVP published vectors (message -> digest).
KNOWN_ANSWERS = (
    (b'', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    (b'abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'),
    (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
     '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'),
    (b'abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu',
     'cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1'),
    (b'a' * 1_000_000, 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0'),
)
CANDIDATE_WIDTHS = (8, 80)


class BackendUnavailable(ValueError):
    """The required independent SHA-256 backend is missing or failed qualification."""


def _hacl():
    try:
        import _sha2
        ctor = _sha2.sha256
    except (ImportError, AttributeError) as exc:
        raise BackendUnavailable('CPython _sha2 (HACL*) is unavailable') from exc
    if type(ctor(b'')).__module__ != '_sha2':
        raise BackendUnavailable('_sha2.sha256 is not the built-in implementation')
    return lambda data: ctor(data).digest()


def _cng():
    if sys.platform != 'win32':
        raise BackendUnavailable('Windows CNG is only available on Windows')
    import ctypes
    from ctypes import wintypes
    try:
        dll = ctypes.WinDLL('bcrypt')
        opener, hasher = dll.BCryptOpenAlgorithmProvider, dll.BCryptHash
    except (OSError, AttributeError) as exc:
        raise BackendUnavailable('bcrypt.dll CNG hashing is unavailable') from exc
    opener.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_wchar_p, ctypes.c_wchar_p, wintypes.ULONG]
    opener.restype = ctypes.c_long
    hasher.argtypes = [ctypes.c_void_p, ctypes.c_char_p, wintypes.ULONG, ctypes.c_char_p, wintypes.ULONG,
                       ctypes.c_char_p, wintypes.ULONG]
    hasher.restype = ctypes.c_long
    handle = ctypes.c_void_p()
    if opener(ctypes.byref(handle), 'SHA256', None, 0) != 0:
        raise BackendUnavailable('CNG SHA256 provider could not be opened')

    def digest(data):
        out = ctypes.create_string_buffer(32)
        status = hasher(handle, None, 0, data, len(data), out, 32)
        if status != 0:
            raise BackendUnavailable('BCryptHash failed with status %d' % status)
        return out.raw
    return digest


def _reference():
    return sha256_reference.sha256


_FACTORIES = {'hacl': _hacl, 'cng': _cng, 'reference': _reference}


def qualify(digest, *, vectors=KNOWN_ANSWERS, quick=False):
    """Known-answer qualification; the million-`a` vector is skipped for the slow reference when quick."""
    for message, expected in vectors:
        if quick and len(message) > 1000:
            continue
        if digest(message).hex() != expected:
            raise BackendUnavailable('known-answer vector failed')


class CandidateHasher:
    """Strict candidate digest interface: 8- or 80-byte candidates, raw 32-byte big-endian digest."""

    def __init__(self, backend='hacl'):
        if backend not in BACKENDS:
            raise BackendUnavailable('unknown or non-independent candidate SHA-256 backend: %r' % (backend,))
        self.backend = backend
        self._digest = _FACTORIES[backend]()
        qualify(self._digest, quick=backend == 'reference')
        self.qualified = True

    def digest(self, candidate):
        if type(candidate) is not bytes or len(candidate) not in CANDIDATE_WIDTHS:
            raise ValueError('candidate must be 8 or 80 raw bytes')
        return self._digest(candidate)

    def evaluator(self):
        """Hot-loop callable; same checks are enforced by the verifier's reconstructed widths."""
        return self._digest

    def identity(self):
        """What actually evaluated candidate digests, and its relationship to the producer."""
        import platform
        info = dict(role='candidate-evaluation', backend=self.backend, lineage=LINEAGE[self.backend],
                    known_answers='passed', python=sys.version.split()[0], platform=platform.platform(),
                    producer_backend='hashlib.sha256 (OpenSSL)',
                    independent_of_producer=True, shared_with_producer=False)
        if self.backend == 'hacl':
            info['interpreter_sha256'] = _file_sha256(sys.executable)
            info['sha2_container'] = _sha2_container()
        return info


def _file_sha256(path):
    # Integrity pin only; unrelated to candidate evaluation.
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _sha2_container():
    """The binary that actually contains the built-in ``_sha2``.

    On Windows CPython builds the module into ``python3XY.dll``, not the small ``python.exe``
    launcher, so the executable hash alone does not pin it. Record the loaded DLL's path and
    hash, and whether it embeds a HACL* source-tree path (``Modules/_hacl/Hacl_*``). That marker
    shows the HACL* tree is compiled into this binary; it does not by itself prove the SHA-2 code path
    (the CPython 3.12 source lineage and known-answer/behavioural tests supply the rest).
    """
    import _sha2
    builtin = '_sha2' in sys.builtin_module_names and getattr(_sha2, '__file__', None) is None
    path = sys.executable
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetModuleHandleW.restype = wintypes.HMODULE
        handle = kernel.GetModuleHandleW('python%d%d.dll' % sys.version_info[:2])
        if handle:
            buffer = ctypes.create_unicode_buffer(1024)
            kernel.GetModuleFileNameW(wintypes.HMODULE(handle), buffer, 1024)
            path = buffer.value
    with open(path, 'rb') as handle:
        blob = handle.read()
    marker = (rb'_hacl\Hacl_', b'_hacl/Hacl_')
    return dict(builtin_module=builtin, path=path, sha256=hashlib.sha256(blob).hexdigest(),
                hacl_source_tree_marker_present=any(m in blob for m in marker))


def file_integrity_backend():
    """SHA-256 for file pins/integrity: hashlib (OpenSSL). Conceptually separate from candidate evaluation."""
    import ssl
    module = type(hashlib.sha256()).__module__
    return dict(role='file-integrity', implementation='hashlib.sha256', module=module,
                openssl=ssl.OPENSSL_VERSION if module == '_hashlib' else None,
                used_for_candidate_evaluation=False)
