"""크레딧/포인트 원장 서비스. 잔액 컬럼 없이 delta 합산이 유일한 진실."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CreditLedger, PointLedger


def credit_balance(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(CreditLedger.user_id == user_id)
    )


def point_balance(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(PointLedger.delta), 0)).where(PointLedger.user_id == user_id)
    )


def add_credit(db: Session, user_id: int, delta: int, reason: str, ref_id: int | None = None) -> None:
    db.add(CreditLedger(user_id=user_id, delta=delta, reason=reason, ref_id=ref_id))


def add_point(db: Session, user_id: int, delta: int, reason: str, ref_id: int | None = None) -> None:
    db.add(PointLedger(user_id=user_id, delta=delta, reason=reason, ref_id=ref_id))
