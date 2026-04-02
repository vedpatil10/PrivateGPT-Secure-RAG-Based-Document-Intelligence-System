"""
Security utilities — JWT tokens, password hashing, file encryption.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from config.settings import get_settings


# ── Password Hashing ────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ───────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with tenant & role claims."""
    settings = get_settings()
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


# ── File Encryption ──────────────────────────────────────────────

def get_fernet() -> Fernet:
    """Get a Fernet encryption instance."""
    settings = get_settings()
    key = settings.encryption_key
    # If the key isn't a valid Fernet key, generate one deterministically
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Use a derived key for development
        import hashlib
        import base64
        derived = hashlib.sha256(key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(derived)
        return Fernet(fernet_key)


def encrypt_file(data: bytes) -> bytes:
    """Encrypt file data."""
    return get_fernet().encrypt(data)


def decrypt_file(encrypted_data: bytes) -> bytes:
    """Decrypt file data."""
    return get_fernet().decrypt(encrypted_data)


# ── API Key Generation ───────────────────────────────────────────

def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"pgpt_{secrets.token_urlsafe(32)}"
