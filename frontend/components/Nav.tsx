"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "../lib/api";

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
        <Link href="/" className="nav-brand">JNU MVP</Link>
        <div className="nav-links">
          <Link href="/">둘러보기</Link>
          {me ? (
            <>
              <Link href="/mvps/new">MVP 등록</Link>
              <Link href="/me">마이페이지</Link>
              {me.is_admin && <Link href="/admin">관리자</Link>}
              <span className="muted">
                {me.nickname} · 크레딧 {me.credit_balance} · 포인트 {me.point_balance}
              </span>
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
              <Link href="/signup">가입</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
