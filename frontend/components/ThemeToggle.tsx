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
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("jnu_theme", next);
    setDark(!dark);
  }

  return (
    <button className="theme-toggle" onClick={toggle} title={dark ? "라이트 모드" : "다크 모드"}
            aria-label="테마 전환">
      {dark ? "☀️" : "🌙"}
    </button>
  );
}
