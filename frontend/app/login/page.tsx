"use client";

import { useState } from "react";
import { api, setToken } from "../../lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const r = await api<{ access_token: string }>("/api/auth/login", {
        body: { email, password },
      });
      setToken(r.access_token);
      location.href = "/";
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="auth-wrap reveal">
      <div className="auth-card">
        <h1>다시 오셨네요 👋</h1>
        <p className="muted" style={{ marginBottom: 8 }}>전남대 계정으로 로그인하세요.</p>
        <form onSubmit={submit}>
          <label>전남대 이메일</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                 placeholder="you@jnu.ac.kr" required />
          <label>비밀번호</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p className="error">{error}</p>}
          <div style={{ marginTop: 18 }}>
            <button className="btn" type="submit" style={{ width: "100%" }}>로그인</button>
          </div>
        </form>
        <p className="muted" style={{ marginTop: 16, textAlign: "center" }}>
          아직 계정이 없나요? <a href="/signup">가입하기</a>
        </p>
      </div>
    </div>
  );
}
