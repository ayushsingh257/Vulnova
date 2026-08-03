"""Pydantic v2 DTO Schemas for Multi-Provider LLM Gateway, Prompt Orchestrator & AI Analysis Engine."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateProviderRequest(BaseModel):
    """Request model for configuring an LLM provider."""

    provider_type: str  # OPENAI, ANTHROPIC, GOOGLE, OLLAMA, CUSTOM
    name: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    priority: int = 10


class LLMProviderConfigDTO(BaseModel):
    """DTO representing a configured LLM provider (secrets masked)."""

    id: str
    provider_type: str
    name: str
    api_endpoint: Optional[str] = None
    priority: int
    is_active: bool
    is_healthy: bool
    consecutive_failures: int
    cooldown_until: Optional[str] = None
    created_at: str


class RegisterModelRequest(BaseModel):
    """Request model for registering a supported LLM model."""

    provider_type: str
    model_alias: str
    model_name: str
    context_window_tokens: int = 128000
    max_output_tokens: int = 4096
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    is_default: bool = False


class LLMModelDTO(BaseModel):
    """DTO representing a registered LLM model."""

    id: str
    provider_type: str
    model_alias: str
    model_name: str
    context_window_tokens: int
    max_output_tokens: int
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    is_default: bool
    created_at: str


class CreatePromptTemplateRequest(BaseModel):
    """Request model for creating an immutable versioned prompt template."""

    category: str  # FINDING_EXPLAINER, ATTACK_PATH_SYNTHESIS, REMEDIATION_PATCH, SYSTEM_PROMPT
    name: str
    system_prompt: str
    user_prompt_template: str


class PromptTemplateDTO(BaseModel):
    """DTO representing an immutable versioned prompt template."""

    id: str
    category: str
    name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    is_active: bool
    created_at: str


class LLMMessageDTO(BaseModel):
    """Message item for AI chat requests."""

    role: str
    content: str


class AIChatCompletionRequest(BaseModel):
    """Request model for AI chat completion execution."""

    messages: List[LLMMessageDTO]
    model_alias: Optional[str] = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2
    prompt_category: Optional[str] = None


class AIChatCompletionResponse(BaseModel):
    """Response model for AI chat completion execution."""

    content: str
    model_used: str
    provider_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    status: str


class AIUsageSummaryDTO(BaseModel):
    """DTO summarizing organizational token usage and cost analytics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


class LLMRequestLogDTO(BaseModel):
    """DTO representing a single historical AI request audit log."""

    id: str
    provider_type: str
    model_used: str
    prompt_category: Optional[str] = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    status: str
    error_message: Optional[str] = None
    created_at: str


# ── Phase 5.2: AI Finding Explainer & Impact Analysis DTOs ──


class GenerateExplanationRequest(BaseModel):
    """Request model for generating an AI finding explanation."""

    finding_id: str
    model_alias: Optional[str] = None
    temperature: float = 0.2


class AIFindingExplanationDTO(BaseModel):
    """DTO representing a generated AI finding explanation."""

    id: str
    finding_id: str
    vulnerability_summary: str
    technical_root_cause: str
    affected_asset_context: str
    exploitability_analysis: str
    business_impact: str
    attack_prerequisites: str
    severity_reasoning: str
    remediation_priority: str
    model_used: str
    provider_used: str
    prompt_version: int
    status: str
    created_at: str


class GenerateImpactAnalysisRequest(BaseModel):
    """Request model for generating an AI impact analysis."""

    finding_id: str
    model_alias: Optional[str] = None
    temperature: float = 0.2


class AIImpactAnalysisDTO(BaseModel):
    """DTO representing a generated AI impact analysis report."""

    id: str
    finding_id: str
    technical_impact_summary: str
    executive_impact_summary: str
    risk_justification: str
    affected_business_components: str
    cvss_interpretation: str
    epss_context: str
    exposure_assessment: str
    evidence_correlation: str
    model_used: str
    provider_used: str
    prompt_version: int
    status: str
    created_at: str


# ── Phase 5.3: AI Attack Path Synthesis DTOs ──


