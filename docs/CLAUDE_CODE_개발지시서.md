# Claude Code 개발 지시서 — 전남대 MVP 공유·평가 플랫폼

> 이 문서는 Claude Code에 전달하는 개발 브리핑이다. 함께 첨부된 `MVP_공유평가_사이트_제작가이드라인.md`(기획 배경·정책)와 `ERD.mermaid`(데이터 모델)를 반드시 같이 읽고 작업할 것. 이 문서가 우선순위·작업 순서의 기준이다.

## 1. 프로젝트 한 줄 정의

전남대 구성원이 자신의 MVP(프로그램)를 올리면, 다른 구성원이 사이트 안에서 블랙박스로 실행·체험하고 구조화된 평가를 남기는 플랫폼. 소스코드는 절대 외부 노출되지 않고, 평가·참여 데이터는 본부 승인 하에만 반출된다.

## 2. 절대 원칙 (모든 코드에 적용)

1. **소스코드 비노출**: 업로드된 원본 파일(zip)은 내부 스토리지에만 저장. 원본 다운로드 API를 만들지 않는다. 평가자에게는 실행 결과 화면만 노출.
2. **전대 회원 전용**: 가입은 `@jnu.ac.kr` 이메일 인증 코드 확인 필수. 전대 포털 비밀번호는 절대 수집하지 않는다 (자체 비번 사용, 추후 SSO 전환 전제).
3. **업로드는 인증 회원 전용**: 웹/API/CLI 모든 채널에서 미인증 요청 거부. API 토큰은 이메일 인증 완료 계정만 발급.
4. **개인정보 거버넌스**: 데이터 반출은 본부 관리자 승인 필수, 반출 시 익명화(이메일·이름·계정ID 제거 또는 가명화), 전 건 감사 로그 기록.
5. **크레딧/포인트는 원장(ledger) 방식**: 잔액 컬럼 대신 증감 기록 테이블. 잔액은 집계로 계산.

## 3. 기술 스택 (확정)

- 백엔드: Python 3.12+, FastAPI, SQLAlchemy 2.x, Alembic (마이그레이션)
- DB: PostgreSQL (로컬 개발은 Docker Compose로 기동)
- 프론트엔드: React (Next.js, App Router)
- 샌드박스 실행: Docker Engine API + Traefik (리버스 프록시, MVP별 고유 경로 라우팅)
- 파일 스토리지: 로컬 개발 MinIO (S3 호환), 운영 시 국내 리전 S3 호환 스토리지
- 인증: JWT (access/refresh), 비밀번호 bcrypt/argon2 해시
- 개발 환경: Docker Compose로 전체 스택 로컬 재현

## 4. 데이터 모델

`ERD.mermaid` 기준. 핵심 테이블 요약 (17개):

| 테이블 | 역할 | 주의점 |
|---|---|---|
| USER | 계정 | jnu_verified 필수 게이트, 동의 플래그 2종 |
| API_TOKEN | CLI/API 업로드용 토큰 | 해시만 저장, 폐기(revoked_at) 지원 |
| MVP | MVP 메타데이터 | status: draft/pending/published/rejected/terminated |
| MVP_ARTIFACT | 업로드 버전 이력 | publish_status(draft/published/archived), upload_channel, storage_key는 외부 비노출 |
| MVP_INSTANCE | 실행 컨테이너 상태 | route_path로 iframe 임베드, 유휴 자동 종료 |
| TEST_STEP | 제작자 정의 테스트 단계(2~7개) | fixed_category 4종 매핑 필수 (pre_entry/setup/core/post) |
| REVIEW | 구조화 평가 | (mvp_id, reviewer_id) 유니크 = 재평가 방지, stuck_step_id → TEST_STEP |
| REVIEW_VOTE | 유용 투표 | 정렬용 |
| CREDIT_LEDGER | 소모형 크레딧 원장 | +1 평가작성 / -3 MVP등록 / +3 가입보너스 / 회수 |
| POINT_LEDGER | 누적형 포인트 원장 | 보상 전환용, 현재는 적립만 |
| DATA_EXPORT_REQUEST | 반출 신청 | pending/approved/rejected, 본부 관리자만 승인 |
| EXPORT_AUDIT_LOG | 반출 감사 로그 | 전 건 기록 |
| GROUP / GROUP_MEMBER / GROUP_ASSIGNMENT | 수업·동아리 그룹 | 후순위 Phase |
| REPORT | 신고 | 확정 시 크레딧/포인트 회수 트리거 |

