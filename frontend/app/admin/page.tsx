"use client";

import { useCallback, useEffect, useState } from "react";
import { api, getToken } from "../../lib/api";

interface PendingMvp {
  id: number; title: string; tagline: string; category: string;
  runtime_type: string; owner_nickname: string; created_at: string;
}
interface ExportReq {
  id: number; mvp_id: number; mvp_title: string; requester_nickname: string;
  include_free_text: boolean; created_at: string;
}
interface ReportItem {
  id: number; target_type: string; target_id: number; reason: string; created_at: string;
}
interface AuditRow {
  id: number; mvp_id: number; exported_by: string; data_scope: string; exported_at: string;
}

export default function AdminPage() {
  const [mvps, setMvps] = useState<PendingMvp[]>([]);
  const [exports, setExports] = useState<ExportReq[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    api<PendingMvp[]>("/api/admin/mvps?status_filter=pending").then(setMvps).catch((e) => setError(e.message));
    api<ExportReq[]>("/api/admin/export-requests").then(setExports).catch(() => {});
    api<ReportItem[]>("/api/admin/reports").then(setReports).catch(() => {});
    api<AuditRow[]>("/api/admin/export-audit").then(setAudit).catch(() => {});
  }, []);

  useEffect(() => {
    if (!getToken()) { setError("로그인 후 이용할 수 있습니다."); return; }
    load();
  }, [load]);

  async function act(path: string, body: unknown = { note: "" }) {
    setError(""); setMsg("");
    try {
      await api(path, { body });
      setMsg("처리 완료");
      load();
    } catch (err: any) { setError(err.message); }
  }

  return (
    <div>
      <h1>본부 관리자</h1>
      {msg && <p className="success">{msg}</p>}
      {error && <p className="error">{error}</p>}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>게시 승인 대기 ({mvps.length})</h2>
        {mvps.length === 0 && <p className="muted">대기 중인 MVP가 없습니다.</p>}
        {mvps.map((m) => (
          <div key={m.id} style={{ display: "flex", justifyContent: "space-between",
                                   alignItems: "center", borderTop: "1px solid var(--line)",
                                   padding: "10px 0", gap: 10, flexWrap: "wrap" }}>
            <div>
              <strong>{m.title}</strong> <span className="badge">{m.category}</span>{" "}
              <span className="badge">{m.runtime_type}</span>
              <div className="muted" style={{ fontSize: 13 }}>{m.tagline} — by {m.owner_nickname}</div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <a className="btn btn-ghost btn-sm" href={`/mvps/${m.id}`}>검수</a>
              <button className="btn btn-sm" onClick={() => act(`/api/admin/mvps/${m.id}/approve`, undefined)}>승인</button>
              <button className="btn btn-danger btn-sm"
                      onClick={() => act(`/api/admin/mvps/${m.id}/reject`)}>반려</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>데이터 반출 심사 ({exports.length})</h2>
        {exports.length === 0 && <p className="muted">대기 중인 반출 신청이 없습니다.</p>}
        {exports.map((r) => (
          <div key={r.id} style={{ display: "flex", justifyContent: "space-between",
                                   alignItems: "center", borderTop: "1px solid var(--line)",
                                   padding: "10px 0", gap: 10, flexWrap: "wrap" }}>
            <div>
              <strong>{r.mvp_title}</strong>{" "}
              <span className="badge">{r.include_free_text ? "자유 서술 포함" : "수치만"}</span>
              <div className="muted" style={{ fontSize: 13 }}>
                신청자: {r.requester_nickname} · {r.created_at?.slice(0, 10)}
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn btn-sm"
                      onClick={() => act(`/api/admin/export-requests/${r.id}/approve`)}>승인</button>
              <button className="btn btn-danger btn-sm"
                      onClick={() => act(`/api/admin/export-requests/${r.id}/reject`)}>반려</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>신고 처리 ({reports.length})</h2>
        {reports.length === 0 && <p className="muted">대기 중인 신고가 없습니다.</p>}
        {reports.map((r) => (
          <div key={r.id} style={{ display: "flex", justifyContent: "space-between",
                                   alignItems: "center", borderTop: "1px solid var(--line)",
                                   padding: "10px 0", gap: 10, flexWrap: "wrap" }}>
            <div>
              <span className="badge">{r.target_type} #{r.target_id}</span> {r.reason}
              <div className="muted" style={{ fontSize: 13 }}>{r.created_at?.slice(0, 16).replace("T", " ")}</div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button className="btn btn-danger btn-sm"
                      onClick={() => act(`/api/admin/reports/${r.id}/confirm`)}>확정 (보상 회수)</button>
              <button className="btn btn-ghost btn-sm"
                      onClick={() => act(`/api/admin/reports/${r.id}/dismiss`)}>기각</button>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>반출 감사 로그</h2>
        <table>
          <thead><tr><th>일시</th><th>MVP</th><th>반출자</th><th>범위</th></tr></thead>
          <tbody>
            {audit.map((a) => (
              <tr key={a.id}>
                <td className="muted">{a.exported_at?.slice(0, 16).replace("T", " ")}</td>
                <td>#{a.mvp_id}</td>
                <td>{a.exported_by}</td>
                <td><code>{a.data_scope}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
        {audit.length === 0 && <p className="muted">반출 이력이 없습니다.</p>}
      </div>
    </div>
  );
}
