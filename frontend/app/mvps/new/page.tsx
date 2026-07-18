"use client";

import { useState } from "react";
import { api } from "../../../lib/api";

const CATEGORIES = ["pre_entry", "setup", "core", "post"] as const;
const CATEGORY_LABELS: Record<string, string> = {
  pre_entry: "진입 전",
  setup: "가입·설정",
  core: "핵심 기능",
  post: "완료 후",
};

interface StepDraft {
  title: string;
  guide_text: string;
  fixed_category: string;
}

export default function NewMvpPage() {
  const [title, setTitle] = useState("");
  const [tagline, setTagline] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");
  const [steps, setSteps] = useState<StepDraft[]>([
    { title: "", guide_text: "", fixed_category: "pre_entry" },
    { title: "", guide_text: "", fixed_category: "core" },
  ]);
  const [error, setError] = useState("");

  function updateStep(i: number, field: keyof StepDraft, value: string) {
    setSteps(steps.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const r = await api<{ id: number }>("/api/mvps", {
        body: {
          title, tagline,
          description_md: description,
          category,
          tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
          runtime_type: "static",
          test_steps: steps,
        },
      });
      location.href = `/me?mvp=${r.id}`;
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div style={{ maxWidth: 680, margin: "0 auto" }}>
      <h1>MVP 등록</h1>
      <p className="muted">등록에는 크레딧 3이 소모됩니다. 등록 후 마이페이지에서 zip을 업로드하고 게시를 신청하세요.</p>

      <form onSubmit={submit}>
        <div className="card">
          <label>제목</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={100} />
          <label>한 줄 소개</label>
          <input value={tagline} onChange={(e) => setTagline(e.target.value)} required maxLength={200} />
          <label>상세 설명 (마크다운)</label>
          <textarea rows={6} value={description} onChange={(e) => setDescription(e.target.value)} />
          <div className="field-row">
            <div style={{ flex: 1 }}>
              <label>카테고리</label>
              <input value={category} onChange={(e) => setCategory(e.target.value)}
                     placeholder="예: 생산성, 교육, 게임" required />
            </div>
            <div style={{ flex: 1 }}>
              <label>태그 (쉼표 구분)</label>
              <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="react, 대학생활" />
            </div>
          </div>
        </div>

        <div className="card">
          <h2 style={{ marginTop: 0 }}>테스트 시나리오 (2~7단계, 필수)</h2>
          <p className="muted">평가자가 이 단계를 따라 체험하고, 막힌 지점을 단계 중에서 선택합니다.
            각 단계는 공통 통계용 고정 카테고리에 매핑해주세요.</p>

          {steps.map((s, i) => (
            <div key={i} style={{ borderTop: i > 0 ? "1px dashed var(--line)" : "none", paddingTop: i > 0 ? 10 : 0 }}>
              <div className="field-row">
                <div style={{ flex: 2 }}>
                  <label>단계 {i + 1} 제목</label>
                  <input value={s.title} onChange={(e) => updateStep(i, "title", e.target.value)} required />
                </div>
                <div style={{ flex: 1 }}>
                  <label>고정 카테고리</label>
                  <select value={s.fixed_category}
                          onChange={(e) => updateStep(i, "fixed_category", e.target.value)}>
                    {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
                  </select>
                </div>
                {steps.length > 2 && (
                  <button type="button" className="btn btn-danger btn-sm"
                          onClick={() => setSteps(steps.filter((_, idx) => idx !== i))}>
                    삭제
                  </button>
                )}
              </div>
              <label>한 줄 안내</label>
              <input value={s.guide_text} onChange={(e) => updateStep(i, "guide_text", e.target.value)}
                     placeholder="예: 메인 화면에서 시작 버튼을 눌러보세요" />
            </div>
          ))}

          {steps.length < 7 && (
            <button type="button" className="btn btn-ghost btn-sm" style={{ marginTop: 12 }}
                    onClick={() => setSteps([...steps, { title: "", guide_text: "", fixed_category: "core" }])}>
              + 단계 추가
            </button>
          )}
        </div>

        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit">등록하기 (크레딧 -3)</button>
      </form>
    </div>
  );
}
