# Vulnova — Relational & Vector Database Architecture (DATABASE.md)

This document defines the PostgreSQL relational database schema, enterprise scan profiles, vulnerability lifecycle history tracking, separate evidence management system, `pgvector` vector embedding storage, indexing strategies, Alembic migration workflow, and Redis caching topologies for **Vulnova**.

---

## 🗄️ 1. Database Topology Overview

Vulnova leverages **PostgreSQL 16+** with the **`pgvector`** extension as a unified data storage layer:

- **Relational Data**: Tenant organizations, user credentials, scan profiles, targets, findings, vulnerability history, decoupled evidence records, and audit events.
- **Vector Embeddings**: Security knowledge base (CWEs, OWASP Cheat Sheets, advisories) and finding similarity embeddings for RAG retrieval.
- **Redis 7 Cache**: Distributed task queue broker (Celery), WebSocket state, API rate-limiting token buckets, and session cache.

---

## 📐 2. Data Models & Entity Relationship Schema

```
  ┌─────────────────┐       1:N       ┌─────────────────┐
  │  organizations  │────────────────►│      users      │
  └────────┬────────┘                 └────────┬────────┘
           │ 1:N                               │ 1:N
           ▼                                   ▼
  ┌─────────────────┐                 ┌─────────────────┐
  │  scan_targets   │                 │   audit_logs    │
  └────────┬────────┘                 └─────────────────┘
           │ 1:N
           ▼
  ┌─────────────────┐       1:N       ┌─────────────────┐
  │   scan_jobs     │────────────────►│    findings     │
  └─────────────────┘                 └───┬─────────┬───┘
                                      1:N │         │ 1:N
                                          ▼         ▼
                      ┌──────────────────────┐   ┌──────────────────────┐
                      │ vulnerability_history│   │   evidence_records   │
                      └──────────────────────┘   └──────────────────────┘
```

---

## 💻 3. Core Database Table Definitions (DDL)

