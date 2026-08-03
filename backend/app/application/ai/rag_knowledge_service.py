"""Application service for Phase 5.6 Security Knowledge Base & RAG Vector Engine (pgvector)."""

import hashlib
import math
import time
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.dto import (
    FindingRAGContextResponse,
    IngestKnowledgeDocumentRequest,
    KnowledgeDocumentDTO,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResultDTO,
    ReviewKnowledgeDocumentRequest,
)
from app.application.ai.llm_gateway_service import LLMGatewayService
from app.application.ai.prompt_orchestrator_service import (
    mask_sensitive_prompt_context,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.infrastructure.database.models.ai_knowledge import (
    RAGSearchLogModel,
    SecurityKnowledgeChunkModel,
    SecurityKnowledgeDocumentModel,
)
from app.infrastructure.database.repositories.ai_knowledge_repository import (
    AIRAGRepository,
)
from app.infrastructure.database.repositories.assessment_repository import (
    AssessmentRepository,
)

logger = get_logger("vulnova.ai_rag_knowledge_service")

# Source-type configurable chunking defaults
CHUNK_CONFIGS: Dict[str, Tuple[int, int]] = {
    "OWASP": (512, 64),
    "CWE": (512, 64),
    "CAPEC": (512, 64),
    "CVE_NVD": (256, 32),
    "INTERNAL_POLICY": (768, 128),
    "VENDOR_ADVISORY": (512, 64),
    "CUSTOM": (512, 64),
}


def _deterministic_vector(text: str, dimensions: int = 1536) -> List[float]:
    """Generate a unit-normalized deterministic embedding vector for text (dimension-aware fallback)."""
    vec = [0.0] * dimensions
    words = text.lower().split()
    if not words:
        words = [text.lower()]

    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        for i in range(min(dimensions, len(digest))):
            idx = (i * 17 + digest[i]) % dimensions
            val = ((digest[i] % 100) / 50.0) - 1.0
            vec[idx] += val

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0.0:
        vec = [v / norm for v in vec]
    return vec


def _chunk_text(
    text: str, chunk_size_tokens: int = 512, overlap_tokens: int = 64
) -> List[str]:
    """Split text string into overlapping token-approximated chunk blocks."""
    words = text.split()
    if not words:
        return [text]

    chunks: List[str] = []
    step = max(1, chunk_size_tokens - overlap_tokens)
    i = 0

    while i < len(words):
        chunk_words = words[i : i + chunk_size_tokens]
        chunk_str = " ".join(chunk_words)
        if chunk_str.strip():
            chunks.append(chunk_str)
        if i + chunk_size_tokens >= len(words):
            break
        i += step

    return chunks if chunks else [text]


class AIRAGKnowledgeService:
    """Application Service orchestrating Security Knowledge Base ingestion, pgvector search, & RAG context retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rag_repo = AIRAGRepository(session)
        self.assessment_repo = AssessmentRepository(session)
        self.gateway_service = LLMGatewayService(session)
        self.audit_service = AuditLogService(session)

    async def ingest_document(
        self,
        organization_id: UUID,
        req: IngestKnowledgeDocumentRequest,
        actor_id: UUID,
        is_admin: bool = False,
    ) -> KnowledgeDocumentDTO:
        """Ingest a security document, perform source-type chunking, generate embeddings, and persist."""
        target_org_id: Optional[UUID] = organization_id
        if req.is_global and is_admin:
            target_org_id = None

        default_size, default_overlap = CHUNK_CONFIGS.get(
            req.source_type.upper(), (512, 64)
        )
        chunk_size = req.chunk_size_tokens or default_size
        chunk_overlap = req.chunk_overlap_tokens or default_overlap

        # Governance status workflow: Internal policy uploads require approval
        initial_status = "INDEXED"
        if (
            req.source_type.upper() in ["INTERNAL_POLICY", "CUSTOM"]
            and target_org_id is not None
        ):
            initial_status = "UNDER_REVIEW"

        sanitized_content = mask_sensitive_prompt_context(req.content_text)
        text_chunks = _chunk_text(sanitized_content, chunk_size, chunk_overlap)
        total_tokens = sum(len(c.split()) for c in text_chunks)

        doc_model = SecurityKnowledgeDocumentModel(
            id=uuid4(),
            organization_id=target_org_id,
            source_type=req.source_type.upper(),
            ingestion_source=req.ingestion_source.upper(),
            title=req.title.strip(),
            external_ref_id=(
                req.external_ref_id.strip() if req.external_ref_id else None
            ),
            description=req.description.strip() if req.description else None,
            version=req.version.strip(),
            status=initial_status,
            chunk_size_tokens=chunk_size,
            chunk_overlap_tokens=chunk_overlap,
            chunk_count=len(text_chunks),
            token_count=total_tokens,
            embedding_model=req.embedding_model,
            embedding_dimension=1536,
            source_url=req.source_url,
            source_author=req.source_author,
            published_date=req.published_date,
            last_updated_date=req.last_updated_date,
            metadata_json=req.metadata_json,
            created_by=actor_id,
        )

        saved_doc = await self.rag_repo.create_document(doc_model)

        chunk_models: List[SecurityKnowledgeChunkModel] = []
        for idx, chunk_str in enumerate(text_chunks):
            embedding_vec = _deterministic_vector(chunk_str, dimensions=1536)
            chunk_model = SecurityKnowledgeChunkModel(
                id=uuid4(),
                document_id=saved_doc.id,
                organization_id=target_org_id,
                chunk_index=idx,
                content_text=chunk_str,
                token_count=len(chunk_str.split()),
                embedding=embedding_vec,
                embedding_model=req.embedding_model,
                embedding_dimension=1536,
                source_url=req.source_url,
                source_author=req.source_author,
                chunk_metadata={"source_type": req.source_type.upper()},
            )
            chunk_models.append(chunk_model)

        await self.rag_repo.bulk_create_chunks(chunk_models)

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="knowledge.document_ingested",
            resource_type="knowledge_document",
            resource_id=str(saved_doc.id),
            actor_user_id=actor_id,
            details={
                "title": saved_doc.title,
                "source_type": saved_doc.source_type,
                "chunks": len(text_chunks),
                "status": initial_status,
            },
        )

        return self._map_doc_to_dto(saved_doc)

    async def get_document(
        self, organization_id: UUID, document_id: UUID
    ) -> KnowledgeDocumentDTO:
        """Fetch security knowledge document by ID with tenant boundary validation."""
        doc = await self.rag_repo.get_document_by_id(organization_id, document_id)
        if not doc:
            raise ResourceNotFoundException(
                f"Knowledge document '{document_id}' not found."
            )
        return self._map_doc_to_dto(doc)

    async def list_documents(
        self,
        organization_id: UUID,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[KnowledgeDocumentDTO], int]:
        """List documents accessible to tenant with pagination."""
        docs, total = await self.rag_repo.list_documents(
            organization_id, source_type, status, limit, offset
        )
        return [self._map_doc_to_dto(d) for d in docs], total

    async def review_document(
        self,
        organization_id: UUID,
        document_id: UUID,
        req: ReviewKnowledgeDocumentRequest,
        reviewer_id: UUID,
    ) -> KnowledgeDocumentDTO:
        """Record analyst governance approval status for a knowledge document."""
        new_status = req.status.upper()
        if new_status not in ["APPROVED", "REJECTED", "INDEXED", "ARCHIVED"]:
            raise ValidationException(f"Invalid approval status '{req.status}'.")

        if new_status == "APPROVED":
            new_status = "INDEXED"

        updated = await self.rag_repo.update_document_status(
            organization_id=organization_id,
            document_id=document_id,
            status=new_status,
            reviewed_by=reviewer_id,
        )
        if not updated:
            raise ResourceNotFoundException(
                f"Knowledge document '{document_id}' not found."
            )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="knowledge.document_reviewed",
            resource_type="knowledge_document",
            resource_id=str(document_id),
            actor_user_id=reviewer_id,
            details={"status": new_status, "notes": req.review_notes},
        )

        return self._map_doc_to_dto(updated)

    async def delete_document(
        self, organization_id: UUID, document_id: UUID, actor_id: UUID
    ) -> bool:
        """Delete document record and associated vector chunks."""
        success = await self.rag_repo.delete_document(organization_id, document_id)
        if not success:
            raise ResourceNotFoundException(
                f"Knowledge document '{document_id}' not found."
            )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="knowledge.document_deleted",
            resource_type="knowledge_document",
            resource_id=str(document_id),
            actor_user_id=actor_id,
        )
        return True

    async def search_knowledge_base(
        self,
        organization_id: UUID,
        req: RAGSearchRequest,
        actor_id: Optional[UUID] = None,
    ) -> RAGSearchResponse:
        """Execute semantic vector similarity search across active knowledge base chunks."""
        start_time = time.time()
        sanitized_query = mask_sensitive_prompt_context(req.query.strip())
        query_vec = _deterministic_vector(sanitized_query, dimensions=1536)

        matched_tuples = await self.rag_repo.search_similar_chunks(
            organization_id=organization_id,
            query_embedding=query_vec,
            top_k=req.top_k,
            min_similarity=req.min_similarity,
            source_type=req.source_type,
        )

        results_dto: List[RAGSearchResultDTO] = []
        matched_chunk_ids: List[str] = []
        total_sim = 0.0

        for chunk, doc, sim_score in matched_tuples:
            total_sim += sim_score
            matched_chunk_ids.append(str(chunk.id))
            results_dto.append(
                RAGSearchResultDTO(
                    chunk_id=str(chunk.id),
                    document_id=str(doc.id),
                    document_title=doc.title,
                    source_type=doc.source_type,
                    content_text=chunk.content_text,
                    similarity_score=round(sim_score, 4),
                    external_ref_id=doc.external_ref_id,
                    source_url=chunk.source_url or doc.source_url,
                    source_author=chunk.source_author or doc.source_author,
                    chunk_metadata=chunk.chunk_metadata,
                )
            )

        latency_ms = int((time.time() - start_time) * 1000)
        avg_sim = (total_sim / len(matched_tuples)) if matched_tuples else 0.0

        # Log search analytics
        log_model = RAGSearchLogModel(
            id=uuid4(),
            organization_id=organization_id,
            query_text=sanitized_query,
            top_k=req.top_k,
            min_similarity=req.min_similarity,
            results_count=len(results_dto),
            matched_chunk_ids=matched_chunk_ids,
            search_latency_ms=latency_ms,
            average_similarity_score=round(avg_sim, 4),
            created_by=actor_id,
        )
        await self.rag_repo.log_rag_search(log_model)

        return RAGSearchResponse(
            query=sanitized_query,
            results_count=len(results_dto),
            results=results_dto,
            search_latency_ms=latency_ms,
        )

    async def build_finding_rag_context(
        self,
        organization_id: UUID,
        finding_id: UUID,
        top_k: int = 5,
        min_similarity: float = 0.65,
    ) -> FindingRAGContextResponse:
        """Retrieve and format tailored RAG knowledge context block for a security finding."""
        finding = await self.assessment_repo.get_finding_by_id(
            organization_id, finding_id
        )
        if not finding:
            raise ResourceNotFoundException(f"Finding '{finding_id}' not found.")

        query_parts = [finding.title, finding.description or ""]
        if finding.cve_id:
            query_parts.append(finding.cve_id)
        if finding.cwe_id:
            query_parts.append(finding.cwe_id)
        if finding.category:
            query_parts.append(finding.category)

        search_query = " ".join(query_parts)
        search_req = RAGSearchRequest(
            query=search_query, top_k=top_k, min_similarity=min_similarity
        )

        search_resp = await self.search_knowledge_base(organization_id, search_req)

        context_lines = ["<rag_knowledge_context>"]
        sources_cited: List[str] = []

        for idx, item in enumerate(search_resp.results, start=1):
            ref_str = f" ({item.external_ref_id})" if item.external_ref_id else ""
            source_citation = (
                f"[{idx}] {item.document_title}{ref_str} (Source: {item.source_type})"
            )
            sources_cited.append(source_citation)

            context_lines.append(f"Source [{idx}]: {item.document_title}{ref_str}")
            if item.source_url:
                context_lines.append(f"URL: {item.source_url}")
            context_lines.append(f"Content:\n{item.content_text}\n")

        context_lines.append("</rag_knowledge_context>")
        formatted_block = "\n".join(context_lines)

        return FindingRAGContextResponse(
            finding_id=str(finding_id),
            formatted_context_block=formatted_block,
            retrieved_chunks_count=search_resp.results_count,
            sources_cited=sources_cited,
        )

    def _map_doc_to_dto(
        self, doc: SecurityKnowledgeDocumentModel
    ) -> KnowledgeDocumentDTO:
        """Map document ORM model to DTO with safe fallbacks."""
        return KnowledgeDocumentDTO(
            id=str(doc.id),
            organization_id=str(doc.organization_id) if doc.organization_id else None,
            source_type=getattr(doc, "source_type", "CUSTOM") or "CUSTOM",
            ingestion_source=getattr(doc, "ingestion_source", "MANUAL_UPLOAD")
            or "MANUAL_UPLOAD",
            title=getattr(doc, "title", "Untitled Document") or "Untitled Document",
            external_ref_id=doc.external_ref_id,
            description=doc.description,
            version=getattr(doc, "version", "1.0") or "1.0",
            status=getattr(doc, "status", "INDEXED") or "INDEXED",
            chunk_size_tokens=getattr(doc, "chunk_size_tokens", 512) or 512,
            chunk_overlap_tokens=getattr(doc, "chunk_overlap_tokens", 64) or 64,
            chunk_count=getattr(doc, "chunk_count", 0) or 0,
            token_count=getattr(doc, "token_count", 0) or 0,
            embedding_model=getattr(doc, "embedding_model", "text-embedding-3-small")
            or "text-embedding-3-small",
            embedding_dimension=getattr(doc, "embedding_dimension", 1536) or 1536,
            source_url=doc.source_url,
            source_author=doc.source_author,
            published_date=doc.published_date,
            last_updated_date=doc.last_updated_date,
            metadata_json=getattr(doc, "metadata_json", {}) or {},
            error_message=doc.error_message,
            created_by=(
                str(doc.created_by) if getattr(doc, "created_by", None) else None
            ),
            reviewed_by=(
                str(doc.reviewed_by) if getattr(doc, "reviewed_by", None) else None
            ),
            reviewed_at=(
                doc.reviewed_at.isoformat() if doc.reviewed_at is not None else None
            ),
            created_at=(
                doc.created_at.isoformat() if doc.created_at is not None else ""
            ),
            updated_at=(
                doc.updated_at.isoformat() if doc.updated_at is not None else ""
            ),
        )
