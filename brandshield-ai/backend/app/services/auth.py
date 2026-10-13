import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, Optional, Tuple

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import settings

# Initialize Argon2 password hasher
password_hasher = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash."""
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, int]:
    """
    Create a signed JWT access token.
    Returns (token_string, expires_in_seconds).
    """
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_utc = now_utc + delta
    
    to_encode.update({
        "exp": expire_utc,
        "iat": now_utc,
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    expires_in_seconds = int(delta.total_seconds())
    return encoded_jwt, expires_in_seconds


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises jwt.PyJWTError on invalid, tampered, or expired tokens.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ---------------------------------------------------------------------------
# In-Memory Login Rate Limiter (Brute-Force Protection)
# ---------------------------------------------------------------------------
class LoginRateLimiter:
    """
    Simple in-memory rate limiter tracking failed login attempts per key (email or IP).
    Limits to 5 failed attempts per 5-minute window.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: Dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            attempts = [t for t in self._failures[key] if now - t < self.window_seconds]
            self._failures[key] = attempts
            return len(attempts) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._failures[key].append(now)

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=300)
