"use client";

import { useState, useCallback } from "react";
import UploadZone from "@/components/UploadZone";
import ProgressTracker from "@/components/ProgressTracker";
import TranscriptView from "@/components/TranscriptView";
import PostsView from "@/components/PostsView";
import ShortsView from "@/components/ShortsView";
import { uploadVideo, transcribeVideo } from "@/lib/assemblyai";
import { generatePosts, designShorts } from "@/lib/claude";
import type { Sentence } from "@/lib/assemblyai";
import type { Short } from "@/lib/claude";

type PipelineStatus = "transcribing" | "generating" | "cutting" | "complete";
type Phase = "idle" | "running" | "done" | "error";

interface State {
  phase: Phase;
  pipelineStatus: PipelineStatus;
  progress: number;
  label: string;
  transcript: Sentence[];
  twitter: string;
  linkedin: string;
  blog: string;
  shorts: Short[];
  error: string;
}

const INITIAL: State = {
  phase: "idle",
  pipelineStatus: "transcribing",
  progress: 0,
  label: "",
  transcript: [],
  twitter: "",
  linkedin: "",
  blog: "",
  shorts: [],
  error: "",
};

const TABS = ["Transcript", "Posts", "Shorts"] as const;
type Tab = typeof TABS[number];

export default function Home() {
  const [state, setState] = useState<State>(INITIAL);
  const [tab, setTab] = useState<Tab>("Transcript");

  const patch = useCallback((p: Partial<State>) => {
    setState((s) => ({ ...s, ...p }));
  }, []);

  async function handleFile(file: File) {
    setState({ ...INITIAL, phase: "running", pipelineStatus: "transcribing", label: "Uploading video…", progress: 2 });

    try {
      // 1. Upload to AssemblyAI CDN
      const uploadUrl = await uploadVideo(file);
      patch({ progress: 5, label: "Starting transcription…" });

      // 2. Transcribe
      const transcript = await transcribeVideo(uploadUrl, (label, pct) => {
        patch({ label, progress: pct });
      });
      patch({ transcript });

      // 3. Generate posts
      patch({ pipelineStatus: "generating", progress: 45, label: "Writing posts with AI…" });
      const posts = await generatePosts(transcript);
      patch({ ...posts, progress: 72, label: "Posts generated" });

      // 4. Design shorts (timestamps)
      patch({ pipelineStatus: "cutting", progress: 75, label: "Finding best clip moments…" });
      const shorts = await designShorts(transcript, 3);

      patch({ shorts, pipelineStatus: "complete", progress: 100, label: "Done!", phase: "done" });

    } catch (err) {
      patch({
        phase: "error",
        error: err instanceof Error ? err.message : "Something went wrong",
      });
    }
  }

  // ── Idle ───────────────────────────────────────────────────────────────────

  if (state.phase === "idle") {
    return (
      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-65px)] px-4 py-16">
        <div className="text-center mb-12 max-w-2xl">
          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 leading-tight">
            Turn any video into
            <br />
            <span className="text-indigo-400">content that works</span>
          </h1>
          <p className="text-zinc-400 text-lg">
            Upload once. Get a transcript, Twitter thread, LinkedIn post, blog
            article, and clip timestamps — in minutes.
          </p>
        </div>

        <UploadZone onUpload={handleFile} />

        <div className="mt-10 flex flex-wrap gap-3 justify-center">
          {[
            "Sentence timestamps",
            "Twitter thread",
            "LinkedIn post",
            "Blog article",
            "Clip timestamps",
          ].map((f) => (
            <span
              key={f}
              className="px-3 py-1 text-xs bg-[var(--surface)] border border-[var(--border)] rounded-full text-zinc-400"
            >
              {f}
            </span>
          ))}
        </div>
      </main>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────────

  if (state.phase === "error") {
    return (
      <main className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h2 className="text-xl font-bold text-white mb-4">Something went wrong</h2>
        <div className="rounded-xl border border-red-800 bg-red-900/20 p-4 text-red-400 text-sm mb-6">
          {state.error}
        </div>
        <button
          onClick={() => setState(INITIAL)}
          className="px-4 py-2 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-lg text-sm hover:bg-indigo-500/30 transition-colors"
        >
          Try again
        </button>
      </main>
    );
  }

  // ── Processing ─────────────────────────────────────────────────────────────

  if (state.phase === "running") {
    return (
      <main className="max-w-2xl mx-auto px-4 py-10">
        <h2 className="text-2xl font-bold text-white mb-6">
          Processing your video…
        </h2>
        <ProgressTracker
          progress={state.progress}
          stepLabel={state.label}
          status={state.pipelineStatus}
        />
        <p className="text-center text-zinc-600 text-xs mt-4">
          Keep this tab open. Transcription usually takes 1–3 minutes.
        </p>
      </main>
    );
  }

  // ── Results ────────────────────────────────────────────────────────────────

  return (
    <main className="max-w-5xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Your content is ready</h2>
        <button
          onClick={() => setState(INITIAL)}
          className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          ← Process another video
        </button>
      </div>

      <div className="flex gap-1 border-b border-[var(--border)] mb-6">
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
            {t === "Shorts" && state.shorts.length > 0 && (
              <span className="ml-1.5 text-xs bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded-full">
                {state.shorts.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === "Transcript" && <TranscriptView transcript={state.transcript} />}
      {tab === "Posts" && (
        <PostsView
          twitter={state.twitter}
          linkedin={state.linkedin}
          blog={state.blog}
        />
      )}
      {tab === "Shorts" && <ShortsView shorts={state.shorts} />}
    </main>
  );
}
