from datetime import datetime

from pydantic import BaseModel, Field


class ReviewBody(BaseModel):
    """구조화 평가 폼 6항목 (전체 필수)."""

    first_impression: int = Field(ge=1, le=5)   # ① 첫인상
    onboarding_ok: bool                          # ② 온보딩 성공 여부
    onboarding_note: str = ""
    reached_core: bool                           # ③ 핵심 기능 도달
    stuck_step_id: int | None = None             #    막힌 단계 (미도달 시 필수)
    stuck_note: str = ""
    rating: int = Field(ge=1, le=5)              # ④ 완성도·유용성
    improvement_note: str                        # ⑤ 개선 제안 (최소 글자 수)
    nps: int = Field(ge=0, le=10)                # ⑥ 계속 쓸 의향


class ReviewItem(BaseModel):
    id: int
    mvp_id: int
    reviewer_nickname: str
    first_impression: int
    onboarding_ok: bool
    onboarding_note: str
    reached_core: bool
    stuck_step_id: int | None
    stuck_step_title: str | None
    stuck_note: str
    rating: int
    improvement_note: str
    nps: int
    useful_count: int
    my_vote: bool | None = None
    is_mine: bool = False
    created_at: datetime


class VoteRequest(BaseModel):
    is_useful: bool = True
