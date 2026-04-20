"use client";

import { useCallback, useState } from "react";
import { Upload, Loader2 } from "lucide-react";

interface Props {
  onUpload: (file: File) => Promise<void>;
}

export default function UploadZone({ onUpload }: Props) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handle = useCallback(
    async (file: File) => {
      setError("");
      setLoading(true);
      try {
        await onUpload(file);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Something went wrong");
        setLoading(false);
      }
    },
    [onUpload]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handle(file);
    },
    [handle]
  );

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handle(file);
  };

  return (
    <div className="w-full max-w-xl">
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`
          flex flex-col items-center justify-center w-full h-56 rounded-2xl border-2 border-dashed
          cursor-pointer transition-all duration-200
          ${dragging
            ? "border-indigo-400 bg-indigo-500/10"
            : "border-[var(--border)] bg-[var(--surface)] hover:border-indigo-500/60 hover:bg-indigo-500/5"
          }
        `}
      >
        {loading ? (
          <>
            <Loader2 className="w-10 h-10 text-indigo-400 animate-spin mb-3" />
            <p className="text-zinc-400 text-sm">Uploading…</p>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 text-indigo-400 mb-3" />
            <p className="text-white font-medium">Drop your video here</p>
            <p className="text-zinc-500 text-sm mt-1">or click to browse</p>
            <p className="text-zinc-600 text-xs mt-3">MP4, MOV, AVI, MKV, WebM — up to 500 MB</p>
          </>
        )}
        <input
          type="file"
          accept="video/*"
          className="hidden"
          onChange={onInputChange}
          disabled={loading}
        />
      </label>

      {error && (
        <p className="mt-3 text-center text-sm text-red-400">{error}</p>
      )}
    </div>
  );
}
