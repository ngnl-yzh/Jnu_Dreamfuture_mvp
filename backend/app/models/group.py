from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class Group(Base):
    """수업/동아리 그룹. 후순위 Phase — 스키마만 선반영."""

    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(20), unique=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GroupMember(Base):
    __tablename__ = "group_member"

    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GroupAssignment(Base):
    __tablename__ = "group_assignment"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), index=True)
    mvp_id: Mapped[int] = mapped_column(ForeignKey("mvp.id"))
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
