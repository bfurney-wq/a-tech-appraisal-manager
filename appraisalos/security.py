
import base64
import hashlib
import hmac
import os


def new_salt() -> str:
    return base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8")


def hash_password(password: str, salt: str, iterations: int = 200_000) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected_hash)
