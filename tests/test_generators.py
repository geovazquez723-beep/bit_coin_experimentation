from __future__ import annotations

import itertools

import pytest

from hashlab.candidates import (
    PatternedGenerator,
    RandomBytesGenerator,
    SequentialGenerator,
    StructuredGenerator,
    UniformIntegerGenerator,
    build_generator,
    derive_seed,
    expected_duplicates,
)
from hashlab.candidates.patterned import minimal_period, mobius, primitive_word_count
from hashlab.candidates.structured import gray_code, reverse_bits


def take(gen, n, seed=None, start=0):
    return list(itertools.islice(gen.stream(seed, start), n))


# ---- determinism


@pytest.mark.parametrize(
    "gen,seed",
    [
        (SequentialGenerator("a", 4), None),
        (SequentialGenerator("b", 6, encoding="ascii-decimal", start=17), None),
        (UniformIntegerGenerator("c", 8), 99),
        (UniformIntegerGenerator("d", 10, encoding="ascii-decimal"), 99),
        (PatternedGenerator("e", 6, max_period=3), None),
        (StructuredGenerator("f", 4, mode="stride", stride=12345, offset=7), None),
        (RandomBytesGenerator("g", 13), 99),
    ],
)
def test_generators_reproduce_exactly(gen, seed) -> None:
    assert take(gen, 200, seed) == take(gen, 200, seed)
    assert all(isinstance(c, bytes) and len(c) == gen.width for c in take(gen, 200, seed))


def test_seeded_generators_differ_across_seeds() -> None:
    for gen in (UniformIntegerGenerator("u", 8), RandomBytesGenerator("r", 8)):
        assert take(gen, 50, 1) != take(gen, 50, 2)


def test_seeded_generators_require_seed() -> None:
    with pytest.raises(ValueError):
        next(UniformIntegerGenerator("u", 8).stream(None))
    with pytest.raises(ValueError):
        next(RandomBytesGenerator("r", 8).stream(None))


def test_derive_seed_is_stable_and_label_sensitive() -> None:
    assert derive_seed(1, "g", "discovery") == derive_seed(1, "g", "discovery")
    assert derive_seed(1, "g", "discovery") != derive_seed(1, "g", "validation")
    assert derive_seed(1, "g", "discovery") != derive_seed(2, "g", "discovery")
    assert 0 <= derive_seed(1, "x") < 2**64


def test_random_bytes_stream_is_a_contiguous_slicing() -> None:
    narrow = b"".join(take(RandomBytesGenerator("r", 3), 100, 5))
    wide = b"".join(take(RandomBytesGenerator("r", 100), 3, 5))
    assert narrow == wide


# ---- domains: characters vs bytes


def test_ascii_decimal_is_a_character_domain_distinct_from_bytes() -> None:
    dec = SequentialGenerator("d", 4, encoding="ascii-decimal")
    raw = SequentialGenerator("r", 4, encoding="be-bytes")
    assert take(dec, 1, start=42) == [b"0042"]
    assert take(raw, 1, start=42) == [b"\x00\x00\x00\x2a"]
    assert dec.domain().kind == "ascii-chars" and dec.domain().cardinality == 10**4
    assert raw.domain().kind == "bytes" and raw.domain().cardinality == 256**4


def test_uniform_ascii_decimal_only_produces_digits() -> None:
    for c in take(UniformIntegerGenerator("u", 12, encoding="ascii-decimal"), 300, 3):
        assert c.isdigit() and len(c) == 12


def test_repeated_chars_stay_in_alphabet() -> None:
    gen = PatternedGenerator("p", 6, mode="repeated-chars", alphabet="digits", max_period=3)
    assert gen.domain().kind == "ascii-chars"
    for c in take(gen, 1000):
        assert set(c) <= set(b"0123456789")


def test_repeated_bytes_includes_zero_and_ff_runs() -> None:
    first = take(PatternedGenerator("p", 4, max_period=2), 256)
    assert first[0] == b"\x00" * 4 and first[255] == b"\xff" * 4


# ---- uniqueness and exact domain sizes


