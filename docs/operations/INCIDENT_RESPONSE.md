# Vulnova Security Incident Response & Audit Escalation Runbook

This document defines the enterprise security incident response lifecycle, severity classification matrix, escalation procedures, forensic audit correlation workflows, breach notification protocols, and Post-Incident Review (PIR) standards for the Vulnova platform.

---

## 1. Incident Severity Classification Matrix

Vulnova classifies security incidents into four distinct severity tiers based on threat impact, data sensitivity, blast radius, and system availability.

| Severity Level | Name | Description & Trigger Criteria | Target MTTA | Target MTTC | Target MTTR | Escalation Channels |
|---|---|---|---|---|---|---|
| **SEV-1** | **Critical** | Active security breach, unauthorized data exfiltration, tenant boundary violation (BOLA/IDOR cross-org compromise), total auth bypass, or multi-service security failure. | `< 5 min` | `< 30 min` | `< 4 hours` | PagerDuty (Immediate Page), Slack (`#security-incident-sev1`), Email (Exec Team + Legal) |
| **SEV-2** | **High** | High-severity vulnerability actively exploited in production, uncontained privilege escalation (Viewer/Analyst $\rightarrow$ Admin/Owner), mass API key leakage, or significant suspicious scanning. | `< 15 min` | `< 1 hour` | `< 8 hours` | Slack (`#security-incident-sev2`), PagerDuty, Email (Security Leads) |
| **SEV-3** | **Medium** | Limited-impact security event, policy violation (e.g. repeated brute-force rate limit trigger, anomalous credential rotation, single-service DDoS mitigation), or misconfiguration without active exploit. | `< 1 hour` | `< 4 hours` | `< 24 hours` | Slack (`#security-alerts`), Email (Security Analysts) |
| **SEV-4** | **Low** | Informational security event, minor anomaly, dependency CVE without direct exploitability, routine compliance scan discrepancy, or non-actionable vulnerability report. | `< 4 hours` | `< 24 hours` | `< 72 hours` | Jira Ticket, Slack (`#security-low-priority`) |

---

## 2. 7-Phase Security Incident Lifecycle

Vulnova executes a structured 7-phase incident management lifecycle:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             7-Phase Security Incident Lifecycle                             │
├─────────────┬────────────┬─────────────┬───────────────┬─────────────┬───────────┬──────────┤
│ 1.Detection │  2.Triage  │3.Containment│4.Investigation│5.Eradication│6.Recovery │  7.PIR   │
│ (Alerts/    │ (Severity  │ (Network/   │  (Forensics/  │  (Patches/  │ (Restore/ │ (Root    │
│  AuditLogs) │  Assigned) │  Tokens)    │  Audit Logs)  │   Revoke)   │ Validate) │  Cause)  │
└─────────────┴────────────┴─────────────┴───────────────┴─────────────┴───────────┴──────────┘
```

### Phase 1: Detection
- **Automated Triggers**: Sentry exceptions, Prometheus anomaly alerts, rate limiter DDoS threshold trips, unauthorized DB access logs, failed JWT signature spikes.
- **Audit Log Telemetry**: Continuous ingestion from `AuditLogService` monitoring action patterns (`auth.login_failed`, `api_key.revoked`, `user.role_escalated`).
- **External Reports**: Responsible disclosure reports, customer support escalations, or cloud provider abuse notifications.

### Phase 2: Triage
- **Initial Assessment**: Incident Commander (IC) validates veracity, filters false positives, and assigns severity (`SEV-1` through `SEV-4`).
- **War Room Activation**: For `SEV-1` and `SEV-2`, an automated Slack channel (`#incident-YYYYMMDD-<id>`) and incident conference bridge are spawned.
- **Role Assignment**: IC assigns Technical Lead, Communications Lead, and Scribe.

### Phase 3: Containment
- **Short-Term Containment**:
  - Isolate affected containers via network policy or bridge disconnection.
  - Invalidate compromised user sessions (`MultiLayerCacheManager.invalidate_user_session`).
  - Revoke affected API keys (`APIKeyModel.is_active = False`) and rotate JWT signing secrets if compromised.
- **Long-Term Containment**:
  - Apply temporary WAF/Rate Limiting block rules for offending IP addresses/ranges.
  - Freeze tenant write operations if cross-tenant corruption is suspected.

### Phase 4: Forensic Investigation
- **Audit Log Correlation**: Query `AuditLogService` across actor IDs, tenant organization boundaries, timestamps, and client IP addresses.
- **Blast Radius Analysis**: Determine precisely which records, vulnerabilities, API keys, or tenant assets were accessed or exfiltrated.
- **Chain of Custody & Evidence Preservation**: Generate SHA-256 cryptographic digests of database snapshots, log archives, and memory dumps before taking remediation action.

### Phase 5: Eradication
- **Vulnerability Remediation**: Deploy code fixes, emergency security patches, or configuration updates through CI/CD pipelines.
- **Credential Rotation**: Force password resets for affected accounts and regenerate all tenant API keys and webhook secrets.
- **Malicious Artifact Removal**: Purge injected payloads, stale temporary files, or backdoored worker tasks.

### Phase 6: Service Recovery
- **Dependency-Ordered Restoration**: Follow Vulnova DR sequence (PostgreSQL $\rightarrow$ Redis $\rightarrow$ Backend API $\rightarrow$ Celery Workers $\rightarrow$ Frontend).
- **Integrity Validation**: Execute health probes (`/api/v1/system/health`, `/api/v1/system/readiness`) and dry-run query benchmarks.
- **Monitoring Intensification**: Maintain heightened 48-hour monitoring on affected endpoints for recurrence.

