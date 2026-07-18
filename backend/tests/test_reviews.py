from tests.conftest import signup_and_login
from tests.helpers import VALID_REVIEW, publish_mvp


def _review(client, headers, mvp_id, **overrides):
    body = dict(VALID_REVIEW, **overrides)
    return client.post(f"/api/mvps/{mvp_id}/reviews", headers=headers, json=body)


def test_review_awards_credit_and_point(client):
    owner = signup_and_login(client, email="owner@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="rev@jnu.ac.kr", nickname="평가자")

    r = _review(client, reviewer, mvp_id)
    assert r.status_code == 201, r.text
    me = client.get("/api/auth/me", headers=reviewer).json()
    assert me["credit_balance"] == 4  # 가입 3 + 평가 1
    assert me["point_balance"] == 1


def test_cannot_review_own_mvp(client):
    owner = signup_and_login(client, email="own2@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    assert _review(client, owner, mvp_id).status_code == 400


def test_cannot_review_twice_but_can_edit(client):
    owner = signup_and_login(client, email="own3@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="rev3@jnu.ac.kr", nickname="평가자3")

    review_id = _review(client, reviewer, mvp_id).json()["id"]
    assert _review(client, reviewer, mvp_id).status_code == 409  # 재평가 방지

    r = client.put(f"/api/reviews/{review_id}", headers=reviewer,
                   json=dict(VALID_REVIEW, rating=2))
    assert r.status_code == 200 and r.json()["rating"] == 2
    # 수정으로는 추가 크레딧이 지급되지 않음
    assert client.get("/api/auth/me", headers=reviewer).json()["credit_balance"] == 4


def test_improvement_note_min_length(client):
    owner = signup_and_login(client, email="own4@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="rev4@jnu.ac.kr", nickname="평가자4")
    assert _review(client, reviewer, mvp_id, improvement_note="짧음").status_code == 400


def test_stuck_step_required_when_core_not_reached(client):
    owner = signup_and_login(client, email="own5@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="rev5@jnu.ac.kr", nickname="평가자5")

    r = _review(client, reviewer, mvp_id, reached_core=False, stuck_step_id=None)
    assert r.status_code == 400

    steps = client.get(f"/api/mvps/{mvp_id}", headers=reviewer).json()["test_steps"]
    r = _review(client, reviewer, mvp_id, reached_core=False,
                stuck_step_id=steps[0]["id"], stuck_note="첫 화면에서 막힘")
    assert r.status_code == 201


def test_stuck_step_must_belong_to_mvp(client):
    owner = signup_and_login(client, email="own6@jnu.ac.kr")
    mvp_a = publish_mvp(client, owner, title="A")
    reviewer = signup_and_login(client, email="rev6@jnu.ac.kr", nickname="평가자6")
    _review(client, reviewer, mvp_a)  # 크레딧 확보용이 아니라 단계 조회용

    other_owner = signup_and_login(client, email="own6b@jnu.ac.kr", nickname="타주인")
    mvp_b = publish_mvp(client, other_owner, title="B")
    steps_a = client.get(f"/api/mvps/{mvp_a}", headers=reviewer).json()["test_steps"]
    r = client.post(f"/api/mvps/{mvp_b}/reviews", headers=reviewer,
                    json=dict(VALID_REVIEW, reached_core=False, stuck_step_id=steps_a[0]["id"]))
    assert r.status_code == 400


def test_delete_review_revokes_reward(client):
    owner = signup_and_login(client, email="own7@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    reviewer = signup_and_login(client, email="rev7@jnu.ac.kr", nickname="평가자7")
    review_id = _review(client, reviewer, mvp_id).json()["id"]

    assert client.delete(f"/api/reviews/{review_id}", headers=reviewer).status_code == 204
    me = client.get("/api/auth/me", headers=reviewer).json()
    assert me["credit_balance"] == 3 and me["point_balance"] == 0  # 보상 회수


def test_vote_and_useful_sort(client):
    owner = signup_and_login(client, email="own8@jnu.ac.kr")
    mvp_id = publish_mvp(client, owner)
    r1 = signup_and_login(client, email="r8a@jnu.ac.kr", nickname="평가갑")
    r2 = signup_and_login(client, email="r8b@jnu.ac.kr", nickname="평가을")
    voter = signup_and_login(client, email="r8c@jnu.ac.kr", nickname="투표병")

    rev1 = _review(client, r1, mvp_id).json()["id"]
    rev2 = _review(client, r2, mvp_id).json()["id"]

    # 자기 평가에는 투표 불가
    assert client.post(f"/api/reviews/{rev1}/vote", headers=r1,
                       json={"is_useful": True}).status_code == 400

    r = client.post(f"/api/reviews/{rev2}/vote", headers=voter, json={"is_useful": True})
    assert r.json()["useful_count"] == 1

    items = client.get(f"/api/mvps/{mvp_id}/reviews?sort=useful", headers=voter).json()
    assert items[0]["id"] == rev2 and items[0]["useful_count"] == 1

    # 투표 변경(업서트) — 중복 행이 아니라 값 갱신
    r = client.post(f"/api/reviews/{rev2}/vote", headers=voter, json={"is_useful": False})
    assert r.json()["useful_count"] == 0


def test_mvp_list_sorting(client):
    owner_a = signup_and_login(client, email="own9a@jnu.ac.kr", nickname="주인갑")
    owner_b = signup_and_login(client, email="own9b@jnu.ac.kr", nickname="주인을")
    reviewer = signup_and_login(client, email="rev9@jnu.ac.kr", nickname="평가자9")
    mvp_low = publish_mvp(client, owner_a, title="낮은 평점", category="교육")
    _review(client, reviewer, mvp_low, rating=2)
    mvp_high = publish_mvp(client, owner_b, title="높은 평점", category="생산성")
    _review(client, reviewer, mvp_high, rating=5)

    by_rating = client.get("/api/mvps?sort=rating").json()
    assert by_rating[0]["title"] == "높은 평점"

    by_category = client.get("/api/mvps?category=교육").json()
    assert [m["title"] for m in by_category] == ["낮은 평점"]
