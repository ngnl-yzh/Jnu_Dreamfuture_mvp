from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, require_verified
from app.models import Mvp, MvpArtifact, Review, ReviewVote, TestStep, User
from app.models.mvp import UPLOAD_CHANNELS
from app.schemas.mvp import (
    ArtifactItem,
    InstanceOut,
    MvpCreate,
    MvpDetail,
    MvpItem,
    TestStepOut,
)
from app.services.credits import add_credit, credit_balance
from app.services.storage import get_storage
from app.services.zipcheck import ZipValidationError, validate_static_zip

router = APIRouter(prefix="/api/mvps", tags=["mvps"])

SORTS = ("latest", "rating", "reviews", "votes")


def _review_aggregates(db: Session, mvp_id: int) -> tuple[int, float | None, int]:
    review_count = db.scalar(select(func.count(Review.id)).where(Review.mvp_id == mvp_id))
    avg_rating = db.scalar(select(func.avg(Review.rating)).where(Review.mvp_id == mvp_id))
    votes = db.scalar(
        select(func.count(ReviewVote.id))
        .join(Review, Review.id == ReviewVote.review_id)
        .where(Review.mvp_id == mvp_id, ReviewVote.is_useful.is_(True))
    )
    return review_count, round(avg_rating, 2) if avg_rating is not None else None, votes


def _to_item(db: Session, mvp: Mvp) -> MvpItem:
    review_count, avg_rating, votes = _review_aggregates(db, mvp.id)
    return MvpItem(
        id=mvp.id,
        title=mvp.title,
        tagline=mvp.tagline,
        category=mvp.category,
        tags=[t for t in mvp.tags.split(",") if t],
        runtime_type=mvp.runtime_type,
        status=mvp.status,
        owner_nickname=mvp.owner.nickname,
        view_count=mvp.view_count,
        review_count=review_count,
        avg_rating=avg_rating,
        useful_vote_count=votes,
        created_at=mvp.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_mvp(body: MvpCreate, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    settings = get_settings()
    if not (settings.test_step_min <= len(body.test_steps) <= settings.test_step_max):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"테스트 단계는 {settings.test_step_min}~{settings.test_step_max}개여야 합니다",
        )
    if credit_balance(db, user.id) < settings.credit_mvp_cost:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"크레딧이 부족합니다 (등록에 {settings.credit_mvp_cost} 필요). 다른 MVP를 평가하고 크레딧을 모아주세요.",
        )

    mvp = Mvp(
        owner_id=user.id,
        title=body.title,
        tagline=body.tagline,
        description_md=body.description_md,
        category=body.category,
        tags=",".join(t.strip() for t in body.tags if t.strip()),
        runtime_type=body.runtime_type,
        status="draft",
    )
    db.add(mvp)
    db.flush()
    for i, step in enumerate(body.test_steps, start=1):
        db.add(TestStep(
            mvp_id=mvp.id, step_order=i, title=step.title,
            guide_text=step.guide_text, fixed_category=step.fixed_category,
        ))
    add_credit(db, user.id, -settings.credit_mvp_cost, "mvp_cost", ref_id=mvp.id)
    db.commit()
    return {"id": mvp.id, "status": mvp.status}


@router.get("", response_model=list[MvpItem])
def list_mvps(
    sort: str = "latest",
    category: str | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
):
    if sort not in SORTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"sort는 {SORTS} 중 하나여야 합니다")

    query = select(Mvp).where(Mvp.status == "published")
    if category:
        query = query.where(Mvp.category == category)
    mvps = db.scalars(query).all()
    if tag:
        mvps = [m for m in mvps if tag in m.tags.split(",")]

    items = [_to_item(db, m) for m in mvps]
    if sort == "latest":
        items.sort(key=lambda x: x.created_at, reverse=True)
    elif sort == "rating":
        items.sort(key=lambda x: (x.avg_rating is not None, x.avg_rating or 0), reverse=True)
    elif sort == "reviews":
        items.sort(key=lambda x: x.review_count, reverse=True)
    elif sort == "votes":
        items.sort(key=lambda x: x.useful_vote_count, reverse=True)
    return items


