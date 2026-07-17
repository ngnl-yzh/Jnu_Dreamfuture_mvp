from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow

EXPORT_STATUSES = ("pending", "approved", "rejected")
REPORT_STATUSES = ("pending", "confirmed", "dismissed")


class DataExportRequest(Base):
    __tablename__ = "data_export_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    mvp_id: Mapped[int] = mapped_column(ForeignKey("mvp.id"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    # 자유 서술 텍스트 포함 여부는 신청 시 옵션으로 분리 (본부 협의 사항)
    include_free_text: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    decision_note: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExportAuditLog(Base):
    __tablename__ = "export_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    export_request_id: Mapped[int] = mapped_column(ForeignKey("data_export_request.id"), index=True)
    exported_by: Mapped[int] = mapped_column(ForeignKey("user.id"))
    data_scope: Mapped[str] = mapped_column(String(100))  # 예: reviews_csv, reviews_json+free_text
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "report"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(20))  # review | mvp
    target_id: Mapped[int] = mapped_column(Integer)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
