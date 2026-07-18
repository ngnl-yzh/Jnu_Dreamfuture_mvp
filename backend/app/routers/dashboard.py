from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Mvp, Review, TestStep, User
from app.models.mvp import FIXED_CATEGORIES

router = APIRouter(prefix="/api/me", tags=["dashboard"])


def _nps_score(values: list[int]) -> float | None:
    if not values:
        return None
    promoters = sum(1 for v in values if v >= 9)
    detractors = sum(1 for v in values if v <= 6)
    return round((promoters - detractors) / len(values) * 100, 1)


def _mvp_stats(db: Session, mvp: Mvp) -> dict:
    reviews = db.scalars(select(Review).where(Review.mvp_id == mvp.id)).all()
    steps = db.scalars(
        select(TestStep).where(TestStep.mvp_id == mvp.id).order_by(TestStep.step_order)
    ).all()

    rating_dist = {str(i): 0 for i in range(1, 6)}
    for r in reviews:
        rating_dist[str(r.rating)] += 1

    # 단계별 이탈: 커스텀 단계 기준 + 고정 4카테고리 공통 통계
    stuck_by_step = {
        s.id: {"step_order": s.step_order, "title": s.title,
               "fixed_category": s.fixed_category, "stuck_count": 0}
        for s in steps
    }
    stuck_by_category = {c: 0 for c in FIXED_CATEGORIES}
    for r in reviews:
        if r.stuck_step_id and r.stuck_step_id in stuck_by_step:
            stuck_by_step[r.stuck_step_id]["stuck_count"] += 1
            stuck_by_category[stuck_by_step[r.stuck_step_id]["fixed_category"]] += 1

    ratings = [r.rating for r in reviews]
    return {
        "mvp_id": mvp.id,
        "title": mvp.title,
        "status": mvp.status,
        "view_count": mvp.view_count,
        "review_count": len(reviews),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "rating_distribution": rating_dist,
        "onboarding_success_rate": (
            round(sum(1 for r in reviews if r.onboarding_ok) / len(reviews) * 100, 1)
            if reviews else None
        ),
        "core_reach_rate": (
            round(sum(1 for r in reviews if r.reached_core) / len(reviews) * 100, 1)
            if reviews else None
        ),
        "stuck_by_step": list(stuck_by_step.values()),
        "stuck_by_category": stuck_by_category,
        "nps": _nps_score([r.nps for r in reviews]),
    }


@router.get("/dashboard")
def my_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """제작자 대시보드. 사이트 내 열람은 반출 승인이 필요 없다 (가이드라인 6.5)."""
    mvps = db.scalars(
        select(Mvp).where(Mvp.owner_id == user.id).order_by(Mvp.created_at.desc())
    ).all()
    return {"mvps": [_mvp_stats(db, m) for m in mvps]}
