from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.database import get_sessionmaker
from app.models import Mvp, MvpInstance
from app.sandbox.runner import set_runner_for_testing
from tests.conftest import signup_and_login
from tests.helpers import create_mvp, make_static_zip, upload_zip


class FakeRunner:
    def __init__(self):
        self.started: list[int] = []
        self.stopped: list[str] = []

    def start(self, mvp_id: int, zip_data: bytes) -> str:
        assert zip_data  # 스토리지에서 실제 zip을 읽어와야 함
        self.started.append(mvp_id)
        return f"fake-container-{mvp_id}"

    def stop(self, container_id: str) -> None:
        self.stopped.append(container_id)


@pytest.fixture()
def sandbox(client):
    settings = get_settings()
    old = settings.sandbox_enabled
    settings.sandbox_enabled = True
    runner = FakeRunner()
    set_runner_for_testing(runner)
    yield runner
    settings.sandbox_enabled = old
    set_runner_for_testing(None)


def _published_mvp(client, headers):
    mvp_id = create_mvp(client, headers).json()["id"]
    upload_zip(client, headers, mvp_id, make_static_zip())
    client.post(f"/api/mvps/{mvp_id}/artifacts/1/publish", headers=headers)
    with get_sessionmaker()() as db:
        mvp = db.get(Mvp, mvp_id)
        mvp.status = "published"  # 관리자 승인은 admin 라우터 테스트에서 별도 검증
        db.commit()
    return mvp_id


def test_sandbox_disabled_returns_503(client):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]
    r = client.post(f"/api/mvps/{mvp_id}/instance/start", headers=headers)
    assert r.status_code == 503


def test_start_stop_instance(client, sandbox):
    headers = signup_and_login(client)
    mvp_id = _published_mvp(client, headers)

    r = client.post(f"/api/mvps/{mvp_id}/instance/start", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "running"
    assert r.json()["route_path"] == f"/run/mvp-{mvp_id}"
    assert sandbox.started == [mvp_id]

    r = client.post(f"/api/mvps/{mvp_id}/instance/stop", headers=headers)
    assert r.json()["status"] == "stopped"
    assert sandbox.stopped == [f"fake-container-{mvp_id}"]


def test_start_requires_published_artifact(client, sandbox):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]
    upload_zip(client, headers, mvp_id, make_static_zip())  # draft만 존재
    r = client.post(f"/api/mvps/{mvp_id}/instance/start", headers=headers)
    assert r.status_code == 400


def test_idle_instances_are_stopped(client, sandbox):
    from app.routers.instances import stop_idle_instances

    headers = signup_and_login(client)
    mvp_id = _published_mvp(client, headers)
    client.post(f"/api/mvps/{mvp_id}/instance/start", headers=headers)

    with get_sessionmaker()() as db:
        instance = db.scalar(select(MvpInstance).where(MvpInstance.mvp_id == mvp_id))
        instance.last_active_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.commit()
        assert stop_idle_instances(db) == 1
        db.refresh(instance)
        assert instance.status == "stopped"


def test_heartbeat_refreshes_idle_timer(client, sandbox):
    from app.routers.instances import stop_idle_instances

    headers = signup_and_login(client)
    mvp_id = _published_mvp(client, headers)
    client.post(f"/api/mvps/{mvp_id}/instance/start", headers=headers)

    with get_sessionmaker()() as db:
        instance = db.scalar(select(MvpInstance).where(MvpInstance.mvp_id == mvp_id))
        instance.last_active_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        db.commit()

    assert client.post(f"/api/mvps/{mvp_id}/instance/heartbeat", headers=headers).status_code == 200
    with get_sessionmaker()() as db:
        assert stop_idle_instances(db) == 0  # 하트비트로 갱신되어 종료되지 않음
