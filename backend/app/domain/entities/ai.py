"""Pure Domain Entities & Enums for Multi-Provider LLM Gateway, Prompt Orchestrator & AI Analysis Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    OLLAMA = "OLLAMA"
    CUSTOM = "CUSTOM"


class AIModelCapability(str, Enum):
    """Capabilities supported by LLM models."""

    CHAT = "CHAT"
    COMPLETION = "COMPLETION"
    EMBEDDING = "EMBEDDING"
    VISION = "VISION"
    CODE_GEN = "CODE_GEN"


class PromptCategory(str, Enum):
    """Categories of versioned security prompt templates."""

    FINDING_EXPLAINER = "FINDING_EXPLAINER"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    ATTACK_PATH_SYNTHESIS = "ATTACK_PATH_SYNTHESIS"
    REMEDIATION_PATCH = "REMEDIATION_PATCH"
    SYSTEM_PROMPT = "SYSTEM_PROMPT"
    CUSTOM = "CUSTOM"


class AIRequestState(str, Enum):
    """Lifecycle execution status of an AI gateway request."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FALLBACK_TRIGGERED = "FALLBACK_TRIGGERED"


@dataclass
class LLMMessage:
    """Standardized chat message payload."""

    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMRequest:
    """Standardized gateway request to an LLM provider."""

    messages: List[LLMMessage]
    model_alias: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2
    prompt_category: Optional[PromptCategory] = None
    stream: bool = False


@dataclass
class LLMResponse:
    """Standardized gateway response payload from an LLM provider."""

    content: str
    model_used: str
    provider_type: LLMProviderType
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    status: AIRequestState = AIRequestState.COMPLETED
    error_message: Optional[str] = None


@dataclass
class ProviderHealthState:
    """Track provider health, failures, and cooldown periods."""

    provider_id: UUID
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None


