"""Course video rendering through the Remotion renderer service.

Builds render scenes from the approved course draft (objectives, lesson titles,
takeaways), synthesizes one narration clip per storyboard scene with Gemini TTS,
sizes each scene to its audio, and asks the renderer to produce the MP4.
Narration is optional only when no Gemini key is configured; a TTS failure
fails the job rather than silently producing a video without narration.
"""

from __future__ import annotations

import base64
import contextlib
import io
import logging
import wave
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.modules.training_studio import narration
from app.modules.training_studio.schemas import CourseDraft, StoryboardScene

logger = logging.getLogger(__name__)

FPS = 30
RENDER_TIMEOUT_SEC = 900.0
SCENE_TAIL_SEC = 0.6
MIN_SCENE_SEC = 3.0
MAX_SCENE_SEC = 120.0


class RenderError(Exception):
    """Raised when the renderer cannot produce a video."""


def _bullets_for_scene(scene: StoryboardScene, course: CourseDraft, is_last: bool) -> list[str]:
    title = scene.title.strip()
    if title == "Key Learning Objectives" or scene.scene_number == 1:
        return [o for o in course.learning_objectives[:4]]
    if is_last:
        return [k for k in course.key_takeaways[:4]]
    for module in course.modules:
        if module.title.strip() == title:
            return [lesson.title for lesson in module.lessons[:5]]
    return []


def _kicker_for_scene(scene: StoryboardScene, course: CourseDraft, idx: int, last: int) -> str:
    if idx == 0:
        return "Introduction"
    if idx == last:
        return "Summary"
    if scene.title.strip() == "Key Learning Objectives":
        return "Objectives"
    module_titles = [m.title.strip() for m in course.modules]
    if scene.title.strip() in module_titles:
        return f"Module {module_titles.index(scene.title.strip()) + 1} of {len(module_titles)}"
    return "Lesson"


def build_render_scenes(course: CourseDraft, storyboard: list[StoryboardScene]) -> list[dict]:
    scenes: list[dict] = []
    last = len(storyboard) - 1
    for idx, scene in enumerate(storyboard):
        scenes.append(
            {
                "title": scene.title,
                "kicker": _kicker_for_scene(scene, course, idx, last),
                "bullets": _bullets_for_scene(scene, course, is_last=idx == last),
                "narration": scene.narration,
                "duration_sec": float(scene.duration_sec),
            }
        )
    return scenes


def _read_wav(data: bytes) -> tuple[bytes, int]:
    with wave.open(io.BytesIO(data), "rb") as wf:
        if wf.getsampwidth() != 2 or wf.getnchannels() != 1:
            raise RenderError("narration must be 16-bit mono PCM")
        return wf.readframes(wf.getnframes()), wf.getframerate()


def _build_narration_track(clips: list[tuple[bytes, int]], scene_seconds: list[float]) -> bytes:
    """Concatenate per-scene PCM, padding each clip out to its scene length."""
    if not clips:
        return b""
    rate = clips[0][1]
    out = bytearray()
    for (pcm, clip_rate), seconds in zip(clips, scene_seconds, strict=True):
        if clip_rate != rate:
            raise RenderError("narration sample rates differ between scenes")
        target = int(seconds * rate) * 2
        out += pcm[:target]
        out += b"\x00" * max(0, target - min(len(pcm), target))
    wav = io.BytesIO()
    with wave.open(wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(bytes(out))
    return wav.getvalue()


def render_course_video(
    *,
    job_id: str,
    course: CourseDraft,
    storyboard: list[StoryboardScene],
    storage_dir: Path,
) -> tuple[str, int]:
    """Render the course video. Returns (asset_relative_url, duration_seconds)."""
    if not storyboard:
        raise RenderError("storyboard is empty")

    settings = get_settings()
    scenes = build_render_scenes(course, storyboard)

    narration_b64: str | None = None
    if (settings.gemini_api_key or "").strip():
        clips: list[tuple[bytes, int]] = []
        for scene in storyboard:
            try:
                wav_bytes = narration.synthesize_wav(scene.narration)
            except narration.NarrationError as exc:
                raise RenderError(
                    f"narration failed for scene {scene.scene_number}: {exc}"
                ) from exc
            clips.append(_read_wav(wav_bytes))

        # Each scene lasts at least its storyboard length and at least its narration.
        durations: list[float] = []
        for (pcm, rate), scene in zip(clips, storyboard, strict=True):
            clip_sec = len(pcm) / 2 / rate
            durations.append(
                min(
                    MAX_SCENE_SEC, max(MIN_SCENE_SEC, scene.duration_sec, clip_sec + SCENE_TAIL_SEC)
                )
            )
        for scene_dict, seconds in zip(scenes, durations, strict=True):
            scene_dict["duration_sec"] = seconds
        track = _build_narration_track(clips, durations)
        narration_b64 = base64.b64encode(track).decode("ascii")
    else:
        logger.warning("GEMINI_API_KEY not set; rendering course video without narration")

    payload = {
        "job_id": job_id,
        "course_title": course.title,
        "accent_color": "#38BDF8",
        "scenes": scenes,
        "narration_wav_base64": narration_b64,
    }
    try:
        response = httpx.post(
            f"{settings.renderer_url.rstrip('/')}/render",
            json=payload,
            timeout=RENDER_TIMEOUT_SEC,
        )
    except httpx.HTTPError as exc:
        raise RenderError(f"renderer unreachable: {type(exc).__name__}") from exc
    if response.status_code != 200:
        detail = ""
        with contextlib.suppress(ValueError):
            detail = str(response.json().get("error", ""))[:300]
        raise RenderError(f"renderer returned HTTP {response.status_code}: {detail}")

    asset = storage_dir / f"video_{job_id}.mp4"
    if not asset.is_file() or asset.stat().st_size < 1024:
        raise RenderError("renderer finished but the video file is missing in shared storage")

    total = int(round(sum(s["duration_sec"] for s in scenes)))
    return f"/api/v1/studio/video-asset/{asset.name}", total
