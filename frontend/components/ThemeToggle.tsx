"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("jnu_theme");
    const isDark = stored
      ? stored === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(isDark);
  }, []);

  function toggle() {
    const next = dark ? "light" : "dark";
    const root = document.documentElement;
    // 전환 중에는 트랜지션을 끊어야 테두리 색 등이 이전 테마에 남지 않는다
    root.classList.add("theme-switching");
    root.setAttribute("data-theme", next);
    localStorage.setItem("jnu_theme", next);
    setDark(!dark);
    // rAF는 백그라운드 탭에서 멈추므로 타이머 폴백을 함께 건다
    const clear = () => root.classList.remove("theme-switching");
    requestAnimationFrame(() => requestAnimationFrame(clear));
    setTimeout(clear, 120);
  }

  return (
    <button className="theme-toggle" onClick={toggle} title={dark ? "라이트 모드" : "다크 모드"}
            aria-label="테마 전환">
      {dark ? "☀️" : "🌙"}
    </button>
  );
}