class GenerateAttackPathRequest(BaseModel):
    """Request payload for triggering AI attack path synthesis."""

    finding_id: str
    model_alias: Optional[str] = None
    temperature: float = 0.2


class ReviewAttackPathRequest(BaseModel):
    """Request payload for analyst review of a synthesized attack path."""

    status: str
    review_notes: Optional[str] = None


class AttackPathStepDTO(BaseModel):
    """DTO representing an individual step in an attack path chain."""

    id: str
    sequence_number: int
    step_type: str
    asset_node_id: Optional[str] = None
    finding_id: Optional[str] = None
    title: str
    description: str
    mitre_tactic: str
    mitre_technique_id: str
    mitre_technique_name: str
    attacker_action: str
    required_privilege: str
    evidence_reference: Optional[str] = None
    confidence_score: float = 1.0


class AIAttackPathDTO(BaseModel):
    """DTO representing a full AI-synthesized attack path with steps and review metadata."""

    id: str
    root_finding_id: str
    source_asset_id: Optional[str] = None
    target_asset_id: Optional[str] = None
    title: str
    attack_summary: str
    composite_risk_score: float
    confidence_score: float
    model_used: str
    provider_used: str
    prompt_version: int
    status: str
    steps: List[AttackPathStepDTO]
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


# ── Phase 5.4: AI Remediation Engine DTOs ──


class GenerateRemediationRequest(BaseModel):
    """Request payload for triggering AI remediation plan generation."""

    finding_id: str
    model_alias: Optional[str] = None
    temperature: float = 0.2


class ReviewRemediationPlanRequest(BaseModel):
    """Request payload for analyst review of a remediation plan."""

    status: str
    review_notes: Optional[str] = None


class AIPatchSuggestionDTO(BaseModel):
    """DTO representing a non-executable code or config patch suggestion."""

    id: str
    language: str
    file_type: str
    target_file_path: Optional[str] = None
    original_code_snippet: str
    proposed_patch_diff: str
    explanation: str
    security_impact_notes: str
    confidence_score: float = 1.0


class RemediationStepDTO(BaseModel):
    """DTO representing an individual step in a remediation plan."""

    id: str
    sequence_number: int
    step_type: str
    title: str
    description: str
    affected_component: str
    recommended_action: str
    validation_command: Optional[str] = None
    rollback_strategy: Optional[str] = None
    confidence_score: float = 1.0


class AIRemediationPlanDTO(BaseModel):
    """DTO representing a full AI-synthesized remediation plan."""

    id: str
    root_finding_id: str
    attack_path_id: Optional[str] = None
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    affected_version: Optional[str] = None
    fixed_version: Optional[str] = None
    title: str
    summary: str
    technical_solution: str
    business_solution: str
    risk_reduction_explanation: str
    validation_strategy: str
    composite_risk_score: float
    ai_confidence_score: float
    effectiveness_confidence_score: float
    requires_backup: bool
    requires_downtime: bool
    rollback_available: bool
    model_used: str
    provider_used: str
    prompt_version: int
    status: str
    steps: List[RemediationStepDTO]
    patch_suggestions: List[AIPatchSuggestionDTO]
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


# ── Phase 5.5: AI False Positive Filter & Confidence DTOs ──


class GenerateConfidenceAnalysisRequest(BaseModel):
    """Request payload for triggering AI confidence analysis."""

    finding_id: str
    model_alias: Optional[str] = None
    temperature: float = 0.2


class ReviewConfidenceAnalysisRequest(BaseModel):
    """Request payload for analyst review of confidence analysis."""

    status: str
    review_notes: Optional[str] = None


class AIFindingSimilarityMatchDTO(BaseModel):
    """DTO representing a duplicate or related finding similarity match."""

    id: str
    source_finding_id: str
    matched_finding_id: str
    similarity_score: float
    similarity_reason: str
    matched_signals: List[str]
    status: str
    created_at: str


