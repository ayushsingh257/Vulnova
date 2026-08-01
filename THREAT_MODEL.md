# Vulnova — STRIDE Threat Model & Risk Assessment (THREAT_MODEL.md)

This document presents the formal **STRIDE Threat Model** for Vulnova, evaluating potential security threats across the system's attack surface—including scanner sandboxing and legal target authorization—and specifying concrete mitigation controls.

---

## 🎯 1. STRIDE Threat Matrix Overview

| Threat Category | Target Subsystem | Description | Likelihood | Impact | Severity | Primary Mitigation Control |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **Spoofing** | API Gateway | Attacker impersonates valid user or API client | Medium | High | **HIGH** | OAuth2 JWT verification, RS256 signature check, API key hashing |
| **Tampering** | Scan Findings / DB | Attacker alters scan findings or severity scores | Low | High | **HIGH** | DB parameterization, RBAC authorization, signed audit logs |
| **Repudiation** | User Actions | User denies launching scan against target URL | Low | Medium | **MEDIUM** | Immutable audit log of scan authorization declaration & client IP |
| **Info Disclosure**| Multi-Tenant Storage | Tenant A views target scans or findings of Tenant B | Medium | High | **CRITICAL** | Row-level tenant isolation, mandatory `org_id` context filters |
| **Denial of Service**| Scanner Sandbox | Malicious scan targets cause infinite crawl loops or worker RAM exhaustion | High | High | **HIGH** | Container CPU/RAM limits (1 vCPU, 512MB RAM), execution timeouts (60s) |
| **Elevation of Priv**| Role Management | Analyst escalates role to Admin or Owner | Low | High | **HIGH** | Strict FastAPI dependency injectors checking granular RBAC scopes |
| **Sandbox Escape** | Scanner Worker | Malicious payload breaks out of container to compromise host or internal network | Low | Critical | **CRITICAL** | Unprivileged containers (`UID 10001`), `read_only_rootfs`, egress proxy filtering internal IP ranges |
| **Unauthorized Scan**| Target Scanner | Malicious tenant uses Vulnova to scan third-party target without permission | Medium | High | **HIGH** | Mandatory "Authorized Security Assessment Confirmation" & DNS TXT verification |

---

## 🔍 2. Detailed Threat Analysis & Mitigations

### A. Sandbox Escape & Platform Compromise
- **Threat Vector**: A malicious web target returns an exploit payload targeting Chromium or Playwright parser vulnerabilities to gain container root shell and attempt pivoting into Vulnova's database.
- **Mitigation**: Scanner workers execute under `UID 10001` with `read_only_rootfs: true` and all Linux capabilities dropped. Worker network access is constrained to an isolated bridge network; egress proxy strictly blocks connections to internal IP ranges (`10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.1`, `169.254.169.254`).

### B. Unauthorized Target Scanning & Legal Liability
- **Threat Vector**: An authenticated user submits a target URL belonging to an unconsenting competitor organization.
- **Mitigation**: Scan dispatcher requires mandatory completion of the "Authorized Security Assessment Confirmation" contract. High-intensity scan profiles require domain verification via DNS TXT records. All scan creation events generate immutable audit records with cryptographic declaration hashes.

### C. Information Disclosure (Cross-Tenant Leakage)
- **Threat Vector**: Tenant isolation breakdown resulting in cross-organization finding leakage.
- **Mitigation**: All database queries automatically append `WHERE organization_id = :org_id` bound from authenticated JWT context. Automated security integration tests verify cross-tenant boundary security.

### D. Denial of Service (Scanner Exhaustion)
- **Threat Vector**: Target web application responds with dynamic infinite link loops or zip bombs.
- **Mitigation**: Crawlers execute with strict execution timeouts (max 60s per URL), depth caps (max 5 levels), response body size caps (max 10MB), and Celery worker container memory bounds (512MB limit per worker).

---

## 📈 3. Vulnerability Remediation Lifecycle & SLA Matrix

| Finding Severity | Target Remediation SLA | Enterprise Escalation Path |
| :--- | :--- | :--- |
| 🔴 **CRITICAL** | 24 Hours | Immediate Slack/Teams page, automatic ticket creation |
| 🟠 **HIGH** | 7 Days | Jira issue dispatch, notification email to SecOps team |
| 🟡 **MEDIUM** | 30 Days | Included in weekly vulnerability triage report |
| 🟢 **LOW / INFO** | 90 Days / Backlog | Monitored in dashboard backlog |
