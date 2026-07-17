from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="JNU_", extra="ignore")

    app_name: str = "JNU MVP Platform"
    secret_key: str = "dev-secret-change-me-0123456789abcdef"  # 운영에서는 반드시 교체
    database_url: str = "postgresql+psycopg://jnu:jnu@localhost:5432/jnu_mvp"

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    allowed_email_domain: str = "jnu.ac.kr"
    email_code_expire_minutes: int = 10
    # 인증 코드 발송 레이트 리밋: 같은 이메일 기준 최소 재발송 간격(초)
    email_code_resend_seconds: int = 60
    # True면 SMTP 대신 로그로 코드 출력 (로컬 개발)
    email_dev_mode: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@jnu-mvp.local"

    storage_backend: str = "local"  # local | s3
    storage_local_path: str = "./data/storage"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "mvp-artifacts"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    upload_max_bytes: int = 100 * 1024 * 1024        # zip 원본 100MB
    upload_max_uncompressed: int = 300 * 1024 * 1024  # zip 폭탄 방어

    sandbox_enabled: bool = False  # Docker 미설치 환경에서는 False
    sandbox_network: str = "jnu-sandbox"
    sandbox_idle_minutes: int = 30
    sandbox_cpu_quota: float = 0.5
    sandbox_mem_limit: str = "128m"

    # 크레딧/포인트 규칙 (docs/개발지시서 8절)
    credit_signup_bonus: int = 3
    credit_review_reward: int = 1
    credit_mvp_cost: int = 3
    point_review_reward: int = 1

    review_improvement_min_chars: int = 30
    test_step_min: int = 2
    test_step_max: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