class AIFindingConfidenceAnalysisDTO(BaseModel):
    """DTO representing a full AI confidence analysis assessment."""

    id: str
    finding_id: str
    classification: str
    confidence_score: float
    evidence_quality_score: float
    reasoning: str
    supporting_evidence: str
    contradicting_evidence: str
    missing_information: str
    validation_requirements: str
    recommendation: str
    composite_risk_score: float
    model_used: str
    provider_used: str
    prompt_version: int
    status: str
    similarity_matches: List[AIFindingSimilarityMatchDTO]
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    # Calibration feedback tracking metadata
    predicted_confidence_score: Optional[float] = None
    analyst_final_decision: Optional[str] = None
    confidence_accuracy_delta: Optional[float] = None
    feedback_timestamp: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str


# ── Phase 5.6: Security Knowledge Base & RAG Vector Engine DTOs ──


class IngestKnowledgeDocumentRequest(BaseModel):
    """Request payload for ingesting a security reference document or company policy."""

    title: str = Field(..., min_length=3, max_length=255)
    source_type: str = Field(
        ...,
        description="OWASP, CWE, CAPEC, CVE_NVD, VENDOR_ADVISORY, INTERNAL_POLICY, CUSTOM",
    )
    content_text: str = Field(
        ..., min_length=10, description="Full text content of document"
    )
    ingestion_source: str = Field("MANUAL_UPLOAD")
    external_ref_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    version: str = Field("1.0", max_length=50)
    chunk_size_tokens: Optional[int] = Field(None, ge=64, le=4096)
    chunk_overlap_tokens: Optional[int] = Field(None, ge=0, le=512)
    embedding_model: str = Field("text-embedding-3-small")
    source_url: Optional[str] = Field(None, max_length=500)
    source_author: Optional[str] = Field(None, max_length=255)
    published_date: Optional[str] = Field(None, max_length=50)
    last_updated_date: Optional[str] = Field(None, max_length=50)
    is_global: bool = Field(
        False,
        description="If True (and user is admin), document is global public benchmark",
    )
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ReviewKnowledgeDocumentRequest(BaseModel):
    """Request payload for analyst governance approval of a security knowledge document."""

    status: str = Field(..., description="APPROVED, REJECTED, ARCHIVED")
    review_notes: Optional[str] = Field(None, max_length=1000)


class KnowledgeChunkDTO(BaseModel):
    """DTO representing an individual text chunk with vector metadata & source citations."""

    id: str
    document_id: str
    chunk_index: int
    content_text: str
    token_count: int
    organization_id: Optional[str] = None
    embedding_model: str
    embedding_dimension: int
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class KnowledgeDocumentDTO(BaseModel):
    """DTO representing a security knowledge document master record."""

    id: str
    organization_id: Optional[str] = None
    source_type: str
    ingestion_source: str
    title: str
    external_ref_id: Optional[str] = None
    description: Optional[str] = None
    version: str
    status: str
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    chunk_count: int
    token_count: int
    embedding_model: str
    embedding_dimension: int
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    published_date: Optional[str] = None
    last_updated_date: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str
    updated_at: str


class RAGSearchRequest(BaseModel):
    """Request payload for executing semantic vector similarity search."""

    query: str = Field(..., min_length=2, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    min_similarity: float = Field(0.70, ge=0.0, le=1.0)
    source_type: Optional[str] = None


class RAGSearchResultDTO(BaseModel):
    """DTO representing a vector similarity search result with source attribution."""

    chunk_id: str
    document_id: str
    document_title: str
    source_type: str
    content_text: str
    similarity_score: float
    external_ref_id: Optional[str] = None
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGSearchResponse(BaseModel):
    """Response envelope for a RAG vector similarity search."""

    query: str
    results_count: int
    results: List[RAGSearchResultDTO]
    search_latency_ms: int


class FindingRAGContextRequest(BaseModel):
    """Request payload for generating tailored RAG context for a security finding."""

    top_k: int = Field(5, ge=1, le=10)
    min_similarity: float = Field(0.65, ge=0.0, le=1.0)


class FindingRAGContextResponse(BaseModel):
    """Response containing assembled RAG context block tailored for a finding."""

    finding_id: str
    formatted_context_block: str
    retrieved_chunks_count: int
    sources_cited: List[str]
