"""Narration synthesis for AI Training Studio videos via Gemini TTS.

Calls the Gemini ``generateContent`` API with AUDIO response modality. The API
returns raw 16-bit PCM (base64). This module wraps it in a WAV container so the
renderer and any player can read it. The API key is sent in a header and never
logged.
"""

from __future__ import annotations

import base64
import contextlib
import io
import logging
import re
import time
import wave

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_TTS_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_TTS_MODEL = "gemini-3.8-flash-tts"
DEFAULT_VOICE = "Kore"
DEFAULT_RATE = 24000
MAX_NARRATION_CHARS = 1200
MAX_ATTEMPTS = 5
MAX_BACKOFF_SEC = 30.0
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

_RATE_RE = re.compile(r"rate=(\d+)")


class NarrationError(Exception):
    """Raised when narration audio cannot be produced."""


def pcm_to_wav(pcm: bytes, *, rate: int = DEFAULT_RATE, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _parse_inline_audio(payload: dict) -> tuple[bytes, int]:
    """Extract (pcm_bytes, sample_rate) from a generateContent audio response."""
    try:
        part = payload["candidates"][0]["content"]["parts"][0]
        inline = part["inlineData"]
        data = base64.b64decode(inline["data"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise NarrationError("TTS response did not contain audio data") from exc
    if not data:
        raise NarrationError("TTS returned empty audio")
    match = _RATE_RE.search(str(inline.get("mimeType", "")))
    rate = int(match.group(1)) if match else DEFAULT_RATE
    return data, rate


def synthesize_wav(text: str, *, voice: str = DEFAULT_VOICE) -> bytes:
    """Return WAV bytes narrating ``text``. Raises NarrationError on any failure."""
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        raise NarrationError("GEMINI_API_KEY is not configured")

    cleaned = " ".join(text.split())[:MAX_NARRATION_CHARS]
    if not cleaned:
        raise NarrationError("narration text is empty")

    model = settings.gemini_tts_model or DEFAULT_TTS_MODEL
    body = {
        "contents": [{"parts": [{"text": cleaned}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    headers = {"x-goog-api-key": api_key, "content-type": "application/json"}
    url = GEMINI_TTS_URL.format(model=model)

    response: httpx.Response | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = httpx.post(url, headers=headers, json=body, timeout=120.0)
        except httpx.HTTPError as exc:
            if attempt == MAX_ATTEMPTS - 1:
                raise NarrationError(f"TTS request failed: {type(exc).__name__}") from exc
            time.sleep(_backoff_seconds(attempt, None))
            continue

        if response.status_code == 200:
            break
        if response.status_code == 429 and _is_quota_exhausted(response):
            # Daily/free-tier quota: retrying in seconds cannot succeed.
            raise NarrationError(
                "Gemini TTS quota is exhausted for this API key. Enable billing or wait for reset."
            )
        if response.status_code not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS - 1:
            logger.warning("Gemini TTS failed model=%s status=%s", model, response.status_code)
            raise NarrationError(f"TTS request returned HTTP {response.status_code}")
        logger.info("Gemini TTS retryable status=%s attempt=%s", response.status_code, attempt + 1)
        time.sleep(_backoff_seconds(attempt, response.headers.get("retry-after")))

    if response is None or response.status_code != 200:
        raise NarrationError("TTS request did not succeed")
    pcm, rate = _parse_inline_audio(response.json())
    return pcm_to_wav(pcm, rate=rate)


def _is_quota_exhausted(response: httpx.Response) -> bool:
    text = response.text.lower()
    return "resource_exhausted" in text and ("free_tier" in text or "quota" in text)


def _backoff_seconds(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        with contextlib.suppress(ValueError):
            return min(MAX_BACKOFF_SEC, max(1.0, float(retry_after)))
    return min(MAX_BACKOFF_SEC, 3.0 * (2**attempt))
