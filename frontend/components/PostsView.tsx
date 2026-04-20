"use client";

import { useState } from "react";
import { Copy, Check, Twitter, Linkedin, BookOpen } from "lucide-react";

interface Props {
  twitter: string;
  linkedin: string;
  blog: string;
}

type Platform = "twitter" | "linkedin" | "blog";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function PostsView({ twitter, linkedin, blog }: Props) {
  const [platform, setPlatform] = useState<Platform>("twitter");

  const PLATFORMS: { key: Platform; label: string; icon: React.ReactNode }[] = [
    { key: "twitter",  label: "Twitter / X", icon: <Twitter className="w-4 h-4" /> },
    { key: "linkedin", label: "LinkedIn",     icon: <Linkedin className="w-4 h-4" /> },
    { key: "blog",     label: "Blog",         icon: <BookOpen className="w-4 h-4" /> },
  ];

  const tweets = twitter.split("|||").map((t) => t.trim()).filter(Boolean);

  return (
    <div>
      {/* Platform selector */}
      <div className="flex gap-2 mb-5">
        {PLATFORMS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPlatform(p.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              platform === p.key
                ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/40"
                : "bg-[var(--surface)] text-zinc-400 border border-[var(--border)] hover:border-zinc-500"
            }`}
          >
            {p.icon}
            {p.label}
          </button>
        ))}
      </div>

      {/* Twitter thread */}
      {platform === "twitter" && (
        <div className="space-y-3">
          {tweets.map((tweet, i) => (
            <div
              key={i}
              className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4"
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs text-zinc-600 font-mono">
                  {i + 1}/{tweets.length}
                </span>
                <CopyButton text={tweet} />
              </div>
              <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{tweet}</p>
              <p className="text-xs text-zinc-600 mt-2 text-right">{tweet.length}/280</p>
            </div>
          ))}
          <CopyButton text={twitter.replace(/\|\|\|/g, "\n\n")} />
        </div>
      )}

      {/* LinkedIn */}
      {platform === "linkedin" && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex justify-end mb-3">
            <CopyButton text={linkedin} />
          </div>
          <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">{linkedin}</p>
        </div>
      )}

      {/* Blog */}
      {platform === "blog" && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5">
          <div className="flex justify-end mb-3">
            <CopyButton text={blog} />
          </div>
          <div className="prose prose-invert prose-sm max-w-none">
            <pre className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap font-sans">
              {blog}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
