from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import require_verified
from app.models import Mvp, MvpArtifact, MvpInstance, User
from app.sandbox.runner import get_runner, route_slug
from app.services.storage import get_storage

router = APIRouter(prefix="/api/mvps", tags=["instances"])


def _require_sandbox_enabled():
    if not get_settings().sandbox_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "샌드박스 실행이 비활성화되어 있습니다 (Docker 필요)",
        )


@router.post("/{mvp_id}/instance/start")
def start_instance(mvp_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    """published MVP는 모든 인증 회원이 재기동 가능 (유휴 종료 후 재접속 시나리오)."""
    _require_sandbox_enabled()
    mvp = db.get(Mvp, mvp_id)
    if mvp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    is_owner_or_admin = user.id == mvp.owner_id or user.is_admin
    if mvp.status != "published" and not is_owner_or_admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")

    artifact = db.scalar(
        select(MvpArtifact).where(
            MvpArtifact.mvp_id == mvp.id, MvpArtifact.publish_status == "published"
        )
    )
    if artifact is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "게시된 버전이 없습니다")

    zip_data = get_storage().load(artifact.storage_key)

    instance = db.scalar(select(MvpInstance).where(MvpInstance.mvp_id == mvp.id))
    if instance is None:
        instance = MvpInstance(mvp_id=mvp.id)
        db.add(instance)

    try:
        container_id = get_runner().start(mvp.id, zip_data)
    except Exception:
        instance.status = "error"
        db.commit()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "샌드박스 기동에 실패했습니다") from None

    instance.container_id = container_id
    instance.route_path = f"/run/{route_slug(mvp.id)}"
    instance.status = "running"
    instance.last_active_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": instance.status, "route_path": instance.route_path}


@router.post("/{mvp_id}/instance/stop")
def stop_instance(mvp_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    _require_sandbox_enabled()
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or (mvp.owner_id != user.id and not user.is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    instance = db.scalar(select(MvpInstance).where(MvpInstance.mvp_id == mvp.id))
    if instance is None or instance.status != "running":
        return {"status": "stopped"}
    get_runner().stop(instance.container_id)
    instance.status = "stopped"
    db.commit()
    return {"status": "stopped"}


def stop_idle_instances(db: Session) -> int:
    """유휴 30분 초과 인스턴스 정리. 스케줄러/관리자 호출용."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=get_settings().sandbox_idle_minutes)
    stopped = 0
    for instance in db.scalars(select(MvpInstance).where(MvpInstance.status == "running")):
        last = instance.last_active_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is None or last < cutoff:
            get_runner().stop(instance.container_id)
            instance.status = "stopped"
            stopped += 1
    db.commit()
    return stopped


@router.post("/{mvp_id}/instance/heartbeat")
def heartbeat(mvp_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    """뷰어 페이지가 주기적으로 호출 → 유휴 종료 타이머 갱신."""
    instance = db.scalar(select(MvpInstance).where(MvpInstance.mvp_id == mvp_id))
    if instance is None or instance.status != "running":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "실행 중인 인스턴스가 없습니다")
    instance.last_active_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "running"}