```sql
-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Organizations (Multi-Tenancy)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'SECURITY_ANALYST',
    is_mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_org_id ON users(organization_id);

-- Scan Profiles
CREATE TABLE scan_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- NULL for global default profiles
    name VARCHAR(255) NOT NULL, -- 'Quick Scan', 'Full Security Assessment', 'API Security Scan', 'Compliance Scan'
    description TEXT,
    enabled_plugin_ids JSONB NOT NULL,
    max_crawl_depth INT DEFAULT 3,
    max_concurrent_requests INT DEFAULT 10,
    is_custom BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Scan Targets (Phase 6.2 Target Scan Configuration)
CREATE TABLE scan_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    target_url TEXT NOT NULL,
    environment VARCHAR(50) DEFAULT 'PRODUCTION',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    is_ownership_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ownership_verification_token VARCHAR(255),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_scan_targets_org ON scan_targets(organization_id);
CREATE INDEX idx_scan_targets_org_url ON scan_targets(organization_id, target_url);

-- Authorization Declarations (Phase 6.2 Authorized Assessment Contract Audit Storage)
CREATE TABLE authorization_declarations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scan_target_id UUID NOT NULL REFERENCES scan_targets(id) ON DELETE CASCADE,
    declared_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_authorized BOOLEAN NOT NULL,
    authorization_scope VARCHAR(50) NOT NULL DEFAULT 'full',
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_auth_decl_org_target ON authorization_declarations(organization_id, scan_target_id);


-- Assessment Jobs (Phase 4.1, Phase 4.7 & Phase 6.3 State Machine Extensions)
CREATE TABLE assessment_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- Synchronized legacy status field
    execution_state VARCHAR(50) NOT NULL DEFAULT 'QUEUED', -- Granular state machine ('QUEUED', 'CRAWLING', 'ASSESSING', 'AI_ANALYSIS', 'COMPLETED', 'FAILED', 'CANCELLED', 'RETRYING')
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    last_error TEXT,
    current_step VARCHAR(100),
    profile_id VARCHAR(100) DEFAULT 'full_assessment',
    policy_json JSONB,
    enabled_plugins_json JSONB,
    duration_seconds NUMERIC(10, 2),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assessment_jobs_org_status ON assessment_jobs(organization_id, status);
CREATE INDEX idx_assessment_jobs_org_exec_state ON assessment_jobs(organization_id, execution_state);

CREATE INDEX idx_assessment_jobs_org_profile ON assessment_jobs(organization_id, profile_id);

-- ── Real-Time Scan Event Stream Architecture (Phase 6.4) ──
-- Real-time events stream ephemerally over Redis Pub/Sub channels (key format: 'vulnova:scan:events:{organization_id}:{scan_id}')
-- Ephemeral Event Payload JSON Schema:
-- {
--   "event_id": "evt_123456789abc",
--   "job_id": "UUID",
--   "organization_id": "UUID",
--   "event_type": "STATE_CHANGE | PROGRESS_UPDATE | PLUGIN_STARTED | PLUGIN_COMPLETED | FINDING_DISCOVERED | ERROR_LOG | HEARTBEAT",
--   "payload": { ... },
--   "timestamp": "ISO-8601 UTC string"
-- }


-- Security Findings (Normalized, Evidence Enriched, & Asset Correlated - Phase 4.5, 4.6, 4.8)
CREATE TABLE security_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    assessment_job_id UUID NOT NULL REFERENCES assessment_jobs(id) ON DELETE CASCADE,
    asset_node_id UUID REFERENCES asset_nodes(id) ON DELETE SET NULL, -- Phase 4.8 optional FK to AssetNode (keeps legacy backward compatibility)
    plugin_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    cve_id VARCHAR(50),
    cwe_id VARCHAR(50),
    remediation TEXT,
    evidence_json JSONB,
    cvss_json JSONB,
    epss_json JSONB,
    risk_score NUMERIC(5, 2),
    confidence VARCHAR(20) DEFAULT 'HIGH',
    is_duplicate BOOLEAN DEFAULT FALSE,
    canonical_finding_id UUID REFERENCES security_findings(id) ON DELETE SET NULL,
    deduplication_hash VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_security_findings_org_severity ON security_findings(organization_id, severity);
CREATE INDEX idx_security_findings_org_category ON security_findings(organization_id, category);
CREATE INDEX idx_security_findings_org_risk ON security_findings(organization_id, risk_score);
CREATE INDEX idx_security_findings_org_asset ON security_findings(organization_id, asset_node_id);

-- Multi-Modal Evidence Artifacts (Phase 4.6)
CREATE TABLE evidence_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL, -- 'SCREENSHOT', 'DOM_SNAPSHOT', 'HTTP_REQUEST', 'HTTP_RESPONSE', 'COOKIE_DATA', 'HEADER_DATA'
    storage_path VARCHAR(1024) NOT NULL,
    metadata_json JSONB,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_evidence_artifacts_org_finding ON evidence_artifacts(organization_id, finding_id);

-- Posture Snapshots (Phase 4.9)
CREATE TABLE asset_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    assessment_job_id UUID REFERENCES assessment_jobs(id) ON DELETE SET NULL,
    total_assets INT NOT NULL DEFAULT 0,
    total_findings INT NOT NULL DEFAULT 0,
    critical_findings INT NOT NULL DEFAULT 0,
    high_findings INT NOT NULL DEFAULT 0,
    medium_findings INT NOT NULL DEFAULT 0,
    low_findings INT NOT NULL DEFAULT 0,
    info_findings INT NOT NULL DEFAULT 0,
    avg_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    max_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_asset_snapshots_org_created ON asset_snapshots(organization_id, created_at);

-- Security Change Events (Phase 4.9)
CREATE TABLE asset_change_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    asset_node_id UUID REFERENCES asset_nodes(id) ON DELETE SET NULL,
    assessment_job_id UUID REFERENCES assessment_jobs(id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL, -- 'ASSET_ADDED', 'ASSET_REMOVED', 'TECH_UPDATED', 'FINDING_NEW', 'FINDING_RESOLVED', 'FINDING_REOPENED'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    details_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_change_events_org_created ON asset_change_events(organization_id, created_at);
CREATE INDEX idx_change_events_org_type ON asset_change_events(organization_id, change_type);

-- Finding Triage History (Phase 4.10)
CREATE TABLE finding_triage_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    previous_status VARCHAR(50) NOT NULL DEFAULT 'UNREVIEWED',
    new_status VARCHAR(50) NOT NULL, -- 'UNREVIEWED', 'CONFIRMED', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'REMEDIATED', 'REOPENED'
    comment TEXT,
    risk_accepted_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_triage_history_org_finding ON finding_triage_history(organization_id, finding_id);
CREATE INDEX idx_triage_history_org_created ON finding_triage_history(organization_id, created_at);

-- Finding Suppression Rules (Phase 4.10)
CREATE TABLE finding_suppression_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- 'EXACT_CWE', 'TARGET_PATTERN', 'PLUGIN_ID', 'COMPOSITE'
    plugin_id VARCHAR(100),
    cwe_id VARCHAR(50),
    target_pattern TEXT,
    reason TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_suppression_rules_org_active ON finding_suppression_rules(organization_id, is_active);

-- LLM Providers Table (Phase 5.1)
CREATE TABLE llm_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_type VARCHAR(50) NOT NULL, -- 'OPENAI', 'ANTHROPIC', 'GOOGLE', 'OLLAMA', 'CUSTOM'
    name VARCHAR(255) NOT NULL,
    api_endpoint TEXT,
    encrypted_api_key TEXT, -- Encrypted via AES-256-GCM
    priority INT NOT NULL DEFAULT 10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_healthy BOOLEAN NOT NULL DEFAULT TRUE,
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    cooldown_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_llm_providers_org_active ON llm_providers(organization_id, is_active, priority);

-- LLM Model Registry Table (Phase 5.1)
CREATE TABLE llm_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_type VARCHAR(50) NOT NULL,
    model_alias VARCHAR(100) NOT NULL, -- e.g. 'gpt-4o', 'claude-3-5-sonnet', 'llama3'
    model_name VARCHAR(255) NOT NULL,
    context_window_tokens INT NOT NULL DEFAULT 128000,
    max_output_tokens INT NOT NULL DEFAULT 4096,
    input_cost_per_1k_tokens NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    output_cost_per_1k_tokens NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_llm_models_org_alias ON llm_models(organization_id, model_alias);

-- Prompt Templates Table (Phase 5.1)
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL, -- 'FINDING_EXPLAINER', 'ATTACK_PATH_SYNTHESIS', 'REMEDIATION_PATCH', 'SYSTEM_PROMPT'
    name VARCHAR(255) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_prompt_templates_org_cat ON prompt_templates(organization_id, category, is_active);

-- LLM Request Logs Table (Phase 5.1)
CREATE TABLE llm_request_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_type VARCHAR(50) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    prompt_category VARCHAR(50),
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL, -- 'SUCCESS', 'FAILED', 'FALLBACK'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_llm_logs_org_created ON llm_request_logs(organization_id, created_at);

-- AI Finding Explanations Table (Phase 5.2)
CREATE TABLE ai_finding_explanations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    vulnerability_summary TEXT NOT NULL,
    technical_root_cause TEXT NOT NULL,
    affected_asset_context TEXT NOT NULL,
    exploitability_analysis TEXT NOT NULL,
    business_impact TEXT NOT NULL,
    attack_prerequisites TEXT NOT NULL,
    severity_reasoning TEXT NOT NULL,
    remediation_priority TEXT NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    provider_used VARCHAR(50) NOT NULL,
    prompt_version INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED', -- 'COMPLETED', 'FAILED', 'STALE'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_explanations_org_finding ON ai_finding_explanations(organization_id, finding_id);
CREATE INDEX idx_ai_explanations_org_created ON ai_finding_explanations(organization_id, created_at);

-- AI Impact Analyses Table (Phase 5.2)
CREATE TABLE ai_impact_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    technical_impact_summary TEXT NOT NULL,
    executive_impact_summary TEXT NOT NULL,
    risk_justification TEXT NOT NULL,
    affected_business_components TEXT NOT NULL,
    cvss_interpretation TEXT NOT NULL,
    epss_context TEXT NOT NULL,
    exposure_assessment TEXT NOT NULL,
    evidence_correlation TEXT NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    provider_used VARCHAR(50) NOT NULL,
    prompt_version INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED', -- 'COMPLETED', 'FAILED', 'STALE'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_impact_org_finding ON ai_impact_analyses(organization_id, finding_id);
CREATE INDEX idx_ai_impact_org_created ON ai_impact_analyses(organization_id, created_at);

-- AI Attack Paths Master Table (Option A - Phase 5.3)
CREATE TABLE ai_attack_paths (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    root_finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    source_asset_id UUID REFERENCES asset_nodes(id) ON DELETE SET NULL,
    target_asset_id UUID REFERENCES asset_nodes(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    attack_summary TEXT NOT NULL,
    composite_risk_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    model_used VARCHAR(100) NOT NULL,
    provider_used VARCHAR(50) NOT NULL,
    prompt_version INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'GENERATED', -- 'GENERATED', 'REVIEWED', 'ACCEPTED', 'REJECTED', 'STALE', 'FAILED'
    review_notes TEXT,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_paths_org_finding ON ai_attack_paths(organization_id, root_finding_id);
CREATE INDEX idx_ai_paths_org_status ON ai_attack_paths(organization_id, status);
CREATE INDEX idx_ai_paths_org_created ON ai_attack_paths(organization_id, created_at);

-- AI Attack Path Steps Detail Table (Option A - Phase 5.3)
CREATE TABLE ai_attack_path_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attack_path_id UUID NOT NULL REFERENCES ai_attack_paths(id) ON DELETE CASCADE,
    sequence_number INT NOT NULL,
    step_type VARCHAR(50) NOT NULL, -- 'INITIAL_ACCESS', 'EXECUTION', 'PRIVILEGE_ESCALATION', 'CREDENTIAL_ACCESS', 'LATERAL_MOVEMENT', 'IMPACT'
    asset_node_id UUID REFERENCES asset_nodes(id) ON DELETE SET NULL,
    finding_id UUID REFERENCES security_findings(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    mitre_tactic VARCHAR(100) NOT NULL,
    mitre_technique_id VARCHAR(50) NOT NULL,
    mitre_technique_name VARCHAR(255) NOT NULL,
    attacker_action TEXT NOT NULL,
    required_privilege VARCHAR(100) NOT NULL,
    evidence_reference TEXT,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_ai_steps_path_seq ON ai_attack_path_steps(attack_path_id, sequence_number);
CREATE INDEX idx_ai_steps_mitre ON ai_attack_path_steps(mitre_technique_id);

-- AI Remediation Plans Master Table (Phase 5.4)
CREATE TABLE ai_remediation_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    root_finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    attack_path_id UUID REFERENCES ai_attack_paths(id) ON DELETE SET NULL,
    cve_id VARCHAR(50),
    cwe_id VARCHAR(50),
    affected_version VARCHAR(100),
    fixed_version VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    technical_solution TEXT NOT NULL,
    business_solution TEXT NOT NULL,
    risk_reduction_explanation TEXT NOT NULL,
    validation_strategy TEXT NOT NULL,
    composite_risk_score DOUBLE PRECISION NOT NULL,
    ai_confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    effectiveness_confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    requires_backup BOOLEAN NOT NULL DEFAULT FALSE,
    requires_downtime BOOLEAN NOT NULL DEFAULT FALSE,
    rollback_available BOOLEAN NOT NULL DEFAULT TRUE,
    model_used VARCHAR(100) NOT NULL,
    provider_used VARCHAR(50) NOT NULL,
    prompt_version INT NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'GENERATED', -- 'GENERATED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'IMPLEMENTED', 'VERIFIED', 'VALIDATION_FAILED', 'FAILED'
    review_notes TEXT,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_remed_org_finding ON ai_remediation_plans(organization_id, root_finding_id);
CREATE INDEX idx_ai_remed_org_status ON ai_remediation_plans(organization_id, status);
CREATE INDEX idx_ai_remed_org_created ON ai_remediation_plans(organization_id, created_at);

-- AI Remediation Steps Detail Table (Phase 5.4)
CREATE TABLE ai_remediation_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    remediation_plan_id UUID NOT NULL REFERENCES ai_remediation_plans(id) ON DELETE CASCADE,
    sequence_number INT NOT NULL,
    step_type VARCHAR(50) NOT NULL, -- 'CODE_PATCH', 'CONFIGURATION_CHANGE', 'DEPENDENCY_UPDATE', 'ARCHITECTURE_CHANGE', 'SECURITY_CONTROL', 'MANUAL_PROCESS'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    affected_component VARCHAR(255) NOT NULL,
    recommended_action TEXT NOT NULL,
    validation_command TEXT,
    rollback_strategy TEXT,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_ai_remed_step_plan_seq ON ai_remediation_steps(remediation_plan_id, sequence_number);

-- AI Patch Suggestions Table (Phase 5.4)
CREATE TABLE ai_patch_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    remediation_plan_id UUID NOT NULL REFERENCES ai_remediation_plans(id) ON DELETE CASCADE,
    language VARCHAR(50) NOT NULL, -- 'PYTHON', 'JAVASCRIPT', 'GO', 'JAVA', 'NGINX', 'DOCKER', 'TERRAFORM', 'YAML'
    file_type VARCHAR(50) NOT NULL, -- 'SOURCE_CODE', 'CONFIG', 'IAC', 'DOCKERFILE', 'MANIFEST'
    target_file_path VARCHAR(500),
    original_code_snippet TEXT NOT NULL,
    proposed_patch_diff TEXT NOT NULL,
    explanation TEXT NOT NULL,
    security_impact_notes TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_ai_patch_plan_lang ON ai_patch_suggestions(remediation_plan_id, language);

-- AI Finding Confidence Analyses Master Table (Phase 5.5)
CREATE TABLE ai_finding_confidence_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    classification VARCHAR(30) NOT NULL, -- 'TRUE_POSITIVE', 'FALSE_POSITIVE', 'NEEDS_REVIEW'
    confidence_score DOUBLE PRECISION NOT NULL,
    evidence_quality_score DOUBLE PRECISION NOT NULL,
    reasoning TEXT NOT NULL,
    supporting_evidence TEXT NOT NULL,
    contradicting_evidence TEXT NOT NULL,
    missing_information TEXT NOT NULL,
    validation_requirements TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    composite_risk_score DOUBLE PRECISION NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    provider_used VARCHAR(50) NOT NULL,
    prompt_version INT NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'GENERATED', -- 'GENERATED', 'REVIEWED', 'ACCEPTED', 'REJECTED', 'STALE', 'FAILED'
    review_notes TEXT,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    predicted_confidence_score DOUBLE PRECISION,
    analyst_final_decision VARCHAR(30),
    confidence_accuracy_delta DOUBLE PRECISION,
    feedback_timestamp TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_conf_org_finding ON ai_finding_confidence_analyses(organization_id, finding_id);
CREATE INDEX idx_ai_conf_org_class ON ai_finding_confidence_analyses(organization_id, classification);
CREATE INDEX idx_ai_conf_org_created ON ai_finding_confidence_analyses(organization_id, created_at);

-- AI Finding Similarity Matches Detail Table (Phase 5.5)
CREATE TABLE ai_finding_similarity_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    confidence_analysis_id UUID REFERENCES ai_finding_confidence_analyses(id) ON DELETE CASCADE,
    source_finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    matched_finding_id UUID NOT NULL REFERENCES security_findings(id) ON DELETE CASCADE,
    similarity_score DOUBLE PRECISION NOT NULL,
    similarity_reason TEXT NOT NULL,
    matched_signals JSONB, -- ['CVE', 'CWE', 'ENDPOINT', 'ASSET_NODE', 'PLUGIN_ID', 'VULNERABILITY_TITLE', 'AFFECTED_COMPONENT', 'ATTACK_TECHNIQUE']
    status VARCHAR(20) NOT NULL DEFAULT 'GENERATED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_sim_org_source ON ai_finding_similarity_matches(organization_id, source_finding_id);
CREATE INDEX idx_ai_sim_score ON ai_finding_similarity_matches(similarity_score);

-- Security Knowledge Documents Master Table (Phase 5.6)
CREATE TABLE security_knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- NULL = Global public benchmark
    source_type VARCHAR(50) NOT NULL, -- 'OWASP', 'CWE', 'CAPEC', 'CVE_NVD', 'VENDOR_ADVISORY', 'INTERNAL_POLICY', 'CUSTOM'
    ingestion_source VARCHAR(50) NOT NULL DEFAULT 'MANUAL_UPLOAD', -- 'MANUAL_UPLOAD', 'API_IMPORT', 'NVD_SYNC', 'OWASP_SYNC', 'VENDOR_FEED', 'INTERNAL_SYNC'
    title VARCHAR(255) NOT NULL,
    external_ref_id VARCHAR(100), -- 'CWE-89', 'OWASP-A03:2021'
    description TEXT,
    version VARCHAR(50) NOT NULL DEFAULT '1.0',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'UNDER_REVIEW', 'APPROVED', 'INDEXED', 'REJECTED', 'FAILED', 'ARCHIVED'
    chunk_size_tokens INT NOT NULL DEFAULT 512,
    chunk_overlap_tokens INT NOT NULL DEFAULT 64,
    chunk_count INT NOT NULL DEFAULT 0,
    token_count INT NOT NULL DEFAULT 0,
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    embedding_dimension INT NOT NULL DEFAULT 1536,
    source_url VARCHAR(500),
    source_author VARCHAR(255),
    published_date VARCHAR(50),
    last_updated_date VARCHAR(50),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sec_doc_org ON security_knowledge_documents(organization_id);
CREATE INDEX idx_sec_doc_source ON security_knowledge_documents(source_type);
CREATE INDEX idx_sec_doc_status ON security_knowledge_documents(status);

-- Security Knowledge Chunks Detail Table with pgvector (Phase 5.6)
CREATE TABLE security_knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES security_knowledge_documents(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content_text TEXT NOT NULL,
    token_count INT NOT NULL,
    embedding vector(1536), -- pgvector 1536-dimensional embedding
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    embedding_dimension INT NOT NULL DEFAULT 1536,
    source_url VARCHAR(500),
    source_author VARCHAR(255),
    chunk_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sec_chunk_doc ON security_knowledge_chunks(document_id, chunk_index);
CREATE INDEX idx_sec_chunk_org ON security_knowledge_chunks(organization_id);
CREATE INDEX idx_sec_chunk_embedding_hnsw ON security_knowledge_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- RAG Search Logs Audit & Performance Table (Phase 5.6)
CREATE TABLE rag_search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    top_k INT NOT NULL DEFAULT 5,
    min_similarity DOUBLE PRECISION NOT NULL DEFAULT 0.70,
    results_count INT NOT NULL,
    matched_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    search_latency_ms INT NOT NULL,
    retrieval_quality_score DOUBLE PRECISION,
    average_similarity_score DOUBLE PRECISION,
    analyst_feedback TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_rag_log_org ON rag_search_logs(organization_id, created_at);

-- AI Copilot Sessions Master Table (Phase 5.7)
CREATE TABLE ai_copilot_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Security Investigation',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'ARCHIVED', 'CLOSED'
    focused_finding_id UUID REFERENCES security_findings(id) ON DELETE SET NULL,
    model_alias VARCHAR(100) NOT NULL DEFAULT 'default',
    temperature DOUBLE PRECISION NOT NULL DEFAULT 0.2,
    total_tokens INT NOT NULL DEFAULT 0,
    message_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_copilot_sess_org_user ON ai_copilot_sessions(organization_id, user_id);
CREATE INDEX idx_copilot_sess_status ON ai_copilot_sessions(organization_id, status);

-- AI Copilot Messages Detail Table with Explainability Metadata (Phase 5.7)
CREATE TABLE ai_copilot_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES ai_copilot_sessions(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'USER', 'ASSISTANT', 'SYSTEM', 'TOOL'
    content TEXT NOT NULL,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'SECURITY_ANALYST',
    token_count INT NOT NULL DEFAULT 0,
    response_confidence_score DOUBLE PRECISION,
    sources_used JSONB NOT NULL DEFAULT '[]'::jsonb,
    knowledge_chunks_used JSONB NOT NULL DEFAULT '[]'::jsonb,
    tools_called JSONB NOT NULL DEFAULT '[]'::jsonb,
    reasoning_summary TEXT,
    model_used VARCHAR(100),
    prompt_version VARCHAR(50) NOT NULL DEFAULT '1.0',
    response_evaluation_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_copilot_msg_session ON ai_copilot_messages(session_id, role);

-- AI Copilot Context Memory Table (Phase 5.7)
CREATE TABLE ai_copilot_context_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES ai_copilot_sessions(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    memory_key VARCHAR(100) NOT NULL,
    memory_value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    memory_type VARCHAR(50) NOT NULL DEFAULT 'INVESTIGATION_STATE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_copilot_mem_session_key ON ai_copilot_context_memories(session_id, memory_key);

-- AI Copilot Tool Executions Audit Table (Phase 5.7)
CREATE TABLE ai_copilot_tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES ai_copilot_sessions(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    message_id UUID REFERENCES ai_copilot_messages(id) ON DELETE SET NULL,
    tool_name VARCHAR(100) NOT NULL,
    input_params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    latency_ms INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_copilot_tool_exec_session ON ai_copilot_tool_executions(session_id, tool_name);

-- AI Copilot Analyst Feedback Table (Phase 5.7)
CREATE TABLE ai_copilot_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES ai_copilot_sessions(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES ai_copilot_messages(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INT NOT NULL, -- 1 to 5
    is_helpful BOOLEAN NOT NULL DEFAULT TRUE,
    feedback_category VARCHAR(100),
    feedback_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_copilot_feedback_org ON ai_copilot_feedback(organization_id, rating);

-- Worker Nodes Master Table (Phase 6.1)
CREATE TABLE worker_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    worker_id VARCHAR(100) NOT NULL UNIQUE,
    hostname VARCHAR(255) NOT NULL DEFAULT 'localhost',
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE', -- 'IDLE', 'BUSY', 'OFFLINE', 'PAUSED', 'UNHEALTHY'
    current_task_count INT NOT NULL DEFAULT 0,
    max_concurrency INT NOT NULL DEFAULT 4,
    memory_usage_mb DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    cpu_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    queue_subscriptions JSONB NOT NULL DEFAULT '["scans.default"]'::jsonb,
    sandbox_limits JSONB NOT NULL DEFAULT '{"cpu_limit_vcpu": 1.0, "memory_limit_mb": 512}'::jsonb,
    last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_worker_node_org_status ON worker_nodes(organization_id, status);
CREATE INDEX idx_worker_node_heartbeat ON worker_nodes(last_heartbeat);

-- Worker Task Executions Audit Table (Phase 6.1)
CREATE TABLE worker_task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(100) NOT NULL UNIQUE,
    scan_id UUID REFERENCES assessment_jobs(id) ON DELETE SET NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    worker_node_id UUID REFERENCES worker_nodes(id) ON DELETE SET NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'scans.default',
    task_name VARCHAR(255) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'CANCELLED'
    retry_count INT NOT NULL DEFAULT 0,
    runtime_ms INT NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_worker_task_org_state ON worker_task_executions(organization_id, state);
CREATE INDEX idx_worker_task_scan ON worker_task_executions(scan_id);
```