@dataclass
class LLMProvider:
    """Domain entity representing a configured LLM provider."""

    organization_id: UUID
    provider_type: LLMProviderType
    name: str
    id: UUID = field(default_factory=uuid4)
    api_endpoint: Optional[str] = None
    encrypted_api_key: Optional[str] = None
    priority: int = 10
    is_active: bool = True
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_failure_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LLMModel:
    """Domain entity representing a registered model and pricing metadata."""

    organization_id: UUID
    provider_type: LLMProviderType
    model_alias: str
    model_name: str
    id: UUID = field(default_factory=uuid4)
    context_window_tokens: int = 128000
    max_output_tokens: int = 4096
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PromptTemplate:
    """Domain entity representing an immutable versioned security prompt template."""

    organization_id: UUID
    category: PromptCategory
    name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class AIAnalysisStatus(str, Enum):
    """Lifecycle status of an AI-generated analysis record."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STALE = "STALE"


@dataclass
class AIFindingExplanation:
    """Domain entity representing an AI-generated finding explanation with persistent identity."""

    organization_id: UUID
    finding_id: UUID
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
    prompt_version: int = 1
    id: UUID = field(default_factory=uuid4)
    status: AIAnalysisStatus = AIAnalysisStatus.COMPLETED
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AIImpactAnalysis:
    """Domain entity representing an AI-generated impact analysis report with persistent identity."""

    organization_id: UUID
    finding_id: UUID
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
    prompt_version: int = 1
    id: UUID = field(default_factory=uuid4)
    status: AIAnalysisStatus = AIAnalysisStatus.COMPLETED
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Phase 5.3: AI Attack Path Synthesis Domain Entities ──


class AttackPathStatus(str, Enum):
    """Lifecycle status of an AI-synthesized attack path."""

    GENERATED = "GENERATED"
    REVIEWED = "REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    FAILED = "FAILED"


class AttackStepType(str, Enum):
    """Classification of individual steps in an attack chain aligned with MITRE ATT&CK tactics."""

    INITIAL_ACCESS = "INITIAL_ACCESS"
    EXECUTION = "EXECUTION"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    LATERAL_MOVEMENT = "LATERAL_MOVEMENT"
    IMPACT = "IMPACT"


KNOWN_MITRE_TECHNIQUES = {
    "T1190": "Exploit Public-Facing Application",
    "T1059": "Command and Scripting Interpreter",
    "T1068": "Exploitation for Privilege Escalation",
    "T1078": "Valid Accounts",
    "T1021": "Remote Services",
    "T1555": "Credentials from Password Stores",
    "T1003": "OS Credential Dumping",
    "T1210": "Exploitation of Remote Services",
    "T1083": "File and Directory Discovery",
    "T1499": "Endpoint Denial of Service",
    "T1110": "Brute Force",
    "T1566": "Phishing",
    "T1134": "Access Token Manipulation",
    "T1046": "Network Service Discovery",
}


@dataclass
class AttackPathStep:
    """Domain entity representing a single evidence-grounded step in an attack chain."""

    sequence_number: int
    step_type: AttackStepType
    title: str
    description: str
    mitre_tactic: str
    mitre_technique_id: str
    mitre_technique_name: str
    attacker_action: str
    required_privilege: str
    id: UUID = field(default_factory=uuid4)
    attack_path_id: Optional[UUID] = None
    asset_node_id: Optional[UUID] = None
    finding_id: Optional[UUID] = None
    evidence_reference: Optional[str] = None
    confidence_score: float = 1.0


@dataclass
class AttackPath:
    """Domain entity representing a full AI-synthesized attack path with persistent identity."""

    organization_id: UUID
    root_finding_id: UUID
    title: str
    attack_summary: str
    composite_risk_score: float
    model_used: str
    provider_used: str
    confidence_score: float = 1.0
    prompt_version: int = 1
    id: UUID = field(default_factory=uuid4)
    source_asset_id: Optional[UUID] = None
    target_asset_id: Optional[UUID] = None
    status: AttackPathStatus = AttackPathStatus.GENERATED
    steps: List[AttackPathStep] = field(default_factory=list)
    review_notes: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Phase 5.4: AI Remediation Engine Domain Entities ──


class RemediationStatus(str, Enum):
    """Lifecycle status of an AI-synthesized remediation plan."""

    GENERATED = "GENERATED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    FAILED = "FAILED"


class RemediationType(str, Enum):
    """Classification of remediation action types."""

    CODE_PATCH = "CODE_PATCH"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    DEPENDENCY_UPDATE = "DEPENDENCY_UPDATE"
    ARCHITECTURE_CHANGE = "ARCHITECTURE_CHANGE"
    SECURITY_CONTROL = "SECURITY_CONTROL"
    MANUAL_PROCESS = "MANUAL_PROCESS"


@dataclass
class AIPatchSuggestion:
    """Domain entity representing a suggested code or configuration patch diff."""

    language: str
    file_type: str
    original_code_snippet: str
    proposed_patch_diff: str
    explanation: str
    security_impact_notes: str
    id: UUID = field(default_factory=uuid4)
    remediation_plan_id: Optional[UUID] = None
    target_file_path: Optional[str] = None
    confidence_score: float = 1.0


@dataclass
class AIRemediationStep:
    """Domain entity representing an individual step within a remediation plan."""

    sequence_number: int
    step_type: RemediationType
    title: str
    description: str
    affected_component: str
    recommended_action: str
    id: UUID = field(default_factory=uuid4)
    remediation_plan_id: Optional[UUID] = None
    validation_command: Optional[str] = None
    rollback_strategy: Optional[str] = None
    confidence_score: float = 1.0


@dataclass
class AIRemediationPlan:
    """Domain entity representing a full AI-synthesized remediation plan with persistent identity."""

    organization_id: UUID
    root_finding_id: UUID
    title: str
    summary: str
    technical_solution: str
    business_solution: str
    risk_reduction_explanation: str
    validation_strategy: str
    composite_risk_score: float
    model_used: str
    provider_used: str
    ai_confidence_score: float = 1.0
    effectiveness_confidence_score: float = 1.0
    requires_backup: bool = False
    requires_downtime: bool = False
    rollback_available: bool = True
    prompt_version: int = 1
    id: UUID = field(default_factory=uuid4)
    attack_path_id: Optional[UUID] = None
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    affected_version: Optional[str] = None
    fixed_version: Optional[str] = None
    status: RemediationStatus = RemediationStatus.GENERATED
    steps: List[AIRemediationStep] = field(default_factory=list)
    patch_suggestions: List[AIPatchSuggestion] = field(default_factory=list)
    review_notes: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Phase 5.5: AI False Positive Filter & Finding Confidence Domain Entities ──


class FindingConfidenceClassification(str, Enum):
    """Classification rating of vulnerability finding authenticity."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class AIConfidenceStatus(str, Enum):
    """Lifecycle status of an AI confidence analysis or similarity match."""

    GENERATED = "GENERATED"
    REVIEWED = "REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    FAILED = "FAILED"


