"""
Jarvis OS — Memory Manager.

Multi-tier memory system (spec Volume 4):
  - Working Memory:  current task context
  - Short-Term:      active conversation
  - Long-Term:       persistent facts, preferences, projects
  - Semantic:        vector-searchable knowledge
  - Episodic:        past events and actions

All long-lived memories are stored in ChromaDB collections with
BAAI/bge-small-en-v1.5 embeddings.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from jarvis.config.settings import get_settings
from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.memory.embeddings import JarvisEmbeddingFunction, chunk_text, generate_chunk_id

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Memory data types
# ---------------------------------------------------------------------------
class MemoryType(str, Enum):
    CONVERSATION = "conversations"
    DOCUMENT = "documents"
    PREFERENCE = "preferences"
    PROJECT = "projects"
    TASK = "tasks"
    WORKFLOW = "workflows"
    EPISODIC = "episodic"


@dataclass
class MemoryEntry:
    """A single memory record."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    content: str = ""
    memory_type: MemoryType = MemoryType.CONVERSATION
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5  # 0.0–1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "importance": self.importance,
            **self.metadata,
        }


@dataclass
class SearchResult:
    """A memory search result with relevance score."""

    entry: MemoryEntry
    score: float  # 0.0–1.0 relevance
    distance: float  # raw distance from vector search


# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------
class MemoryManager:
    """
    Central memory system for Jarvis OS.

    Manages multiple ChromaDB collections, one per ``MemoryType``.
    Provides store, search, and lifecycle operations.
    """

    def __init__(self) -> None:
        self._settings = get_settings().memory
        self._bus = get_event_bus()
        self._client = None
        self._collections: dict[str, Any] = {}
        self._embedding_fn = JarvisEmbeddingFunction()

        # Working memory (in-process, not persisted)
        self._working_memory: dict[str, Any] = {}
        # Short-term conversation buffer
        self._conversation_buffer: list[dict[str, str]] = []
        self._max_buffer = 50

    # -- Initialisation -----------------------------------------------------

    def _ensure_client(self):
        """Lazily create the ChromaDB client and collections."""
        if self._client is not None:
            return

        import chromadb

        persist_dir = self._settings.chroma_persist_dir
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=persist_dir)
        logger.info("memory.chromadb_initialized", persist_dir=persist_dir)

        # Create/get a collection for each memory type
        for mem_type in MemoryType:
            self._collections[mem_type.value] = self._client.get_or_create_collection(
                name=mem_type.value,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
        logger.info("memory.collections_ready", count=len(self._collections))

    # -- Working Memory (ephemeral) -----------------------------------------

    def set_working(self, key: str, value: Any) -> None:
        """Store a value in working memory (current task only)."""
        self._working_memory[key] = value

    def get_working(self, key: str, default: Any = None) -> Any:
        """Retrieve from working memory."""
        return self._working_memory.get(key, default)

    def clear_working(self) -> None:
        """Reset working memory."""
        self._working_memory.clear()

    # -- Conversation Buffer (short-term) -----------------------------------

    def add_to_conversation(self, role: str, content: str) -> None:
        """Append a message to the short-term conversation buffer."""
        self._conversation_buffer.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        if len(self._conversation_buffer) > self._max_buffer:
            self._conversation_buffer = self._conversation_buffer[-self._max_buffer:]

    def get_conversation(self, limit: int = 20) -> list[dict[str, str]]:
        """Return recent conversation messages."""
        return self._conversation_buffer[-limit:]

    def clear_conversation(self) -> None:
        """Clear the conversation buffer."""
        self._conversation_buffer.clear()

    # -- Long-term Memory (ChromaDB) ----------------------------------------

    async def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        chunk: bool = True,
        project_id: int | None = None,
    ) -> list[str]:
        """
        Store content in long-term memory.

        If *chunk* is True, long content is split into overlapping
        chunks before storing (better retrieval quality).

        Returns the list of stored memory IDs.
        """
        self._ensure_client()
        collection = self._collections[memory_type.value]
        meta = metadata or {}
        stored_ids = []

        # Optionally chunk long content
        texts = chunk_text(content) if (chunk and len(content) > 500) else [content]

        for i, text in enumerate(texts):
            entry = MemoryEntry(
                content=text,
                memory_type=memory_type,
                metadata={**meta, "chunk_index": i, "total_chunks": len(texts)},
                importance=importance,
            )

            # Prepare metadata for ChromaDB (must be str/int/float/bool)
            chroma_meta = {
                "memory_type": memory_type.value,
                "timestamp": entry.timestamp,
                "importance": importance,
                "chunk_index": i,
                "total_chunks": len(texts),
            }
            if project_id is not None:
                chroma_meta["project_id"] = project_id
            # Add user metadata (filter non-serializable values)
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    chroma_meta[k] = v

            collection.add(
                ids=[entry.id],
                documents=[text],
                metadatas=[chroma_meta],
            )
            stored_ids.append(entry.id)

        await self._bus.publish(Event(
            type=EventTypes.MEMORY_STORED,
            data={
                "memory_type": memory_type.value,
                "ids": stored_ids,
                "content_preview": content[:100],
            },
            source="memory_manager",
        ))

        logger.info(
            "memory.stored",
            memory_type=memory_type.value,
            chunks=len(stored_ids),
            content_len=len(content),
        )
        return stored_ids

    async def search(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 10,
        min_relevance: float = 0.0,
        project_id: int | None = None,
    ) -> list[SearchResult]:
        """
        Search memories by semantic similarity.

        If *memory_type* is None, searches across **all** collections.
        """
        import os
        import httpx
        self._ensure_client()
        results: list[SearchResult] = []

        collections_to_search = (
            [self._collections[memory_type.value]]
            if memory_type
            else list(self._collections.values())
        )

        jina_api_key = os.getenv("JINA_API_KEY")
        fetch_limit = max(limit, 50) if jina_api_key else limit

        for collection in collections_to_search:
            if collection.count() == 0:
                continue

            try:
                where_clause = {"project_id": project_id} if project_id is not None else None
                search_results = collection.query(
                    query_texts=[query],
                    n_results=min(fetch_limit, collection.count()),
                    where=where_clause,
                )
            except Exception as exc:
                logger.warning("memory.search_error", error=str(exc))
                continue

            if not search_results or not search_results.get("documents"):
                continue

            documents = search_results["documents"][0]
            metadatas = search_results["metadatas"][0]
            distances = search_results["distances"][0]
            ids = search_results["ids"][0]

            for doc, meta, dist, doc_id in zip(documents, metadatas, distances, ids):
                # Convert cosine distance to relevance score (0–1)
                relevance = max(0.0, 1.0 - dist)
                if relevance < min_relevance:
                    continue

                entry = MemoryEntry(
                    id=doc_id,
                    content=doc,
                    memory_type=MemoryType(meta.get("memory_type", "conversations")),
                    metadata=meta,
                    timestamp=meta.get("timestamp", 0),
                    importance=meta.get("importance", 0.5),
                )
                results.append(SearchResult(entry=entry, score=relevance, distance=dist))

        # 2. Rerank (Stage 2)
        if jina_api_key and len(results) > 1:
            try:
                docs = [r.entry.content for r in results]
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        "https://api.jina.ai/v1/rerank",
                        headers={"Authorization": f"Bearer {jina_api_key}"},
                        json={
                            "model": "jina-reranker-v3.5",
                            "query": query,
                            "documents": docs,
                            "top_n": limit
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    reranked_results = []
                    for item in data["results"]:
                        idx = item["index"]
                        new_score = item["relevance_score"]
                        original_result = results[idx]
                        original_result.score = new_score
                        reranked_results.append(original_result)
                    
                    results = reranked_results
                    logger.info("memory.jina_reranked", items=len(results))
            except Exception as exc:
                logger.warning("memory.jina_reranker_failed", error=str(exc))
                results.sort(key=lambda r: r.score, reverse=True)
        else:
            results.sort(key=lambda r: r.score, reverse=True)

        await self._bus.publish(Event(
            type=EventTypes.MEMORY_RETRIEVED,
            data={"query": query[:100], "results_count": len(results[:limit])},
            source="memory_manager",
        ))

        return results[:limit]

    async def get_recent(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """
        Fetch recent memories, optionally filtered by type.
        """
        self._ensure_client()
        
        collections_to_search = (
            [self._collections[memory_type.value]]
            if memory_type
            else list(self._collections.values())
        )
        
        all_entries: list[MemoryEntry] = []
        for collection in collections_to_search:
            try:
                data = collection.get()
                if not data or not data.get("documents"):
                    continue
                
                for doc, meta, doc_id in zip(data["documents"], data["metadatas"], data["ids"]):
                    all_entries.append(
                        MemoryEntry(
                            id=doc_id,
                            content=doc,
                            memory_type=MemoryType(meta.get("memory_type", "conversations")),
                            metadata=meta,
                            timestamp=meta.get("timestamp", 0),
                            importance=meta.get("importance", 0.5),
                        )
                    )
            except Exception as exc:
                logger.warning("memory.get_recent_error", error=str(exc))
                continue
                
        # Sort by timestamp descending
        all_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return all_entries[:limit]

    # -- Stats & maintenance ------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return memory statistics."""
        self._ensure_client()
        stats = {
            "working_memory_keys": len(self._working_memory),
            "conversation_buffer_size": len(self._conversation_buffer),
            "collections": {},
        }
        for name, collection in self._collections.items():
            stats["collections"][name] = {"count": collection.count()}
        return stats

    async def clear_collection(self, memory_type: MemoryType) -> int:
        """Delete all entries in a collection. Returns count deleted."""
        self._ensure_client()
        collection = self._collections[memory_type.value]
        count = collection.count()
        if count > 0:
            # ChromaDB requires IDs to delete; get all then delete
            all_data = collection.get()
            if all_data["ids"]:
                collection.delete(ids=all_data["ids"])
        logger.info("memory.collection_cleared", collection=memory_type.value, deleted=count)
        return count