### Scan Schedules (Phase 6.5)

```sql
-- Recurring Scan Schedules
CREATE TABLE scan_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    scan_target_id UUID NOT NULL REFERENCES scan_targets(id),
    name VARCHAR(255) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    frequency VARCHAR(20) NOT NULL DEFAULT 'DAILY', -- 'HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'CUSTOM_CRON'
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',   -- 'ACTIVE', 'PAUSED', 'DISABLED'
    profile_id VARCHAR(50) DEFAULT 'full_assessment',
    enabled_plugins_json TEXT,
    total_runs_count INT NOT NULL DEFAULT 0,
    next_run_at TIMESTAMP WITH TIME ZONE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_scan_schedules_org ON scan_schedules(organization_id);
CREATE INDEX idx_scan_schedules_target ON scan_schedules(scan_target_id);
CREATE INDEX idx_scan_schedules_status ON scan_schedules(organization_id, status);
CREATE INDEX idx_scan_schedules_next_run ON scan_schedules(status, next_run_at);
```

---

## ⚡ 4. Redis Cache Key Topologies

| Key Pattern | Data Type | TTL | Purpose |
| :--- | :--- | :--- | :--- |
| `rate_limit:{ip}` | String / Counter | 60 sec | API rate limiting token bucket |
| `session:{user_id}` | Hash | 15 min | User active session data |
| `scan_progress:{scan_id}`| Hash | 24 hrs | Real-time scan execution metrics |
| `ws_channel:{scan_id}` | Pub/Sub Channel | Real-time | Live progress streaming to clients |
| `lock:scan:{org_id}:{url_hash}` | String | 1 hr | Distributed scan target lock (Phase 6.3) |
| `vulnova:scan:events:{org_id}:{scan_id}` | Pub/Sub Channel | Real-time | Scan event streaming (Phase 6.4) |
| `dashboard:metrics:{org_id}` | String (JSON) | 30 sec | Consolidated SOC dashboard metrics cache per organization (Phase 7.1) |
| `trust_center:public_summary` | String (JSON) | 300 sec | Cached public Enterprise Trust Center summary & OWASP ASVS control mappings (Phase 7.2) |
| `dashboard:trends:{org_id}:{timeframe}` | String (JSON) | 300 sec | Historical risk trajectory points and velocity metrics cache (Phase 7.3) |
| `rate_limit:export:{org_id}` | String / Counter | 60 sec | Executive report export rate limiting counter (Phase 7.3) |

