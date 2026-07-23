"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import StepNodes from "../components/StepNodes";
import { api, getToken } from "../lib/api";

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

const STEPS = [
  { id: 1, order: 1, title: "MVP 업로드", category: "pre_entry",
    guide: "웹·CLI·API 어느 채널로든 zip을 올리면 draft로 저장됩니다. 크레딧 3을 소모해 등록해요." },
  { id: 2, order: 2, title: "블랙박스 실행", category: "core",
    guide: "본부 승인 후, 다른 구성원이 사이트 안 샌드박스에서 바로 체험합니다. 소스코드는 절대 노출되지 않아요." },
  { id: 3, order: 3, title: "구조화 평가 수집", category: "post",
    guide: "6항목 평가와 단계별 이탈 데이터가 쌓이고, 평가자는 크레딧을 얻습니다. 반출은 본부 승인 하에만." },
];

const FEATURES = [
  { i: "🔒", t: "소스코드 블랙박스", d: "원본 파일은 내부 스토리지에만. 다운로드 API 자체가 없고, 평가자는 실행 화면만 봅니다." },
  { i: "📊", t: "단계별 이탈 분석", d: "제작자가 정의한 테스트 단계에서 어디서 막혔는지, 온보딩·핵심 도달률·NPS까지 대시보드로." },
  { i: "🎓", t: "전대 구성원 인증", d: "@jnu.ac.kr 이메일 인증을 통과한 계정만 참여. 신뢰할 수 있는 피드백만 쌓입니다." },
  { i: "🛡️", t: "데이터 거버넌스", d: "반출은 본부 승인 필수, 익명화 가명 처리, 전 건 감사 로그. 개인정보보호법을 전제로 설계." },
  { i: "⚡", t: "크레딧 경제", d: "평가 1건에 크레딧 +1, 등록에 -3. \"내 것을 올리려면 남의 것을 평가\"하는 선순환." },
  { i: "🚀", t: "한 줄 배포 CLI", d: "pip install jnu-mvp → mvp push. Vercel·Netlify처럼 커맨드 한 줄로 배포하고 게시 신청까지." },
];

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
  const [authed, setAuthed] = useState(false);

  useEffect(() => { setAuthed(!!getToken()); }, []);

  useEffect(() => {
    const params = new URLSearchParams({ sort });
    if (category) params.set("category", category);
    api<MvpItem[]>(`/api/mvps?${params}`).then(setItems).catch((e) => setError(e.message));
  }, [sort, category]);

  const categories = Array.from(new Set(items.map((m) => m.category)));
  const totalReviews = items.reduce((acc, m) => acc + m.review_count, 0);
  const totalViews = items.reduce((acc, m) => acc + m.view_count, 0);

  return (
    <div className="landing">
      {/* ── 히어로 ── */}
      <section className="hero">
        <div className="hero-bg">
          <div className="hero-grid-overlay" />
          <div className="hero-orb o1" />
          <div className="hero-orb o2" />
          <div className="hero-orb o3" />
        </div>
        <div className="hero-inner">
          <div className="eyebrow">🎓 전남대학교 구성원 전용 · Dreamfuture</div>
          <h1>
            만든 사람은 <span className="accent">피드백</span>을,<br />
            써본 사람은 <span className="accent">크레딧</span>을.
          </h1>
          <p className="hero-sub">
            내가 만든 MVP를 올리면 다른 구성원이 사이트 안에서 바로 체험하고 구조화된 평가를 남깁니다.
            소스코드는 절대 공개되지 않는 블랙박스 방식으로요.
          </p>
          <div className="hero-cta">
            {authed ? (
              <>
                <Link href="/mvps/new" className="btn btn-lg">MVP 등록하기</Link>
                <a href="#explore" className="btn btn-lg btn-ghost">둘러보기</a>
              </>
            ) : (
              <>
                <Link href="/signup" className="btn btn-lg">무료로 시작하기</Link>
                <a href="#how" className="btn btn-lg btn-ghost">어떻게 작동하나요?</a>
              </>
            )}
          </div>
          <div className="hero-trust">
            <span className="badge live">실시간 샌드박스</span>
            <span>·</span><span>가입 즉시 크레딧 3 지급</span>
            <span>·</span><span>@jnu.ac.kr 인증</span>
          </div>
        </div>

        <div className="stat-band">
          <div className="cell"><div className="num">{items.length}</div><div className="lab">게시된 MVP</div></div>
          <div className="cell"><div className="num">{totalReviews}</div><div className="lab">누적 평가</div></div>
          <div className="cell"><div className="num">{totalViews}</div><div className="lab">체험 조회수</div></div>
          <div className="cell"><div className="num">100%</div><div className="lab">코드 비노출</div></div>
        </div>
      </section>

      {/* ── 작동 방식 ── */}
      <section id="how" className="section">
        <div className="section-head">
          <div className="eyebrow">HOW IT WORKS</div>
          <h2>3단계로 끝나는 MVP 검증</h2>
          <p>업로드부터 데이터 수집까지, 코드를 지키면서 진짜 사용자 피드백을 모으세요.</p>
        </div>
        <StepNodes steps={STEPS} />
      </section>

      {/* ── 기능 ── */}
      <section className="section" style={{ paddingTop: 0 }}>
        <div className="section-head">
          <div className="eyebrow">WHY JNU MVP</div>
          <h2>학교 공식 플랫폼을 전제로 설계</h2>
          <p>단순 공유를 넘어, 개인정보 거버넌스와 데이터 축적 구조까지 갖췄습니다.</p>
        </div>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <div className="feature" key={f.t}>
              <div className="feature-ico">{f.i}</div>
              <div>
                <h3>{f.t}</h3>
                <p>{f.d}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 둘러보기 ── */}
      <section id="explore" className="section" style={{ paddingTop: 0 }}>
        <div className="section-head">
          <div className="eyebrow">EXPLORE</div>
          <h2>지금 체험할 수 있는 MVP</h2>
          <p>카드를 눌러 샌드박스에서 바로 실행하고 평가를 남겨보세요.</p>
        </div>

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
          <div className="card empty">
            <div className="emoji">🚀</div>
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
      </section>

      {/* ── CTA ── */}
      {!authed && (
        <section className="section" style={{ paddingTop: 0 }}>
          <div className="cta-band">
            <h2>당신의 MVP도 검증받을 준비가 되었나요?</h2>
            <p>@jnu.ac.kr 이메일이면 30초 만에 시작할 수 있습니다. 가입 즉시 크레딧 3을 드려요.</p>
            <Link href="/signup" className="btn btn-lg btn-white">무료로 시작하기 →</Link>
          </div>
        </section>
      )}
    </div>
  );
}
