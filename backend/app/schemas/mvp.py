from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.mvp import FIXED_CATEGORIES, RUNTIME_TYPES


class TestStepIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    guide_text: str = Field(default="", max_length=300)
    fixed_category: str

    @field_validator("fixed_category")
    @classmethod
    def check_category(cls, v: str) -> str:
        if v not in FIXED_CATEGORIES:
            raise ValueError(f"fixed_category는 {FIXED_CATEGORIES} 중 하나여야 합니다")
        return v


class TestStepOut(BaseModel):
    id: int
    step_order: int
    title: str
    guide_text: str
    fixed_category: str


class MvpCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    tagline: str = Field(min_length=1, max_length=200)
    description_md: str = ""
    category: str = Field(min_length=1, max_length=50)
    tags: list[str] = []
    runtime_type: str = "static"
    test_steps: list[TestStepIn]

    @field_validator("runtime_type")
    @classmethod
    def check_runtime(cls, v: str) -> str:
        if v not in RUNTIME_TYPES:
            raise ValueError(f"runtime_type은 {RUNTIME_TYPES} 중 하나여야 합니다")
        return v


class MvpItem(BaseModel):
    id: int
    title: str
    tagline: str
    category: str
    tags: list[str]
    runtime_type: str
    status: str
    owner_nickname: str
    view_count: int
    review_count: int
    avg_rating: float | None
    useful_vote_count: int
    created_at: datetime


class InstanceOut(BaseModel):
    status: str
    route_path: str  # iframe 임베드용 /run/{slug}


class MvpDetail(MvpItem):
    description_md: str
    owner_id: int
    test_steps: list[TestStepOut]
    instance: InstanceOut | None
    my_review_id: int | None = None


class ArtifactItem(BaseModel):
    """버전 이력. storage_key는 절대 포함하지 않는다 (소스코드 비노출)."""

    id: int
    version: int
    file_size: int
    validation_status: str
    publish_status: str
    upload_channel: str
    uploaded_at: datetime
