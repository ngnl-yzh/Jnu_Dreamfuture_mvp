import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

API_TOKEN_PREFIX = "jnu_"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def create_access_token(user_id: int) -> str:
    return _create_token(user_id, "access", timedelta(minutes=get_settings().access_token_expire_minutes))


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, "refresh", timedelta(days=get_settings().refresh_token_expire_days))


def decode_token(token: str, expected_type: str) -> int | None:
    """유효하면 user_id, 아니면 None."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None


def generate_api_token() -> tuple[str, str]:
    """(원문, 해시) 반환. 원문은 발급 응답에서 1회만 노출."""
    raw = API_TOKEN_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_token(raw)


def hash_api_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_email_code() -> tuple[str, str]:
    """6자리 인증 코드 (원문, 해시)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    return code, hashlib.sha256(code.encode()).hexdigest()


def hash_email_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
