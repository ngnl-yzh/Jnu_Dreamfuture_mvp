"use client";

import { useState } from "react";
import { api, setToken } from "../../lib/api";

export default function SignupPage() {
  const [step, setStep] = useState<"form" | "verify">("form");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [consentPrivacy, setConsentPrivacy] = useState(false);
  const [consentShare, setConsentShare] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function submitSignup(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/auth/signup", {
        body: {
          email, password, nickname,
          consent_privacy: consentPrivacy,
          consent_data_share: consentShare,
        },
      });
      setStep("verify");
      setNotice("이메일로 발송된 6자리 인증 코드를 입력해주세요. (개발 모드에서는 서버 로그에 출력됩니다)");
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function submitVerify(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/auth/verify-email", { body: { email, code } });
      const r = await api<{ access_token: string }>("/api/auth/login", {
        body: { email, password },
      });
      setToken(r.access_token);
      location.href = "/";
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function resend() {
    setError("");
    try {
      await api("/api/auth/verify-email", { body: { email } });
      setNotice("인증 코드를 재발송했습니다.");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="auth-wrap reveal" style={{ maxWidth: 480 }}>
      <div className="auth-card">
        <h1>{step === "form" ? "가입하기 🎓" : "이메일 인증 ✉️"}</h1>
        <p className="muted">전남대학교 구성원 전용 — @jnu.ac.kr 이메일 인증이 필요합니다.
          전대 포털 비밀번호가 아닌 이 사이트 전용 비밀번호를 새로 만들어주세요.</p>

        {step === "form" ? (
          <form onSubmit={submitSignup}>
            <label>전남대 이메일</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                   placeholder="you@jnu.ac.kr" required />
            <label>비밀번호 (8자 이상, 새로 만든 비밀번호)</label>
            <input type="password" value={password} minLength={8}
                   onChange={(e) => setPassword(e.target.value)} required />
            <label>닉네임</label>
            <input value={nickname} minLength={2} onChange={(e) => setNickname(e.target.value)} required />

            <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 400 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={consentPrivacy}
                     onChange={(e) => setConsentPrivacy(e.target.checked)} />
              (필수) 개인정보 수집·이용에 동의합니다
            </label>
            <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 400 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={consentShare}
                     onChange={(e) => setConsentShare(e.target.checked)} />
              (선택) 내 평가·참여 데이터가 익명화되어 MVP 제작자에게 제공될 수 있음에 동의합니다
            </label>

            {error && <p className="error">{error}</p>}
            <div style={{ marginTop: 18 }}>
              <button className="btn" type="submit" disabled={!consentPrivacy} style={{ width: "100%" }}>
                가입하고 인증 코드 받기
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={submitVerify}>
            {notice && <p className="success">{notice}</p>}
            <label>인증 코드 (6자리)</label>
            <input value={code} onChange={(e) => setCode(e.target.value)}
                   pattern="[0-9]{6}" maxLength={6} required />
            {error && <p className="error">{error}</p>}
            <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
              <button className="btn" type="submit">인증 완료</button>
              <button className="btn btn-ghost" type="button" onClick={resend}>코드 재발송</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
