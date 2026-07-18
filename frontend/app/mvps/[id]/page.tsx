"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { api, getToken, RUN_BASE } from "../../../lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  pre_entry: "진입 전", setup: "가입·설정", core: "핵심 기능", post: "완료 후",
};

interface TestStep { id: number; step_order: number; title: string; guide_text: string; fixed_category: string; }
interface Detail {
  id: number; title: string; tagline: string; description_md: string; category: string;
  tags: string[]; status: string; owner_id: number; owner_nickname: string;
  view_count: number; review_count: number; avg_rating: number | null;
  test_steps: TestStep[];
  instance: { status: string; route_path: string } | null;
  my_review_id: number | null;
}
interface ReviewItem {
  id: number; reviewer_nickname: string; first_impression: number; onboarding_ok: boolean;
  onboarding_note: string; reached_core: boolean; stuck_step_id: number | null;
  stuck_step_title: string | null; stuck_note: string; rating: number;
  improvement_note: string; nps: number; useful_count: number;
  my_vote: boolean | null; is_mine: boolean; created_at: string;
}

const EMPTY_FORM = {
  first_impression: 3, onboarding_ok: true, onboarding_note: "",
  reached_core: true, stuck_step_id: null as number | null, stuck_note: "",
  rating: 3, improvement_note: "", nps: 7,
};

