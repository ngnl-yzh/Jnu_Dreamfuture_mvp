import type { Metadata } from "next";
import "./globals.css";
import Nav from "../components/Nav";

export const metadata: Metadata = {
  title: "JNU MVP — 전남대 MVP 공유·평가 플랫폼",
  description: "전남대 구성원이 만든 MVP를 블랙박스로 체험하고 평가하는 플랫폼",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <Nav />
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