---

## 🖥️ 5. Scan Portal Index Usage (Phase 7.4)

Paginated scan listing queries (`GET /api/v1/assessments`) utilize composite index `idx_assessment_jobs_org` (`organization_id`, `created_at DESC`) on `assessment_jobs` to guarantee sub-20ms execution times across large datasets.

---

---

## ⚙️ 7. Admin Control Plane Table & Repository Reuse (Phase 7.6)

Phase 7.6 requires zero new database tables or schema migrations. `AdminService` (`app/application/admin/admin_service.py`) reuses 4 existing PostgreSQL tables across Era 2 models:
- `organizations` (`idx_organizations_slug`) for organization profile and member statistics.
- `users` (`idx_users_org_role`, `idx_users_email`) for team member listing, invitations, role updates, and deactivation.
- `api_keys` (`idx_api_keys_org`, `idx_api_keys_hash`, `idx_api_keys_prefix`) for machine-to-machine integration API key listing, generation, and revocation.
- `audit_logs` (`idx_audit_logs_org_action`, `idx_audit_logs_actor`) for administrative action logging (`organization.updated`, `user.invited`, `user.role_updated`, `user.deactivated`, `api_key.created`, `api_key.revoked`).

---

## 📊 8. Executive Reporting Engine Table Reuse & Audit Event Logging (Phase 8.1)