export default function MvpDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [reviewSort, setReviewSort] = useState<"latest" | "useful">("useful");
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [starting, setStarting] = useState(false);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(() => {
    api<Detail>(`/api/mvps/${id}`).then(setDetail).catch((e) => setError(e.message));
    api<ReviewItem[]>(`/api/mvps/${id}/reviews?sort=${reviewSort}`).then(setReviews).catch(() => {});
  }, [id, reviewSort]);

  useEffect(() => {
    if (!getToken()) { setError("로그인 후 이용할 수 있습니다."); return; }
    load();
  }, [load]);

  // 실행 중이면 30초마다 하트비트 → 유휴 종료 방지
  useEffect(() => {
    if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    if (detail?.instance?.status === "running") {
      heartbeatRef.current = setInterval(() => {
        api(`/api/mvps/${id}/instance/heartbeat`, { method: "POST" }).catch(() => {});
      }, 30_000);
    }
    return () => { if (heartbeatRef.current) clearInterval(heartbeatRef.current); };
  }, [detail?.instance?.status, id]);

  async function startInstance() {
    setStarting(true);
    setError("");
    try {
      await api(`/api/mvps/${id}/instance/start`, { method: "POST" });
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setStarting(false);
    }
  }

  async function submitReview(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    try {
      if (editingId) {
        await api(`/api/reviews/${editingId}`, { method: "PUT", body: form });
      } else {
        await api(`/api/mvps/${id}/reviews`, { body: form });
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
      load();
    } catch (err: any) {
      setFormError(err.message);
    }
  }

  async function vote(reviewId: number, isUseful: boolean) {
    try {
      await api(`/api/reviews/${reviewId}/vote`, { body: { is_useful: isUseful } });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  }

  function startEdit(r: ReviewItem) {
    setEditingId(r.id);
    setForm({
      first_impression: r.first_impression, onboarding_ok: r.onboarding_ok,
      onboarding_note: r.onboarding_note, reached_core: r.reached_core,
      stuck_step_id: r.stuck_step_id, stuck_note: r.stuck_note,
      rating: r.rating, improvement_note: r.improvement_note, nps: r.nps,
    });
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }

  if (error && !detail) return <p className="error">{error}</p>;
  if (!detail) return <p className="muted">불러오는 중…</p>;

  const running = detail.instance?.status === "running";
  const runUrl = running ? `${RUN_BASE}${detail.instance!.route_path}/` : null;
  const canReview = detail.my_review_id === null;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0 }}>{detail.title}</h1>
        <span className="badge">{detail.category}</span>
        <span className={`badge ${detail.status}`}>{detail.status}</span>
      </div>
      <p className="muted">{detail.tagline} — by {detail.owner_nickname} · 조회 {detail.view_count}
        {detail.avg_rating !== null && <> · <span className="stars">★ {detail.avg_rating}</span> ({detail.review_count})</>}
      </p>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>체험하기</h2>
          <div>
            <span className={`badge ${running ? "running" : ""}`}>
              {running ? "실행 중" : "중지됨"}
            </span>{" "}
            <button className="btn btn-sm" onClick={startInstance} disabled={starting}>
              {starting ? "기동 중…" : running ? "재시작" : "실행"}
            </button>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        {runUrl ? (
          <div className="iframe-wrap" style={{ marginTop: 12 }}>
            {/* 블랙박스 실행: sandbox 속성으로 플랫폼 도메인과 격리 */}
            <iframe src={runUrl} sandbox="allow-scripts allow-forms allow-same-origin"
                    title={detail.title} />
          </div>
        ) : (
          <p className="muted" style={{ marginTop: 10 }}>
            실행 버튼을 누르면 샌드박스에서 MVP가 기동됩니다. 소스코드는 노출되지 않습니다.
          </p>
        )}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>테스트 시나리오</h2>
        <p className="muted">아래 단계를 따라 체험해보세요. 평가 시 막힌 단계를 선택하게 됩니다.</p>
        <ul className="step-list">
          {detail.test_steps.map((s) => (
            <li key={s.id}>
              <span className="step-num">{s.step_order}</span>
              <span><strong>{s.title}</strong>
                {s.guide_text && <span className="muted"> — {s.guide_text}</span>}{" "}
                <span className="badge">{CATEGORY_LABELS[s.fixed_category]}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      {detail.description_md && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>소개</h2>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: 0 }}>{detail.description_md}</pre>
        </div>
      )}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>평가 ({reviews.length})</h2>
          <div className="tabs" style={{ margin: 0 }}>
            <button className={`tab ${reviewSort === "useful" ? "active" : ""}`}
                    onClick={() => setReviewSort("useful")}>유용순</button>
            <button className={`tab ${reviewSort === "latest" ? "active" : ""}`}
                    onClick={() => setReviewSort("latest")}>최신순</button>
          </div>
        </div>

        {reviews.map((r) => (
          <div key={r.id} style={{ borderTop: "1px solid var(--line)", paddingTop: 12, marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
              <strong>{r.reviewer_nickname} <span className="stars">{"★".repeat(r.rating)}</span></strong>
              <span className="muted" style={{ fontSize: 12 }}>
                첫인상 {r.first_impression}/5 · NPS {r.nps}/10 ·{" "}
                {r.onboarding_ok ? "온보딩 성공" : "온보딩 실패"} ·{" "}
                {r.reached_core ? "핵심 도달" : `막힘: ${r.stuck_step_title ?? "-"}`}
              </span>
            </div>
            {!r.reached_core && r.stuck_note && <p className="muted" style={{ margin: "4px 0" }}>막힌 지점: {r.stuck_note}</p>}
            {r.onboarding_note && <p className="muted" style={{ margin: "4px 0" }}>온보딩: {r.onboarding_note}</p>}
            <p style={{ margin: "6px 0" }}>{r.improvement_note}</p>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {!r.is_mine && (
                <button className="btn btn-ghost btn-sm" onClick={() => vote(r.id, !(r.my_vote === true))}>
                  👍 유용해요 {r.useful_count}
                </button>
              )}
              {r.is_mine && (
                <button className="btn btn-ghost btn-sm" onClick={() => startEdit(r)}>내 평가 수정</button>
              )}
            </div>
          </div>
        ))}
        {reviews.length === 0 && <p className="muted">아직 평가가 없습니다. 첫 평가를 남겨보세요! (+크레딧 1)</p>}
      </div>

      {(canReview || editingId) && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>{editingId ? "내 평가 수정" : "평가 작성 (+크레딧 1, +포인트 1)"}</h2>
          <form onSubmit={submitReview}>
            <label>① 첫인상 (설명을 읽기 전 화면만 보고): {form.first_impression}/5</label>
            <input type="range" min={1} max={5} value={form.first_impression}
                   onChange={(e) => setForm({ ...form, first_impression: +e.target.value })} />

            <label>② 설명 없이 시작할 수 있었나요?</label>
            <div style={{ display: "flex", gap: 14 }}>
              <label style={{ fontWeight: 400 }}><input type="radio" style={{ width: "auto" }}
                     checked={form.onboarding_ok} onChange={() => setForm({ ...form, onboarding_ok: true })} /> 예</label>
              <label style={{ fontWeight: 400 }}><input type="radio" style={{ width: "auto" }}
                     checked={!form.onboarding_ok} onChange={() => setForm({ ...form, onboarding_ok: false })} /> 아니오</label>
            </div>
            <input value={form.onboarding_note} placeholder="온보딩 경험을 적어주세요"
                   onChange={(e) => setForm({ ...form, onboarding_note: e.target.value })} />

            <label>③ 핵심 기능에 도달했나요?</label>
            <div style={{ display: "flex", gap: 14 }}>
              <label style={{ fontWeight: 400 }}><input type="radio" style={{ width: "auto" }}
                     checked={form.reached_core}
                     onChange={() => setForm({ ...form, reached_core: true, stuck_step_id: null })} /> 예</label>
              <label style={{ fontWeight: 400 }}><input type="radio" style={{ width: "auto" }}
                     checked={!form.reached_core} onChange={() => setForm({ ...form, reached_core: false })} /> 아니오</label>
            </div>
            {!form.reached_core && (
              <>
                <label>막힌 단계 (필수)</label>
                <select value={form.stuck_step_id ?? ""} required
                        onChange={(e) => setForm({ ...form, stuck_step_id: e.target.value ? +e.target.value : null })}>
                  <option value="">단계 선택</option>
                  {detail.test_steps.map((s) => (
                    <option key={s.id} value={s.id}>{s.step_order}. {s.title}</option>
                  ))}
                </select>
                <input value={form.stuck_note} placeholder="어떻게 막혔는지 적어주세요"
                       onChange={(e) => setForm({ ...form, stuck_note: e.target.value })} />
              </>
            )}

            <label>④ 완성도·유용성: {form.rating}/5</label>
            <input type="range" min={1} max={5} value={form.rating}
                   onChange={(e) => setForm({ ...form, rating: +e.target.value })} />

            <label>⑤ 개선 제안 (최소 30자)</label>
            <textarea rows={3} minLength={30} required value={form.improvement_note}
                      onChange={(e) => setForm({ ...form, improvement_note: e.target.value })} />

            <label>⑥ 계속 쓸 의향 (NPS): {form.nps}/10</label>
            <input type="range" min={0} max={10} value={form.nps}
                   onChange={(e) => setForm({ ...form, nps: +e.target.value })} />

            {formError && <p className="error">{formError}</p>}
            <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
              <button className="btn" type="submit">{editingId ? "수정 저장" : "평가 제출"}</button>
              {editingId && (
                <button className="btn btn-ghost" type="button"
                        onClick={() => { setEditingId(null); setForm(EMPTY_FORM); }}>취소</button>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