## 5. API 설계 개요

- `POST /api/auth/signup` — 가입 (동의 플래그 필수)
- `POST /api/auth/verify-email` — @jnu.ac.kr 인증 코드 발송/확인
- `POST /api/auth/login`, `POST /api/auth/refresh`
- `GET/POST /api/tokens` — API 토큰 발급/목록, `DELETE /api/tokens/{id}` 폐기
- `GET/POST /api/mvps` — 목록(정렬: 최신/평점/리뷰수/유용투표, 필터: 카테고리/태그) / 등록(크레딧 3 차감, 테스트 시나리오 필수)
- `GET /api/mvps/{id}` — 상세
- `POST /api/mvps/{id}/artifacts` — zip 업로드 (웹/CLI/API 공용, Bearer 토큰 인증). draft로 저장
- `POST /api/mvps/{id}/artifacts/{ver}/publish` — 게시 (제작자 선택)
- `POST /api/mvps/{id}/instance/start|stop` — 실행 제어 (내부/관리자)
- `GET/POST /api/mvps/{id}/reviews` — 평가 목록/작성 (구조화 폼 전체 필수, 작성 시 크레딧+1·포인트+1)
- `POST /api/reviews/{id}/vote` — 유용 투표
- `GET /api/me/dashboard` — 내 MVP 통계 (평점 분포, 단계별 이탈, NPS)
- `POST /api/mvps/{id}/export-requests` — 반출 신청 / `GET /api/admin/export-requests` + `POST .../approve|reject` — 본부 승인
- `GET /api/mvps/{id}/export` — 승인된 경우만, 익명화 CSV/JSON + 감사 로그 기록
- `GET /api/admin/mvps` — 승인/반려/강제 종료, `GET /api/admin/reports` — 신고 처리

## 6. 샌드박스 실행 규격 (1차: 정적 웹만)

1. zip 업로드 → 구조 검증 (루트 `index.html` 필수, 100MB 제한, zip 폭탄 방어)
2. nginx 베이스 이미지에 파일 복사 → 이미지 빌드 → 컨테이너 실행
3. Traefik에 `/run/{mvp_slug}` 경로 라우팅 등록 → 상세 페이지 iframe(sandbox 속성 적용)으로 임베드
4. 컨테이너 제약: CPU/메모리 제한, 아웃바운드 네트워크 차단, 유휴 30분 시 자동 종료 (재접속 시 재기동)
5. 게시 전 관리자 승인(pending → published) 단계 유지

서버형(Dockerfile)·노트북(Streamlit)은 인터페이스만 열어두고 구현은 후순위.

## 7. 개발 순서 (Phase별, 이 순서대로 진행)

각 Phase는 "완료 기준"을 만족한 뒤 다음으로 넘어갈 것.

