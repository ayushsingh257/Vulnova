"""Pure Domain Entities & Enums for Multi-Provider LLM Gateway, Prompt Orchestrator & AI Analysis Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
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
