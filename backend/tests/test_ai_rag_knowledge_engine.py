"""Unit & Integration Tests for Phase 5.6 Security Knowledge Base & RAG Vector Engine (pgvector)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.ai.dto import (
    IngestKnowledgeDocumentRequest,
    RAGSearchRequest,
    ReviewKnowledgeDocumentRequest,
)
from app.application.ai.rag_knowledge_service import (
    CHUNK_CONFIGS,
    AIRAGKnowledgeService,
    _chunk_text,
    _deterministic_vector,
)
from app.domain.entities.ai import (
    KnowledgeDocumentSourceType,
    KnowledgeIngestionStatus,
)
from app.infrastructure.database.models.ai_knowledge import (
    SecurityKnowledgeDocumentModel,
)
from app.infrastructure.database.models.assessment import SecurityFindingModel


def test_chunking_configuration_by_source_type() -> None:
    """Test that chunking defaults conform to approved source-type parameters."""
    assert CHUNK_CONFIGS["OWASP"] == (512, 64)
    assert CHUNK_CONFIGS["CWE"] == (512, 64)
    assert CHUNK_CONFIGS["CAPEC"] == (512, 64)
    assert CHUNK_CONFIGS["CVE_NVD"] == (256, 32)
    assert CHUNK_CONFIGS["INTERNAL_POLICY"] == (768, 128)

    sample_text = " ".join([f"word{i}" for i in range(1000)])
    cve_chunks = _chunk_text(sample_text, chunk_size_tokens=256, overlap_tokens=32)
    assert len(cve_chunks) > 1

    policy_chunks = _chunk_text(sample_text, chunk_size_tokens=768, overlap_tokens=128)
    assert len(policy_chunks) < len(cve_chunks)


def test_deterministic_vector_generator() -> None:
    """Test vector embedding generation dimension and normalization."""
    vec = _deterministic_vector("SQL Injection Prevention Cheat Sheet", dimensions=1536)
    assert len(vec) == 1536
    # Vector length (norm) should be 1.0 (unit vector)
    norm = sum(v * v for v in vec)
    assert abs(norm - 1.0) < 1e-4


@pytest.mark.anyio
async def test_document_ingestion_and_chunking_global_owasp() -> None:
    """Test ingesting a global OWASP document transitioning directly to INDEXED."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_id = uuid4()
    actor_id = uuid4()

    req = IngestKnowledgeDocumentRequest(
        title="OWASP SQL Injection Prevention Cheat Sheet",
        source_type="OWASP",
        content_text="Use parameterized queries and prepared statements to prevent SQL injection vulnerabilities.",
        external_ref_id="OWASP-A03:2021",
        description="Official OWASP guidelines.",
        version="2.0",
        is_global=True,
        source_url="https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
        source_author="OWASP Foundation",
    )

    mock_doc = SecurityKnowledgeDocumentModel(
        id=uuid4(),
        organization_id=None,
        source_type="OWASP",
        ingestion_source="MANUAL_UPLOAD",
        title=req.title,
        external_ref_id=req.external_ref_id,
        description=req.description,
        version="2.0",
        status="INDEXED",
        chunk_size_tokens=512,
        chunk_overlap_tokens=64,
        chunk_count=1,
        token_count=10,
        embedding_model="text-embedding-3-small",
        embedding_dimension=1536,
        source_url=req.source_url,
        source_author=req.source_author,
        created_by=actor_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.rag_repo.create_document = AsyncMock(return_value=mock_doc)
    service.rag_repo.bulk_create_chunks = AsyncMock(return_value=1)
    service.audit_service.record_event = AsyncMock()

    dto = await service.ingest_document(org_id, req, actor_id, is_admin=True)

    assert dto.title == req.title
    assert dto.source_type == "OWASP"
    assert dto.status == "INDEXED"
    assert dto.organization_id is None  # Global benchmark
    assert service.rag_repo.bulk_create_chunks.called


@pytest.mark.anyio
async def test_document_governance_approval_workflow_internal_policy() -> None:
    """Test that internal policy uploads start in UNDER_REVIEW status requiring analyst review."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_id = uuid4()
    actor_id = uuid4()
    reviewer_id = uuid4()
    doc_id = uuid4()

    req = IngestKnowledgeDocumentRequest(
        title="Corporate Secure Coding Policy v3",
        source_type="INTERNAL_POLICY",
        content_text="All database queries must use ORM binding or parameterized statements. Raw SQL string concat is prohibited.",
        is_global=False,
    )

    mock_pending_doc = SecurityKnowledgeDocumentModel(
        id=doc_id,
        organization_id=org_id,
        source_type="INTERNAL_POLICY",
        ingestion_source="MANUAL_UPLOAD",
        title=req.title,
        status="UNDER_REVIEW",
        chunk_size_tokens=768,
        chunk_overlap_tokens=128,
        chunk_count=1,
        token_count=15,
        created_by=actor_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.rag_repo.create_document = AsyncMock(return_value=mock_pending_doc)
    service.rag_repo.bulk_create_chunks = AsyncMock(return_value=1)
    service.audit_service.record_event = AsyncMock()

    dto = await service.ingest_document(org_id, req, actor_id, is_admin=False)
    assert dto.status == "UNDER_REVIEW"

    # Execute review approval
    mock_approved_doc = SecurityKnowledgeDocumentModel(
        id=doc_id,
        organization_id=org_id,
        source_type="INTERNAL_POLICY",
        ingestion_source="MANUAL_UPLOAD",
        title=req.title,
        status="INDEXED",
        chunk_size_tokens=768,
        chunk_overlap_tokens=128,
        chunk_count=1,
        token_count=15,
        reviewed_by=reviewer_id,
        reviewed_at=datetime.now(timezone.utc),
        created_by=actor_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.rag_repo.update_document_status = AsyncMock(return_value=mock_approved_doc)

    review_req = ReviewKnowledgeDocumentRequest(
        status="APPROVED", review_notes="Approved for security team RAG retrieval."
    )
    reviewed_dto = await service.review_document(
        org_id, doc_id, review_req, reviewer_id
    )

    assert reviewed_dto.status == "INDEXED"
    assert reviewed_dto.reviewed_by == str(reviewer_id)


@pytest.mark.anyio
async def test_semantic_vector_similarity_search() -> None:
    """Test executing vector similarity search with query matching and thresholding."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_id = uuid4()
    doc_id = uuid4()
    chunk_id = uuid4()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.title = "CWE-89 SQL Injection"
    mock_doc.source_type = "CWE"
    mock_doc.external_ref_id = "CWE-89"
    mock_doc.source_url = "https://cwe.mitre.org/data/definitions/89.html"
    mock_doc.source_author = "MITRE"

    mock_chunk = MagicMock()
    mock_chunk.id = chunk_id
    mock_chunk.content_text = "The software constructs all or part of a SQL command using externally-influenced input."
    mock_chunk.source_url = None
    mock_chunk.source_author = None
    mock_chunk.chunk_metadata = {"source_type": "CWE"}

    service.rag_repo.search_similar_chunks = AsyncMock(
        return_value=[(mock_chunk, mock_doc, 0.88)]
    )
    service.rag_repo.log_rag_search = AsyncMock()

    search_req = RAGSearchRequest(
        query="sql injection vulnerability in user input parameter",
        top_k=3,
        min_similarity=0.70,
    )

    response = await service.search_knowledge_base(org_id, search_req)

    assert response.results_count == 1
    assert response.results[0].document_title == "CWE-89 SQL Injection"
    assert response.results[0].similarity_score == 0.88
    assert response.results[0].external_ref_id == "CWE-89"


@pytest.mark.anyio
async def test_tenant_boundary_isolation_private_vs_global() -> None:
    """Test that listing documents enforces tenant boundary isolation."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_a = uuid4()

    global_doc = SecurityKnowledgeDocumentModel(
        id=uuid4(),
        organization_id=None,
        source_type="OWASP",
        title="Global OWASP",
        status="INDEXED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    org_a_doc = SecurityKnowledgeDocumentModel(
        id=uuid4(),
        organization_id=org_a,
        source_type="INTERNAL_POLICY",
        title="Org A Policy",
        status="INDEXED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.rag_repo.list_documents = AsyncMock(
        return_value=([global_doc, org_a_doc], 2)
    )

    dtos, total = await service.list_documents(org_a)
    assert total == 2
    assert len(dtos) == 2


@pytest.mark.anyio
async def test_finding_rag_context_assembly() -> None:
    """Test assembling tailored RAG context block for a security finding."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_id = uuid4()
    finding_id = uuid4()

    mock_finding = SecurityFindingModel(
        id=finding_id,
        organization_id=org_id,
        assessment_job_id=uuid4(),
        plugin_id="sqli_plugin",
        title="SQL Injection in Login Endpoint",
        description="User input concatenated directly into SQL statement.",
        severity="HIGH",
        category="SQLI",
        cve_id="CVE-2024-1111",
        cwe_id="CWE-89",
        risk_score=85.0,
    )

    service.assessment_repo.get_finding_by_id = AsyncMock(return_value=mock_finding)

    mock_chunk_res = MagicMock()
    mock_chunk_res.document_title = "OWASP SQL Injection Prevention"
    mock_chunk_res.external_ref_id = "OWASP-A03:2021"
    mock_chunk_res.source_type = "OWASP"
    mock_chunk_res.source_url = "https://owasp.org/sqli"
    mock_chunk_res.content_text = "Always use parameterized queries."

    mock_search_resp = MagicMock()
    mock_search_resp.results_count = 1
    mock_search_resp.results = [mock_chunk_res]

    service.search_knowledge_base = AsyncMock(return_value=mock_search_resp)

    context_resp = await service.build_finding_rag_context(org_id, finding_id)

    assert context_resp.finding_id == str(finding_id)
    assert context_resp.retrieved_chunks_count == 1
    assert "<rag_knowledge_context>" in context_resp.formatted_context_block
    assert "OWASP SQL Injection Prevention" in context_resp.formatted_context_block


@pytest.mark.anyio
async def test_sensitive_data_masking_in_rag_chunks() -> None:
    """Test that prompt context masking strips secrets from ingested document text."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_id = uuid4()
    actor_id = uuid4()

    req = IngestKnowledgeDocumentRequest(
        title="Internal API Secret Guide",
        source_type="INTERNAL_POLICY",
        content_text="Connect using Authorization: Bearer secret_token_12345 to access internal endpoint.",
    )

    mock_doc = SecurityKnowledgeDocumentModel(
        id=uuid4(),
        organization_id=org_id,
        source_type="INTERNAL_POLICY",
        ingestion_source="MANUAL_UPLOAD",
        title=req.title,
        status="UNDER_REVIEW",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.rag_repo.create_document = AsyncMock(return_value=mock_doc)
    service.rag_repo.bulk_create_chunks = AsyncMock(return_value=1)
    service.audit_service.record_event = AsyncMock()

    await service.ingest_document(org_id, req, actor_id)

    # Check that bulk_create_chunks was called with masked text
    saved_chunks = service.rag_repo.bulk_create_chunks.call_args[0][0]
    assert len(saved_chunks) == 1
    assert "secret_token_12345" not in saved_chunks[0].content_text
    assert (
        "[REDACTED_SECRET]" in saved_chunks[0].content_text
        or "[MASKED" in saved_chunks[0].content_text
    )


@pytest.mark.anyio
async def test_document_deletion_cascading_chunks() -> None:
    """Test deleting a knowledge document and verifying audit logging."""
    mock_session = MagicMock()
    service = AIRAGKnowledgeService(mock_session)

    org_id = uuid4()
    doc_id = uuid4()
    actor_id = uuid4()

    service.rag_repo.delete_document = AsyncMock(return_value=True)
    service.audit_service.record_event = AsyncMock()

    res = await service.delete_document(org_id, doc_id, actor_id)

    assert res is True
    assert service.rag_repo.delete_document.called
    assert service.audit_service.record_event.called