Phase 8.1 requires zero new database tables or schema migrations. `ExecutiveSecurityReportService` (`app/application/reporting/report_service.py`) reuses existing database tables and models:
- `security_findings` (`ix_security_findings_org_sev`, `ix_security_findings_org_risk`) for top open finding extraction.
- `risk_posture_snapshots` (`idx_risk_snapshots_org_date`) for historical risk trajectory points and MTTR analytics.
- `audit_logs` (`idx_audit_logs_org_action`, `idx_audit_logs_actor`) for non-repudiable audit logging:
  - `report.generated`: Records report ID, title, analysis window timeframe, posture score, and total open findings count.
  - `report.downloaded`: Records report ID, download format (`pdf`, `html`, `json`, `csv`), title, and byte size payload.

### Developer Technical Remediation Export Table Reuse & Chunking (Phase 8.2)
Phase 8.2 introduces **zero new database tables** and **zero schema migrations**. `DeveloperExportService` (`app/application/reporting/developer_export_service.py`) reuses existing database tables and models:
- `security_findings`: Queried using offset/limit batch cursors (`_stream_findings`, batch size 50) on `(organization_id, is_duplicate)` to stream findings into JSON, CSV, and Markdown exports without loading the full dataset into worker memory.
- `evidence_artifacts`: Proof payload retrieval with automated token/credential masking.
- `ai_remediation_plans`, `ai_finding_explanations`, `ai_attack_paths`: Reused for single finding remediation package exports.
- `audit_logs`: Records export audit events:
  - `report.exported`: Records bulk export details (`format`: `json` | `csv` | `markdown`, `findings_count`, `export_type`: `bulk_findings`).
  - `vulnerability.exported`: Records single vulnerability export details (`resource_id`: `finding_id`, `format`, `finding_title`, `severity`).

