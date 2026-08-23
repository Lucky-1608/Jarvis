"""
Jarvis OS — Memory Manager.

Multi-tier memory system (spec Volume 4):
  - Working Memory:  current task context
  - Short-Term:      active conversation
  - Long-Term:       persistent facts, preferences, projects
  - Semantic:        vector-searchable knowledge
  - Episodic:        past events and actions

All long-lived memories are stored in Supabase (PostgreSQL) using pgvector
with BAAI/bge-small-en-v1.5 embeddings.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from sqlalchemy import String, cast, delete, func, select

from jarvis.config.settings import get_settings
from jarvis.database.core import AsyncSessionLocal
from jarvis.database.models import MemoryNode
from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.memory.embeddings import JarvisEmbeddingFunction, chunk_text

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

    Manages PostgreSQL pgvector storage via SQLAlchemy MemoryNode.
    Provides store, search, and lifecycle operations.
    """

    def __init__(self) -> None:
        self._settings = get_settings().memory
        self._bus = get_event_bus()
        self._embedding_fn = JarvisEmbeddingFunction()

        # Working memory (in-process, not persisted)
        self._working_memory: dict[str, Any] = {}
        # Short-term conversation buffer
        self._conversation_buffer: list[dict[str, str]] = []
        self._max_buffer = 50

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

    # -- Long-term Memory (pgvector) ----------------------------------------

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
        Store content in long-term memory via pgvector.
        """
        meta = metadata or {}
        stored_ids = []

        texts = chunk_text(content) if (chunk and len(content) > 500) else [content]
        embeddings = self._embedding_fn(texts)

        async with AsyncSessionLocal() as session:
            for i, (text, emb) in enumerate(zip(texts, embeddings)):
                entry_id = uuid.uuid4().hex[:16]

                db_meta = {**meta, "chunk_index": i, "total_chunks": len(texts)}
                if project_id is not None:
                    db_meta["project_id"] = project_id

                node = MemoryNode(
                    id=entry_id,
                    content=text,
                    memory_type=memory_type.value,
                    metadata_=db_meta,
                    timestamp=time.time(),
                    importance=importance,
                    embedding=emb
                )
                session.add(node)
                stored_ids.append(entry_id)

            await session.commit()

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
        Search memories by semantic similarity using pgvector.
        """
        import os

        import httpx

        results: list[SearchResult] = []
        jina_api_key = os.getenv("JINA_API_KEY")
        fetch_limit = max(limit, 50) if jina_api_key else limit

        # Generate query embedding
        query_vector = self._embedding_fn([query])[0]

        async with AsyncSessionLocal() as session:
            # calculate cosine distance
            distance_col = MemoryNode.embedding.cosine_distance(query_vector).label("distance")

            stmt = select(MemoryNode, distance_col).order_by(distance_col).limit(fetch_limit)

            if memory_type:
                stmt = stmt.where(MemoryNode.memory_type == memory_type.value)

            if project_id is not None:
                # filter by project_id in JSON metadata
                stmt = stmt.where(cast(MemoryNode.metadata_["project_id"].as_string(), String) == str(project_id))

            db_result = await session.execute(stmt)
            rows = db_result.all()

            for node, dist in rows:
                relevance = max(0.0, 1.0 - dist)
                if relevance < min_relevance:
                    continue

                entry = MemoryEntry(
                    id=node.id,
                    content=node.content,
                    memory_type=MemoryType(node.memory_type),
                    metadata=node.metadata_,
                    timestamp=node.timestamp,
                    importance=node.importance,
                )
                results.append(SearchResult(entry=entry, score=relevance, distance=dist))

        # Rerank (Stage 2)
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
        all_entries: list[MemoryEntry] = []

        async with AsyncSessionLocal() as session:
            stmt = select(MemoryNode).order_by(MemoryNode.timestamp.desc()).limit(limit)
            if memory_type:
                stmt = stmt.where(MemoryNode.memory_type == memory_type.value)

            db_result = await session.execute(stmt)
            for node in db_result.scalars():
                all_entries.append(
                    MemoryEntry(
                        id=node.id,
                        content=node.content,
                        memory_type=MemoryType(node.memory_type),
                        metadata=node.metadata_,
                        timestamp=node.timestamp,
                        importance=node.importance,
                    )
                )

        return all_entries

    async def delete_entry(self, entry_id: str) -> bool:
        """Delete a specific memory entry by ID."""
        async with AsyncSessionLocal() as session:
            stmt = delete(MemoryNode).where(MemoryNode.id == entry_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def update_entry(self, entry_id: str, content: str | None = None, metadata: dict[str, Any] | None = None) -> bool:
        """Update a specific memory entry's content or metadata."""
        from sqlalchemy import update
        async with AsyncSessionLocal() as session:
            updates = {}
            if content is not None:
                updates["content"] = content
                updates["embedding"] = self._embedding_fn([content])[0]
            if metadata is not None:
                updates["metadata_"] = metadata
                
            if not updates:
                return False
                
            stmt = update(MemoryNode).where(MemoryNode.id == entry_id).values(**updates)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    # -- Stats & maintenance ------------------------------------------------

    async def get_stats(self) -> dict[str, Any]:
        """Return memory statistics."""
        stats = {
            "working_memory_keys": len(self._working_memory),
            "conversation_buffer_size": len(self._conversation_buffer),
            "collections": {},
        }

        async with AsyncSessionLocal() as session:
            stmt = select(MemoryNode.memory_type, func.count(MemoryNode.id)).group_by(MemoryNode.memory_type)
            result = await session.execute(stmt)

            for mem_type, count in result.all():
                stats["collections"][mem_type] = {"count": count}

            # Fill empty ones
            for mt in MemoryType:
                if mt.value not in stats["collections"]:
                    stats["collections"][mt.value] = {"count": 0}

        return stats

    async def clear_collection(self, memory_type: MemoryType) -> int:
        """Delete all entries in a collection. Returns count deleted."""
        async with AsyncSessionLocal() as session:
            stmt = delete(MemoryNode).where(MemoryNode.memory_type == memory_type.value)
            result = await session.execute(stmt)
            count = result.rowcount
            await session.commit()

        logger.info("memory.collection_cleared", collection=memory_type.value, deleted=count)
        return count
