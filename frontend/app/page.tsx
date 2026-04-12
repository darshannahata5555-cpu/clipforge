"use client";

import { useRouter } from "next/navigation";
import UploadZone from "@/components/UploadZone";

export default function Home() {
  const router = useRouter();

  async function handleFile(file: File) {
    const form = new FormData();
    form.append("file", file);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload`, {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }

    const { job_id } = await res.json();
    router.push(`/jobs/${job_id}`);
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-[calc(100vh-65px)] px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-12 max-w-2xl">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 leading-tight">
          Turn any video into
          <br />
          <span className="text-indigo-400">content that works</span>
        </h1>
        <p className="text-zinc-400 text-lg">
          Upload once. Get a transcript, Twitter thread, LinkedIn post, blog article,
          and ready-to-post shorts — in minutes.
        </p>
      </div>

      {/* Upload */}
      <UploadZone onUpload={handleFile} />

      {/* Feature pills */}
      <div className="mt-10 flex flex-wrap gap-3 justify-center">
        {[
          "Sentence timestamps",
          "Twitter thread",
          "LinkedIn post",
          "Blog article",
          "Auto-shorts",
          "Burned-in captions",
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
