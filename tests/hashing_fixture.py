"""Shared synthetic runtime-hashing identity for unit plans (fictitious paths and digests)."""


def synthetic_hashing_identity(interpreter='1'*64):
    def art(role, path, n):
        return dict(role=role, path=path, size=n, sha256=format(n, '064x'))
    rows = [art('hashlib_extension', 'X:/rt/_hashlib.pyd', 11),
            dict(role='interpreter', path='X:/rt/python.exe', size=5, sha256=interpreter),
            art('libcrypto', 'X:/rt/libcrypto-3-x64.dll', 13), art('python_dll', 'X:/rt/python312.dll', 17)]
    return dict(schema='hashlab-e002-runtime-hashing-identity-v1', sha256_provider='_hashlib',
                libcrypto_version='OpenSSL 3.5.8 synthetic', python_version='3.13.0', artifacts=rows)
