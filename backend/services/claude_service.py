import json
import re
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-haiku-4-5-20251001"

# ── Scaler brand context injected into every prompt ──────────────────────────
SCALER_CONTEXT = """
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
  (e.g. "Full podcast on our YouTube channel 🔗" or "This is why we built Scaler.")
- Use relevant hashtags: #Scaler #TechCareers #StartupIndia #BuildInPublic etc.
"""


def _chat(prompt: str, max_tokens: int = 4096) -> str:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _extract_json(text: str) -> dict | list:
    """Strip markdown fences, then parse the first complete JSON value found."""
    clean = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    # raw_decode stops after the first valid JSON value — ignores any trailing text
    decoder = json.JSONDecoder()
    for start_char in ('{', '['):
        idx = clean.find(start_char)
        if idx != -1:
            try:
                obj, _ = decoder.raw_decode(clean, idx)
                return obj
            except json.JSONDecodeError:
                continue
    # Log what Claude actually returned to help diagnose failures
    preview = clean[:300].replace("\n", "\\n")
    print(f"[claude] _extract_json failed — raw preview: {preview!r}")
    return json.loads(clean)  # raises with original error


def extract_metadata(transcript: list[dict]) -> dict:
    """
    Extract speaker name and episode title from the transcript.
    Returns: {speaker_name: str, episode_title: str}
    """
    sample_text = " ".join(s["text"] for s in transcript[:80])

    prompt = f"""{SCALER_CONTEXT}

Read this excerpt from a Scaler podcast/session transcript and extract two things:

1. "speaker_name": The full name of the main guest/speaker. If it's Abhimanyu Saxena or Anshuman Singh (Scaler co-founders) hosting a session, use their name. If the speaker name is never mentioned, return "Guest Speaker".
2. "episode_title": A short punchy episode title (max 8 words) that captures the main theme.

TRANSCRIPT EXCERPT:
{sample_text[:3500]}

Return only valid JSON with no explanation: {{"speaker_name": "...", "episode_title": "..."}}"""

    try:
        raw = _chat(prompt, max_tokens=128)
        return _extract_json(raw)
    except Exception:
        return {"speaker_name": "Guest Speaker", "episode_title": "Scaler Podcast"}


def generate_posts(transcript: list[dict]) -> dict:
    """
    Given sentence-level transcript, return Twitter thread, LinkedIn post, blog post.
    Returns: {twitter: str, linkedin: str, blog: str}
    """
    full_text = " ".join(s["text"] for s in transcript)

    prompt = f"""{SCALER_CONTEXT}

Based on this podcast/session transcript from Scaler's YouTube channel, create content for three platforms.

TRANSCRIPT:
{full_text}

---
Create the following and return as valid JSON (no markdown code blocks):

1. "twitter": A viral Twitter/X thread posted by @scaler_official. 6-8 tweets.
   - First tweet: punchy hook that highlights the most surprising/inspiring insight
   - Middle tweets: key lessons, story beats, surprising facts from the talk
   - Last tweet: soft CTA ("Full podcast on our YouTube ↓ Link in bio") + 2-3 relevant hashtags
   - Separate tweets with "|||". Each tweet max 280 chars.
   - Write as Scaler sharing the speaker's story/insights, not as the speaker themselves

2. "linkedin": A LinkedIn post by Scaler (250-400 words).
   - Open with a powerful moment or quote from the talk
   - Tell the speaker's story with context (who they are, why Scaler had them on)
   - 3-4 bullet point takeaways from the session
   - Close with what this means for Scaler's community + a question to drive comments
   - Mention "Full podcast on our YouTube channel" naturally at the end

3. "blog": A full blog post in Markdown (900-1200 words) published on Scaler's blog.
   - H1 title that frames it from Scaler's perspective (e.g. "What [Speaker] Taught Our Community About...")
   - Intro: why Scaler invited this speaker / what makes their story relevant to tech careers
   - 3-4 H2 sections covering the key insights from the session
   - Conclusion: what Scaler's students/community can take away + link to watch the full video

Return only valid JSON: {{"twitter": "...", "linkedin": "...", "blog": "..."}}"""

    raw = _chat(prompt, max_tokens=4096)
    return _extract_json(raw)


def design_shorts(transcript: list[dict], max_shorts: int = 3) -> list[dict]:
    """
    Ask Claude to design the best YouTube Shorts from the full transcript.
    Each short can pull non-consecutive clips from anywhere in the video and
    stitch them together — always cutting on complete sentence boundaries.

    Returns list of designs:
      [{title, hook_text, score, segments: [{start_ms, end_ms}], rationale}]
    """
    if not transcript:
        return []

    # Build timestamped transcript — format: [MM:SS] sentence
    lines = []
    for s in transcript:
        total_s = s["start_ms"] // 1000
        mm, ss = divmod(total_s, 60)
        lines.append(f"[{mm:02d}:{ss:02d}] {s['text']}")
    transcript_text = "\n".join(lines)

    prompt = f"""{SCALER_CONTEXT}

You are a YouTube Shorts editor working for Scaler. You have the full timestamped transcript below.

Design exactly {max_shorts} YouTube Shorts that are:
- Self-contained and fully understandable without watching the full video
- Under 90 seconds total duration each
- Built from the BEST moments — you can pull multiple non-consecutive clips from anywhere
  in the video and stitch them together into one coherent short
- Always starting AND ending on a complete sentence boundary (use the exact [MM:SS] timestamps)
- Focused on a single clear insight, story beat, or takeaway that resonates with ambitious
  engineers and students following Scaler
- Immediately gripping in the first 5 seconds — no warm-up, no intros

TRANSCRIPT:
{transcript_text}

Rules for segments:
- start_ms and end_ms must match actual sentence boundaries from the transcript above
  (convert [MM:SS] → milliseconds: MM*60000 + SS*1000)
- Multiple segments must be in chronological order and non-overlapping
- Total duration of all segments combined must be ≤ 90 seconds
- Minimum 25 seconds total

Return a JSON array of exactly {max_shorts} objects. No markdown, just the array:
[{{
  "title": "Punchy title max 8 words",
  "hook_text": "First-frame caption that stops the scroll (max 15 words)",
  "score": 9,
  "rationale": "One sentence on why this works standalone",
  "segments": [{{"start_ms": 0, "end_ms": 30000}}]
}}]"""

    try:
        raw = _chat(prompt, max_tokens=2048).strip()
        raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
        designs = json.loads(raw)
        valid = []
        for d in designs:
            if "segments" not in d or "title" not in d:
                continue
            # Coerce to int and compute total duration
            total_ms = 0
            clean_segs = []
            for seg in d["segments"]:
                s_ms = int(seg["start_ms"])
                e_ms = int(seg["end_ms"])
                if e_ms > s_ms:
                    clean_segs.append({"start_ms": s_ms, "end_ms": e_ms})
                    total_ms += e_ms - s_ms
            if not clean_segs:
                continue
            d["segments"] = clean_segs
            d["duration_s"] = total_ms / 1000
            valid.append(d)
        return valid
    except Exception as exc:
        print(f"[claude] design_shorts failed: {exc}")
        return []
