import type { Metadata } from "next";
import "./globals.css";
import Nav from "../components/Nav";

export const metadata: Metadata = {
  title: "JNU MVP — 전남대 MVP 공유·평가 플랫폼",
  description: "전남대 구성원이 만든 MVP를 블랙박스로 체험하고 구조화된 평가를 남기는 플랫폼",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='24' fill='%234f46e5'/><text x='50' y='72' font-size='62' font-weight='800' font-family='sans-serif' fill='white' text-anchor='middle'>J</text></svg>",
  },
};

export const viewport = {
  themeColor: "#4f46e5",
};

// 첫 페인트 전에 저장된 테마를 적용해 깜빡임 방지
const themeInit = `(function(){try{var t=localStorage.getItem('jnu_theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body>
        <Nav />
        <main className="container">{children}</main>
        <footer className="footer">
          <div className="footer-inner">
            <span className="footer-brand">
              <span className="brand-mark" style={{ width: 24, height: 24, fontSize: 12 }}>J</span>
              JNU MVP
            </span>
            <span>전남대학교 구성원 전용 · 소스코드는 블랙박스로 보호됩니다</span>
            <span>© 2026 Dreamfuture</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
