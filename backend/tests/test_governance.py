from tests.conftest import signup_and_login
from tests.helpers import VALID_REVIEW, create_mvp, make_static_zip, publish_mvp, upload_zip


def test_admin_approval_flow(client):
    owner = signup_and_login(client, email="flow@jnu.ac.kr")
    admin = signup_and_login(client, email="staff@jnu.ac.kr", nickname="본부관리자", admin=True)

    mvp_id = create_mvp(client, owner).json()["id"]
    upload_zip(client, owner, mvp_id, make_static_zip())
    client.post(f"/api/mvps/{mvp_id}/artifacts/1/publish", headers=owner)

    pending = client.get("/api/admin/mvps?status_filter=pending", headers=admin).json()
    assert any(m["id"] == mvp_id for m in pending)

    r = client.post(f"/api/admin/mvps/{mvp_id}/approve", headers=admin)
    assert r.json()["status"] == "published"
    assert any(m["id"] == mvp_id for m in client.get("/api/mvps").json())


def test_non_admin_cannot_use_admin_api(client):
    user = signup_and_login(client, email="pleb@jnu.ac.kr")
    assert client.get("/api/admin/mvps", headers=user).status_code == 403
    assert client.get("/api/admin/export-requests", headers=user).status_code == 403
    assert client.get("/api/admin/export-audit", headers=user).status_code == 403


def test_dashboard_stats(client):
    owner = signup_and_login(client, email="dash@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    steps = client.get(f"/api/mvps/{mvp_id}", headers=owner).json()["test_steps"]

    r1 = signup_and_login(client, email="d1@jnu.ac.kr", nickname="대시갑")
    r2 = signup_and_login(client, email="d2@jnu.ac.kr", nickname="대시을")
    client.post(f"/api/mvps/{mvp_id}/reviews", headers=r1,
                json=dict(VALID_REVIEW, rating=5, nps=10))
    client.post(f"/api/mvps/{mvp_id}/reviews", headers=r2,
                json=dict(VALID_REVIEW, rating=2, nps=3, reached_core=False,
                          stuck_step_id=steps[1]["id"], stuck_note="핵심 기능에서 막힘"))

    stats = client.get("/api/me/dashboard", headers=owner).json()["mvps"][0]
    assert stats["review_count"] == 2
    assert stats["rating_distribution"]["5"] == 1 and stats["rating_distribution"]["2"] == 1
    assert stats["core_reach_rate"] == 50.0
    assert stats["stuck_by_category"]["core"] == 1
    assert stats["nps"] == 0.0  # 추천 1, 비추천 1


def test_export_requires_approval_and_writes_audit(client):
    owner = signup_and_login(client, email="exp@jnu.ac.kr")
    admin = signup_and_login(client, email="staff2@jnu.ac.kr", nickname="본부심사역", admin=True)
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="exprev@jnu.ac.kr", nickname="반출평가자")
    client.post(f"/api/mvps/{mvp_id}/reviews", headers=reviewer, json=VALID_REVIEW)

    # 승인 전 export 차단
    assert client.get(f"/api/mvps/{mvp_id}/export", headers=owner).status_code == 403

    req_id = client.post(f"/api/mvps/{mvp_id}/export-requests", headers=owner,
                         json={"include_free_text": False}).json()["id"]
    # 중복 신청 차단
    assert client.post(f"/api/mvps/{mvp_id}/export-requests", headers=owner,
                       json={"include_free_text": False}).status_code == 409

    client.post(f"/api/admin/export-requests/{req_id}/approve", headers=admin,
                json={"note": "익명화 조건 승인"})

    r = client.get(f"/api/mvps/{mvp_id}/export?format=csv", headers=owner)
    assert r.status_code == 200
    body = r.text
    # 익명화: 이메일·닉네임 미포함, 가명 ID 포함, 자유 서술 미포함(옵션 false)
    assert "exprev@jnu.ac.kr" not in body and "반출평가자" not in body
    assert "rater-" in body
    assert "improvement_note" not in body

    r = client.get(f"/api/mvps/{mvp_id}/export?format=json", headers=owner)
    assert r.status_code == 200 and r.json()[0]["rater"].startswith("rater-")

    audit = client.get("/api/admin/export-audit", headers=admin).json()
    assert len(audit) == 2  # csv + json 각 1건 전 건 기록
    assert audit[0]["mvp_id"] == mvp_id


def test_export_free_text_option(client):
    owner = signup_and_login(client, email="exp2@jnu.ac.kr")
    admin = signup_and_login(client, email="staff3@jnu.ac.kr", nickname="본부심사역2", admin=True)
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="exprev2@jnu.ac.kr", nickname="반출평가자2")
    client.post(f"/api/mvps/{mvp_id}/reviews", headers=reviewer, json=VALID_REVIEW)

    req_id = client.post(f"/api/mvps/{mvp_id}/export-requests", headers=owner,
                         json={"include_free_text": True}).json()["id"]
    client.post(f"/api/admin/export-requests/{req_id}/approve", headers=admin, json={"note": ""})

    rows = client.get(f"/api/mvps/{mvp_id}/export?format=json", headers=owner).json()
    assert "improvement_note" in rows[0]


def test_report_confirm_revokes_reward(client):
    owner = signup_and_login(client, email="rep@jnu.ac.kr")
    admin = signup_and_login(client, email="staff4@jnu.ac.kr", nickname="본부신고처리", admin=True)
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="reprev@jnu.ac.kr", nickname="신고당한자")
    review_id = client.post(f"/api/mvps/{mvp_id}/reviews", headers=reviewer,
                            json=VALID_REVIEW).json()["id"]
    assert client.get("/api/auth/me", headers=reviewer).json()["credit_balance"] == 4

    client.post("/api/reports", headers=owner,
                json={"target_type": "review", "target_id": review_id, "reason": "무성의한 도배 평가"})
    report = client.get("/api/admin/reports", headers=admin).json()[0]
    client.post(f"/api/admin/reports/{report['id']}/confirm", headers=admin, json={"note": "확인"})

    me = client.get("/api/auth/me", headers=reviewer).json()
    assert me["credit_balance"] == 3 and me["point_balance"] == 0  # 회수 완료