### Compliance Framework Mapping Engine Table Reuse (Phase 8.3)
Phase 8.3 introduces **zero new database tables** and **zero schema migrations**. `ComplianceMappingService` (`app/application/compliance/compliance_service.py`) and `FrameworkMapper` (`app/application/compliance/framework_mapper.py`) evaluate compliance dynamically against existing database models:
- `security_findings`: Queried using batch cursors (`_fetch_tenant_findings`, batch size 100) filtered by `organization_id` and `is_duplicate = False`. Active open findings (`status` in `OPEN`, `CONFIRMED`, `NEW`, `UNREAD`, `TRIAGED`, `IN_REMEDIATION`) are evaluated against static CWE and category mapping definitions (`owasp_top10.py`, `asvs_v4.py`, `pci_dss.py`, `iso27001.py`). Resolved and false-positive findings do not impact compliance scores.
- `evidence_artifacts`: Reused for evidence checksum and artifact traceability verification (`ComplianceFindingMappingDTO`).
- `assessment_jobs`: Target URL and asset name resolution.
- `audit_logs`: Records compliance audit events:
  - `compliance.viewed`: Records `framework_id`, `framework_version`, `compliance_percentage`, `failed_controls_count`, and `actor_user_id`.
  - `compliance.exported`: Records `framework_id`, `framework_version`, `compliance_percentage`, and timestamp.

### 8.8 Enterprise Integration & External Ticket Mapping Schema Strategy (Era 9 Phase 9.1)
- **Zero Database Table Duplication**: Features **zero new database tables** and **zero schema migrations**. Provider configurations and external ticket references reuse authoritative PostgreSQL models (`OrganizationModel`, `security_findings`, `audit_logs`).
- **Encrypted Provider Secret Storage**: Jira API tokens and GitHub Personal Access Tokens (PATs) are encrypted at rest using AES-256-GCM / Fernet (`SecretEncryptionService`) and stored securely within `OrganizationModel.settings_json["integrations"]`. Plaintext secrets are never stored or exposed in API queries.
- **External Ticket Reference Storage**: Created issue references (`issue_id`, `issue_key`, `issue_url`, `status`, `created_at`) are attached to finding metadata (`security_findings.evidence_json["external_jira_issue"]` or `security_findings.evidence_json["external_github_issue"]`).
- **Controlled Status Sync Architecture**: External status changes (`DONE`/`CLOSED` -> `RESOLVED`) map safely through `ControlledJiraStatusMapper` and `ControlledGitHubStatusMapper` before updating `security_findings.status`.
- **Immutable Integration Audit Events**:
  - `integration.configuration_updated`: Records `provider` (`jira` | `github`), `host_url`/`repo_owner`, and `actor_user_id`.
  - `integration.issue_created`: Records `provider`, `issue_key`, `issue_url`, and `finding_id`.
  - `integration.issue_synced`: Records `provider`, `issue_key`/`issue_number`, `external_status`, `previous_status`, and `updated_status`.

