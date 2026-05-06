import uuid
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from sqlalchemy import select, update, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.core.config import settings


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_memory(
        self,
        project_id: uuid.UUID,
        content: str,
        category: str = "general",
        confidence: float = 1.0,
        source_task_id: Optional[uuid.UUID] = None,
        ttl_days: Optional[int] = None,
    ) -> Memory:
        embedding = await self._get_embedding(content)
        ttl = ttl_days or settings.DEFAULT_MEMORY_TTL_DAYS
        memory = Memory(
            project_id=project_id,
            content=content,
            embedding=embedding,
            category=category,
            confidence=confidence,
            source_task_id=source_task_id,
            expired_at=datetime.utcnow() + timedelta(days=ttl),
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        return memory

    async def search_memories(
        self,
        project_id: uuid.UUID,
        query: str,
        top_k: Optional[int] = None,
    ) -> list[Memory]:
        k = top_k or settings.DEFAULT_MEMORY_TOP_K
        query_embedding = await self._get_embedding(query)
        if query_embedding is None:
            return []
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        sql = text("""
            SELECT id, project_id, content, category, confidence, source_task_id,
                   is_expired, created_at, expired_at,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM memories
            WHERE project_id = :project_id AND is_expired = false
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        result = await self.db.execute(
            sql,
            {"embedding": embedding_str, "project_id": str(project_id), "limit": k},
        )
        rows = result.fetchall()
        memories = []
        for row in rows:
            memory = Memory(
                id=row[0],
                project_id=row[1],
                content=row[2],
                category=row[3],
                confidence=row[4],
                source_task_id=row[5],
                is_expired=row[6],
                created_at=row[7],
                expired_at=row[8],
            )
            memories.append(memory)
        return memories

    async def expire_old_memories(self) -> int:
        now = datetime.utcnow()
        result = await self.db.execute(
            update(Memory)
            .where(and_(Memory.expired_at < now, Memory.is_expired == False))
            .values(is_expired=True)
        )
        await self.db.commit()
        return result.rowcount

    async def decay_confidence(self, decay_factor: float = 0.95) -> int:
        threshold = 0.3
        result = await self.db.execute(
            update(Memory)
            .where(and_(Memory.is_expired == False, Memory.confidence > threshold))
            .values(confidence=Memory.confidence * decay_factor)
        )
        await self.db.execute(
            update(Memory)
            .where(and_(Memory.confidence <= threshold, Memory.is_expired == False))
            .values(is_expired=True)
        )
        await self.db.commit()
        return result.rowcount

    async def _get_embedding(self, text: str) -> Optional[list[float]]:
        try:
            from openai import AsyncOpenAI
            client_kwargs = {"api_key": settings.OPENAI_API_KEY}
            if settings.OPENAI_BASE_URL:
                client_kwargs["base_url"] = settings.OPENAI_BASE_URL
            client = AsyncOpenAI(**client_kwargs)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception:
            dim = 1536
            np.random.seed(hash(text) % (2**31))
            embedding = np.random.randn(dim).tolist()
            norm = sum(x**2 for x in embedding) ** 0.5
            return [x / norm for x in embedding]
