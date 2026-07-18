"""배포 대상 디렉터리를 zip으로 패킹."""

import io
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next", "dist"}
EXCLUDE_FILES = {"jnu-mvp.json", ".env", ".env.local", ".DS_Store"}


def make_zip(root: Path) -> bytes:
    root = root.resolve()
    if not (root / "index.html").exists():
        raise FileNotFoundError("루트에 index.html이 필요합니다 (정적 웹 규격)")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(root)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            if rel.name in EXCLUDE_FILES:
                continue
            zf.write(path, rel.as_posix())
    return buf.getvalue()
