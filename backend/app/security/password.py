"""Vulnova Argon2id Password Hashing & Verification Adapter."""

from passlib.context import CryptContext

# Configure Passlib with Argon2id algorithm
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id.

    Args:
        password: The plaintext password string to hash.

    Returns:
        The Argon2id hashed password string.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Args:
        plain_password: The plaintext password string.
        hashed_password: The Argon2id hashed password string.

    Returns:
        True if password matches hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
