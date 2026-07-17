from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow


class Review(Base):
    __tablename__ = "review"
    # 동일 사용자는 동일 MVP에 평가 1회 (수정은 PUT으로)
    __table_args__ = (UniqueConstraint("mvp_id", "reviewer_id", name="uq_review_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mvp_id: Mapped[int] = mapped_column(ForeignKey("mvp.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    first_impression: Mapped[int] = mapped_column(Integer)  # 1-5
    onboarding_ok: Mapped[bool] = mapped_column(Boolean)
    onboarding_note: Mapped[str] = mapped_column(Text, default="")
    reached_core: Mapped[bool] = mapped_column(Boolean)
    stuck_step_id: Mapped[int | None] = mapped_column(ForeignKey("test_step.id"))
    stuck_note: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    improvement_note: Mapped[str] = mapped_column(Text)  # 최소 글자 수 검증
    nps: Mapped[int] = mapped_column(Integer)  # 0-10
    # 신고 확정 시 크레딧/포인트 회수 여부 (이중 회수 방지)
    penalized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    votes: Mapped[list["ReviewVote"]] = relationship(back_populates="review")


class ReviewVote(Base):
    __tablename__ = "review_vote"
    __table_args__ = (UniqueConstraint("review_id", "voter_id", name="uq_vote_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("review.id"), index=True)
    voter_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    is_useful: Mapped[bool] = mapped_column(Boolean, default=True)

    review: Mapped[Review] = relationship(back_populates="votes")
