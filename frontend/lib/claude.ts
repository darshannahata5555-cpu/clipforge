import type { Sentence } from "./assemblyai";

const MODEL = "claude-haiku-4-5-20251001";

export interface Short {
  id: string;
  title: string;
  hook_text: string;
  score: number;
  duration_s: number;
  rationale: string;
  segments: { start_ms: number; end_ms: number }[];
}

// ── Brand context (mirrors backend/services/claude_service.py) ────────────────

const SCALER_CONTEXT = `
BRAND CONTEXT:
You are writing on behalf of Scaler School of Technology — India's leading tech education platform.
These videos are from Scaler's YouTube channel: podcasts and sessions featuring either:
- Guest speakers (founders, CTOs, industry leaders) invited by Scaler
- Scaler's own co-founders (Abhimanyu Saxena & Anshuman Singh) sharing insights

TONE & VOICE:
- Inspiring, aspirational, and grounded — speaks to ambitious engineers and students
- Celebrates real journeys: rejections, failures, pivots, and breakthroughs
- Always ties back to Scaler's mission: helping people build exceptional tech careers
- Never corporate-stiff — warm, direct, story-driven

POSTING STYLE:
- Posts are published by Scaler (not the speaker themselves)
- Credit the speaker naturally ("In our latest podcast, [Speaker Name] shared...")
- End Twitter threads / LinkedIn posts with a soft CTA pointing to Scaler
- Use relevant hashtags: #Scaler #TechCareers #StartupIndia #BuildInPublic etc.
`.trim();

// ── Helpers ──────────────────────────────────────────────────────────────────

async function chat(prompt: string, maxTokens = 4096): Promise<string> {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY!,
      "anthropic-version": "2023-06-01",
      // Opt-in for direct browser access — keys are in Netlify env vars
      "anthropic-dangerous-direct-browser-access": "true",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: maxTokens,
      messages: [{ role: "user", content: prompt }],
    }),
  });
  const data = await res.json();
  if (data.error) throw new Error(data.error.message);
  return (data.content[0] as { text: string }).text;
}

function extractJson(text: string): unknown {
  const clean = text.replace(/```(?:json)?\s*/g, "").replace(/```/g, "").trim();
  for (const ch of ["{", "["]) {
    const idx = clean.indexOf(ch);
    if (idx !== -1) {
      try { return JSON.parse(clean.slice(idx)); } catch { /* try next */ }
    }
  }
  return JSON.parse(clean);
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function generatePosts(
  transcript: Sentence[]
): Promise<{ twitter: string; linkedin: string; blog: string }> {
  const fullText = transcript.map((s) => s.text).join(" ");

  const prompt = `${SCALER_CONTEXT}

Based on this podcast/session transcript from Scaler's YouTube channel, create content for three platforms.

TRANSCRIPT:
${fullText}

---
Create the following and return as valid JSON (no markdown code blocks):

1. "twitter": A viral Twitter/X thread posted by @scaler_official. 6-8 tweets.
   - First tweet: punchy hook that highlights the most surprising/inspiring insight
   - Middle tweets: key lessons, story beats, surprising facts
   - Last tweet: soft CTA + 2-3 relevant hashtags
   - Separate tweets with "|||". Each tweet max 280 chars.

2. "linkedin": A LinkedIn post by Scaler (250-400 words).
   - Open with a powerful moment or quote
   - Tell the speaker's story with context
   - 3-4 bullet point takeaways
   - Close with a question to drive comments + YouTube CTA

3. "blog": A full blog post in Markdown (900-1200 words).
   - H1 title from Scaler's perspective
   - 3-4 H2 sections covering key insights
   - Conclusion with takeaway + link to full video

Return only valid JSON: {"twitter": "...", "linkedin": "...", "blog": "..."}`;

  const raw = await chat(prompt, 4096);
  return extractJson(raw) as { twitter: string; linkedin: string; blog: string };
}

export async function designShorts(
  transcript: Sentence[],
  maxShorts = 3
): Promise<Short[]> {
  if (!transcript.length) return [];

  const lines = transcript.map((s) => {
    const total = Math.floor(s.start_ms / 1000);
    const mm = Math.floor(total / 60);
    const ss = total % 60;
    return `[${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}] ${s.text}`;
  });

  const prompt = `${SCALER_CONTEXT}

Design exactly ${maxShorts} YouTube Shorts from this timestamped transcript. Each short must be:
- Under 90 seconds total, self-contained, immediately gripping
- Built from the best moments (can use non-consecutive clips)
- Starting and ending on complete sentence boundaries

TRANSCRIPT:
${lines.join("\n")}

Rules:
- start_ms and end_ms: convert [MM:SS] → milliseconds (MM*60000 + SS*1000)
- Multiple segments must be chronological and non-overlapping
- Total combined duration 25–90 seconds

Return a JSON array of exactly ${maxShorts} objects (no markdown):
[{
  "title": "Punchy title max 8 words",
  "hook_text": "First-frame caption max 15 words",
  "score": 9,
  "rationale": "One sentence on why this works standalone",
  "segments": [{"start_ms": 0, "end_ms": 30000}]
}]`;

  try {
    const raw = await chat(prompt, 2048);
    const designs = extractJson(raw) as Array<{
      title?: string;
      hook_text?: string;
      score?: number;
      rationale?: string;
      segments?: Array<{ start_ms: number; end_ms: number }>;
    }>;

    return designs
      .filter((d) => d.segments?.length && d.title)
      .map((d) => {
        const segs = (d.segments ?? [])
          .filter((s) => s.end_ms > s.start_ms)
          .map((s) => ({ start_ms: Number(s.start_ms), end_ms: Number(s.end_ms) }));
        const totalMs = segs.reduce((sum, s) => sum + s.end_ms - s.start_ms, 0);
        return {
          id: Math.random().toString(36).slice(2, 10),
          title: d.title ?? "Clip",
          hook_text: d.hook_text ?? "",
          score: d.score ?? 0,
          duration_s: totalMs / 1000,
          rationale: d.rationale ?? "",
          segments: segs,
        };
      });
  } catch {
    return [];
  }
}
