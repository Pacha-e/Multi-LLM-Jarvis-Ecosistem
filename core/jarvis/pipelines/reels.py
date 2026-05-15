"""J.A.R.V.I.S. — Reels pipeline.

Input: a URL (Instagram Reel / TikTok / YouTube Short).
Output: a Markdown note in the Obsidian vault with metadata + transcript.

Download strategy — cheapest first, escalate only on failure:
  1. yt-dlp        free, fast    (subprocess, no shell)
  2. Playwright    free, slow    (dedicated browser profile, NEVER the personal one)
  3. Apify         PAID          (last resort; only if APIFY_TOKEN is set)

Transcription reuses the existing WhisperSTT model (jarvis.voice.stt).

Security:
  - No tokens written to disk; APIFY_TOKEN read from env only.
  - Temp videos land under var/reels-tmp/ (gitignored) and are deleted after use.
  - Browser scraping uses a dedicated profile dir, isolated from the user's Chrome.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from jarvis.config import config

logger = logging.getLogger(__name__)


# --- data ------------------------------------------------------------------

@dataclass
class ReelResult:
    url: str
    video_path: Optional[Path] = None
    source: str = ""                       # which downloader won
    title: str = ""
    author: str = ""
    upload_date: str = ""
    duration: str = ""
    description: str = ""
    extra: dict = field(default_factory=dict)


# --- helpers ---------------------------------------------------------------

def _reels_dir() -> Path:
    """Resolve the Obsidian output folder for reel notes."""
    if config.REELS_DIR:
        d = Path(config.REELS_DIR)
    else:
        d = Path(config.OBSIDIAN_VAULT) / "Reels"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tmp_dir() -> Path:
    d = Path(config.REELS_TMP_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fmt_duration(seconds) -> str:
    try:
        s = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    return f"{s // 60}:{s % 60:02d}"


def _slugify(text: str, fallback: str = "reel") -> str:
    slug = re.sub(r"[^\w\s-]", "", (text or "").strip().lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:60] or fallback


# --- stage 1: yt-dlp -------------------------------------------------------

def _download_ytdlp(url: str) -> Optional[ReelResult]:
    """Free, fast. Uses yt-dlp from PATH; metadata + video in one pass."""
    if not shutil.which("yt-dlp"):
        logger.warning("[reels] yt-dlp not on PATH; skipping stage 1.")
        return None

    tmp = _tmp_dir()
    out_tpl = str(tmp / "%(id)s.%(ext)s")
    try:
        proc = subprocess.run(
            [
                "yt-dlp",
                "--no-playlist",
                "--print-json",
                "--no-progress",
                "-f", "mp4/best",
                "-o", out_tpl,
                url,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        logger.warning("[reels] yt-dlp timed out.")
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[reels] yt-dlp failed to launch: {e}")
        return None

    if proc.returncode != 0:
        logger.warning(f"[reels] yt-dlp exit {proc.returncode}: {proc.stderr.strip()[:200]}")
        return None

    try:
        meta = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        logger.warning("[reels] yt-dlp produced no JSON metadata.")
        return None

    vid_id = meta.get("id", "reel")
    video_path = next(iter(tmp.glob(f"{vid_id}.*")), None)
    if video_path is None or not video_path.exists():
        logger.warning("[reels] yt-dlp reported success but no file found.")
        return None

    upload = meta.get("upload_date", "")
    if len(upload) == 8:  # YYYYMMDD
        upload = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}"

    return ReelResult(
        url=url,
        video_path=video_path,
        source="yt-dlp",
        title=meta.get("title", "") or meta.get("fulltitle", ""),
        author=meta.get("uploader", "") or meta.get("channel", ""),
        upload_date=upload,
        duration=_fmt_duration(meta.get("duration")),
        description=meta.get("description", "") or "",
        extra={"id": vid_id, "view_count": meta.get("view_count")},
    )


# --- stage 2: Playwright (dedicated profile) -------------------------------

def _download_playwright(url: str) -> Optional[ReelResult]:
    """Free fallback. Renders the page in a dedicated browser profile and
    grabs the first <video> source. NEVER touches the personal Chrome profile."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("[reels] playwright not installed; skipping stage 2.")
        return None

    tmp = _tmp_dir()
    profile = Path(config.BROWSER_PROFILE_DIR)
    profile.mkdir(parents=True, exist_ok=True)

    video_url = None
    try:
        with sync_playwright() as pw:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                headless=True,
            )
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)
            video_url = page.evaluate(
                "() => { const v = document.querySelector('video'); "
                "return v ? (v.currentSrc || v.src) : null; }"
            )
            ctx.close()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[reels] playwright stage failed: {e}")
        return None

    if not video_url:
        logger.warning("[reels] playwright found no <video> source.")
        return None

    # Fetch the resolved media URL.
    try:
        import httpx

        dest = tmp / f"pw-{_slugify(url, 'reel')}.mp4"
        with httpx.stream("GET", video_url, timeout=120, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[reels] playwright media download failed: {e}")
        return None

    return ReelResult(url=url, video_path=dest, source="playwright")


# --- stage 3: Apify (paid, last resort) ------------------------------------

def _download_apify(url: str) -> Optional[ReelResult]:
    """PAID fallback. Disabled unless APIFY_TOKEN is set."""
    if not config.APIFY_TOKEN:
        logger.info("[reels] APIFY_TOKEN unset; Apify fallback disabled.")
        return None
    try:
        import httpx
    except ImportError:
        return None

    # Generic Instagram/TikTok scraper actor; returns a videoUrl field.
    actor = "apify~instagram-scraper"
    api = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
    try:
        resp = httpx.post(
            api,
            params={"token": config.APIFY_TOKEN},
            json={"directUrls": [url], "resultsLimit": 1},
            timeout=300,
        )
        resp.raise_for_status()
        items = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[reels] apify request failed: {e}")
        return None

    if not items:
        return None
    item = items[0]
    video_url = item.get("videoUrl") or item.get("videoUrlHd")
    if not video_url:
        return None

    tmp = _tmp_dir()
    dest = tmp / f"apify-{_slugify(url, 'reel')}.mp4"
    try:
        with httpx.stream("GET", video_url, timeout=180, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[reels] apify media download failed: {e}")
        return None

    return ReelResult(
        url=url,
        video_path=dest,
        source="apify",
        title=item.get("caption", "")[:120],
        author=item.get("ownerUsername", ""),
        upload_date=str(item.get("timestamp", ""))[:10],
        description=item.get("caption", "") or "",
    )


# --- transcription ---------------------------------------------------------

def _transcribe(video_path: Path, language: Optional[str] = None) -> str:
    """Reuse the shared WhisperSTT model. faster-whisper reads audio from
    video containers directly (ffmpeg backend)."""
    try:
        from jarvis.voice.stt import stt
    except Exception as e:  # noqa: BLE001
        logger.error(f"[reels] could not import WhisperSTT: {e}")
        return ""
    return stt.transcribe_file(str(video_path), language=language)


# --- note writer -----------------------------------------------------------

def _write_note(result: ReelResult, transcript: str) -> Path:
    reels_dir = _reels_dir()
    date_tag = datetime.now().strftime("%Y-%m-%d")
    base = _slugify(result.title or result.author or "reel")
    note_path = reels_dir / f"{date_tag}-{base}.md"
    n = 1
    while note_path.exists():
        note_path = reels_dir / f"{date_tag}-{base}-{n}.md"
        n += 1

    def esc(v: str) -> str:
        return (v or "").replace('"', "'").replace("\n", " ").strip()

    fm = [
        "---",
        f'url: "{esc(result.url)}"',
        f'autor: "{esc(result.author)}"',
        f'titulo: "{esc(result.title)}"',
        f'fecha_publicacion: "{esc(result.upload_date)}"',
        f'duracion: "{esc(result.duration)}"',
        f'fuente_descarga: "{result.source}"',
        f'capturado: "{date_tag}"',
        "tags: [reel, transcripcion]",
        "---",
    ]
    body = [
        "",
        f"# {result.title or 'Reel'}",
        "",
        "## Transcripción",
        "",
        transcript or "_(sin transcripción — Whisper no devolvió texto)_",
        "",
        "## Metadatos",
        "",
        f"- **URL:** {result.url}",
        f"- **Autor:** {result.author or '—'}",
        f"- **Publicado:** {result.upload_date or '—'}",
        f"- **Duración:** {result.duration or '—'}",
        f"- **Descargado vía:** {result.source}",
    ]
    if result.description:
        body += ["", "## Descripción original", "", result.description.strip()]

    note_path.write_text("\n".join(fm + body) + "\n", encoding="utf-8")
    return note_path


# --- orchestration ---------------------------------------------------------

def process_reel(url: str, language: Optional[str] = None) -> dict:
    """Run the full pipeline for one URL. Returns a summary dict."""
    logger.info(f"[reels] processing {url}")

    result = None
    for stage in (_download_ytdlp, _download_playwright, _download_apify):
        result = stage(url)
        if result and result.video_path:
            break

    if not result or not result.video_path:
        return {"ok": False, "url": url, "error": "all download stages failed"}

    logger.info(f"[reels] downloaded via {result.source}: {result.video_path.name}")

    transcript = _transcribe(result.video_path, language=language)
    note_path = _write_note(result, transcript)

    # Cleanup temp video — keep only the Obsidian note.
    try:
        result.video_path.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[reels] could not delete temp video: {e}")

    logger.info(f"[reels] note written: {note_path}")
    return {
        "ok": True,
        "url": url,
        "source": result.source,
        "note": str(note_path),
        "transcript_chars": len(transcript),
    }


def main(argv: Optional[list] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m jarvis.pipelines.reels <url> [--lang es]")
        return 2

    url = argv[0]
    language = None
    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv):
            language = argv[i + 1]

    res = process_reel(url, language=language)
    if res["ok"]:
        print(f"[reels] OK ({res['source']}) -> {res['note']}")
        print(f"[reels] transcripción: {res['transcript_chars']} caracteres")
        return 0
    print(f"[reels] ERROR: {res['error']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
