"""LLM Client for AI Training Studio.

Supports Google Gemini API, GroqCloud (Llama 3.3 / Mixtral), and offline
deterministic fallback. Keeps all API keys server-side and safely degrades
if network or API keys are unavailable.
"""

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = (
    "You are an expert corporate training instructional designer. "
    "Return valid JSON matching the requested schema."
)


def generate_structured_content(
    *,
    prompt: str,
    system_instruction: str = DEFAULT_SYSTEM_PROMPT,
    timeout_seconds: float = 30.0,
) -> dict[str, Any] | None:
    """Attempt generation via Gemini or GroqCloud, returning parsed JSON dict or None."""
    settings = get_settings()

    # 1. Try Google Gemini if configured
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        gemini_result = _call_gemini(
            prompt=prompt,
            system_instruction=system_instruction,
            api_key=settings.gemini_api_key.strip(),
            model=settings.ai_model or "gemini-3.8-flash",
            timeout=timeout_seconds,
        )
        if gemini_result is not None:
            return gemini_result

    # 2. Try GroqCloud if configured
    if settings.groq_api_key and settings.groq_api_key.strip():
        groq_result = _call_groq(
            prompt=prompt,
            system_instruction=system_instruction,
            api_key=settings.groq_api_key.strip(),
            model=settings.groq_model or "openai/gpt-oss-120b",
            timeout=timeout_seconds,
        )
        if groq_result is not None:
            return groq_result

    return None


def generate_gemini_json(
    *,
    prompt: str,
    system_instruction: str,
    response_schema: dict[str, Any],
) -> dict[str, Any] | None:
    """Schema-constrained JSON from Gemini. Returns None if unconfigured or failed."""
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        return None
    return _call_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        api_key=api_key,
        model=settings.ai_model or "gemini-3.8-flash",
        timeout=90.0,
        response_schema=response_schema,
    )


def _call_gemini(
    *,
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: str,
    timeout: float,
    response_schema: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Call Google Gemini generateContent API with structured JSON output.

    The key is sent in a header (never in the URL) and only exception types are
    logged, so credentials cannot leak through logs or error text.
    """
    models_to_try = [model]
    for fallback in ["gemini-3.8-flash"]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    generation_config: dict[str, Any] = {
        "temperature": 0.2,
        "responseMimeType": "application/json",
    }
    if response_schema is not None:
        generation_config["responseSchema"] = response_schema
    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nTask:\n{prompt}"}]}],
        "generationConfig": generation_config,
    }
    headers = {"x-goog-api-key": api_key, "content-type": "application/json"}

    with httpx.Client(timeout=timeout) as client:
        for candidate_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent"
            try:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            raw_text = parts[0]["text"]
                            parsed = _parse_json(raw_text)
                            if parsed is not None:
                                return parsed
                else:
                    logger.warning(
                        "Gemini API call failed for model=%s status=%s body=%s",
                        candidate_model,
                        resp.status_code,
                        resp.text[:150],
                    )
            except Exception as exc:
                logger.warning(
                    "Gemini API request error for model=%s: %s", candidate_model, type(exc).__name__
                )

    return None


def _call_groq(
    *,
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: str,
    timeout: float,
) -> dict[str, Any] | None:
    """Call GroqCloud API with JSON mode."""
    models_to_try = [model]
    for fallback in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
        if fallback not in models_to_try:
            models_to_try.append(fallback)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout) as client:
        for candidate_model in models_to_try:
            payload = {
                "model": candidate_model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            try:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        parsed = _parse_json(content)
                        if parsed is not None:
                            return parsed
                else:
                    logger.warning(
                        "Groq API call failed for model=%s status=%s body=%s",
                        candidate_model,
                        resp.status_code,
                        resp.text[:150],
                    )
            except Exception as exc:
                logger.warning("Groq API request error for model=%s: %s", candidate_model, exc)

    return None


def _parse_json(text: str) -> dict[str, Any] | None:
    """Safely parse JSON from LLM response text, stripping markdown code blocks if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ```
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        res = json.loads(cleaned)
        return res if isinstance(res, dict) else None
    except Exception:
        return None
