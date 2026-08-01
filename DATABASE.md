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

-- Scan Jobs
CREATE TABLE scan_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES scan_targets(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES scan_profiles(id),
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    authorization_declaration_hash VARCHAR(255) NOT NULL,
    progress_percentage INT DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_scan_jobs_org_status ON scan_jobs(organization_id, status);

-- Findings
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scan_job_id UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    plugin_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    cvss_score NUMERIC(3, 1),
    cwe_id VARCHAR(50),
    target_url TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN', -- 'OPEN', 'TRIAGED', 'FALSE_POSITIVE', 'REMEDIATED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_findings_scan_job ON findings(scan_job_id);
CREATE INDEX idx_findings_org_severity ON findings(organization_id, severity);

-- Vulnerability History Tracking
CREATE TABLE vulnerability_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    previous_status VARCHAR(50) NOT NULL,
    new_status VARCHAR(50) NOT NULL,
    changed_by_user_id UUID REFERENCES users(id),
    reason TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_vuln_history_finding ON vulnerability_history(finding_id);

-- Decoupled Evidence Management System
CREATE TABLE evidence_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL, -- 'HTTP_REQUEST', 'HTTP_RESPONSE', 'SCREENSHOT', 'PROOF_PAYLOAD'
    raw_payload TEXT,
    screenshot_url TEXT,
    payload_hash VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) DEFAULT 'application/json',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_evidence_finding ON evidence_records(finding_id);

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
