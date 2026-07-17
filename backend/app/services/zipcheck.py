"""업로드 zip 검증 — 정적 웹 1차 규격.

- 루트 index.html 필수
- 원본 100MB / 해제 후 300MB 제한 (zip 폭탄 방어)
- 경로 탈출(zip slip) 방어
- 파일 확장자 화이트리스트
"""

import io
import posixpath
import zipfile

from app.config import get_settings

ALLOWED_EXTENSIONS = {
    "html", "htm", "css", "js", "mjs", "json", "map", "txt", "md", "xml",
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "avif",
    "woff", "woff2", "ttf", "otf", "eot",
    "mp3", "mp4", "webm", "ogg", "wav",
    "webmanifest", "wasm", "pdf",
}


class ZipValidationError(ValueError):
    pass


def validate_static_zip(data: bytes) -> None:
    settings = get_settings()
    if len(data) > settings.upload_max_bytes:
        raise ZipValidationError(f"zip 파일이 {settings.upload_max_bytes // (1024 * 1024)}MB를 초과합니다")

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ZipValidationError("유효한 zip 파일이 아닙니다") from None

    total_uncompressed = 0
    has_root_index = False

    for info in zf.infolist():
        name = info.filename
        # zip slip 방어: 절대 경로·상위 경로 탈출 금지
        normalized = posixpath.normpath(name.replace("\\", "/"))
        if normalized.startswith(("/", "..")) or ".." in normalized.split("/"):
            raise ZipValidationError(f"허용되지 않는 경로입니다: {name}")

        if info.is_dir():
            continue

        total_uncompressed += info.file_size
        if total_uncompressed > settings.upload_max_uncompressed:
            raise ZipValidationError("압축 해제 크기가 제한을 초과합니다")

        if normalized == "index.html":
            has_root_index = True

        ext = normalized.rsplit(".", 1)[-1].lower() if "." in normalized.split("/")[-1] else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ZipValidationError(f"허용되지 않는 파일 형식입니다: {name}")

    if not has_root_index:
        raise ZipValidationError("루트에 index.html이 필요합니다")
