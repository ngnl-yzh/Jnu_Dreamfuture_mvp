from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiToken, User
from app.security import API_TOKEN_PREFIX, decode_token, hash_api_token


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증이 필요합니다")
    return auth.removeprefix("Bearer ").strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """JWT 액세스 토큰 또는 API 토큰(jnu_ 접두사) 모두 허용. 웹/API/CLI 공용."""
    token = _bearer_token(request)

    if token.startswith(API_TOKEN_PREFIX):
        row = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_api_token(token)))
        if row is None or row.revoked_at is not None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 API 토큰입니다")
        row.last_used_at = datetime.now(timezone.utc)
        db.commit()
        user = db.get(User, row.user_id)
    else:
        user_id = decode_token(token, "access")
        user = db.get(User, user_id) if user_id is not None else None

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 인증입니다")
    return user


def require_verified(user: User = Depends(get_current_user)) -> User:
    """전대 이메일 미인증 계정은 업로드/등록/평가 등 모든 핵심 기능 403."""
    if not user.jnu_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "전남대 이메일 인증이 필요합니다")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본부 관리자 권한이 필요합니다")
    return user
