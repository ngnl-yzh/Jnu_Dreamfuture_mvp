import logging
import smtplib
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger("jnu.email")


def send_verification_code(email: str, code: str) -> None:
    settings = get_settings()
    if settings.email_dev_mode:
        # 로컬 개발: SMTP 없이 서버 로그로 코드 확인
        logger.warning("[DEV] %s 인증 코드: %s", email, code)
        return

    msg = MIMEText(f"전남대 MVP 플랫폼 이메일 인증 코드: {code}\n({settings.email_code_expire_minutes}분 내 입력)")
    msg["Subject"] = "[JNU MVP] 이메일 인증 코드"
    msg["From"] = settings.smtp_from
    msg["To"] = email
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
