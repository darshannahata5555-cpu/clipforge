"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";

interface Sentence {
  text: string;
  start_ms: number;
  end_ms: number;
}

function fmt(ms: number) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export default function TranscriptView({ transcript }: { transcript: Sentence[] }) {
  const [copied, setCopied] = useState(false);
  const [search, setSearch] = useState("");

  const fullText = transcript.map((s) => s.text).join(" ");
  const filtered = search
    ? transcript.filter((s) =>
        s.text.toLowerCase().includes(search.toLowerCase())
      )
    : transcript;

  const copy = () => {
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Search transcript…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded-lg px-4 py-2 text-sm text-zinc-300 placeholder-zinc-600 outline-none focus:border-indigo-500"
        />
        <button
          onClick={copy}
          className="flex items-center gap-2 px-4 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-sm text-zinc-300 hover:border-indigo-500 transition-colors"
        >
          {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          {copied ? "Copied" : "Copy all"}
        </button>
      </div>

      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl divide-y divide-[var(--border)] max-h-[60vh] overflow-y-auto">
        {filtered.map((s, i) => (
          <div key={i} className="flex gap-4 px-4 py-3 hover:bg-white/[0.02]">
            <span className="text-xs text-indigo-400 font-mono pt-0.5 w-12 shrink-0">
              {fmt(s.start_ms)}
            </span>
            <p className="text-sm text-zinc-300 leading-relaxed">{s.text}</p>
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-600 mt-3">
        {transcript.length} sentences · ~{Math.round(fullText.split(" ").length)} words
      </p>
    </div>
  );
}
