const BASE = "https://api.assemblyai.com";

function key() {
  return process.env.NEXT_PUBLIC_ASSEMBLYAI_API_KEY!;
}

export interface Sentence {
  text: string;
  start_ms: number;
  end_ms: number;
}

export async function uploadVideo(file: File): Promise<string> {
  const res = await fetch(`${BASE}/v2/upload`, {
    method: "POST",
    headers: {
      Authorization: key(),
      "Content-Type": "application/octet-stream",
    },
    body: file,
  });
  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  const { upload_url } = await res.json();
  return upload_url as string;
}

export async function transcribeVideo(
  uploadUrl: string,
  onProgress: (label: string, pct: number) => void
): Promise<Sentence[]> {
  const headers = {
    Authorization: key(),
    "Content-Type": "application/json",
  };

  // Create transcript job
  const createRes = await fetch(`${BASE}/v2/transcript`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      audio_url: uploadUrl,
      punctuate: true,
      format_text: true,
      language_detection: true,
    }),
  });
  if (!createRes.ok) throw new Error("Failed to start transcription");
  const { id } = await createRes.json();

  // Poll until complete
  onProgress("Transcribing audio…", 10);
  while (true) {
    await new Promise((r) => setTimeout(r, 3000));

    const pollRes = await fetch(`${BASE}/v2/transcript/${id}`, {
      headers: { Authorization: key() },
    });
    const data = await pollRes.json();

    if (data.status === "error") {
      throw new Error(data.error ?? "Transcription failed");
    }
    if (data.status === "completed") {
      onProgress("Transcription complete", 40);
      // Fetch sentence-level timestamps
      const sentRes = await fetch(`${BASE}/v2/transcript/${id}/sentences`, {
        headers: { Authorization: key() },
      });
      const { sentences } = await sentRes.json();
      return (sentences as { text: string; start: number; end: number }[]).map(
        (s) => ({ text: s.text, start_ms: s.start, end_ms: s.end })
      );
    }
    onProgress(
      "Transcribing audio…",
      data.status === "processing" ? 25 : 15
    );
  }
}
