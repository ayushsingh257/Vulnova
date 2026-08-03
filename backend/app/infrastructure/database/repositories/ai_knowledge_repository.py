"""Repository Layer for Phase 5.6 Security Knowledge Base & RAG Vector Engine (pgvector)."""

import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.ai_knowledge import (
    RAGSearchLogModel,
    SecurityKnowledgeChunkModel,
    SecurityKnowledgeDocumentModel,
)


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vector lists (0.0 to 1.0)."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    sim = dot_product / (norm_a * norm_b)
    return max(0.0, min(1.0, float(sim)))


class AIRAGRepository:
    """Repository managing security knowledge documents, vector chunks, & RAG search logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_document(
        self, document: SecurityKnowledgeDocumentModel
    ) -> SecurityKnowledgeDocumentModel:
        """Persist a new security knowledge document master record."""
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def get_document_by_id(
        self, organization_id: UUID, document_id: UUID
    ) -> Optional[SecurityKnowledgeDocumentModel]:
        """Fetch document by ID with tenant boundary security (accessible if global OR owned by tenant)."""
        stmt = (
            select(SecurityKnowledgeDocumentModel)
            .options(selectinload(SecurityKnowledgeDocumentModel.chunks))
            .where(
                SecurityKnowledgeDocumentModel.id == document_id,
                or_(
                    SecurityKnowledgeDocumentModel.organization_id.is_(None),
                    SecurityKnowledgeDocumentModel.organization_id == organization_id,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        organization_id: UUID,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[SecurityKnowledgeDocumentModel], int]:
        """List security knowledge documents accessible to tenant (global or org-private) with pagination."""
        base_filter = or_(
            SecurityKnowledgeDocumentModel.organization_id.is_(None),
            SecurityKnowledgeDocumentModel.organization_id == organization_id,
        )

        conditions = [base_filter]
        if source_type:
            conditions.append(SecurityKnowledgeDocumentModel.source_type == source_type)
        if status:
            conditions.append(SecurityKnowledgeDocumentModel.status == status)

        count_stmt = (
            select(func.count())
            .select_from(SecurityKnowledgeDocumentModel)
            .where(*conditions)
        )
        total_count = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(SecurityKnowledgeDocumentModel)
            .options(selectinload(SecurityKnowledgeDocumentModel.chunks))
            .where(*conditions)
            .order_by(SecurityKnowledgeDocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        docs = list(result.scalars().all())
        return docs, total_count

    async def update_document_status(
        self,
        organization_id: UUID,
        document_id: UUID,
        status: str,
        reviewed_by: Optional[UUID] = None,
        error_message: Optional[str] = None,
    ) -> Optional[SecurityKnowledgeDocumentModel]:
        """Update governance approval or ingestion status of a document."""
        doc = await self.get_document_by_id(organization_id, document_id)
        if not doc:
            return None

        doc.status = status
        doc.updated_at = datetime.now(timezone.utc)
        if reviewed_by:
            doc.reviewed_by = reviewed_by
            doc.reviewed_at = datetime.now(timezone.utc)
        if error_message:
            doc.error_message = error_message

        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def delete_document(self, organization_id: UUID, document_id: UUID) -> bool:
        """Delete document record and associated vector chunks (cascading)."""
        doc = await self.get_document_by_id(organization_id, document_id)
        if not doc:
            return False

        await self.session.delete(doc)
        await self.session.commit()
        return True

    async def bulk_create_chunks(
        self, chunks: List[SecurityKnowledgeChunkModel]
    ) -> int:
        """Bulk insert text chunks with vector embeddings."""
        if not chunks:
            return 0
        self.session.add_all(chunks)
        await self.session.commit()
        return len(chunks)

    async def search_similar_chunks(
        self,
        organization_id: UUID,
        query_embedding: List[float],
        top_k: int = 5,
        min_similarity: float = 0.70,
        source_type: Optional[str] = None,
    ) -> List[
        Tuple[SecurityKnowledgeChunkModel, SecurityKnowledgeDocumentModel, float]
    ]:
        """Search similar vector chunks accessible to tenant, returning (chunk, doc, similarity_score)."""
        doc_conditions = [SecurityKnowledgeDocumentModel.status == "INDEXED"]
        if source_type:
            doc_conditions.append(
                SecurityKnowledgeDocumentModel.source_type == source_type
            )

        stmt = (
            select(SecurityKnowledgeChunkModel, SecurityKnowledgeDocumentModel)
            .join(
                SecurityKnowledgeDocumentModel,
                SecurityKnowledgeChunkModel.document_id
                == SecurityKnowledgeDocumentModel.id,
            )
            .where(
                or_(
                    SecurityKnowledgeChunkModel.organization_id.is_(None),
                    SecurityKnowledgeChunkModel.organization_id == organization_id,
                ),
                *doc_conditions,
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        scored_results: List[
            Tuple[SecurityKnowledgeChunkModel, SecurityKnowledgeDocumentModel, float]
        ] = []
        for chunk_model, doc_model in rows:
            if chunk_model.embedding:
                score = _cosine_similarity(query_embedding, chunk_model.embedding)
                if score >= min_similarity:
                    scored_results.append((chunk_model, doc_model, score))

        scored_results.sort(key=lambda x: x[2], reverse=True)
        return scored_results[:top_k]

    async def log_rag_search(self, log: RAGSearchLogModel) -> RAGSearchLogModel:
        """Persist RAG search query execution audit log."""
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
