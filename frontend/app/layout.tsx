import "./globals.css";
import type { Metadata } from "next";
import { TopNav } from "@/components/shell/top-nav";

export const metadata: Metadata = {
  title: "IMC Prosperity Suite",
  description: "Market data + submission log analysis for IMC Prosperity 4",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg text-text">
        <TopNav />
        <main className="px-4 py-3">{children}</main>
      </body>
    </html>
  );
}
