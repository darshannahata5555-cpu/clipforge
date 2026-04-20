"use client";

import { Download, Star } from "lucide-react";

interface Short {
  id: string;
  title: string;
  hook_text: string;
  score: number;
  duration_s: number;
  url: string;
}

function fmtDuration(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.round(s % 60);
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 8 ? "text-green-400 bg-green-400/10" :
    score >= 6 ? "text-yellow-400 bg-yellow-400/10" :
                 "text-zinc-400 bg-zinc-400/10";
  return (
    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${color}`}>
      <Star className="w-3 h-3" />
      {score.toFixed(1)}
    </span>
  );
}

export default function ShortsView({ shorts }: { shorts: Short[] }) {
  if (!shorts.length) {
    return (
      <p className="text-zinc-500 text-sm">
        No shorts were generated. The video may be too short or the segments did not meet the
        minimum duration.
      </p>
    );
  }

  // Backend serves /storage/... for local; R2 gives full URLs
  const resolveUrl = (url: string) =>
    url.startsWith("http") ? url : `${process.env.NEXT_PUBLIC_API_URL?.replace("/api", "")}${url}`;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {shorts.map((short, i) => (
        <div
          key={short.id}
          className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl overflow-hidden"
        >
          {/* Video player */}
          <video
            src={resolveUrl(short.url)}
            controls
            className="w-full aspect-video bg-black"
            preload="metadata"
          />

          <div className="p-4">
            <div className="flex items-start justify-between gap-2 mb-2">
              <div>
                <span className="text-xs text-zinc-600 mb-1 block">#{i + 1}</span>
                <p className="text-sm font-semibold text-white leading-snug">{short.title}</p>
              </div>
              <ScoreBadge score={short.score} />
            </div>

            {short.hook_text && (
              <p className="text-xs text-zinc-500 italic mb-3 leading-relaxed">
                "{short.hook_text}"
              </p>
            )}

            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-600">{fmtDuration(short.duration_s)}</span>
              <a
                href={resolveUrl(short.url)}
                download={`short-${i + 1}.mp4`}
                className="flex items-center gap-1.5 text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-3 py-1.5 rounded-lg hover:bg-indigo-500/30 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Download
              </a>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
