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

-- Scan Targets
CREATE TABLE scan_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    target_url TEXT NOT NULL,
    environment VARCHAR(50) DEFAULT 'PRODUCTION',
    is_ownership_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ownership_verification_token VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_scan_targets_org ON scan_targets(organization_id);

-- Assessment Jobs (Phase 4.1 & Phase 4.7 Enterprise Policy Engine)
CREATE TABLE assessment_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    profile_id VARCHAR(100) DEFAULT 'full_assessment', -- Stores selected enterprise scan profile (e.g. 'web_scan', 'api_scan')
    policy_json JSONB, -- Stores execution policy configuration (concurrency, RPS rate limit, scope globs, auth, stop_on_critical)
    enabled_plugins_json JSONB,
    duration_seconds NUMERIC(10, 2),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assessment_jobs_org_status ON assessment_jobs(organization_id, status);
CREATE INDEX idx_assessment_jobs_org_profile ON assessment_jobs(organization_id, profile_id);

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

-- Vector Embeddings for Knowledge Base & RAG
CREATE TABLE security_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(100) NOT NULL, -- 'OWASP', 'CWE', 'ADVISORY'
    title VARCHAR(255) NOT NULL,
    content_text TEXT NOT NULL,
    embedding vector(1536), -- Vector dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
-- HNSW Vector Index for Similarity Search
CREATE INDEX idx_security_embeddings_vector ON security_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

---

## ⚡ 4. Redis Cache Key Topologies

| Key Pattern | Data Type | TTL | Purpose |
| :--- | :--- | :--- | :--- |
| `rate_limit:{ip}` | String / Counter | 60 sec | API rate limiting token bucket |
| `session:{user_id}` | Hash | 15 min | User active session data |
| `scan_progress:{scan_id}`| Hash | 24 hrs | Real-time scan execution metrics |
| `ws_channel:{scan_id}` | Pub/Sub Channel | Real-time | Live progress streaming to clients |
