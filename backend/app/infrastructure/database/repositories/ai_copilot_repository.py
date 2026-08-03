"""Repository implementation for Phase 5.7 Enterprise AI Security Copilot."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.ai_copilot import (
    CopilotContextMemoryModel,
    CopilotFeedbackModel,
    CopilotMessageModel,
    CopilotSessionModel,
    CopilotToolExecutionModel,
)


class AICopilotRepository:
    """Repository managing Copilot session state, message history, context memory, tool execution logs, and analyst feedback."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self, session_model: CopilotSessionModel
    ) -> CopilotSessionModel:
        """Create a new multi-turn Copilot investigation session."""
        self.session.add(session_model)
        await self.session.flush()
        await self.session.refresh(session_model)
        return session_model

    async def get_session_by_id(
        self, organization_id: UUID, session_id: UUID
    ) -> Optional[CopilotSessionModel]:
        """Fetch session by ID with tenant boundary validation."""
        stmt = (
            select(CopilotSessionModel)
            .where(
                CopilotSessionModel.id == session_id,
                CopilotSessionModel.organization_id == organization_id,
            )
            .options(
                selectinload(CopilotSessionModel.messages),
                selectinload(CopilotSessionModel.context_memories),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_sessions_by_org(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[CopilotSessionModel], int]:
        """List sessions for an organization with pagination and filters."""
        stmt = select(CopilotSessionModel).where(
            CopilotSessionModel.organization_id == organization_id
        )
        if user_id:
            stmt = stmt.where(CopilotSessionModel.user_id == user_id)
        if status:
            stmt = stmt.where(CopilotSessionModel.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = (
            stmt.order_by(CopilotSessionModel.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def update_session(
        self,
        organization_id: UUID,
        session_id: UUID,
        title: Optional[str] = None,
        status: Optional[str] = None,
        focused_finding_id: Optional[UUID] = None,
        add_tokens: int = 0,
        increment_message_count: bool = False,
    ) -> Optional[CopilotSessionModel]:
        """Update session status, title, focus, or token metrics."""
        session_obj = await self.get_session_by_id(organization_id, session_id)
        if not session_obj:
            return None

        if title is not None:
            session_obj.title = title
        if status is not None:
            session_obj.status = status
        if focused_finding_id is not None:
            session_obj.focused_finding_id = focused_finding_id
        if add_tokens > 0:
            session_obj.total_tokens += add_tokens
        if increment_message_count:
            session_obj.message_count += 1

        session_obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return session_obj

    async def delete_session(self, organization_id: UUID, session_id: UUID) -> bool:
        """Delete session and cascading messages/context memory."""
        session_obj = await self.get_session_by_id(organization_id, session_id)
        if not session_obj:
            return False
        await self.session.delete(session_obj)
        await self.session.flush()
        return True

    # ── Message Operations ──

    async def create_message(
        self, message_model: CopilotMessageModel
    ) -> CopilotMessageModel:
        """Persist a chat message with grounding & explainability metadata."""
        self.session.add(message_model)
        await self.session.flush()
        await self.session.refresh(message_model)
        return message_model

    async def list_session_messages(
        self, organization_id: UUID, session_id: UUID, limit: int = 100
    ) -> List[CopilotMessageModel]:
        """List messages for a session ordered chronologically."""
        stmt = (
            select(CopilotMessageModel)
            .where(
                CopilotMessageModel.session_id == session_id,
                CopilotMessageModel.organization_id == organization_id,
            )
            .order_by(CopilotMessageModel.created_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ── Context Memory Operations ──

    async def upsert_context_memory(
        self,
        organization_id: UUID,
        session_id: UUID,
        memory_key: str,
        memory_value_json: Dict[str, Any],
        memory_type: str = "INVESTIGATION_STATE",
    ) -> CopilotContextMemoryModel:
        """Upsert a key-value context memory entry for an investigation session."""
        stmt = select(CopilotContextMemoryModel).where(
            CopilotContextMemoryModel.session_id == session_id,
            CopilotContextMemoryModel.organization_id == organization_id,
            CopilotContextMemoryModel.memory_key == memory_key,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.memory_value_json = memory_value_json
            existing.memory_type = memory_type
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        new_mem = CopilotContextMemoryModel(
            session_id=session_id,
            organization_id=organization_id,
            memory_key=memory_key,
            memory_value_json=memory_value_json,
            memory_type=memory_type,
        )
        self.session.add(new_mem)
        await self.session.flush()
        await self.session.refresh(new_mem)
        return new_mem

    async def get_context_memories_by_session(
        self, organization_id: UUID, session_id: UUID
    ) -> List[CopilotContextMemoryModel]:
        """Fetch all persistent context memory entries for a session."""
        stmt = select(CopilotContextMemoryModel).where(
            CopilotContextMemoryModel.session_id == session_id,
            CopilotContextMemoryModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # ── Tool Execution Audit Operations ──

    async def log_tool_execution(
        self, tool_execution: CopilotToolExecutionModel
    ) -> CopilotToolExecutionModel:
        """Record an audit log entry for an internal read-only tool invocation."""
        self.session.add(tool_execution)
        await self.session.flush()
        await self.session.refresh(tool_execution)
        return tool_execution

    # ── Analyst Feedback Operations ──

    async def create_feedback(
        self, feedback_model: CopilotFeedbackModel
    ) -> CopilotFeedbackModel:
        """Record SOC analyst rating and evaluation feedback on a copilot response."""
        self.session.add(feedback_model)
        await self.session.flush()
        await self.session.refresh(feedback_model)
        return feedback_model