- **Phase 0 — 기반**: 모노레포 구조(backend/, frontend/, cli/, infra/), Docker Compose(postgres, minio, traefik), Alembic 초기 마이그레이션(전체 스키마). 완료 기준: `docker compose up`으로 전 스택 기동.
- **Phase 1 — 계정/인증**: 가입+이메일 인증+로그인+JWT, 동의 수집, admin 플래그, API 토큰 발급. 완료 기준: 미인증 계정은 업로드 관련 모든 엔드포인트에서 403.
- **Phase 2 — MVP 등록**: 메타데이터+테스트 시나리오(단계 2~7, 카테고리 매핑 필수)+zip 업로드(draft)+게시 선택, 크레딧 차감 로직. 완료 기준: 크레딧 부족 시 등록 거부, 버전 이력 조회 가능.
- **Phase 3 — 샌드박스 실행**: 정적 웹 빌드→실행→라우팅→유휴 정리. 완료 기준: 업로드한 정적 사이트가 iframe에서 동작, 원본 다운로드 경로 부재 확인.
- **Phase 4 — 뷰어 페이지**: 상세 페이지(iframe, 실행 상태, 테스트 단계 안내, 조회수).
- **Phase 5 — 평가**: 구조화 폼(6항목), 막힌 단계 선택, 크레딧/포인트 적립, 수정/삭제, 재평가 방지.
- **Phase 6 — 목록/정렬**: 정렬 4종+필터, 유용 투표.
- **Phase 6.5 — 대시보드+반출**: 제작자 대시보드(사이트 내 열람은 승인 불필요), 반출 신청→본부 승인→익명화 export→감사 로그.
- **Phase 7 — CLI**: `jnu-mvp` 패키지, `mvp login`(토큰 저장), `mvp push`(zip 생성→API 업로드), `mvp publish`.
- **Phase 8 — 본부 관리자 화면**: MVP 승인/반려, 반출 심사, 신고 처리, 감사 로그 조회.
- **이후(대회 뒤)**: 서버형/노트북 실행, 그룹 기능, GitHub App, MCP 서버, AI 기능(리뷰 요약·유용 댓글 판별·이탈 자동 분석).

**교내 대회 데모 범위 = Phase 0~8.** 발표 킬러 데모: ① CLI `mvp push` 한 줄 배포 ② 블랙박스 실행 ③ 단계별 이탈 통계 대시보드 ④ 본부 승인 반출 플로우.

## 8. 비즈니스 규칙 상세 (구현 시 그대로 적용)

- 크레딧: 가입 +3 / 평가 완성 +1 / MVP 등록 -3 / 신고 확정 시 해당 평가 크레딧·포인트 회수
- 평가 폼 필수 항목: 첫인상(1~5), 온보딩 성공 여부+서술, 핵심 기능 도달 여부, 막힌 단계(미도달 시 필수), 완성도 별점(1~5), 개선 제안(최소 글자 수, 예: 30자), NPS(0~10)
- 동일 사용자는 동일 MVP에 평가 1회 (수정은 가능)
- 자기 MVP에는 평가 불가
- 반출 데이터 익명화: user 식별자 → 가명 ID(mvp별 일관 유지), 이메일·닉네임 제거. 자유 서술 텍스트 포함 여부는 export 옵션으로 분리
- MVP 게시 흐름: 업로드(draft) → 제작자 게시 신청 → 관리자 승인(pending→published) → 노출

## 9. 보안 체크리스트

- zip 처리: 경로 탈출(zip slip) 방어, 압축 해제 크기 제한, 파일 확장자 화이트리스트
- iframe: sandbox 속성, CSP 헤더, 플랫폼 도메인과 실행 도메인/경로 분리
- 컨테이너: 비루트 실행, 리소스 제한, 네트워크 차단, 읽기 전용 파일시스템(가능 시)
- API: 레이트 리밋(업로드·인증 코드 발송), 토큰 해시 저장, CORS 최소화
- 감사: 반출·관리자 행위 전 건 로그

## 10. 저장소 구조 제안

```
jnu-mvp-platform/
├── backend/          # FastAPI 앱 (routers/, models/, services/, sandbox/)
├── frontend/         # Next.js 앱
├── cli/              # jnu-mvp CLI 패키지
├── infra/            # docker-compose.yml, traefik 설정, nginx 템플릿
├── docs/             # 이 지시서 + 가이드라인 + ERD
└── CLAUDE.md         # 이 문서 요약본을 배치 (절대 원칙 + 현재 Phase)
```

## 11. Claude Code에게 주는 작업 지침

- Phase 순서를 건너뛰지 말 것. 각 Phase 완료 기준을 테스트로 검증할 것 (pytest, 핵심 비즈니스 규칙 위주).
- 절대 원칙(2절)에 반하는 요청이 코드 편의상 생기더라도 원칙을 우선할 것 (예: "디버그용 원본 다운로드 엔드포인트" 금지).
- 스키마 변경은 반드시 Alembic 마이그레이션으로.
- 커밋은 Phase 단위보다 잘게, 기능 단위로.
- 모르는 결정사항이 나오면 임의 구현하지 말고 사용자에게 질문할 것.
