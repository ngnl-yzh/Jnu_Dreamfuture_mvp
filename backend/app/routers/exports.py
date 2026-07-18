import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_verified
from app.models import DataExportRequest, ExportAuditLog, Mvp, User
from app.services.anonymize import anonymized_review_rows

router = APIRouter(prefix="/api/mvps", tags=["exports"])


class ExportRequestBody(BaseModel):
    include_free_text: bool = False


def _owned_mvp(db: Session, mvp_id: int, user: User) -> Mvp:
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or mvp.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    return mvp


@router.post("/{mvp_id}/export-requests", status_code=status.HTTP_201_CREATED)
def create_export_request(
    mvp_id: int,
    body: ExportRequestBody,
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    mvp = _owned_mvp(db, mvp_id, user)
    existing = db.scalar(select(DataExportRequest).where(
        DataExportRequest.mvp_id == mvp.id, DataExportRequest.status == "pending"
    ))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 심사 대기 중인 반출 신청이 있습니다")
    req = DataExportRequest(
        mvp_id=mvp.id, requester_id=user.id, include_free_text=body.include_free_text
    )
    db.add(req)
    db.commit()
    return {"id": req.id, "status": req.status}


@router.get("/{mvp_id}/export-requests")
def list_my_export_requests(
    mvp_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)
):
    mvp = _owned_mvp(db, mvp_id, user)
    rows = db.scalars(
        select(DataExportRequest)
        .where(DataExportRequest.mvp_id == mvp.id)
        .order_by(DataExportRequest.created_at.desc())
    ).all()
    return [
        {
            "id": r.id, "status": r.status, "include_free_text": r.include_free_text,
            "decision_note": r.decision_note, "created_at": r.created_at,
            "decided_at": r.decided_at,
        }
        for r in rows
    ]


@router.get("/{mvp_id}/export")
def export_data(
    mvp_id: int,
    format: str = "csv",  # csv | json
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    """승인된 반출 신청이 있어야만 동작. 익명화 적용 + 전 건 감사 로그 기록."""
    mvp = _owned_mvp(db, mvp_id, user)
    approved = db.scalar(
        select(DataExportRequest)
        .where(DataExportRequest.mvp_id == mvp.id, DataExportRequest.status == "approved")
        .order_by(DataExportRequest.decided_at.desc())
    )
    if approved is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본부 승인된 반출 신청이 없습니다")
    if format not in ("csv", "json"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "format은 csv 또는 json이어야 합니다")

    rows = anonymized_review_rows(db, mvp, approved.include_free_text)
    scope = f"reviews_{format}" + ("+free_text" if approved.include_free_text else "")
    db.add(ExportAuditLog(
        export_request_id=approved.id, exported_by=user.id,
        data_scope=scope, exported_at=datetime.now(timezone.utc),
    ))
    db.commit()

    filename = f"mvp-{mvp.id}-reviews.{format}"
    if format == "json":
        return Response(
            json.dumps(rows, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    buf = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["rater"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
