"use client";

import { Fragment } from "react";

export const CATEGORY_LABELS: Record<string, string> = {
  pre_entry: "진입 전",
  setup: "가입·설정",
  core: "핵심 기능",
  post: "완료 후",
};

export interface StepNode {
  id: number | string;
  order: number;
  title: string;
  guide?: string;
  category?: string;
  /** stats 변형에서 이 단계에 막힌 평가자 수 */
  stuckCount?: number;
}

interface Props {
  steps: StepNode[];
  /** guide: 읽기 전용 여정 / select: 막힌 지점 선택 / stats: 이탈 통계 */
  variant?: "guide" | "select" | "stats";
  selectedId?: number | string | null;
  onSelect?: (id: number | string) => void;
  /** stats에서 이탈률 분모 */
  totalReviews?: number;
}

export default function StepNodes({
  steps,
  variant = "guide",
  selectedId = null,
  onSelect,
  totalReviews = 0,
}: Props) {
  if (steps.length === 0) return null;

  const maxStuck = Math.max(1, ...steps.map((s) => s.stuckCount ?? 0));

  return (
    <div className="node-flow" role={variant === "select" ? "radiogroup" : undefined}>
      {steps.map((s, i) => {
        const selected = variant === "select" && selectedId === s.id;
        const stuck = s.stuckCount ?? 0;
        // 이탈이 가장 몰린 노드를 붉게 강조 (이탈이 실제로 있을 때만)
        const hot = variant === "stats" && stuck > 0 && stuck === maxStuck;

        const body = (
          <>
            <div className="node-head">
              <span className="node-num">{s.order}</span>
              {s.category && <span className="node-cat">{CATEGORY_LABELS[s.category] ?? s.category}</span>}
            </div>
            <div className="node-title">{s.title}</div>
            {s.guide && <p className="node-guide">{s.guide}</p>}

            {variant === "select" && (
              <div className="node-pick">{selected ? "✓ 여기서 막혔어요" : "이 단계 선택"}</div>
            )}

            {variant === "stats" && (
              <div className="node-stat">
                <div className="node-stat-row">
                  <span className="node-stat-num">{stuck}</span>
                  <span className="node-stat-lab">
                    {totalReviews > 0 ? `이탈 ${Math.round((stuck / totalReviews) * 100)}%` : "이탈"}
                  </span>
                </div>
                <div className="node-bar">
                  <i style={{ width: `${(stuck / maxStuck) * 100}%` }} />
                </div>
              </div>
            )}
          </>
        );

        return (
          <Fragment key={s.id}>
            {i > 0 && <div className="node-link" aria-hidden="true" />}
            {variant === "select" ? (
              <button
                type="button"
                role="radio"
                aria-checked={selected}
                data-cat={s.category}
                className={`node selectable ${selected ? "is-selected" : ""}`}
                onClick={() => onSelect?.(s.id)}
              >
                {body}
              </button>
            ) : (
              <div data-cat={s.category} className={`node ${hot ? "is-hot" : ""}`}>
                {body}
              </div>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
