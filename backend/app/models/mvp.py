from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User, utcnow

MVP_STATUSES = ("draft", "pending", "published", "rejected", "terminated")
RUNTIME_TYPES = ("static", "server", "notebook")
PUBLISH_STATUSES = ("draft", "published", "archived")
UPLOAD_CHANNELS = ("web", "api", "cli", "github")
FIXED_CATEGORIES = ("pre_entry", "setup", "core", "post")


class Mvp(Base):
    __tablename__ = "mvp"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    tagline: Mapped[str] = mapped_column(String(200))
    description_md: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), index=True)
    tags: Mapped[str] = mapped_column(String(255), default="")  # 콤마 구분
    runtime_type: Mapped[str] = mapped_column(String(20), default="static")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship()
    artifacts: Mapped[list["MvpArtifact"]] = relationship(back_populates="mvp")
    test_steps: Mapped[list["TestStep"]] = relationship(
        back_populates="mvp", order_by="TestStep.step_order"
    )
    instance: Mapped["MvpInstance | None"] = relationship(back_populates="mvp")


class MvpArtifact(Base):
    __tablename__ = "mvp_artifact"
    __table_args__ = (UniqueConstraint("mvp_id", "version", name="uq_artifact_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    mvp_id: Mapped[int] = mapped_column(ForeignKey("mvp.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    # 내부 스토리지 키. API 응답에 절대 노출 금지 (소스코드 비노출 원칙).
    storage_key: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String(20), default="valid")
    publish_status: Mapped[str] = mapped_column(String(20), default="draft")
    upload_channel: Mapped[str] = mapped_column(String(20), default="web")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    mvp: Mapped[Mvp] = relationship(back_populates="artifacts")


class MvpInstance(Base):
    __tablename__ = "mvp_instance"

    id: Mapped[int] = mapped_column(primary_key=True)
    mvp_id: Mapped[int] = mapped_column(ForeignKey("mvp.id"), unique=True)
    container_id: Mapped[str] = mapped_column(String(100), default="")
    route_path: Mapped[str] = mapped_column(String(100), default="")  # /run/{slug}
    status: Mapped[str] = mapped_column(String(20), default="stopped")
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    mvp: Mapped[Mvp] = relationship(back_populates="instance")


class TestStep(Base):
    __tablename__ = "test_step"

    id: Mapped[int] = mapped_column(primary_key=True)
    mvp_id: Mapped[int] = mapped_column(ForeignKey("mvp.id"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(100))
    guide_text: Mapped[str] = mapped_column(String(300), default="")
    # 플랫폼 공통 통계용 고정 4카테고리 매핑 (필수)
    fixed_category: Mapped[str] = mapped_column(String(20))

    mvp: Mapped[Mvp] = relationship(back_populates="test_steps")
