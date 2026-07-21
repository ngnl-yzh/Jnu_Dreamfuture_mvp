"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "../lib/api";
import ThemeToggle from "./ThemeToggle";

interface Me {
  nickname: string;
  is_admin: boolean;
  jnu_verified: boolean;
  credit_balance: number;
  point_balance: number;
}

export default function Nav() {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    if (!getToken()) return;
    api<Me>("/api/auth/me").then(setMe).catch(() => setToken(null));
  }, []);

  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="nav-brand">
          <span className="brand-mark">J</span>
          JNU&nbsp;MVP
        </Link>
        <div className="nav-links">
          <Link href="/">둘러보기</Link>
          {me ? (
            <>
              <Link href="/mvps/new">MVP 등록</Link>
              <Link href="/me">마이페이지</Link>
              {me.is_admin && <Link href="/admin">관리자</Link>}
              <span className="nav-credit" title={`${me.nickname}님 · 포인트 ${me.point_balance}`}>
                ⚡ 크레딧 {me.credit_balance}
              </span>
              <ThemeToggle />
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => { setToken(null); location.href = "/"; }}
              >
                로그아웃
              </button>
            </>
          ) : (
            <>
              <Link href="/login">로그인</Link>
              <ThemeToggle />
              <Link href="/signup" className="btn btn-sm" style={{ color: "#fff" }}>가입하기</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
