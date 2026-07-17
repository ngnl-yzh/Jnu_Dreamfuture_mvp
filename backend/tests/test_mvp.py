import io
import zipfile

from tests.conftest import signup_and_login
from tests.helpers import DEFAULT_STEPS, create_mvp, make_static_zip, upload_zip


def test_create_mvp_deducts_credits(client):
    headers = signup_and_login(client)
    r = create_mvp(client, headers)
    assert r.status_code == 201
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["credit_balance"] == 0  # 3(가입) - 3(등록)


def test_create_mvp_rejected_without_credits(client):
    headers = signup_and_login(client)
    assert create_mvp(client, headers, title="첫번째").status_code == 201
    r = create_mvp(client, headers, title="두번째")  # 잔액 0
    assert r.status_code == 402  # Phase 2 완료 기준: 크레딧 부족 시 거부


def test_test_steps_count_enforced(client):
    headers = signup_and_login(client)
    r = create_mvp(client, headers, steps=[DEFAULT_STEPS[0]])  # 1개 → 거부
    assert r.status_code == 400
    eight = [dict(DEFAULT_STEPS[0], title=f"단계{i}") for i in range(8)]
    assert create_mvp(client, headers, steps=eight).status_code == 400


def test_invalid_fixed_category_rejected(client):
    headers = signup_and_login(client)
    bad = [dict(DEFAULT_STEPS[0], fixed_category="unknown"), DEFAULT_STEPS[1]]
    assert create_mvp(client, headers, steps=bad).status_code == 422


def test_unverified_user_cannot_create_or_upload(client):
    headers = signup_and_login(client, email="unv2@jnu.ac.kr", verified=False)
    assert create_mvp(client, headers).status_code == 403


def test_upload_and_version_history(client):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]

    r = upload_zip(client, headers, mvp_id, make_static_zip())
    assert r.status_code == 201
    assert r.json()["version"] == 1
    assert "storage_key" not in r.json()  # 소스코드 비노출 원칙

    r = upload_zip(client, headers, mvp_id, make_static_zip(), channel="cli")
    assert r.json()["version"] == 2

    r = client.get(f"/api/mvps/{mvp_id}/artifacts", headers=headers)
    versions = [a["version"] for a in r.json()]
    assert versions == [2, 1]
    assert all("storage_key" not in a for a in r.json())


def test_zip_without_index_rejected(client):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]
    r = upload_zip(client, headers, mvp_id, make_static_zip(include_index=False,
                                                           extra_files={"main.css": b"body{}"}))
    assert r.status_code == 400


def test_zip_slip_rejected(client):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", "<html></html>")
        zf.writestr("../evil.sh", "rm -rf /")
    assert upload_zip(client, headers, mvp_id, buf.getvalue()).status_code == 400


def test_zip_disallowed_extension_rejected(client):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]
    data = make_static_zip(extra_files={"run.exe": b"MZ"})
    assert upload_zip(client, headers, mvp_id, data).status_code == 400


def test_publish_flow_sets_pending(client):
    headers = signup_and_login(client)
    mvp_id = create_mvp(client, headers).json()["id"]
    upload_zip(client, headers, mvp_id, make_static_zip())

    r = client.post(f"/api/mvps/{mvp_id}/artifacts/1/publish", headers=headers)
    assert r.status_code == 200
    assert r.json()["mvp_status"] == "pending"  # 관리자 승인 대기

    # 게시 전에는 공개 목록에 노출되지 않음
    assert all(m["id"] != mvp_id for m in client.get("/api/mvps").json())


def test_other_user_cannot_upload_to_my_mvp(client):
    owner = signup_and_login(client, email="owner@jnu.ac.kr")
    mvp_id = create_mvp(client, owner).json()["id"]
    other = signup_and_login(client, email="other@jnu.ac.kr", nickname="타인")
    assert upload_zip(client, other, mvp_id, make_static_zip()).status_code == 404
