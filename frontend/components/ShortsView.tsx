"use client";

import { Star } from "lucide-react";

interface Segment {
  start_ms: number;
  end_ms: number;
}

interface Short {
  id: string;
  title: string;
  hook_text: string;
  score: number;
  duration_s: number;
  rationale: string;
  segments: Segment[];
}

function fmt(ms: number) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function fmtDuration(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 8 ? "text-green-400 bg-green-400/10 border-green-400/20" :
    score >= 6 ? "text-yellow-400 bg-yellow-400/10 border-yellow-400/20" :
                 "text-zinc-400 bg-zinc-400/10 border-zinc-400/20";
  return (
    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${color}`}>
      <Star className="w-3 h-3" />
      {score.toFixed(1)}
    </span>
  );
}

export default function ShortsView({ shorts }: { shorts: Short[] }) {
  if (!shorts.length) {
    return (
      <p className="text-zinc-500 text-sm">
        No shorts were generated. The video may be too short or Claude couldn't
        find strong standalone moments.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        Seek to these timestamps in your video editor or player to cut the clips.
      </p>

      {shorts.map((short, i) => (
        <div
          key={short.id}
          className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-5"
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <span className="text-xs text-zinc-600 font-mono">#{i + 1}</span>
              <h3 className="text-sm font-semibold text-white mt-0.5 leading-snug">
                {short.title}
              </h3>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-zinc-600">{fmtDuration(short.duration_s)}</span>
              <ScoreBadge score={short.score} />
            </div>
          </div>

          {/* Hook */}
          {short.hook_text && (
            <p className="text-xs text-zinc-400 italic mb-4 leading-relaxed">
              "{short.hook_text}"
            </p>
          )}

          {/* Segments */}
          <div className="space-y-2 mb-3">
            {short.segments.map((seg, j) => (
              <div
                key={j}
                className="flex items-center gap-3 bg-indigo-500/5 border border-indigo-500/15 rounded-lg px-3 py-2"
              >
                <span className="text-xs text-zinc-600 w-4 shrink-0">{j + 1}</span>
                <span className="font-mono text-sm text-indigo-300 tracking-wide">
                  {fmt(seg.start_ms)}
                </span>
                <span className="text-zinc-600 text-xs">→</span>
                <span className="font-mono text-sm text-indigo-300 tracking-wide">
                  {fmt(seg.end_ms)}
                </span>
                <span className="text-xs text-zinc-600 ml-auto">
                  {fmtDuration((seg.end_ms - seg.start_ms) / 1000)}
                </span>
              </div>
            ))}
          </div>

          {/* Rationale */}
          {short.rationale && (
            <p className="text-xs text-zinc-600 leading-relaxed">
              {short.rationale}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
