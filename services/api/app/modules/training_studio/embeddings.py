"""Local and remote embedding providers for document indexing and semantic retrieval.

Supports Ollama local embedding models (e.g. nomic-embed-text, all-minilm)
and a deterministic fallback provider for testing and offline environments.
"""

import hashlib
import logging
import math
from typing import Protocol

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol for semantic text embedding providers."""

    def embed_text(self, text: str) -> list[float]:
        """Produce a normalized float vector for the input text."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Produce normalized float vectors for a batch of input texts."""
        ...


class OllamaEmbeddingProvider:
    """Connects to local Ollama daemon for local, free embeddings."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url or "http://localhost:11434").rstrip(
            "/"
        )
        self.model = model or settings.embedding_model or "nomic-embed-text"
        self._fallback = DeterministicEmbeddingProvider()

    def embed_text(self, text: str) -> list[float]:
        endpoint = f"{self.base_url}/api/embeddings"
        payload = {"model": self.model, "prompt": text}

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(endpoint, json=payload)
                if res.status_code == 200:
                    embedding = res.json().get("embedding")
                    if isinstance(embedding, list) and len(embedding) > 0:
                        return embedding
        except Exception as exc:
            logger.debug("Ollama embedding endpoint unreachable (%s), using local fallback", exc)

        return self._fallback.embed_text(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class DeterministicEmbeddingProvider:
    """Offline, deterministic embedding provider producing normalized 384-d vectors."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        cleaned = text.strip().lower()
        # Seed pseudo-random generator with sha256 of text
        h = hashlib.sha256(cleaned.encode("utf-8")).digest()
        vector: list[float] = []

        for i in range(self.dimensions):
            # Deterministic projection
            byte_idx = (i * 7) % len(h)
            val = (h[byte_idx] / 128.0) - 1.0
            vector.append(val)

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return the active embedding provider."""
    global _provider
    if _provider is None:
        _provider = OllamaEmbeddingProvider()
    return _provider
