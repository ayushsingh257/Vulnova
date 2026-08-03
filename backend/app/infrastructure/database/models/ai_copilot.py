"""SQLAlchemy ORM Models for Phase 5.7 Enterprise AI Security Copilot & Interactive Assistant."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    BOOLEAN,
    FLOAT,
    INTEGER,
    TEXT,
    TIMESTAMP,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class CopilotSessionModel(Base):
    """ORM Model for AI Security Copilot multi-turn conversation sessions."""

    __tablename__ = "ai_copilot_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="New Security Investigation"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", index=True
    )
    focused_finding_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("security_findings.id", ondelete="SET NULL"), nullable=True
    )
    model_alias: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default"
    )
    temperature: Mapped[float] = mapped_column(FLOAT, nullable=False, default=0.2)
    total_tokens: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    message_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    messages: Mapped[List["CopilotMessageModel"]] = relationship(
        "CopilotMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CopilotMessageModel.created_at",
    )
    context_memories: Mapped[List["CopilotContextMemoryModel"]] = relationship(
        "CopilotContextMemoryModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class CopilotMessageModel(Base):
    """ORM Model for individual Copilot chat messages with AI response grounding & explainability metadata."""

    __tablename__ = "ai_copilot_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # USER, ASSISTANT, SYSTEM, TOOL
    content: Mapped[str] = mapped_column(TEXT, nullable=False)
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SECURITY_ANALYST"
    )
    token_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)

    # Grounding & Explainability Metadata
    response_confidence_score: Mapped[Optional[float]] = mapped_column(
        FLOAT, nullable=True
    )
    sources_used: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    knowledge_chunks_used: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    tools_called: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    reasoning_summary: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0"
    )
    response_evaluation_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    session: Mapped["CopilotSessionModel"] = relationship(
        "CopilotSessionModel", back_populates="messages"
    )


class CopilotContextMemoryModel(Base):
    """ORM Model for persistent investigation key-value context memory."""

    __tablename__ = "ai_copilot_context_memories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_key: Mapped[str] = mapped_column(String(100), nullable=False)
    memory_value_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    memory_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="INVESTIGATION_STATE"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    session: Mapped["CopilotSessionModel"] = relationship(
        "CopilotSessionModel", back_populates="context_memories"
    )


class CopilotToolExecutionModel(Base):
    """ORM Model for audit logging of internal read-only tool executions."""

    __tablename__ = "ai_copilot_tool_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("ai_copilot_messages.id", ondelete="SET NULL"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_params_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    output_summary_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    execution_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SUCCESS"
    )
    latency_ms: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class CopilotFeedbackModel(Base):
    """ORM Model for SOC analyst evaluation feedback on Copilot responses."""

    __tablename__ = "ai_copilot_feedback"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_copilot_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(INTEGER, nullable=False)  # 1 to 5
    is_helpful: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, default=True)
    feedback_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    feedback_notes: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# Composite Indexes for Multi-Tenant Query Optimization
Index(
    "idx_copilot_session_org_user",
    CopilotSessionModel.organization_id,
    CopilotSessionModel.user_id,
)
Index(
    "idx_copilot_msg_session_role",
    CopilotMessageModel.session_id,
    CopilotMessageModel.role,
)
Index(
    "idx_copilot_mem_session_key",
    CopilotContextMemoryModel.session_id,
    CopilotContextMemoryModel.memory_key,
)