### Phase 7: Post-Incident Review (PIR)
- **Timeline Reconstruction**: Document second-by-second chronology from detection to resolution.
- **Root Cause Analysis (5 Whys)**: Identify systemic contributing factors rather than surface symptoms.
- **Action Items & Governance**: File corrective tickets with clear owners and 14-day SLA completion dates.

---

## 3. Incident Ownership & Roles

| Role | Responsibilities | Assigned Persona |
|---|---|---|
| **Incident Commander (IC)** | Holds ultimate decision-making authority, directs containment strategy, and oversees lifecycle transitions. | Principal Security Engineer / CISO |
| **Technical Lead** | Coordinates engineering investigation, develops patches, and manages technical containment. | Lead Backend / Platform Engineer |
| **Communications Lead** | Manages internal executive briefings, customer notifications, and public communications. | VP of Engineering / Legal Counsel |
| **Scribe** | Maintains chronological log of decisions, timestamps, actions taken, and evidence references. | Senior Security Analyst |

---

## 4. Escalation Timeline & Communication Workflow

```text
Time 0:00 ──► Incident Detected (Audit Log / Prometheus / User Report)
Time 0:05 ──► Triage complete; Severity set; PagerDuty / Slack war room created
Time 0:15 ──► Tech Lead engages containment; compromised tokens & IPs revoked
Time 0:30 ──► Executive status briefing; Customer Comms Lead drafts advisory (if SEV-1)
Time 1:00 ──► Containment verified; Forensic root cause analysis underway
Time 4:00 ──► Eradication complete; Emergency patch deployed to production
Time 8:00 ──► Services restored & validated; Post-Incident Review meeting scheduled
```

---

## 5. Evidence Preservation & Chain of Custody

1. **Snapshot Creation**: Capture immediate read-only EBS/database snapshots before performing database updates.
2. **Log Freeze**: Export audit logs for the incident window into immutable encrypted storage with SHA-256 checksums:
   ```bash
   sha256sum var/logs/audit_incident_<id>.json > var/logs/audit_incident_<id>.sha256
   ```
3. **Container State Export**: Save runtime container logs and ephemeral state:
   ```bash
   docker logs vulnova-backend-api > /secure_storage/incident_<id>_api.log
   ```

---

## 6. Breach Notification Readiness Protocols

### GDPR Article 33/34 Compliance (72-Hour Mandate)
- If personal data breach occurs, notify supervisory authorities within **72 hours** of becoming aware.
- Notify affected data subjects without undue delay if high risk to rights and freedoms.

### HIPAA & SOC 2 Trust Services Criteria
- Breach assessment documented within 24 hours.
- Business Associate (BA) notifications issued within contractual timelines.

### Regulatory Checklist:
- [ ] Nature of the security incident and categories of data involved.
- [ ] Approximate number of data subjects and records impacted.
- [ ] Name and contact details of the Data Protection Officer / Security Lead.
- [ ] Likely consequences and residual risks.
- [ ] Remediation measures taken or proposed to mitigate negative effects.

---

## 7. Post-Incident Review (PIR) Template

```markdown
# Post-Incident Review: [INCIDENT-ID] - [Title]

## 1. Executive Summary
- **Severity**: SEV-1 / SEV-2 / SEV-3 / SEV-4
- **Incident Commander**: [Name]
- **Date & Time of Incident**: YYYY-MM-DD HH:MM UTC
- **Duration (MTTR)**: [X hours, Y minutes]
- **Impact Summary**: [Brief summary of affected tenants, services, and data exposure]

## 2. Chronological Timeline
| Timestamp (UTC) | Phase | Event / Action Taken | Actor |
|---|---|---|---|
| YYYY-MM-DD 14:02 | Detection | Anomaly alert fired for excessive token revocations | System |
| YYYY-MM-DD 14:06 | Triage | Incident classified as SEV-1; War room opened | IC |
| YYYY-MM-DD 14:18 | Containment | Offending IP blocked; Leaked API key revoked | Tech Lead |
| YYYY-MM-DD 15:30 | Eradication | Hotfix deployed with patched authorization checks | Tech Lead |
| YYYY-MM-DD 16:00 | Recovery | System health verified 100%; Incident closed | IC |

## 3. Root Cause Analysis (5 Whys)
1. **Why did the breach occur?** An unauthorized API request accessed another tenant's finding.
2. **Why was the request permitted?** The endpoint omitted tenant ID verification in the path parameter.
3. **Why was the tenant check missing?** A new route was added without the `require_same_organization` dependency.
4. **Why was it not caught in CI?** The BOLA validation suite test was missing for that specific route.
5. **Why was the test missing?** The route was added during an emergency hotfix outside standard PR checks.

## 4. What Went Well
- Automated audit logs captured full attacker IP and query parameters.
- Containment was achieved within 12 minutes of triage.

## 5. Where We Got Lucky / Areas for Improvement
- Attacker did not attempt automated exfiltration after initial probe.
- Alert routing for SEV-2 events needs faster SMS escalation.

## 6. Corrective Action Items
| Action Item | Priority | Owner | Due Date | Status |
|---|---|---|---|---|
| Add mandatory BOLA assertion for all dynamic router endpoints | P0 | @backend-lead | 7 days | Open |
| Enforce pre-commit CI lint rule for `require_same_organization` | P1 | @devops-lead | 14 days | Open |
| Update external penetration test suite scenarios | P2 | @security-lead | 30 days | Open |
```
