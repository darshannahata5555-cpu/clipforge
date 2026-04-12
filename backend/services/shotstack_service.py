import time
import httpx
from config import settings


def _edit_url() -> str:
    return f"https://api.shotstack.io/{settings.shotstack_env}"


def _ingest_url() -> str:
    return f"https://api.shotstack.io/ingest/{settings.shotstack_env}"


def _headers() -> dict:
    return {
        "x-api-key": settings.shotstack_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def ingest_url(source_url: str) -> str:
    """
    Register a publicly accessible clip URL with Shotstack ingest.
    Returns the Shotstack CDN URL once ingestion is ready.
    source_url must be a public HTTP/HTTPS URL (e.g. from R2).
    """
    h = _headers()
    r = httpx.post(
        f"{_ingest_url()}/sources",
        headers=h,
        json={"url": source_url},
        timeout=30,
    )
    r.raise_for_status()
    source_id = r.json()["data"]["id"]

    for _ in range(40):      # up to ~2 min
        time.sleep(3)
        r = httpx.get(f"{_ingest_url()}/sources/{source_id}", headers=h, timeout=30)
        attrs = r.json()["data"]["attributes"]
        status = attrs.get("status", "")
        if status == "ready":
            return attrs["source"]
        if status == "failed":
            raise RuntimeError(f"Shotstack ingest failed for {source_url}")

    raise TimeoutError(f"Shotstack ingest timed out for {source_url}")


def submit_render(
    source_url: str,
    duration_s: float,
    title: str,
    hook_text: str,
    speaker_name: str,
) -> str:
    """
    Submit a Shotstack render job that adds hook text, speaker lower-third,
    and an outro CTA on top of the raw clip.
    Returns the render_id.
    """
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
        )

    hook_len   = min(4.5, duration_s * 0.25)
    lt_start   = min(1.5, duration_s * 0.1)
    lt_len     = max(0.0, duration_s - lt_start - 2.5)
    outro_start = max(0.0, duration_s - 2.5)

    timeline = {
        "tracks": [
            # ── Outro CTA ──────────────────────────────────────────────────────
            {
                "clips": [{
                    "asset": {
                        "type": "html",
                        "html": "<p>Watch the full podcast on Scaler's YouTube ↗</p>",
                        "css": (
                            "p { color: #fff; font-size: 15px; font-weight: 700; "
                            "font-family: Arial, sans-serif; text-align: center; "
                            "padding: 10px 18px; margin: 0; }"
                        ),
                        "width": 520,
                        "height": 58,
                        "background": "rgba(0,0,0,0.78)",
                    },
                    "start": outro_start,
                    "length": 2.5,
                    "position": "center",
                    "transition": {"in": "fade", "out": "fade"},
                }]
            },
            # ── Speaker lower-third ────────────────────────────────────────────
            {
                "clips": [{
                    "asset": {
                        "type": "html",
                        "html": (
                            f"<div>"
                            f"<p class='name'>{esc(speaker_name)}</p>"
                            f"<p class='label'>Scaler Podcast</p>"
                            f"</div>"
                        ),
                        "css": (
                            ".name { color: #fff; font-size: 17px; font-weight: bold; "
                            "font-family: Arial, sans-serif; margin: 0 0 2px 0; } "
                            ".label { color: #f6c90e; font-size: 11px; font-weight: 600; "
                            "font-family: Arial, sans-serif; margin: 0; letter-spacing: 1.5px; "
                            "text-transform: uppercase; }"
                        ),
                        "width": 300,
                        "height": 62,
                        "background": "rgba(0,0,0,0.72)",
                    },
                    "start": lt_start,
                    "length": lt_len,
                    "position": "bottomLeft",
                    "offset": {"x": 0.02, "y": 0.06},
                    "transition": {"in": "slideLeft", "out": "fade"},
                }]
            },
            # ── Hook text (top, first few seconds) ────────────────────────────
            {
                "clips": [{
                    "asset": {
                        "type": "html",
                        "html": f"<p>{esc(hook_text[:130])}</p>",
                        "css": (
                            "p { color: #fff; font-size: 20px; font-weight: 800; "
                            "font-family: Arial, sans-serif; text-align: center; "
                            "text-shadow: 1px 1px 8px rgba(0,0,0,0.95); "
                            "margin: 0; padding: 6px 10px; }"
                        ),
                        "width": 580,
                        "height": 110,
                        "background": "transparent",
                    },
                    "start": 0,
                    "length": hook_len,
                    "position": "top",
                    "offset": {"x": 0, "y": -0.04},
                    "transition": {"in": "fade", "out": "fade"},
                }]
            },
            # ── Base video ────────────────────────────────────────────────────
            {
                "clips": [{
                    "asset": {
                        "type": "video",
                        "src": source_url,
                        "volume": 1,
                    },
                    "start": 0,
                    "length": duration_s,
                }]
            },
        ]
    }

    payload = {
        "timeline": timeline,
        "output": {
            "format": "mp4",
            "resolution": "hd",   # 1280×720
            "fps": 30,
        },
    }

    r = httpx.post(f"{_edit_url()}/render", headers=_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["response"]["id"]


def poll_render(render_id: str, timeout_s: int = 360) -> str:
    """
    Block until the render job completes and return the final video URL.
    Raises RuntimeError on failure, TimeoutError on timeout.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(6)
        r = httpx.get(f"{_edit_url()}/render/{render_id}", headers=_headers(), timeout=30)
        data = r.json()["response"]
        status = data.get("status", "")
        if status == "done":
            return data["url"]
        if status in ("failed", "error"):
            raise RuntimeError(
                f"Shotstack render {render_id} failed: {data.get('error', 'unknown')}"
            )
    raise TimeoutError(f"Shotstack render {render_id} timed out after {timeout_s}s")


def enhance_clip(
    public_url: str,
    duration_s: float,
    title: str,
    hook_text: str,
    speaker_name: str,
) -> str:
    """
    Enhance a clip that already has a public URL (e.g. R2):
    ingest → render → poll → return Shotstack CDN URL.
    Raises on any error (caller should fall back to the raw clip URL).
    """
    cdn_url   = ingest_url(public_url)
    render_id = submit_render(cdn_url, duration_s, title, hook_text, speaker_name)
    return poll_render(render_id)
