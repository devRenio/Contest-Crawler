import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "공모전 보드",
  description: "대학생 IT+인접 공모전·해커톤 모음",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
