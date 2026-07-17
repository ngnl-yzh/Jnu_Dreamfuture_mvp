from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import EmailVerification, User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    SignupRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_email_code,
    hash_email_code,
    hash_password,
    verify_password,
)
from app.services.credits import add_credit, credit_balance, point_balance
from app.services.emailer import send_verification_code

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_CODE_ATTEMPTS = 5


def _require_jnu_email(email: str) -> None:
    domain = get_settings().allowed_email_domain
    if not email.lower().endswith("@" + domain):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"@{domain} 이메일만 가입할 수 있습니다"
        )


def _issue_code(db: Session, email: str) -> None:
    settings = get_settings()
    # 레이트 리밋: 같은 이메일로 최근 발송 후 일정 시간 내 재발송 금지
    recent = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.email == email, EmailVerification.consumed_at.is_(None))
        .order_by(EmailVerification.created_at.desc())
    )
    now = datetime.now(timezone.utc)
    if recent is not None:
        created = recent.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if (now - created).total_seconds() < settings.email_code_resend_seconds:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "잠시 후 다시 시도해주세요")

    code, code_hash = generate_email_code()
    db.add(
        EmailVerification(
            email=email,
            code_hash=code_hash,
            expires_at=now + timedelta(minutes=settings.email_code_expire_minutes),
        )
    )
    db.commit()
    send_verification_code(email, code)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    _require_jnu_email(body.email)
    if not body.consent_privacy:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "개인정보 수집·이용 동의가 필요합니다")
    if db.scalar(select(User).where(User.email == body.email.lower())) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 가입된 이메일입니다")

    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        consent_privacy=body.consent_privacy,
        consent_data_share=body.consent_data_share,
    )
    db.add(user)
    db.commit()
    _issue_code(db, user.email)
    return {"message": "가입 완료. 이메일로 발송된 인증 코드를 확인해주세요."}


@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "가입되지 않은 이메일입니다")

    if body.code is None:
        if user.jnu_verified:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "이미 인증된 계정입니다")
        _issue_code(db, email)
        return {"message": "인증 코드를 발송했습니다."}

    row = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.email == email, EmailVerification.consumed_at.is_(None))
        .order_by(EmailVerification.created_at.desc())
    )
    now = datetime.now(timezone.utc)
    if row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "발송된 인증 코드가 없습니다")

    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "인증 코드가 만료되었습니다")
    if row.attempts >= MAX_CODE_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "시도 횟수를 초과했습니다. 코드를 재발송해주세요")
    if row.code_hash != hash_email_code(body.code):
        row.attempts += 1
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "인증 코드가 일치하지 않습니다")

    row.consumed_at = now
    if not user.jnu_verified:
        user.jnu_verified = True
        user.jnu_verified_at = now
        # 가입 보너스는 이메일 인증 완료 시점에 1회 지급 (어뷰징 방지)
        add_credit(db, user.id, get_settings().credit_signup_bonus, "signup_bonus")
    db.commit()
    return {"message": "이메일 인증이 완료되었습니다."}


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(body.refresh_token, "refresh")
    if user_id is None or db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 리프레시 토큰입니다")
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        is_admin=user.is_admin,
        jnu_verified=user.jnu_verified,
        consent_privacy=user.consent_privacy,
        consent_data_share=user.consent_data_share,
        credit_balance=credit_balance(db, user.id),
        point_balance=point_balance(db, user.id),
    )