@pytest.mark.parametrize("mode", ["gray", "stride", "bit-reversed"])
def test_structured_modes_are_bijections_on_small_domain(mode: str) -> None:
    kwargs = {"stride": 77, "offset": 5} if mode == "stride" else {}
    gen = StructuredGenerator("s", 2, mode=mode, **kwargs)
    everything = list(gen.stream(None))
    assert len(everything) == 65536
    assert len(set(everything)) == 65536


def test_structured_rejects_even_stride() -> None:
    with pytest.raises(ValueError):
        StructuredGenerator("s", 4, mode="stride", stride=4)


def test_gray_and_bit_reverse_helpers() -> None:
    assert [gray_code(i) for i in range(5)] == [0, 1, 3, 2, 6]
    assert reverse_bits(1, 8) == 128
    assert reverse_bits(0b1101, 4) == 0b1011


def test_sequential_exhausts_instead_of_wrapping() -> None:
    gen = SequentialGenerator("s", 1)
    everything = list(gen.stream(None))
    assert len(everything) == 256 and len(set(everything)) == 256
    assert list(gen.stream(None, 300)) == []
    assert gen.available(250) == 6


def test_sequential_start_index_continues_without_overlap() -> None:
    gen = SequentialGenerator("s", 3, start=10)
    discovery = take(gen, 100)
    validation = take(gen, 100, start=100)
    assert not set(discovery) & set(validation)
    assert discovery + validation == take(gen, 200)


@pytest.mark.parametrize("alphabet_size,width,max_period", [(2, 6, 3), (3, 8, 4), (4, 4, 2), (2, 10, 5)])
def test_patterned_cardinality_matches_brute_force(alphabet_size: int, width: int, max_period: int) -> None:
    chars = "abcd"[:alphabet_size]
    gen = PatternedGenerator("p", width, mode="repeated-chars", alphabet_chars=chars, max_period=max_period)
    everything = list(gen.stream(None))
    assert len(everything) == len(set(everything)), "duplicate candidate emitted"
    brute = {
        bytes(w)
        for w in itertools.product(chars.encode(), repeat=width)
        if minimal_period(bytes(w)) <= max_period
    }
    assert set(everything) == brute
    assert gen.domain().cardinality == len(brute)


def test_patterned_start_index_skips_exactly() -> None:
    gen = PatternedGenerator("p", 6, max_period=2)
    assert take(gen, 10, start=300) == take(gen, 310)[300:]


def test_patterned_requires_width_at_least_twice_period() -> None:
    with pytest.raises(ValueError):
        PatternedGenerator("p", 5, max_period=3)


def test_minimal_period_and_mobius() -> None:
    assert minimal_period(b"aaaa") == 1
    assert minimal_period(b"abab") == 2
    assert minimal_period(b"abaab") == 3
    assert minimal_period(b"abcd") == 4
    assert [mobius(n) for n in range(1, 11)] == [1, -1, -1, 0, -1, 1, -1, 0, 0, 1]
    assert primitive_word_count(2, 4) == 12  # 16 - 4 (powers of words of length 1 and 2)


def test_uniform_small_domain_produces_duplicates() -> None:
    draws = take(UniformIntegerGenerator("u", 1), 1000, 4)
    assert len(set(draws)) < len(draws)
    assert set(draws) <= {bytes([b]) for b in range(256)}


def test_expected_duplicates_formula() -> None:
    assert expected_duplicates(0, 10) == 0.0
    assert expected_duplicates(2, 2) == pytest.approx(0.5)
    assert expected_duplicates(10**6, 2**64) == pytest.approx(10**6 * (10**6 - 1) / 2 / 2**64)


def test_build_generator_validates() -> None:
    assert isinstance(build_generator({"id": "x", "type": "structured", "width": 2}), StructuredGenerator)
    with pytest.raises(ValueError):
        build_generator({"id": "x", "type": "nope", "width": 2})
    with pytest.raises(ValueError):
        build_generator({"id": "x", "type": "sequential", "width": 2, "bogus": 1})
    with pytest.raises(ValueError):
        build_generator({"type": "sequential", "width": 2})
