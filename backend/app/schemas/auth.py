from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=2, max_length=50)
    consent_privacy: bool
    consent_data_share: bool


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str | None = None  # 없으면 코드 발송, 있으면 확인


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str
    nickname: str
    is_admin: bool
    jnu_verified: bool
    consent_privacy: bool
    consent_data_share: bool
    credit_balance: int
    point_balance: int


class ApiTokenCreateRequest(BaseModel):
    label: str = Field(default="", max_length=100)


class ApiTokenCreateResponse(BaseModel):
    id: int
    label: str
    token: str  # 원문은 이 응답에서 1회만 노출


class ApiTokenItem(BaseModel):
    id: int
    label: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