class SimilaritySignalType(str, Enum):
    """Signals used for multi-vector duplicate finding similarity correlation."""

    CVE = "CVE"
    CWE = "CWE"
    ENDPOINT = "ENDPOINT"
    ASSET_NODE = "ASSET_NODE"
    PLUGIN_ID = "PLUGIN_ID"
    VULNERABILITY_TITLE = "VULNERABILITY_TITLE"
    AFFECTED_COMPONENT = "AFFECTED_COMPONENT"
    ATTACK_TECHNIQUE = "ATTACK_TECHNIQUE"


@dataclass
class AIFindingSimilarityMatch:
    """Domain entity representing a duplicate or related finding match across multiple correlation signals."""

    organization_id: UUID
    source_finding_id: UUID
    matched_finding_id: UUID
    similarity_score: float
    similarity_reason: str
    matched_signals: List[SimilaritySignalType] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    status: AIConfidenceStatus = AIConfidenceStatus.GENERATED
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AIFindingConfidenceAnalysis:
    """Domain entity representing an AI confidence assessment with calibration metadata and persistent identity."""

    organization_id: UUID
    finding_id: UUID
    classification: FindingConfidenceClassification
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
    prompt_version: int = 1
    id: UUID = field(default_factory=uuid4)
    status: AIConfidenceStatus = AIConfidenceStatus.GENERATED
    similarity_matches: List[AIFindingSimilarityMatch] = field(default_factory=list)
    review_notes: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    # ── AI Confidence Score Calibration Metadata ──
    predicted_confidence_score: Optional[float] = None
    analyst_final_decision: Optional[str] = None
    confidence_accuracy_delta: Optional[float] = None
    feedback_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Phase 5.6 Domain Entities: RAG Knowledge Engine & Vector Store ──


class KnowledgeDocumentSourceType(str, Enum):
    """Source taxonomy of security reference documents."""

    OWASP = "OWASP"
    CWE = "CWE"
    CAPEC = "CAPEC"
    CVE_NVD = "CVE_NVD"
    VENDOR_ADVISORY = "VENDOR_ADVISORY"
    INTERNAL_POLICY = "INTERNAL_POLICY"
    CUSTOM = "CUSTOM"


class KnowledgeIngestionStatus(str, Enum):
    """Lifecycle and governance approval status of security knowledge documents."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    INDEXED = "INDEXED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class IngestionSource(str, Enum):
    """Provenance tracking for security document ingestion origins."""

    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    API_IMPORT = "API_IMPORT"
    NVD_SYNC = "NVD_SYNC"
    OWASP_SYNC = "OWASP_SYNC"
    VENDOR_FEED = "VENDOR_FEED"
    INTERNAL_SYNC = "INTERNAL_SYNC"


class VectorIndexType(str, Enum):
    """Supported pgvector indexing algorithms."""

    HNSW = "HNSW"
    IVFFLAT = "IVFFLAT"


@dataclass
class SecurityKnowledgeDocument:
    """Domain entity representing a security reference document or internal organizational policy."""

    title: str
    source_type: KnowledgeDocumentSourceType
    ingestion_source: IngestionSource = IngestionSource.MANUAL_UPLOAD
    organization_id: Optional[UUID] = None  # None = Global public benchmark
    external_ref_id: Optional[str] = None  # e.g., 'CWE-89', 'OWASP-A03:2021'
    description: Optional[str] = None
    version: str = "1.0"
    status: KnowledgeIngestionStatus = KnowledgeIngestionStatus.PENDING
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    chunk_count: int = 0
    token_count: int = 0
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    published_date: Optional[str] = None
    last_updated_date: Optional[str] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    created_by: Optional[UUID] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityKnowledgeChunk:
    """Domain entity representing an individual text chunk with vector embedding & source citations."""

    document_id: UUID
    chunk_index: int
    content_text: str
    token_count: int
    organization_id: Optional[UUID] = None
    embedding: Optional[List[float]] = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    chunk_metadata: Dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RAGSearchResult:
    """Domain entity representing a vector similarity match with citation metadata."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    source_type: KnowledgeDocumentSourceType
    content_text: str
    similarity_score: float
    external_ref_id: Optional[str] = None
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    chunk_metadata: Dict[str, Any] = field(default_factory=dict)


