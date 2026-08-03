"""SQLAlchemy Database Models for Phase 5.6 Security Knowledge Base & RAG Vector Engine (pgvector)."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class SecurityKnowledgeDocumentModel(Base):
    """SQLAlchemy model representing a security reference document or internal organizational policy."""

    __tablename__ = "security_knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ingestion_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="MANUAL_UPLOAD"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    external_ref_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )
    chunk_size_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=512)
    chunk_overlap_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=64
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="text-embedding-3-small"
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1536
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_updated_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    chunks: Mapped[List["SecurityKnowledgeChunkModel"]] = relationship(
        "SecurityKnowledgeChunkModel",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_sec_doc_org_source", "organization_id", "source_type"),
        Index("idx_sec_doc_org_status", "organization_id", "status"),
    )


class SecurityKnowledgeChunkModel(Base):
    """SQLAlchemy detail model representing a text chunk with vector embedding & source citations."""

    __tablename__ = "security_knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSONB, nullable=True)
    embedding_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="text-embedding-3-small"
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1536
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    document: Mapped["SecurityKnowledgeDocumentModel"] = relationship(
        "SecurityKnowledgeDocumentModel", back_populates="chunks"
    )

    __table_args__ = (
        Index("idx_sec_chunk_doc_index", "document_id", "chunk_index"),
        Index("idx_sec_chunk_org", "organization_id"),
    )


class RAGSearchLogModel(Base):
    """SQLAlchemy audit model representing a RAG vector similarity search execution log."""

    __tablename__ = "rag_search_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    min_similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.70)
    results_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_chunk_ids: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    search_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieval_quality_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    average_similarity_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    analyst_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_rag_log_org_created", "organization_id", "created_at"),
    )
