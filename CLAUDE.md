# jnu-mvp-platform

전남대 구성원 전용 MVP 공유·평가 플랫폼. 상세 스펙은 `docs/CLAUDE_CODE_개발지시서.md`, `docs/MVP_공유평가_사이트_제작가이드라인.md`, `docs/ERD.mermaid` 참조.

## 절대 원칙 (모든 코드에 적용)

1. **소스코드 비노출**: 업로드 원본(zip)은 내부 스토리지에만 저장. 원본 다운로드 API를 만들지 않는다. 평가자에게는 실행 결과 화면만 노출.
2. **전대 회원 전용**: 가입은 `@jnu.ac.kr` 이메일 인증 코드 확인 필수. 전대 포털 비밀번호는 절대 수집하지 않는다.
3. **업로드는 인증 회원 전용**: 웹/API/CLI 모든 채널에서 미인증(jnu_verified=false) 요청 거부. API 토큰은 인증 완료 계정만 발급.
4. **개인정보 거버넌스**: 데이터 반출은 본부 관리자 승인 필수, 익명화(이메일·이름·계정ID 제거/가명화), 전 건 감사 로그.
5. **크레딧/포인트는 원장(ledger) 방식**: 잔액 컬럼 금지. 잔액은 원장 집계로 계산.

## 기술 스택

- backend/: FastAPI + SQLAlchemy 2.x + Alembic, PostgreSQL (테스트는 SQLite 인메모리)
- frontend/: Next.js (App Router)
- cli/: `jnu-mvp` 패키지 (`mvp login` / `mvp push` / `mvp publish`)
- infra/: docker-compose (postgres, minio, traefik), nginx 템플릿
- 샌드박스: Docker Engine API + Traefik `/run/{slug}` 라우팅, 정적 웹(1차)만 실행

## 규칙

- 스키마 변경은 반드시 Alembic 마이그레이션으로.
- 커밋은 기능 단위로 잘게.
- Phase 순서(개발지시서 7절)를 건너뛰지 않는다. 각 Phase 완료 기준을 pytest로 검증.
- 크레딧 규칙: 가입 +3 / 평가 완성 +1 / MVP 등록 -3 / 신고 확정 시 회수. 포인트는 적립만.
- 평가: 동일 (mvp, reviewer) 1회(수정 가능), 자기 MVP 평가 불가, 개선 제안 최소 30자.
- MVP 게시 흐름: 업로드(draft) → 제작자 게시 신청(pending) → 관리자 승인(published).

## 현재 상태

- Phase 0~8 전부 구현 완료 (backend pytest 38건 + cli 2건 통과, CLI 실서버 E2E 검증, 프론트 8개 라우트 빌드·브라우저 검증).
- 로컬에 Docker Desktop 미설치 → `docker compose up` 실기동 및 Phase 3 샌드박스 컨테이너 실행 검증만 남음 (코드·단위테스트는 완료, 미설치 시 실행 API는 503).
- 결정 사항: 새 버전 게시 신청도 매번 관리자 재승인(pending) — 검수 원칙 우선. 가입 보너스 크레딧은 이메일 인증 완료 시점 지급.

## 개발 명령

```
# backend
cd backend
python -m venv .venv && .venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
# 전체 스택 (Docker 필요)
docker compose -f infra/docker-compose.yml up
```
