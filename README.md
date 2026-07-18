# JNU MVP Platform

전남대 구성원 전용 MVP 공유·평가 플랫폼. 제작자가 MVP를 올리면 다른 구성원이 **블랙박스 샌드박스**에서 체험하고 구조화된 평가를 남긴다. 소스코드는 외부에 노출되지 않고, 평가·참여 데이터는 본부 승인 하에만 익명화되어 반출된다.

## 구조

```
backend/   FastAPI + SQLAlchemy 2 + Alembic (PostgreSQL)
frontend/  Next.js (App Router)
cli/       jnu-mvp CLI — mvp login / push / publish
infra/     docker-compose (postgres·minio·traefik), nginx 샌드박스 템플릿
docs/      개발지시서 · 가이드라인 · ERD
```

## 로컬 개발

```bash
# 백엔드 테스트
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest

# 백엔드 단독 실행 (SQLite, 샌드박스 비활성)
.venv/Scripts/alembic upgrade head   # JNU_DATABASE_URL로 DB 지정
.venv/Scripts/uvicorn app.main:app --port 8000

# 프론트엔드
cd frontend && npm install && npm run dev  # http://localhost:3000

# 전체 스택 (Docker Desktop 필요)
docker compose -f infra/docker-compose.yml up
```

## CLI 한 줄 배포

```bash
pip install -e ./cli
mvp login            # 마이페이지에서 발급한 API 토큰
mvp link <MVP_ID>
mvp push --publish   # zip 패킹 → 업로드 → 게시 신청
```

자세한 정책·규칙은 [CLAUDE.md](CLAUDE.md)와 `docs/` 참조.
