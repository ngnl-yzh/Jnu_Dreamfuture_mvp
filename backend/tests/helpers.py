import io
import zipfile

DEFAULT_STEPS = [
    {"title": "메인 화면 진입", "guide_text": "첫 화면을 확인하세요", "fixed_category": "pre_entry"},
    {"title": "핵심 기능 사용", "guide_text": "버튼을 눌러보세요", "fixed_category": "core"},
]


def make_static_zip(extra_files: dict[str, bytes] | None = None, include_index=True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if include_index:
            zf.writestr("index.html", "<html><body>demo</body></html>")
        for name, data in (extra_files or {}).items():
            zf.writestr(name, data)
    return buf.getvalue()


def create_mvp(client, headers, title="데모 MVP", steps=None, category="생산성"):
    r = client.post("/api/mvps", headers=headers, json={
        "title": title,
        "tagline": "한 줄 소개",
        "description_md": "# 설명",
        "category": category,
        "tags": ["tag1", "tag2"],
        "runtime_type": "static",
        "test_steps": steps if steps is not None else DEFAULT_STEPS,
    })
    return r


def publish_mvp(client, headers, title="데모 MVP", category="생산성", steps=None):
    """등록→업로드→게시신청→(관리자 승인 대신 직접 published 전환)까지 수행."""
    from app.database import get_sessionmaker
    from app.models import Mvp

    mvp_id = create_mvp(client, headers, title=title, category=category, steps=steps).json()["id"]
    upload_zip(client, headers, mvp_id, make_static_zip())
    client.post(f"/api/mvps/{mvp_id}/artifacts/1/publish", headers=headers)
    with get_sessionmaker()() as db:
        db.get(Mvp, mvp_id).status = "published"
        db.commit()
    return mvp_id


VALID_REVIEW = {
    "first_impression": 4,
    "onboarding_ok": True,
    "onboarding_note": "설명 없이 시작 가능했습니다",
    "reached_core": True,
    "stuck_step_id": None,
    "stuck_note": "",
    "rating": 4,
    "improvement_note": "버튼 위치를 조금 더 눈에 띄게 바꾸면 좋겠습니다. 색 대비도 개선 여지가 있습니다.",
    "nps": 8,
}


def upload_zip(client, headers, mvp_id, data: bytes, channel="web"):
    return client.post(
        f"/api/mvps/{mvp_id}/artifacts",
        headers=headers,
        files={"file": ("site.zip", data, "application/zip")},
        data={"channel": channel},
    )