# ── Phase 5.7: Enterprise AI Security Copilot Domain Entities ──


class CopilotSessionStatus(str, Enum):
    """Lifecycle states for Copilot conversation sessions."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    CLOSED = "CLOSED"


class CopilotMessageRole(str, Enum):
    """Roles for messages within a Copilot session."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"


class CopilotAgentType(str, Enum):
    """Specialized internal AI agent personas handling analyst queries."""

    ORCHESTRATOR = "ORCHESTRATOR"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    EXPLAINER = "EXPLAINER"
    ATTACK_PATH = "ATTACK_PATH"
    REMEDIATION = "REMEDIATION"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    KNOWLEDGE_RAG = "KNOWLEDGE_RAG"


class CopilotContextMemoryType(str, Enum):
    """Categories of persistent key-value memory for copilot investigation context."""

    INVESTIGATION_STATE = "INVESTIGATION_STATE"
    FOCUSED_ENTITY = "FOCUSED_ENTITY"
    USER_PREFERENCE = "USER_PREFERENCE"
    REASONING_SUMMARY = "REASONING_SUMMARY"


class CopilotToolStatus(str, Enum):
    """Execution status for internal tool invocations."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DENIED = "DENIED"


@dataclass
class CopilotSession:
    """Domain entity representing a multi-turn AI Security Copilot conversation session."""

    organization_id: UUID
    user_id: UUID
    title: str = "New Security Investigation"
    status: CopilotSessionStatus = CopilotSessionStatus.ACTIVE
    focused_finding_id: Optional[UUID] = None
    model_alias: str = "default"
    temperature: float = 0.2
    total_tokens: int = 0
    message_count: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CopilotMessage:
    """Domain entity representing a chat message with grounding & explainability metadata."""

    session_id: UUID
    organization_id: UUID
    role: CopilotMessageRole
    content: str
    agent_type: CopilotAgentType = CopilotAgentType.SECURITY_ANALYST
    token_count: int = 0
    # Grounding & Explainability Metadata
    response_confidence_score: Optional[float] = None
    sources_used: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_chunks_used: List[Dict[str, Any]] = field(default_factory=list)
    tools_called: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_summary: Optional[str] = None
    model_used: Optional[str] = None
    prompt_version: str = "1.0"
    response_evaluation_metadata: Dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CopilotContextMemory:
    """Domain entity representing persistent key-value context memory for an investigation session."""

    session_id: UUID
    organization_id: UUID
    memory_key: str
    memory_value_json: Dict[str, Any]
    memory_type: CopilotContextMemoryType = CopilotContextMemoryType.INVESTIGATION_STATE
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CopilotToolExecution:
    """Domain entity representing an audit execution log of an internal read-only tool call."""

    session_id: UUID
    organization_id: UUID
    tool_name: str
    input_params_json: Dict[str, Any]
    output_summary_json: Dict[str, Any]
    execution_status: CopilotToolStatus = CopilotToolStatus.SUCCESS
    latency_ms: int = 0
    message_id: Optional[UUID] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CopilotFeedback:
    """Domain entity representing SOC analyst evaluation feedback on a copilot response."""

    session_id: UUID
    message_id: UUID
    organization_id: UUID
    user_id: UUID
    rating: int  # 1 to 5 stars
    is_helpful: bool
    feedback_category: Optional[str] = None
    feedback_notes: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
