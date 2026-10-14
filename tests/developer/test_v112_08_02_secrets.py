from __future__ import annotations

import re

import pytest

from app.modules.developer.security.secrets import DeveloperSecretHasher


def test_generated_secret_is_random_and_sufficiently_long():
    hasher = DeveloperSecretHasher()

    first = hasher.generate()
    second = hasher.generate()

    assert first.raw != second.raw
    assert len(first.raw) >= 32


def test_raw_secret_is_not_equal_to_persisted_hash():
    hasher = DeveloperSecretHasher()

    generated = hasher.generate()
    encoded = hasher.encode(generated.hash)

    assert generated.raw not in encoded
    assert encoded != generated.raw


def test_hash_is_not_reversible_and_contains_no_raw_secret():
    hasher = DeveloperSecretHasher()

    generated = hasher.generate()
    encoded = hasher.encode(generated.hash)

    assert encoded.startswith("pbkdf2_sha256$")
    assert generated.raw not in encoded
    assert re.fullmatch(r"pbkdf2_sha256\$\d+\$[^$]+\$[^$]+", encoded)


def test_correct_secret_verifies():
    hasher = DeveloperSecretHasher()

    generated = hasher.generate()

    assert hasher.verify(generated.raw, generated.hash) is True


def test_wrong_secret_is_rejected():
    hasher = DeveloperSecretHasher()

    generated = hasher.generate()

    assert hasher.verify("wrong-secret-value", generated.hash) is False


def test_hash_round_trip_preserves_verification():
    hasher = DeveloperSecretHasher()

    generated = hasher.generate()
    encoded = hasher.encode(generated.hash)
    restored = hasher.decode(encoded)

    assert hasher.verify(generated.raw, restored) is True


def test_invalid_encoded_hash_is_rejected():
    hasher = DeveloperSecretHasher()

    with pytest.raises(ValueError):
        hasher.decode("not-a-valid-hash")


def test_unsupported_hash_algorithm_is_rejected():
    hasher = DeveloperSecretHasher()

    with pytest.raises(ValueError):
        hasher.decode("sha256$310000$salt$digest")


def test_non_text_secret_is_rejected():
    hasher = DeveloperSecretHasher()

    generated = hasher.generate()

    assert hasher.verify(None, generated.hash) is False


def test_each_hash_uses_a_different_salt():
    hasher = DeveloperSecretHasher()

    first = hasher.generate()
    second = hasher.generate()

    assert first.raw != second.raw
    assert first.hash.salt != second.hash.salt
    assert first.hash.digest != second.hash.digest
