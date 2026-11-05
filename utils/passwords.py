"""Password hashing with PBKDF2-HMAC-SHA256 from the standard library.

Stored format: ``pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>``. The
iteration count travels with each hash, so raising ``auth.pbkdf2_iterations``
later still lets existing passwords verify. Plain passwords are never stored
or logged.

Layer: utils (stateless helpers)
Author: Siddhi Baluja
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
_SALT_BYTES = 16


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    """Run PBKDF2-HMAC-SHA256 over ``password``."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str, iterations: int) -> str:
    """Hash a password with a fresh random salt.

    Args:
        password: Plain-text password.
        iterations: PBKDF2 work factor (from ``auth.pbkdf2_iterations``).

    Returns:
        The encoded hash to store in ``users.password_hash``.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = _derive(password, salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against a stored hash in constant time.

    Args:
        password: Plain-text password typed by the user.
        encoded: Value from ``users.password_hash``.

    Returns:
        ``True`` when the password matches; ``False`` for a wrong password or
        a malformed hash.
    """
    try:
        algorithm, iterations, salt_hex, hash_hex = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = _derive(password, bytes.fromhex(salt_hex), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)
