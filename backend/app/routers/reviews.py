from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, require_verified
from app.models import Mvp, Review, ReviewVote, TestStep, User
from app.schemas.review import ReviewBody, ReviewItem, VoteRequest
from app.services.credits import add_credit, add_point

router = APIRouter(tags=["reviews"])


def _validate_review(db: Session, mvp: Mvp, body: ReviewBody) -> None:
    settings = get_settings()
    if len(body.improvement_note.strip()) < settings.review_improvement_min_chars:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"개선 제안은 최소 {settings.review_improvement_min_chars}자 이상 작성해주세요",
        )
    if not body.reached_core and body.stuck_step_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "핵심 기능 미도달 시 막힌 단계를 선택해주세요")
    if body.stuck_step_id is not None:
        step = db.get(TestStep, body.stuck_step_id)
        if step is None or step.mvp_id != mvp.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "막힌 단계가 이 MVP의 테스트 단계가 아닙니다")


def _to_item(db: Session, review: Review, current_user_id: int | None) -> ReviewItem:
    reviewer = db.get(User, review.reviewer_id)
    step = db.get(TestStep, review.stuck_step_id) if review.stuck_step_id else None
    useful = db.scalar(
        select(func.count(ReviewVote.id)).where(
            ReviewVote.review_id == review.id, ReviewVote.is_useful.is_(True)
        )
    )
    my_vote = None
    if current_user_id is not None:
        vote = db.scalar(select(ReviewVote).where(
            ReviewVote.review_id == review.id, ReviewVote.voter_id == current_user_id
        ))
        my_vote = vote.is_useful if vote else None
    return ReviewItem(
        id=review.id,
        mvp_id=review.mvp_id,
        reviewer_nickname=reviewer.nickname if reviewer else "탈퇴 회원",
        first_impression=review.first_impression,
        onboarding_ok=review.onboarding_ok,
        onboarding_note=review.onboarding_note,
        reached_core=review.reached_core,
        stuck_step_id=review.stuck_step_id,
        stuck_step_title=step.title if step else None,
        stuck_note=review.stuck_note,
        rating=review.rating,
        improvement_note=review.improvement_note,
        nps=review.nps,
        useful_count=useful,
        my_vote=my_vote,
        is_mine=current_user_id == review.reviewer_id,
        created_at=review.created_at,
    )


@router.get("/api/mvps/{mvp_id}/reviews", response_model=list[ReviewItem])
def list_reviews(
    mvp_id: int,
    sort: str = "latest",  # latest | useful
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    reviews = db.scalars(select(Review).where(Review.mvp_id == mvp_id)).all()
    items = [_to_item(db, r, user.id) for r in reviews]
    if sort == "useful":
        items.sort(key=lambda x: (x.useful_count, x.created_at), reverse=True)
    else:
        items.sort(key=lambda x: x.created_at, reverse=True)
    return items


@router.post("/api/mvps/{mvp_id}/reviews", response_model=ReviewItem, status_code=status.HTTP_201_CREATED)
def create_review(
    mvp_id: int,
    body: ReviewBody,
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or mvp.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    if mvp.owner_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "자신의 MVP에는 평가를 남길 수 없습니다")
    if db.scalar(select(Review).where(Review.mvp_id == mvp_id, Review.reviewer_id == user.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 평가를 작성했습니다 (수정만 가능)")
    _validate_review(db, mvp, body)

    review = Review(mvp_id=mvp_id, reviewer_id=user.id, **body.model_dump())
    db.add(review)
    db.flush()
    # 평가 완성 보상: 크레딧 +1, 포인트 +1 (원장 기록)
    settings = get_settings()
    add_credit(db, user.id, settings.credit_review_reward, "review_reward", ref_id=review.id)
    add_point(db, user.id, settings.point_review_reward, "review_reward", ref_id=review.id)
    db.commit()
    return _to_item(db, review, user.id)


@router.put("/api/reviews/{review_id}", response_model=ReviewItem)
def update_review(
    review_id: int,
    body: ReviewBody,
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None or review.reviewer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "평가를 찾을 수 없습니다")
    mvp = db.get(Mvp, review.mvp_id)
    _validate_review(db, mvp, body)
    for field, value in body.model_dump().items():
        setattr(review, field, value)
    db.commit()
    return _to_item(db, review, user.id)


@router.delete("/api/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    review = db.get(Review, review_id)
    if review is None or review.reviewer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "평가를 찾을 수 없습니다")
    # 삭제 시 지급 보상 회수 (삭제→재작성 반복 어뷰징 방지)
    if not review.penalized:
        settings = get_settings()
        add_credit(db, user.id, -settings.credit_review_reward, "review_deleted", ref_id=review.id)
        add_point(db, user.id, -settings.point_review_reward, "review_deleted", ref_id=review.id)
    for vote in db.scalars(select(ReviewVote).where(ReviewVote.review_id == review.id)):
        db.delete(vote)
    db.delete(review)
    db.commit()


@router.post("/api/reviews/{review_id}/vote")
def vote_review(
    review_id: int,
    body: VoteRequest,
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "평가를 찾을 수 없습니다")
    if review.reviewer_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "자신의 평가에는 투표할 수 없습니다")
    vote = db.scalar(select(ReviewVote).where(
        ReviewVote.review_id == review_id, ReviewVote.voter_id == user.id
    ))
    if vote is None:
        db.add(ReviewVote(review_id=review_id, voter_id=user.id, is_useful=body.is_useful))
    else:
        vote.is_useful = body.is_useful
    db.commit()
    useful = db.scalar(
        select(func.count(ReviewVote.id)).where(
            ReviewVote.review_id == review_id, ReviewVote.is_useful.is_(True)
        )
    )
    return {"useful_count": useful}
