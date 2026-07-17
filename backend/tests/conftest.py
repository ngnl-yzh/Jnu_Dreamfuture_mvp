import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, set_engine_for_testing
from app.models import User
from app.services.storage import LocalStorage, set_storage_for_testing


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    set_engine_for_testing(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def sent_codes(monkeypatch):
    """발송된 (email, code) 캡처. SMTP 미사용."""
    codes: list[tuple[str, str]] = []

    def fake_send(email: str, code: str) -> None:
        codes.append((email, code))

    monkeypatch.setattr("app.routers.auth.send_verification_code", fake_send)
    return codes


@pytest.fixture()
def client(db_engine, sent_codes, tmp_path):
    set_storage_for_testing(LocalStorage(str(tmp_path / "storage")))
    from app.main import app

    with TestClient(app) as c:
        c.sent_codes = sent_codes
        yield c


def signup_and_login(client, email="tester@jnu.ac.kr", nickname="테스터",
                     verified=True, admin=False, consent_data_share=True):
    """가입→(인증)→로그인까지 수행하고 Authorization 헤더를 반환하는 테스트 헬퍼."""
    r = client.post("/api/auth/signup", json={
        "email": email,
        "password": "password123!",
        "nickname": nickname,
        "consent_privacy": True,
        "consent_data_share": consent_data_share,
    })
    assert r.status_code == 201, r.text

    if verified:
        code = next(c for e, c in reversed(client.sent_codes) if e == email)
        r = client.post("/api/auth/verify-email", json={"email": email, "code": code})
        assert r.status_code == 200, r.text

    if admin:
        from app.database import get_sessionmaker
        from sqlalchemy import select

        with get_sessionmaker()() as db:
            user = db.scalar(select(User).where(User.email == email))
            user.is_admin = True
            db.commit()

    r = client.post("/api/auth/login", json={"email": email, "password": "password123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