### 8.9 Slack & Microsoft Teams Security Alert Webhooks Schema Strategy (Era 9 Phase 9.2)
- **Zero Database Table Duplication**: Requires **zero new database tables** and **zero schema migrations**. Channel configurations and alert dispatch logs reuse existing encryption and audit models (`SecretEncryptionService`, `audit_logs`).
- **Encrypted Webhook Secret Protection**: Incoming Webhook URLs (containing sensitive secret tokens) are encrypted at rest using AES-256-GCM / Fernet (`SecretEncryptionService`).
- **Secret Masking Guarantee**: Webhook URLs returned in REST API queries are masked (`https://hooks.slack.com/services/T00/B00/*****XXXX`), ensuring secrets are unrecoverable from client-side responses.
- **Immutable Webhook Audit Trail**:
  - `notification.channel_created`: Records `channel_id`, `provider` (`slack` | `teams`), `name`, `min_severity`, `actor_user_id`.
  - `notification.channel_updated`: Records `channel_id`, `provider`, `name`, `actor_user_id`.
  - `notification.channel_deleted`: Records `channel_id`, `actor_user_id`.
  - `notification.sent`: Records `channel_id`, `provider`, `event_type`, `status_code`, `status` (`DELIVERED`).
  - `notification.failed`: Records `channel_id`, `provider`, `event_type`, `status_code`, `status` (`FAILED`), `error_message`.

### 8.10 CI/CD Pipeline Scanning CLI Schema Strategy (Era 9 Phase 9.3)
- **Zero Schema Duplication**: Leverages existing machine-to-machine API key infrastructure (`api_keys` table with `vn_cli_` prefix and SHA-256 digests), `assessment_jobs`, `security_findings`, and `audit_logs`. Zero new database tables created.
- **Secure Token Protection**: CLI tokens are hashed via SHA-256 (`key_hash`). Raw tokens are returned once upon creation and unrecoverable from database queries.
- **Immutable CLI Audit Trail**:
  - `cli.token_created`: Records `token_id`, `name`, `prefix`, `actor_user_id`.
  - `cli.token_revoked`: Records `token_id`, `actor_user_id`.
  - `cli.scan_started`: Records `scan_id`, `project_name`, `branch`, `commit_sha`, `target_url`.
  - `cli.scan_completed`: Records `scan_id`, `gate_passed` (`true`), `exit_code` (`0`), finding counts.
  - `cli.pipeline_failed`: Records `scan_id`, `gate_passed` (`false`), `exit_code` (`1`), `failed_conditions`.

### 8.11 OWASP Top 10 (2021) Security Validation Schema Strategy (Era 10 Phase 10.1)
- **Zero Database Table Duplication**: Matches Era 8 compliance architecture: introduces **zero new database tables** (no `owasp_validation_runs`, `validation_results`, `security_audit_reports` tables) and **zero schema migrations**.
- **In-Memory Verification Engine**: Evaluates category assertions (A01 - A10) dynamically against authoritative `security_findings`, `evidence_artifacts`, `assessment_jobs`, `api_keys`, and `AuditLogService`.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Every validation execution generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details for cross-system SIEM correlation.
- **Immutable Validation Audit Trail**:
  - `validation.owasp_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.owasp_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.12 OWASP API Security Top 10 (2023) Validation Schema Strategy (Era 10 Phase 10.2)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates API security assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory API Assertion Engine**: `APISecurityValidationRunnerService` evaluates API1:2023 through API10:2023 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable API Security Audit Trail**:
  - `validation.api_security_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.api_security_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.13 Infrastructure Security Validation Schema Strategy (Era 10 Phase 10.3)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates infrastructure security assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory Infrastructure Assertion Engine**: `InfrastructureSecurityValidationRunnerService` evaluates INFRA1 through INFRA10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable Infrastructure Security Audit Trail**:
  - `validation.infrastructure_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.infrastructure_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.14 Platform Penetration Testing Validation Schema Strategy (Era 10 Phase 10.4)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates penetration test exploit assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory PenTest Assertion Engine**: `PenTestValidationRunnerService` evaluates PEN1 through PEN10 exploit scenarios dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable PenTest Security Audit Trail**:
  - `validation.pentest_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.pentest_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.15 Dependency Security Audit & SCA Validation Schema Strategy (Era 10 Phase 10.5)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates Software Composition Analysis assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory SCA Assertion Engine**: `SCAValidationRunnerService` evaluates SCA1 through SCA10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable SCA Security Audit Trail**:
  - `validation.sca_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.sca_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.16 Container Image Security Audit & Hardening Validation Schema Strategy (Era 10 Phase 10.6)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates container image security and runtime hardening assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory Container Assertion Engine**: `ContainerValidationRunnerService` evaluates CONTAINER1 through CONTAINER10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable Container Security Audit Trail**:
  - `validation.container_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.container_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.17 Secrets & Cryptographic Management Validation Schema Strategy (Era 10 Phase 10.7)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates secrets scanning and cryptographic security assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory Secrets Assertion Engine**: `SecretsValidationRunnerService` evaluates SECRET1 through SECRET10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable Secrets Security Audit Trail**:
  - `validation.secrets_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.secrets_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.18 Threat Model Review & STRIDE Validation Schema Strategy (Era 10 Phase 10.8)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates STRIDE threat model assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory Threat Assertion Engine**: `ThreatValidationRunnerService` evaluates STRIDE1 through STRIDE10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable Threat Model Security Audit Trail**:
  - `validation.threat_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.threat_suite_completed`: Records `suite_id`, `overall_pass_rate`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.19 Automated Security Regression Validation Schema Strategy (Era 10 Phase 10.9)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates security regression assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory Regression Assertion Engine**: `RegressionValidationRunnerService` evaluates REGRESSION1 through REGRESSION10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable Security Regression Audit Trail**:
  - `validation.regression_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