@router.get("/mine", response_model=list[MvpItem])
def list_my_mvps(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mvps = db.scalars(
        select(Mvp).where(Mvp.owner_id == user.id).order_by(Mvp.created_at.desc())
    ).all()
    return [_to_item(db, m) for m in mvps]


def _get_visible_mvp(db: Session, mvp_id: int, user: User | None) -> Mvp:
    mvp = db.get(Mvp, mvp_id)
    if mvp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    if mvp.status != "published":
        allowed = user is not None and (user.id == mvp.owner_id or user.is_admin)
        if not allowed:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    return mvp


@router.get("/{mvp_id}", response_model=MvpDetail)
def mvp_detail(mvp_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mvp = _get_visible_mvp(db, mvp_id, user)
    mvp.view_count += 1
    db.commit()

    my_review = db.scalar(
        select(Review).where(Review.mvp_id == mvp.id, Review.reviewer_id == user.id)
    )
    item = _to_item(db, mvp)
    return MvpDetail(
        **item.model_dump(),
        description_md=mvp.description_md,
        owner_id=mvp.owner_id,
        test_steps=[
            TestStepOut(id=s.id, step_order=s.step_order, title=s.title,
                        guide_text=s.guide_text, fixed_category=s.fixed_category)
            for s in mvp.test_steps
        ],
        instance=(
            InstanceOut(status=mvp.instance.status, route_path=mvp.instance.route_path)
            if mvp.instance else None
        ),
        my_review_id=my_review.id if my_review else None,
    )


@router.post("/{mvp_id}/artifacts", response_model=ArtifactItem, status_code=status.HTTP_201_CREATED)
def upload_artifact(
    mvp_id: int,
    file: UploadFile = File(...),
    channel: str = Form("web"),
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or mvp.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    if channel not in UPLOAD_CHANNELS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"channel은 {UPLOAD_CHANNELS} 중 하나여야 합니다")

    data = file.file.read(get_settings().upload_max_bytes + 1)
    try:
        if mvp.runtime_type == "static":
            validate_static_zip(data)
        else:
            # 서버형/노트북은 인터페이스만 열어둠 (구현 후순위)
            raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "정적 웹만 업로드할 수 있습니다 (1차)")
    except ZipValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None

    version = (db.scalar(
        select(func.max(MvpArtifact.version)).where(MvpArtifact.mvp_id == mvp.id)
    ) or 0) + 1
    storage_key = f"mvps/{mvp.id}/v{version}.zip"
    get_storage().save(storage_key, data)

    artifact = MvpArtifact(
        mvp_id=mvp.id, version=version, storage_key=storage_key,
        file_size=len(data), validation_status="valid",
        publish_status="draft", upload_channel=channel,
    )
    db.add(artifact)
    db.commit()
    return ArtifactItem(
        id=artifact.id, version=artifact.version, file_size=artifact.file_size,
        validation_status=artifact.validation_status, publish_status=artifact.publish_status,
        upload_channel=artifact.upload_channel, uploaded_at=artifact.uploaded_at,
    )


@router.get("/{mvp_id}/artifacts", response_model=list[ArtifactItem])
def list_artifacts(mvp_id: int, user: User = Depends(require_verified), db: Session = Depends(get_db)):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or (mvp.owner_id != user.id and not user.is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    rows = db.scalars(
        select(MvpArtifact).where(MvpArtifact.mvp_id == mvp.id).order_by(MvpArtifact.version.desc())
    ).all()
    return [
        ArtifactItem(
            id=a.id, version=a.version, file_size=a.file_size,
            validation_status=a.validation_status, publish_status=a.publish_status,
            upload_channel=a.upload_channel, uploaded_at=a.uploaded_at,
        )
        for a in rows
    ]


@router.post("/{mvp_id}/artifacts/{version}/publish")
def publish_artifact(
    mvp_id: int, version: int,
    user: User = Depends(require_verified),
    db: Session = Depends(get_db),
):
    mvp = db.get(Mvp, mvp_id)
    if mvp is None or mvp.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "MVP를 찾을 수 없습니다")
    artifact = db.scalar(
        select(MvpArtifact).where(MvpArtifact.mvp_id == mvp.id, MvpArtifact.version == version)
    )
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "해당 버전이 없습니다")

    for other in db.scalars(
        select(MvpArtifact).where(
            MvpArtifact.mvp_id == mvp.id, MvpArtifact.publish_status == "published"
        )
    ):
        other.publish_status = "archived"
    artifact.publish_status = "published"

    # 게시 신청 → 본부 관리자 승인 대기. 새 버전 게시도 재승인 필요 (검수 원칙).
    mvp.status = "pending"
    db.commit()
    return {"mvp_status": mvp.status, "published_version": version}
