"""Password hashing and stateless session tokens."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()

ALGORITHM = "HS256"
TOKEN_TYPE = "session"  # noqa: S105 - a token class name, not a secret


def hash_password(password: str) -> str:
    """Return an Argon2id hash of ``password``."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check ``password`` against a stored hash without leaking why it failed."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the stored hash uses outdated Argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return True


def create_session_token(subject: str) -> str:
    """Issue a signed session token for the given user id."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def read_session_token(token: str) -> str | None:
    """Return the user id in ``token``, or ``None`` if it is not usable."""
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None

    if payload.get("type") != TOKEN_TYPE:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def generate_webhook_token() -> str:
    """Generate an unguessable token for a workflow's webhook endpoint."""
    return secrets.token_urlsafe(32)
