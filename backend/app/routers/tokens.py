from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_verified
from app.models import ApiToken, User
from app.schemas.auth import ApiTokenCreateRequest, ApiTokenCreateResponse, ApiTokenItem
from app.security import generate_api_token

# API 토큰은 전대 인증 완료 계정만 발급/조회 가능 (절대 원칙 3)
router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("", response_model=list[ApiTokenItem])
def list_tokens(user: User = Depends(require_verified), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())
    ).all()
    return [
        ApiTokenItem(
            id=t.id, label=t.label, created_at=t.created_at,
            last_used_at=t.last_used_at, revoked_at=t.revoked_at,
        )
        for t in rows
    ]


@router.post("", response_model=ApiTokenCreateResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    body: ApiTokenCreateRequest,
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    raw, token_hash = generate_api_token()
    row = ApiToken(user_id=user.id, token_hash=token_hash, label=body.label)
    db.add(row)
    db.commit()
    return ApiTokenCreateResponse(id=row.id, label=row.label, token=raw)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    row = db.get(ApiToken, token_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "토큰을 찾을 수 없습니다")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
