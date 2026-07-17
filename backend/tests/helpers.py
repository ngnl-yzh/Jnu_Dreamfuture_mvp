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


def upload_zip(client, headers, mvp_id, data: bytes, channel="web"):
    return client.post(
        f"/api/mvps/{mvp_id}/artifacts",
        headers=headers,
        files={"file": ("site.zip", data, "application/zip")},
        data={"channel": channel},
    )
