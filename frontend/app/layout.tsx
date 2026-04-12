import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClipForge — Turn Videos into Content",
  description:
    "Upload any video. Get transcripts, Twitter threads, LinkedIn posts, blog articles, and shareable shorts — automatically.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <nav className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between">
          <span className="text-lg font-bold tracking-tight text-white">
            Clip<span className="text-indigo-400">Forge</span>
          </span>
          <span className="text-xs text-zinc-500">Beta</span>
        </nav>
        {children}
      </body>
    </html>
  );
}
