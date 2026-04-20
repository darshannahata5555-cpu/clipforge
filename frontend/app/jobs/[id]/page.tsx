"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import ProgressTracker from "@/components/ProgressTracker";
import TranscriptView from "@/components/TranscriptView";
import PostsView from "@/components/PostsView";
import ShortsView from "@/components/ShortsView";

export interface JobData {
  id: string;
  status: string;
  progress: number;
  step_label: string;
  original_filename: string;
  video_duration: number | null;
  transcript: { text: string; start_ms: number; end_ms: number }[] | null;
  twitter_post: string | null;
  linkedin_post: string | null;
  blog_post: string | null;
  shorts: {
    id: string;
    title: string;
    hook_text: string;
    score: number;
    duration_s: number;
    rationale: string;
    segments: { start_ms: number; end_ms: number }[];
  }[] | null;
  error: string | null;
}

const TABS = ["Transcript", "Posts", "Shorts"] as const;
type Tab = typeof TABS[number];

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<JobData | null>(null);
  const [tab, setTab] = useState<Tab>("Transcript");

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    async function poll() {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/jobs/${id}`);
        if (!res.ok) return;
        const data: JobData = await res.json();
        setJob(data);
        if (data.status === "complete" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch {
        // network blip — keep polling
      }
    }

    poll();
    interval = setInterval(poll, 2500);
    return () => clearInterval(interval);
  }, [id]);

  if (!job) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-zinc-500">
        Loading…
      </div>
    );
  }

  const done = job.status === "complete";
  const failed = job.status === "failed";

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <p className="text-zinc-500 text-sm mb-1">Processing: {job.original_filename}</p>
      <h2 className="text-2xl font-bold text-white mb-6">
        {done ? "Your content is ready" : failed ? "Processing failed" : "Processing your video…"}
      </h2>

      {/* Progress */}
      {!done && !failed && (
        <ProgressTracker
          progress={job.progress}
          stepLabel={job.step_label}
          status={job.status}
        />
      )}

      {failed && (
        <div className="rounded-xl border border-red-800 bg-red-900/20 p-4 text-red-400 text-sm">
          {job.error || "An unknown error occurred."}
        </div>
      )}

      {/* Results tabs */}
      {done && (
        <>
          <div className="flex gap-1 border-b border-[var(--border)] mb-6 mt-2">
            {TABS.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                  tab === t
                    ? "bg-[var(--surface)] text-white border border-b-0 border-[var(--border)]"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {t}
                {t === "Shorts" && job.shorts && (
                  <span className="ml-1.5 text-xs bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded-full">
                    {job.shorts.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {tab === "Transcript" && <TranscriptView transcript={job.transcript || []} />}
          {tab === "Posts" && (
            <PostsView
              twitter={job.twitter_post || ""}
              linkedin={job.linkedin_post || ""}
              blog={job.blog_post || ""}
            />
          )}
          {tab === "Shorts" && <ShortsView shorts={job.shorts || []} />}
        </>
      )}
    </main>
  );
}
