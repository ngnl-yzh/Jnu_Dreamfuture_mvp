from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_admin, require_verified
from app.models import (
    DataExportRequest,
    ExportAuditLog,
    Mvp,
    MvpInstance,
    Report,
    Review,
    User,
)
from app.sandbox.runner import get_runner
from app.services.credits import add_credit, add_point

router = APIRouter(tags=["admin"])


class DecisionBody(BaseModel):
    note: str = ""


class ReportBody(BaseModel):
    target_type: str  # review | mvp
    target_id: int
    reason: str = Field(min_length=5)


# ---------- 신고 접수 (일반 회원) ----------

@router.post("/api/reports", status_code=status.HTTP_201_CREATED)
def create_report(body: ReportBody, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    if body.target_type not in ("review", "mvp"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "target_type은 review 또는 mvp여야 합니다")
    model = Review if body.target_type == "review" else Mvp
    if db.get(model, body.target_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "신고 대상을 찾을 수 없습니다")
    report = Report(
        target_type=body.target_type, target_id=body.target_id,
        reporter_id=user.id, reason=body.reason,
    )
    db.add(report)
    db.commit()
    return {"id": report.id, "status": report.status}


# ---------- MVP 승인/반려/강제 종료 ----------

@router.get("/api/admin/mvps")
def admin_list_mvps(status_filter: str = "pending", admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    mvps = db.scalars(
        select(Mvp).where(Mvp.status == status_filter).order_by(Mvp.created_at)
    ).all()
    return [
        {"id": m.id, "title": m.title, "tagline": m.tagline, "category": m.category,
         "runtime_type": m.runtime_type, "status": m.status,
         "owner_nickname": m.owner.nickname, "created_at": m.created_at}
        for m in mvps
    ]


@router.post("/api/admin/mvps/{mvp_id}/approve")
def approve_mvp(mvp_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or mvp.status != "pending":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "승인 대기 중인 MVP가 아닙니다")
    mvp.status = "published"
    db.commit()
    return {"id": mvp.id, "status": mvp.status}


@router.post("/api/admin/mvps/{mvp_id}/reject")
def reject_mvp(mvp_id: int, body: DecisionBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or mvp.status != "pending":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "승인 대기 중인 MVP가 아닙니다")
    mvp.status = "rejected"
    db.commit()
    return {"id": mvp.id, "status": mvp.status}


@router.post("/api/admin/mvps/{mvp_id}/terminate")
def terminate_mvp(mvp_id: int, body: DecisionBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """게시 중인 MVP 강제 종료: 노출 차단 + 실행 중 컨테이너 정리."""
    mvp = db.get(Mvp, mvp_id)
    if mvp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    mvp.status = "terminated"
    instance = db.scalar(select(MvpInstance).where(MvpInstance.mvp_id == mvp.id))
    if instance is not None and instance.status == "running":
        if get_settings().sandbox_enabled:
            get_runner().stop(instance.container_id)
        instance.status = "stopped"
    db.commit()
    return {"id": mvp.id, "status": mvp.status}


# ---------- 데이터 반출 심사 ----------

@router.get("/api/admin/export-requests")
def admin_list_export_requests(
    status_filter: str = "pending", admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(DataExportRequest)
        .where(DataExportRequest.status == status_filter)
        .order_by(DataExportRequest.created_at)
    ).all()
    result = []
    for r in rows:
        mvp = db.get(Mvp, r.mvp_id)
        requester = db.get(User, r.requester_id)
        result.append({
            "id": r.id, "mvp_id": r.mvp_id, "mvp_title": mvp.title if mvp else None,
            "requester_nickname": requester.nickname if requester else None,
            "include_free_text": r.include_free_text, "status": r.status,
            "created_at": r.created_at,
        })
    return result


def _decide_export(db: Session, request_id: int, admin: User, decision: str, note: str):
    req = db.get(DataExportRequest, request_id)
    if req is None or req.status != "pending":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "심사 대기 중인 신청이 아닙니다")
    req.status = decision
    req.reviewed_by = admin.id
    req.decision_note = note
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": req.id, "status": req.status}


@router.post("/api/admin/export-requests/{request_id}/approve")
def approve_export(request_id: int, body: DecisionBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _decide_export(db, request_id, admin, "approved", body.note)


@router.post("/api/admin/export-requests/{request_id}/reject")
def reject_export(request_id: int, body: DecisionBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _decide_export(db, request_id, admin, "rejected", body.note)


@router.get("/api/admin/export-audit")
def admin_export_audit(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(ExportAuditLog).order_by(ExportAuditLog.exported_at.desc())).all()
    result = []
    for log in rows:
        req = db.get(DataExportRequest, log.export_request_id)
        exporter = db.get(User, log.exported_by)
        result.append({
            "id": log.id, "export_request_id": log.export_request_id,
            "mvp_id": req.mvp_id if req else None,
            "exported_by": exporter.nickname if exporter else None,
            "data_scope": log.data_scope, "exported_at": log.exported_at,
        })
    return result


# ---------- 신고 처리 ----------

@router.get("/api/admin/reports")
def admin_list_reports(status_filter: str = "pending", admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Report).where(Report.status == status_filter).order_by(Report.created_at)
    ).all()
    return [
        {"id": r.id, "target_type": r.target_type, "target_id": r.target_id,
         "reason": r.reason, "status": r.status, "created_at": r.created_at}
        for r in rows
    ]


@router.post("/api/admin/reports/{report_id}/confirm")
def confirm_report(report_id: int, body: DecisionBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """신고 확정: 대상이 평가면 지급 크레딧/포인트 회수 (이중 회수 방지)."""
    report = db.get(Report, report_id)
    if report is None or report.status != "pending":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "처리 대기 중인 신고가 아닙니다")
    report.status = "confirmed"

    if report.target_type == "review":
        review = db.get(Review, report.target_id)
        if review is not None and not review.penalized:
            settings = get_settings()
            add_credit(db, review.reviewer_id, -settings.credit_review_reward,
                       "report_penalty", ref_id=review.id)
            add_point(db, review.reviewer_id, -settings.point_review_reward,
                      "report_penalty", ref_id=review.id)
            review.penalized = True
    db.commit()
    return {"id": report.id, "status": report.status}


@router.post("/api/admin/reports/{report_id}/dismiss")
def dismiss_report(report_id: int, body: DecisionBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None or report.status != "pending":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "처리 대기 중인 신고가 아닙니다")
    report.status = "dismissed"
    db.commit()
    return {"id": report.id, "status": report.status}
