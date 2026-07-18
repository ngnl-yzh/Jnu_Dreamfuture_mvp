"""반출 데이터 익명화.

사용자 식별자(이메일·닉네임·계정ID)를 제거하고, MVP별로 일관된 가명 ID로 치환한다.
같은 사용자는 같은 MVP 반출 내에서 항상 같은 가명을 받는다 (시계열 분석 가능),
MVP가 다르면 가명도 달라진다 (교차 결합 방지).
"""

import hashlib

from app.config import get_settings


def pseudonym(mvp_id: int, user_id: int) -> str:
    digest = hashlib.sha256(
        f"{get_settings().secret_key}:{mvp_id}:{user_id}".encode()
    ).hexdigest()
    return f"rater-{digest[:10]}"


FREE_TEXT_FIELDS = ("onboarding_note", "stuck_note", "improvement_note")


def anonymized_review_rows(db, mvp, include_free_text: bool) -> list[dict]:
    from sqlalchemy import select

    from app.models import Review, TestStep

    rows = []
    for review in db.scalars(select(Review).where(Review.mvp_id == mvp.id)):
        step = db.get(TestStep, review.stuck_step_id) if review.stuck_step_id else None
        row = {
            "rater": pseudonym(mvp.id, review.reviewer_id),
            "first_impression": review.first_impression,
            "onboarding_ok": review.onboarding_ok,
            "reached_core": review.reached_core,
            "stuck_step_order": step.step_order if step else None,
            "stuck_step_category": step.fixed_category if step else None,
            "rating": review.rating,
            "nps": review.nps,
            "created_at": review.created_at.isoformat(),
        }
        if include_free_text:
            for field in FREE_TEXT_FIELDS:
                row[field] = getattr(review, field)
        rows.append(row)
    return rows
