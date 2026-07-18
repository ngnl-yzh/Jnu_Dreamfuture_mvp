"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface MvpItem {
  id: number;
  title: string;
  tagline: string;
  category: string;
  tags: string[];
  owner_nickname: string;
  view_count: number;
  review_count: number;
  avg_rating: number | null;
  useful_vote_count: number;
}

const SORTS = [
  ["latest", "최신순"],
  ["rating", "평점순"],
  ["reviews", "리뷰 많은 순"],
  ["votes", "유용 투표순"],
] as const;

function Stars({ value }: { value: number }) {
  const full = Math.round(value);
  return (
    <span className="stars" title={`평균 ${value}점`}>
      {"★".repeat(full)}{"☆".repeat(5 - full)} <span style={{ color: "var(--text)" }}>{value}</span>
    </span>
  );
}

export default function HomePage() {
  const [items, setItems] = useState<MvpItem[]>([]);
  const [sort, setSort] = useState("latest");
  const [category, setCategory] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ sort });
    if (category) params.set("category", category);
    api<MvpItem[]>(`/api/mvps?${params}`).then(setItems).catch((e) => setError(e.message));
  }, [sort, category]);

  const categories = Array.from(new Set(items.map((m) => m.category)));
  const totalReviews = items.reduce((acc, m) => acc + m.review_count, 0);

  return (
    <div>
      <section className="hero">
        <div className="hero-eyebrow">🎓 전남대학교 구성원 전용</div>
        <h1>
          만든 사람은 <span className="accent">피드백</span>을,<br />
          써본 사람은 <span className="accent">크레딧</span>을.
        </h1>
        <p className="hero-sub">
          내가 만든 MVP를 올리면 다른 구성원이 사이트 안에서 바로 체험하고 구조화된 평가를 남깁니다.
          소스코드는 절대 공개되지 않는 블랙박스 방식.
        </p>
        <div className="hero-stats">
          <span className="stat-pill"><strong>{items.length}</strong>개 MVP 게시 중</span>
          <span className="stat-pill"><strong>{totalReviews}</strong>건의 평가</span>
          <span className="stat-pill">평가 1건 = <strong>크레딧 +1</strong></span>
          <span className="stat-pill">등록 1회 = <strong>크레딧 3</strong> 소모</span>
        </div>
      </section>

      <div className="tabs">
        {SORTS.map(([key, label]) => (
          <button key={key} className={`tab ${sort === key ? "active" : ""}`}
                  onClick={() => setSort(key)}>
            {label}
          </button>
        ))}
        {categories.length > 0 && (
          <select style={{ width: "auto", marginLeft: "auto" }} value={category}
                  onChange={(e) => setCategory(e.target.value)}>
            <option value="">전체 카테고리</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      {items.length === 0 && !error && (
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <p style={{ fontSize: 32, margin: "0 0 8px" }}>🚀</p>
          <p className="muted">아직 게시된 MVP가 없습니다. 첫 번째 MVP를 등록해보세요!</p>
        </div>
      )}

      <div className="grid">
        {items.map((m) => (
          <Link key={m.id} href={`/mvps/${m.id}`}>
            <div className="card mvp-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 8 }}>
                <span className="mvp-title">{m.title}</span>
                <span className="badge cat">{m.category}</span>
              </div>
              <p className="mvp-tagline">{m.tagline}</p>
              {m.avg_rating !== null ? <Stars value={m.avg_rating} /> : (
                <span className="muted" style={{ fontSize: 12.5 }}>첫 평가를 기다리는 중</span>
              )}
              <div className="mvp-meta">
                <span>💬 {m.review_count}</span>
                <span>👍 {m.useful_vote_count}</span>
                <span>👀 {m.view_count}</span>
                <span style={{ marginLeft: "auto" }}>by {m.owner_nickname}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
