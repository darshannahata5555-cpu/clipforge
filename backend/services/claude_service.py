import importlib
import json
from pathlib import Path
import re
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-sonnet-4-20250514"
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
LINKEDIN_SKILL = (PROMPTS_DIR / "sst_linkedin_skill.md").read_text(encoding="utf-8")

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
- Write from Scaler's point of view and with a subtle brand-building / audience-growth intent
- End Twitter threads / LinkedIn posts with a soft CTA pointing to Scaler
  (e.g. "Watch the full podcast on Scaler's YouTube channel." or "This is exactly why Scaler builds for ambitious tech talent.")
- Use relevant hashtags: #Scaler #TechCareers #StartupIndia #BuildInPublic etc.
"""


def _chat(
    prompt: str,
    max_tokens: int = 4096,
    *,
    system: str | None = None,
    model: str = MODEL,
) -> str:
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _clean_json_text(text: str) -> str:
    clean = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    clean = clean.replace("“", '"').replace("”", '"')
    clean = clean.replace("‘", "'").replace("’", "'")
    clean = clean.replace("\r\n", "\n")
    # Remove trailing commas before closing arrays/objects.
    clean = re.sub(r",\s*([\]}])", r"\1", clean)
    # Normalize repeated whitespace and remove leading/trailing spaces on each line.
    clean = "\n".join(line.strip() for line in clean.splitlines() if line.strip())
    return clean


def _normalize_json_like(text: str) -> str:
    """Make common non-standard JSON output more parseable."""
    normalized = text
    # Quote bare object keys like: speaker_name: "..."
    normalized = re.sub(r'([\{\[\n,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', normalized)
    # Convert single-quoted strings to double quotes where safe.
    normalized = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', normalized)
    # Remove stray markdown list prefixes like '- ' inside JSON-like blocks.
    normalized = re.sub(r"^[-*+]\s+", "", normalized, flags=re.MULTILINE)
    # Insert commas between lines if the newline separates two key/value entries.
    normalized = re.sub(
        r'(["\]0-9\}\S])\s*\n\s*([A-Za-z_][A-Za-z0-9_]*\s*:)',
        r'\1,\n\2',
        normalized,
    )
    normalized = re.sub(
        r'(["\]0-9\}\S])\s*\n\s*("[A-Za-z_][A-Za-z0-9_]*"\s*:)',
        r'\1,\n\2',
        normalized,
    )
    # Wrap plain key/value residues in braces to make them valid JSON.
    stripped = normalized.strip()
    if stripped and not stripped.startswith(('{', '[')):
        stripped = stripped.rstrip(',')
        normalized = f"{{{stripped}}}"
    # Remove any Unicode ellipsis or invalid punctuation near keys/values.
    normalized = normalized.replace('…', '...')
    return normalized


def _is_top_level_start(text: str, idx: int) -> bool:
    stack = []
    for ch in text[:idx]:
        if ch in "[{":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
    return len(stack) == 0


def _extract_json(text: str) -> dict | list:
    """Strip markdown fences, then parse the first complete JSON value found."""
    clean = _clean_json_text(text)
    decoder = json.JSONDecoder()
    for start_char in ('{', '['):
        idx = clean.find(start_char)
        while idx != -1:
            if _is_top_level_start(clean, idx):
                try:
                    obj, _ = decoder.raw_decode(clean, idx)
                    return obj
                except json.JSONDecodeError:
                    pass
            idx = clean.find(start_char, idx + 1)

    # Try a tolerant JSON5 parser if available.
    if importlib.util.find_spec("json5") is not None:
        try:
            import json5
            return json5.loads(clean)
        except Exception:
            pass

    normalized = _normalize_json_like(clean)
    if normalized != clean:
        try:
            if importlib.util.find_spec("json5") is not None:
                import json5
                return json5.loads(normalized)
            return json.loads(normalized)
        except Exception:
            pass

    # Log what Claude actually returned to help diagnose failures
    preview = clean[:300].replace("\n", "\\n")
    print(f"[claude] _extract_json failed — raw preview: {preview!r}")
    return json.loads(clean)  # raises with original error


def _extract_tagged_section(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"Missing <{tag}> section")
    return match.group(1).strip()


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
The posts will be published on Scaler's channels, so write from Scaler's perspective.
Keep everything tight, clear, and promotional without sounding like an ad.

TRANSCRIPT:
{full_text}

---
Create the following and return ONLY these two tagged sections in this exact format:

<TWITTER>
...
</TWITTER>
<BLOG>
...
</BLOG>

1. TWITTER: A Twitter/X thread posted by @scaler_official. 4-6 tweets only.
   - First tweet: punchy hook around the strongest insight
   - Middle tweets: only the sharpest lessons or story beats
   - Last tweet: soft CTA to watch the full video on Scaler's YouTube + 2-3 relevant hashtags
   - Separate tweets with "|||". Each tweet max 280 chars.
   - Write as Scaler sharing the speaker's insights, not as the speaker
   - Make it feel useful for Scaler's audience and favorable to Scaler's brand

2. BLOG: A concise blog post in Markdown (450-650 words).
   - H1 title framed from Scaler's perspective
   - Intro: why this conversation matters for Scaler's audience
   - 3 short H2 sections covering the best insights only
   - Conclusion: practical takeaway + CTA to watch the full video on Scaler's YouTube
   - Keep it crisp, readable, and not bloated

Do not return JSON. Do not add any explanation outside the two tags."""

    linkedin_prompt = f"""Use the transcript below to write an SST-style LinkedIn post.
Choose the best post type from the skill and follow it exactly.
Ground all claims in the transcript. Do not invent names, companies, amounts, locations, or outcomes.
If some SST-specific detail is not present in the transcript, do not fabricate it.

TRANSCRIPT:
{full_text}"""

    raw = ""
    try:
        raw = _chat(prompt, max_tokens=4096)
        parsed = {
            "twitter": _extract_tagged_section(raw, "TWITTER"),
            "blog": _extract_tagged_section(raw, "BLOG"),
        }
        parsed["linkedin"] = _chat(
            linkedin_prompt,
            max_tokens=1400,
            system=LINKEDIN_SKILL,
        ).strip()
        return parsed
    except Exception as exc:
        print(f"[claude] tagged generate_posts parse failed: {exc}")
        try:
            parsed = _extract_json(raw)
            linkedin = _chat(
                linkedin_prompt,
                max_tokens=1400,
                system=LINKEDIN_SKILL,
            ).strip()
            return {
                "twitter": parsed.get("twitter", ""),
                "linkedin": linkedin or parsed.get("linkedin", ""),
                "blog": parsed.get("blog", ""),
            }
        except Exception as json_exc:
            print(f"[claude] generate_posts failed: {json_exc}")
            return {"twitter": "", "linkedin": "", "blog": ""}


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
- Built around one complete topic, story beat, or answer from the original video
- Under 75 seconds total duration each
- Prefer one continuous segment from the original video whenever possible
- Do not crop a thought midway; if the speaker starts explaining a topic, let that topic reach
  a natural end before choosing the end timestamp
- Always starting AND ending on a complete sentence boundary (use the exact [MM:SS] timestamps)
- Focused on a single clear insight, story beat, or takeaway that resonates with ambitious
  engineers and students following Scaler
- Immediately gripping in the first 5 seconds — no warm-up, no intros

TRANSCRIPT:
{transcript_text}

Rules for segments:
- start_ms and end_ms must match actual sentence boundaries from the transcript above
  (convert [MM:SS] → milliseconds: MM*60000 + SS*1000)
- Each short should usually contain exactly 1 segment; use multiple segments only if they are
  adjacent parts of the same thought and still feel like one complete explanation
- Multiple segments must be in chronological order and non-overlapping
- Total duration of all segments combined must be ≤ 75 seconds
- Minimum 25 seconds total
- Never end on a teaser, cliffhanger, or unfinished explanation
- The viewer should feel they got the full point even without the full video

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
        designs = _extract_json(raw)
        valid = []
        for d in designs:
            if not isinstance(d, dict) or "segments" not in d or "title" not in d:
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
