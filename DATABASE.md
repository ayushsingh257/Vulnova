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
