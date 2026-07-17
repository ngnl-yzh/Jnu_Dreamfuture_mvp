from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class CreditLedger(Base):
    """소모형 크레딧 원장. 잔액 컬럼은 두지 않고 delta 합산으로 계산한다."""

    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)  # +3 가입 / +1 평가 / -3 등록 / 회수
    reason: Mapped[str] = mapped_column(String(50))  # signup_bonus | review_reward | mvp_cost | penalty
    ref_id: Mapped[int | None] = mapped_column(Integer)  # 관련 리뷰/MVP id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PointLedger(Base):
    """누적형 포인트 원장. 보상 전환용, 현재는 적립(및 회수)만."""

    __tablename__ = "point_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(50))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