### 8.20 Security Control Plane Final Certification Validation Schema Strategy (Era 10 Phase 10.10)
- **Zero Database Table Duplication**: Introduces **zero new database tables** and **zero schema migrations**. Evaluates security control plane certification assertions dynamically against existing `security_findings`, `api_keys`, `users`, and `audit_logs`.
- **In-Memory Certification Assertion Engine**: `CertificationValidationRunnerService` evaluates CERTIFICATION1 through CERTIFICATION10 assertions dynamically in memory.
- **Ephemeral Audit Correlation Token (`suite_id`)**: Each validation run generates a runtime `uuid4()` token string (`suite_id`) recorded in audit log details.
- **Immutable Security Certification Audit Trail**:
  - `validation.certification_suite_started`: Records `suite_id`, `actor_user_id`, `organization_id`, timestamp.
  - `validation.certification_suite_completed`: Records `suite_id`, `overall_certification_score`, `overall_status` (`PASSED` | `DEGRADED` | `CRITICAL`), `passed_categories`, `failed_categories`, `warning_categories`, `actor_user_id`, timestamp.

### 8.21 Multi-Factor Authentication (MFA / TOTP) Schema & Security Storage Strategy (Era 10 Phase 10.11)
- **User Schema Hardening**:
  - `mfa_enabled`: `Boolean` default `False` indicating active TOTP enforcement.
  - `mfa_secret`: Encrypted string (`String(512)`) storing AES-256-GCM encrypted Base32 TOTP secret key.
  - `mfa_verified_at`: `DateTime(timezone=True)` timestamp of initial OTP setup verification.
  - `mfa_backup_codes`: Encrypted string (`String(4096)`) storing JSON array of SHA-256 hashed single-use recovery codes.
  - `mfa_last_used_at`: `DateTime(timezone=True)` timestamp of last successful OTP / recovery code verification.
- **Zero Plaintext Storage Guarantee**: Plaintext TOTP secret keys and recovery codes are NEVER stored in database tables.
- **Alembic Migration**: `0003_add_mfa_fields_to_users.py`.
- **Immutable MFA Security Audit Trail**:
  - `security.mfa_enabled`: Records `user_id`, `organization_id`, timestamp.
  - `security.mfa_disabled`: Records `user_id`, `organization_id`, timestamp.
  - `security.mfa_verification_success`: Records `user_id`, `method` (`totp` | `recovery_code`), timestamp.
  - `security.mfa_verification_failed`: Records `user_id`, failure reason, timestamp.
  - `security.mfa_recovery_used`: Records `user_id`, remaining codes count, timestamp.

### 8.22 PostgreSQL Performance Optimization & Composite Index Strategy (Era 11 Phase 11.1)
- **Composite Indexing Migration (`0004_add_performance_indexes.py`)**:
  - `ix_users_org_role`: `users` (`organization_id`, `role`) for tenant user role filters.
  - `ix_users_org_active`: `users` (`organization_id`, `is_active`) for tenant active user queries.
  - `ix_audit_logs_org_action`: `audit_logs` (`organization_id`, `action`) for tenant SIEM action filtering.
  - `ix_audit_logs_org_created`: `audit_logs` (`organization_id`, `created_at DESC`) for SIEM history pagination.
  - `ix_refresh_tokens_user_revoked`: `refresh_tokens` (`user_id`, `is_revoked`) for auth token validation.
  - `ix_api_keys_org_active`: `api_keys` (`organization_id`, `is_active`) for M2M authorization checks.
- **SQLAlchemy Async Connection Pooling**:
  - Configured `pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=1800`, `pool_pre_ping=True`.
- **Query Analyzer & Slow Query Listener**:
  - `QueryAnalyzerService` & `DatabaseQueryMonitor` capturing execution duration metadata for queries > 100ms.


---

## 💾 9. Database Production Reliability & Disaster Recovery Considerations (Planned Era 11)

Era 11 specifies the database production reliability strategy for PostgreSQL 16:

### 1. Backup Strategy & Scheduling
- **Full Base Backups**: Daily automated full physical backups taken via `pgBackRest` or `pg_dumpall`, stored in multi-region encrypted S3/GCS buckets (`AES-256` encryption at rest).
- **WAL Streaming & Retention**: Continuous Write-Ahead Log (WAL) archiving enabled with a strict 30-day retention policy to support granular recovery windows.

### 2. Point-in-Time Recovery (PITR)
- **Targeted PITR Restoration**: Enables restoring PostgreSQL state to any precise millisecond within the 30-day retention window.
- **Recovery Point Objective (RPO)**: Guarantees RPO < 5 minutes of potential data loss in catastrophic hardware failure scenarios.

### 3. Read Replication & Connection Pooling
- **Streaming Replication**: Primary-replica PostgreSQL streaming replication topology with automated health failover.
- **PgBouncer Connection Pooling**: Transaction-level connection pooling (`PgBouncer`) capping active backend PostgreSQL connections and preventing pool exhaustion under peak API concurrency.

### 4. Restore Verification & Automated Testing
- **Automated Restore Testing**: Daily automated sandbox restore job that downloads the latest backup, performs PITR recovery to an isolated test database, runs integrity verification queries (`SELECT count(*) FROM security_findings`), and reports restore duration metrics.




