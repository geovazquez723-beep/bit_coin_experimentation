from __future__ import annotations

import hashlib
from fractions import Fraction

import pytest

from hashlab.experiments.selfcheck import SHA256_VECTORS, SHA256D_VECTORS
from hashlab.hashing import SHA256dEngine, SHA256Engine, Target, digest_to_int, get_engine, leading_zero_bits

MILLION_A = "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"


@pytest.mark.parametrize("message,expected", list(SHA256_VECTORS.items()))
def test_sha256_known_vectors(message: bytes, expected: str) -> None:
    assert SHA256Engine().digest(message).hex() == expected


def test_sha256_million_a_vector() -> None:
    assert SHA256Engine().digest(b"a" * 1_000_000).hex() == MILLION_A


@pytest.mark.parametrize("message,expected", list(SHA256D_VECTORS.items()))
def test_sha256d_known_vectors(message: bytes, expected: str) -> None:
    assert SHA256dEngine().digest(message).hex() == expected


def test_sha256d_is_sha256_of_sha256_digest_bytes_not_hex() -> None:
    inner = hashlib.sha256(b"hashlab").digest()
    assert SHA256dEngine().digest(b"hashlab") == hashlib.sha256(inner).digest()
    assert SHA256dEngine().digest(b"hashlab") != hashlib.sha256(inner.hex().encode()).digest()


def test_get_engine_rejects_unknown() -> None:
    assert get_engine("sha256d").name == "sha256d"
    with pytest.raises(ValueError):
        get_engine("md5")


# ---- leading-zero bytes and big-endian interpretation


def test_digest_to_int_keeps_leading_zero_bytes() -> None:
    digest = bytes([0x00, 0x00, 0x01]) + bytes(29)
    value = digest_to_int(digest)
    assert value == 1 << (256 - 24)
    assert leading_zero_bits(value) == 23
    assert value.to_bytes(32, "big") == digest


def test_leading_zero_bits_extremes() -> None:
    assert leading_zero_bits(0) == 256
    assert leading_zero_bits((1 << 256) - 1) == 0
    assert leading_zero_bits(1) == 255
    with pytest.raises(ValueError):
        leading_zero_bits(1 << 256)


def test_digest_to_int_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        digest_to_int(bytes(31))


def test_all_zero_digest_is_success_for_any_valid_target() -> None:
    assert Target(1).hit(digest_to_int(bytes(32)))


# ---- exact target boundaries


@pytest.mark.parametrize("bits", [0, 1, 8, 13, 32, 255, 256])
def test_leading_zero_target_boundary_is_exact(bits: int) -> None:
    target = Target.from_leading_zero_bits(bits)
    assert target.value == 1 << (256 - bits)
    assert target.hit(target.value - 1)
    assert not target.hit(target.value)
    assert target.equivalent_leading_zero_bits == bits


def test_k_leading_zero_bits_iff_below_target() -> None:
    target = Target.from_leading_zero_bits(12)
    just_below = (1 << 244) - 1  # exactly 12 leading zeros
    at = 1 << 244  # 11 leading zeros
    assert leading_zero_bits(just_below) == 12 and target.hit(just_below)
    assert leading_zero_bits(at) == 11 and not target.hit(at)


def test_non_power_of_two_target_uses_integer_comparison() -> None:
    # Hex "prefix" logic would wrongly treat 0x00ff... and 0x0100... alike at 1 byte of precision.
    target = Target.from_hex("00ff" + "00" * 30)
    assert target.equivalent_leading_zero_bits is None
    assert target.hit(int("00fe" + "ff" * 30, 16))
    assert not target.hit(int("00ff" + "00" * 30, 16))
    assert not target.hit(int("00ff" + "00" * 29 + "01", 16))


def test_target_validation() -> None:
    with pytest.raises(ValueError):
        Target(0)
    with pytest.raises(ValueError):
        Target((1 << 256) + 1)
    with pytest.raises(ValueError):
        Target.from_leading_zero_bits(257)
    with pytest.raises(ValueError):
        Target.from_hex("xyz")
    with pytest.raises(ValueError):
        Target.from_config({"leading_zero_bits": 4, "target_hex": "ff"})


# ---- probabilities


@pytest.mark.parametrize("bits", [0, 1, 8, 20, 64])
def test_probability_for_leading_zero_bits_is_exact(bits: int) -> None:
    assert Target.from_leading_zero_bits(bits).probability == Fraction(1, 2**bits)


def test_probability_for_arbitrary_target() -> None:
    target = Target(3 << 250)
    assert target.probability == Fraction(3, 64)
    assert target.to_dict()["success_probability_exact"] == "3/64"


def test_target_config_forms_agree() -> None:
    a = Target.from_config({"leading_zero_bits": 8})
    b = Target.from_config({"target_hex": "01" + "00" * 31})
    c = Target.from_config({"target_int": str(1 << 248)})
    assert a == b == c
