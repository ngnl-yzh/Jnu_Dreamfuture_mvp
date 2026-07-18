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

  return (
    <div>
      <h1>전남대 구성원의 MVP를 체험하고 평가해보세요</h1>
      <p className="muted">
        소스코드는 공개되지 않습니다 — 사이트 안에서 실행 화면만 체험하는 블랙박스 방식입니다.
        평가 1건 작성 = 크레딧 +1, MVP 등록 = 크레딧 3 소모.
      </p>

      <div className="tabs">
        {SORTS.map(([key, label]) => (
          <button key={key} className={`tab ${sort === key ? "active" : ""}`}
                  onClick={() => setSort(key)}>
            {label}
          </button>
        ))}
        {categories.length > 0 && (
          <select style={{ width: "auto" }} value={category}
                  onChange={(e) => setCategory(e.target.value)}>
            <option value="">전체 카테고리</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      {items.length === 0 && !error && (
        <p className="muted">아직 게시된 MVP가 없습니다. 첫 번째 MVP를 등록해보세요!</p>
      )}

      <div className="grid">
        {items.map((m) => (
          <Link key={m.id} href={`/mvps/${m.id}`} style={{ color: "inherit" }}>
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{m.title}</strong>
                <span className="badge">{m.category}</span>
              </div>
              <p className="muted" style={{ margin: "6px 0" }}>{m.tagline}</p>
              <div className="muted" style={{ fontSize: 12 }}>
                {m.avg_rating !== null && <span className="stars">★ {m.avg_rating} </span>}
                리뷰 {m.review_count} · 유용 {m.useful_vote_count} · 조회 {m.view_count} · by {m.owner_nickname}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
