from tests.conftest import signup_and_login


def test_signup_rejects_non_jnu_email(client):
    r = client.post("/api/auth/signup", json={
        "email": "someone@gmail.com", "password": "password123!",
        "nickname": "외부인", "consent_privacy": True, "consent_data_share": True,
    })
    assert r.status_code == 400


def test_signup_requires_privacy_consent(client):
    r = client.post("/api/auth/signup", json={
        "email": "a@jnu.ac.kr", "password": "password123!",
        "nickname": "동의안함", "consent_privacy": False, "consent_data_share": False,
    })
    assert r.status_code == 400


def test_verify_email_grants_signup_bonus(client):
    headers = signup_and_login(client)
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["jnu_verified"] is True
    assert me["credit_balance"] == 3  # 가입 보너스는 인증 완료 시 1회
    assert me["point_balance"] == 0


def test_wrong_code_rejected(client):
    client.post("/api/auth/signup", json={
        "email": "b@jnu.ac.kr", "password": "password123!",
        "nickname": "비번틀림", "consent_privacy": True, "consent_data_share": True,
    })
    r = client.post("/api/auth/verify-email", json={"email": "b@jnu.ac.kr", "code": "000000"})
    # 실제 코드가 우연히 000000일 수 있으므로 캡처된 코드와 다른 값으로 보정
    real = client.sent_codes[-1][1]
    wrong = "000000" if real != "000000" else "111111"
    r = client.post("/api/auth/verify-email", json={"email": "b@jnu.ac.kr", "code": wrong})
    assert r.status_code == 400


def test_unverified_user_cannot_issue_api_token(client):
    headers = signup_and_login(client, email="unv@jnu.ac.kr", verified=False)
    r = client.post("/api/tokens", json={"label": "cli"}, headers=headers)
    assert r.status_code == 403  # Phase 1 완료 기준


def test_api_token_roundtrip_and_revoke(client):
    headers = signup_and_login(client)
    r = client.post("/api/tokens", json={"label": "노트북 CLI"}, headers=headers)
    assert r.status_code == 201
    raw = r.json()["token"]
    token_id = r.json()["id"]
    assert raw.startswith("jnu_")

    # API 토큰으로도 동일하게 인증 가능 (웹/API/CLI 공용)
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 200

    # 목록에는 해시/원문이 노출되지 않음
    r = client.get("/api/tokens", headers=headers)
    assert "token" not in r.json()[0] and "token_hash" not in r.json()[0]

    # 폐기 후 사용 불가
    assert client.delete(f"/api/tokens/{token_id}", headers=headers).status_code == 204
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 401


def test_refresh_token_flow(client):
    signup_and_login(client, email="rf@jnu.ac.kr")
    r = client.post("/api/auth/login", json={"email": "rf@jnu.ac.kr", "password": "password123!"})
    refresh = r.json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200 and "access_token" in r.json()
    # 액세스 토큰을 리프레시로 쓰면 거부
    access = r.json()["access_token"]
    assert client.post("/api/auth/refresh", json={"refresh_token": access}).status_code == 401
