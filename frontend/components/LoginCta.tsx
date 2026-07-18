export default function LoginCta({ message }: { message?: string }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: "44px 24px", maxWidth: 480, margin: "40px auto" }}>
      <p style={{ fontSize: 36, margin: "0 0 10px" }}>🔐</p>
      <h2 style={{ margin: "0 0 8px" }}>로그인이 필요합니다</h2>
      <p className="muted" style={{ marginBottom: 20 }}>
        {message ?? "전남대 구성원 전용 페이지입니다. 로그인 후 이용해주세요."}
      </p>
      <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
        <a className="btn" href="/login" style={{ color: "#fff" }}>로그인</a>
        <a className="btn btn-ghost" href="/signup">가입하기</a>
      </div>
    </div>
  );
}
