"""Tests for :mod:`utils.passwords` (PBKDF2 hashing).

Layer: tests
Author: Siddhi Baluja
"""

from __future__ import annotations

from utils.passwords import hash_password, verify_password

FAST = 1_000  # low work factor keeps the tests quick


def test_round_trip() -> None:
    """The right password verifies; a wrong one does not."""
    stored = hash_password("S3cret!pass", FAST)
    assert verify_password("S3cret!pass", stored)
    assert not verify_password("s3cret!pass", stored)


def test_salt_makes_hashes_unique() -> None:
    """The same password hashes differently each time."""
    assert hash_password("same-password", FAST) != hash_password("same-password", FAST)


def test_format_carries_iterations() -> None:
    """The work factor is stored, so old hashes keep verifying after a config change."""
    algorithm, iterations, salt, digest = hash_password("pw123456", FAST).split("$")
    assert (algorithm, iterations) == ("pbkdf2_sha256", str(FAST))
    assert len(salt) == 32 and len(digest) == 64


def test_tampered_or_malformed_hash_fails() -> None:
    """A modified or garbage hash never verifies (and never raises)."""
    stored = hash_password("pw123456", FAST)
    tampered = stored[:-1] + ("0" if stored[-1] != "0" else "1")
    assert not verify_password("pw123456", tampered)
    for garbage in ("", "plain-text", "md5$1$aa$bb", "pbkdf2_sha256$x$zz$yy"):
        assert not verify_password("pw123456", garbage)
