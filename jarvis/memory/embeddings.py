"""
Jarvis OS — Embedding Pipeline.

Wraps sentence-transformers to convert text into dense vectors
for semantic search in ChromaDB.

Model: BAAI/bge-small-en-v1.5 (spec Volume 4)
Pipeline: Document → Chunk → Embed → Store
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Any

import httpx
import structlog

from jarvis.config.settings import get_settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy model loading
# ---------------------------------------------------------------------------
_model_instance = None


def _get_model():
    """Lazily load the sentence-transformers model (heavy import)."""
    global _model_instance
    if _model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer

            model_name = get_settings().memory.embedding_model
            logger.info("embeddings.loading_model", model=model_name)
            _model_instance = SentenceTransformer(model_name)
            logger.info("embeddings.model_loaded", model=model_name)
        except ImportError:
            logger.warning(
                "embeddings.sentence_transformers_not_installed",
                hint="pip install sentence-transformers",
            )
            raise
    return _model_instance


# ---------------------------------------------------------------------------
# Embedding functions
# ---------------------------------------------------------------------------


def embed_text(text: str) -> list[float]:
    """Embed a single text string into a dense vector."""
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into dense vectors (more efficient)."""
    if not texts:
        return []

    # Attempt Jina API first if key exists
    jina_api_key = os.getenv("JINA_API_KEY")
    if jina_api_key:
        try:
            logger.info("embeddings.using_jina_api", count=len(texts))
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={"Authorization": f"Bearer {jina_api_key}"},
                    json={
                        "model": "jina-embeddings-v5-omni-small",
                        "input": texts
                    }
                )
                response.raise_for_status()
                data = response.json()
                return [item["embedding"] for item in data["data"]]
        except Exception as exc:
            logger.warning("embeddings.jina_api_failed", error=str(exc), fallback="local")

    # Fallback to local sentence-transformers model
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]


# ---------------------------------------------------------------------------
# Chunking utilities
# ---------------------------------------------------------------------------


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Split *text* into overlapping chunks for embedding.

    Uses sentence-aware splitting: tries to break on sentence
    boundaries (periods, newlines) rather than mid-word.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to find a sentence boundary near the end
        if end < len(text):
            # Look for the last period, newline, or question mark
            for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                boundary = text.rfind(sep, start + chunk_size // 2, end)
                if boundary != -1:
                    end = boundary + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def generate_chunk_id(text: str, index: int = 0) -> str:
    """Generate a deterministic ID for a text chunk."""
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"chunk_{content_hash}_{index}"


# ---------------------------------------------------------------------------
# ChromaDB embedding function (adapter)
# ---------------------------------------------------------------------------


class JarvisEmbeddingFunction:
    """
    ChromaDB-compatible embedding function that uses our model.

    Pass this to ChromaDB collection creation so it uses
    BAAI/bge-small-en-v1.5 automatically.
    """
    
    def name(self) -> str:
        return "JarvisEmbeddingFunction"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return embed_texts(input)
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts)
        
    def embed_query(self, text: str) -> list[float]:
        from jarvis.memory.embeddings import embed_text
        return embed_text(text)
