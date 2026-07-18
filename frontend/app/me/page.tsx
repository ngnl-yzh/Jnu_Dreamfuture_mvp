"use client";

import { useCallback, useEffect, useState } from "react";
import { api, API_BASE, getToken } from "../../lib/api";

interface MvpStats {
  mvp_id: number; title: string; status: string; view_count: number;
  review_count: number; avg_rating: number | null;
  rating_distribution: Record<string, number>;
  onboarding_success_rate: number | null; core_reach_rate: number | null;
  stuck_by_step: { step_order: number; title: string; fixed_category: string; stuck_count: number }[];
  stuck_by_category: Record<string, number>;
  nps: number | null;
}
interface Artifact {
  id: number; version: number; file_size: number; publish_status: string;
  upload_channel: string; uploaded_at: string;
}
interface ApiTokenItem { id: number; label: string; created_at: string; last_used_at: string | null; revoked_at: string | null; }
interface ExportReq { id: number; status: string; include_free_text: boolean; decision_note: string; created_at: string; }

const CATEGORY_LABELS: Record<string, string> = {
  pre_entry: "진입 전", setup: "가입·설정", core: "핵심 기능", post: "완료 후",
};

export default function MyPage() {
  const [stats, setStats] = useState<MvpStats[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [exportReqs, setExportReqs] = useState<ExportReq[]>([]);
  const [tokens, setTokens] = useState<ApiTokenItem[]>([]);
  const [newToken, setNewToken] = useState("");
  const [tokenLabel, setTokenLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const loadAll = useCallback(() => {
    api<{ mvps: MvpStats[] }>("/api/me/dashboard").then((d) => {
      setStats(d.mvps);
      if (d.mvps.length > 0) {
        setSelected((prev) => prev ?? d.mvps[0].mvp_id);
      }
    }).catch((e) => setError(e.message));
    api<ApiTokenItem[]>("/api/tokens").then(setTokens).catch(() => {});
  }, []);

  useEffect(() => {
    if (!getToken()) { setError("로그인 후 이용할 수 있습니다."); return; }
    const params = new URLSearchParams(location.search);
    const pre = params.get("mvp");
    if (pre) setSelected(+pre);
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (selected === null) return;
    api<Artifact[]>(`/api/mvps/${selected}/artifacts`).then(setArtifacts).catch(() => setArtifacts([]));
    api<ExportReq[]>(`/api/mvps/${selected}/export-requests`).then(setExportReqs).catch(() => setExportReqs([]));
  }, [selected, msg]);

  const current = stats.find((s) => s.mvp_id === selected);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || selected === null) return;
    setError(""); setMsg("");
    const form = new FormData();
    form.append("file", file);
    form.append("channel", "web");
    try {
      const r = await api<Artifact>(`/api/mvps/${selected}/artifacts`, { form });
      setMsg(`v${r.version} 업로드 완료 (draft). 게시 신청을 눌러 공개를 요청하세요.`);
      setFile(null);
    } catch (err: any) { setError(err.message); }
  }

  async function publish(version: number) {
    setError(""); setMsg("");
    try {
      await api(`/api/mvps/${selected}/artifacts/${version}/publish`, { method: "POST" });
      setMsg(`v${version} 게시 신청 완료 — 본부 관리자 승인 후 공개됩니다.`);
      loadAll();
    } catch (err: any) { setError(err.message); }
  }

  async function requestExport(includeFreeText: boolean) {
    setError(""); setMsg("");
    try {
      await api(`/api/mvps/${selected}/export-requests`, { body: { include_free_text: includeFreeText } });
      setMsg("반출 신청 완료 — 본부 심사 후 다운로드할 수 있습니다.");
    } catch (err: any) { setError(err.message); }
  }

  async function downloadExport(format: "csv" | "json") {
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/mvps/${selected}/export?format=${format}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => null);
        throw new Error(d?.detail ?? `다운로드 실패 (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mvp-${selected}-reviews.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) { setError(err.message); }
  }

  async function issueToken(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const r = await api<{ token: string }>("/api/tokens", { body: { label: tokenLabel } });
      setNewToken(r.token);
      setTokenLabel("");
      loadAll();
    } catch (err: any) { setError(err.message); }
  }

  async function revokeToken(id: number) {
    await api(`/api/tokens/${id}`, { method: "DELETE" });
    loadAll();
  }

  if (error && stats.length === 0) return <p className="error">{error}</p>;

  return (
    <div>
      <h1>마이페이지</h1>
      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}

      <h2>내 MVP 대시보드</h2>
      {stats.length === 0 ? (
        <p className="muted">등록한 MVP가 없습니다. <a href="/mvps/new">MVP를 등록해보세요</a>.</p>
      ) : (
        <>
          <div className="tabs">
            {stats.map((s) => (
              <button key={s.mvp_id} className={`tab ${selected === s.mvp_id ? "active" : ""}`}
                      onClick={() => setSelected(s.mvp_id)}>
                {s.title} <span className={`badge ${s.status}`}>{s.status}</span>
              </button>
            ))}
          </div>

          {current && (
            <div className="card">
              <div className="stat-grid">
                {[
                  ["조회", current.view_count],
                  ["리뷰", current.review_count],
                  ["평균 별점", current.avg_rating !== null ? `★ ${current.avg_rating}` : "-"],
                  ["온보딩 성공률", current.onboarding_success_rate !== null ? `${current.onboarding_success_rate}%` : "-"],
                  ["핵심 도달률", current.core_reach_rate !== null ? `${current.core_reach_rate}%` : "-"],
                  ["NPS", current.nps ?? "-"],
                ].map(([k, v]) => (
                  <div className="stat-box" key={k as string}>
                    <div className="k">{k}</div>
                    <div className="v">{v}</div>
                  </div>
                ))}
              </div>

              <h3>평점 분포</h3>
              {Object.entries(current.rating_distribution).reverse().map(([star, count]) => {
                const max = Math.max(1, ...Object.values(current.rating_distribution));
                return (
                  <div className="bar-row" key={star}>
                    <span style={{ width: 30 }}>{star}점</span>
                    <div className="bar-track"><div className="bar-fill" style={{ width: `${(count / max) * 100}%` }} /></div>
                    <span style={{ width: 24 }}>{count}</span>
                  </div>
                );
              })}

              <h3>단계별 이탈 (막힌 지점)</h3>
              {current.stuck_by_step.map((s) => {
                const max = Math.max(1, ...current.stuck_by_step.map((x) => x.stuck_count));
                return (
                  <div className="bar-row" key={s.step_order}>
                    <span style={{ width: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {s.step_order}. {s.title} <span className="muted">({CATEGORY_LABELS[s.fixed_category]})</span>
                    </span>
                    <div className="bar-track"><div className="bar-fill bad" style={{ width: `${(s.stuck_count / max) * 100}%` }} /></div>
                    <span style={{ width: 24 }}>{s.stuck_count}</span>
                  </div>
                );
              })}
            </div>
          )}

          <div className="card">
            <h3 style={{ marginTop: 0 }}>버전 관리</h3>
            <form onSubmit={upload} className="field-row">
              <div style={{ flex: 1 }}>
                <label>정적 웹 zip 업로드 (루트 index.html 필수, 100MB 이하)</label>
                <input type="file" accept=".zip"
                       onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </div>
              <button className="btn" type="submit" disabled={!file}>업로드</button>
            </form>
            <table style={{ marginTop: 12 }}>
              <thead><tr><th>버전</th><th>상태</th><th>채널</th><th>크기</th><th>업로드</th><th></th></tr></thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr key={a.id}>
                    <td>v{a.version}</td>
                    <td><span className={`badge ${a.publish_status}`}>{a.publish_status}</span></td>
                    <td>{a.upload_channel}</td>
                    <td>{(a.file_size / 1024).toFixed(1)} KB</td>
                    <td className="muted">{a.uploaded_at?.slice(0, 16).replace("T", " ")}</td>
                    <td>
                      {a.publish_status !== "published" && (
                        <button className="btn btn-sm" onClick={() => publish(a.version)}>게시 신청</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {artifacts.length === 0 && <p className="muted">아직 업로드된 버전이 없습니다.
              CLI로도 배포할 수 있습니다: <code>mvp push</code></p>}
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>데이터 반출 (본부 승인 필요)</h3>
            <p className="muted">사이트 내 대시보드 열람은 승인이 필요 없지만, CSV/JSON 반출은 본부 심사를 거칩니다.
              반출 데이터는 익명화(가명 ID) 처리됩니다.</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => requestExport(false)}>반출 신청 (수치만)</button>
              <button className="btn btn-ghost btn-sm" onClick={() => requestExport(true)}>반출 신청 (자유 서술 포함)</button>
              <button className="btn btn-sm" onClick={() => downloadExport("csv")}>CSV 다운로드</button>
              <button className="btn btn-sm" onClick={() => downloadExport("json")}>JSON 다운로드</button>
            </div>
            {exportReqs.length > 0 && (
              <table style={{ marginTop: 12 }}>
                <thead><tr><th>신청일</th><th>범위</th><th>상태</th><th>비고</th></tr></thead>
                <tbody>
                  {exportReqs.map((r) => (
                    <tr key={r.id}>
                      <td className="muted">{r.created_at?.slice(0, 10)}</td>
                      <td>{r.include_free_text ? "자유 서술 포함" : "수치만"}</td>
                      <td><span className={`badge ${r.status === "approved" ? "published" : r.status}`}>{r.status}</span></td>
                      <td className="muted">{r.decision_note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      <h2>API 토큰 (CLI 배포용)</h2>
      <div className="card">
        <p className="muted">
          <code>pip install jnu-mvp</code> → <code>mvp login</code>에 아래 토큰을 입력하면
          <code> mvp push</code> 한 줄로 배포할 수 있습니다.
        </p>
        <form onSubmit={issueToken} className="field-row">
          <div style={{ flex: 1 }}>
            <label>토큰 이름</label>
            <input value={tokenLabel} onChange={(e) => setTokenLabel(e.target.value)}
                   placeholder="예: 내 노트북 CLI" />
          </div>
          <button className="btn" type="submit">발급</button>
        </form>
        {newToken && (
          <p className="success" style={{ wordBreak: "break-all" }}>
            새 토큰 (지금만 표시됩니다): <code>{newToken}</code>
          </p>
        )}
        <table style={{ marginTop: 12 }}>
          <thead><tr><th>이름</th><th>발급일</th><th>마지막 사용</th><th>상태</th><th></th></tr></thead>
          <tbody>
            {tokens.map((t) => (
              <tr key={t.id}>
                <td>{t.label || "(이름 없음)"}</td>
                <td className="muted">{t.created_at?.slice(0, 10)}</td>
                <td className="muted">{t.last_used_at?.slice(0, 16).replace("T", " ") ?? "-"}</td>
                <td>{t.revoked_at ? <span className="badge rejected">폐기됨</span> : <span className="badge published">활성</span>}</td>
                <td>{!t.revoked_at && (
                  <button className="btn btn-danger btn-sm" onClick={() => revokeToken(t.id)}>폐기</button>
                )}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
