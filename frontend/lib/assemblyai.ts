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
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Upload failed (${res.status}): ${body}`);
  }
  const { upload_url } = await res.json();
  return upload_url as string;
}

export async function transcribeVideo(
  uploadUrl: string,
  onProgress: (label: string, pct: number) => void
): Promise<Sentence[]> {
  const authHeaders = {
    Authorization: key(),
    "Content-Type": "application/json",
  };

  // Create transcript job
  const createRes = await fetch(`${BASE}/v2/transcript`, {
    method: "POST",
    headers: authHeaders,
    body: JSON.stringify({
      audio_url: uploadUrl,
      punctuate: true,
      format_text: true,
      language_detection: true,
    }),
  });
  if (!createRes.ok) {
    const body = await createRes.json().catch(() => ({}));
    throw new Error(
      `Transcription start failed (${createRes.status}): ${body?.error ?? body?.message ?? JSON.stringify(body)}`
    );
  }
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
      throw new Error(`Transcription failed: ${data.error ?? "unknown error"}`);
    }

    if (data.status === "completed") {
      onProgress("Transcription complete", 40);

      // Get sentence-level timestamps
      const sentRes = await fetch(`${BASE}/v2/transcript/${id}/sentences`, {
        headers: { Authorization: key() },
      });
      const sentData = await sentRes.json();

      // sentences lives at sentData.sentences
      const raw: { text: string; start: number; end: number }[] =
        sentData.sentences ?? [];

      if (!raw.length) {
        // Fall back to words-grouped-by-utterance if sentences endpoint is empty
        return wordsToSentences(data.words ?? []);
      }

      return raw.map((s) => ({
        text: s.text,
        start_ms: s.start,
        end_ms: s.end,
      }));
    }

    onProgress(
      "Transcribing audio…",
      data.status === "processing" ? 25 : 15
    );
  }
}

// Fallback: group words into rough sentences on punctuation boundaries
function wordsToSentences(
  words: { text: string; start: number; end: number }[]
): Sentence[] {
  const sentences: Sentence[] = [];
  let buf: typeof words = [];

  for (const w of words) {
    buf.push(w);
    if (/[.!?]$/.test(w.text) || buf.length >= 20) {
      sentences.push({
        text: buf.map((x) => x.text).join(" "),
        start_ms: buf[0].start,
        end_ms: buf[buf.length - 1].end,
      });
      buf = [];
    }
  }
  if (buf.length) {
    sentences.push({
      text: buf.map((x) => x.text).join(" "),
      start_ms: buf[0].start,
      end_ms: buf[buf.length - 1].end,
    });
  }
  return sentences;
}
