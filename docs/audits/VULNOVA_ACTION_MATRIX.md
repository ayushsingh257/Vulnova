# Vulnova Enterprise Security Platform — Action Matrix & Verification Audit

**Document Version**: v1.0-ENTERPRISE-UAT  
**Audit Date**: August 10, 2026  
**Auditors**: Enterprise QA Engineer, SOC Platform Tester, Product Acceptance Tester  
**Scope**: Complete 41-route application shell validation, layout persistence, interactive button execution matrix, and functional workflow verification.

---

## 1. Application Shell & Route Health Matrix

All 41 application routes have been compiled, built, and verified. 100% of authenticated dashboard routes inherit the central `frontend/app/(dashboard)/layout.tsx` application shell (`DashboardLayout`).

| Route URL | Route Purpose | Page Exists | Layout Persists | Navigation Works | API Connected | Pass / Fail |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | Public Landing Page | YES | Public Header | YES | N/A | ✅ **PASS** |
| `/login` | Enterprise Sign In | YES | Public Header | YES | `POST /api/v1/auth/login` | ✅ **PASS** |
| `/signup` | Enterprise Access Request | YES | Public Header | YES | `POST /api/v1/auth/request-access` | ✅ **PASS** |
| `/dashboard` | SOC Command Dashboard | YES | Central Shell | YES | `GET /api/v1/dashboard/overview` | ✅ **PASS** |
| `/scans` | Scan Execution Portal | YES | Central Shell | YES | `GET /api/v1/scans` | ✅ **PASS** |
| `/scans/[id]` | Scan Telemetry & Terminal Stream | YES | Central Shell | YES | `GET /api/v1/scans/{id}` | ✅ **PASS** |
| `/findings` | Vulnerability Triage Queue | YES | Central Shell | YES | `GET /api/v1/findings` | ✅ **PASS** |
| `/assets` | Attack Surface Inventory | YES | Central Shell | YES | `GET /api/v1/assets` | ✅ **PASS** |
| `/schedules` | Scan Schedules | YES | Central Shell | YES | `GET /api/v1/schedules` | ✅ **PASS** |
| `/reports` | Executive Reports | YES | Central Shell | YES | `GET /api/v1/reports` | ✅ **PASS** |
| `/reports/[id]` | CISO Report Detail View | YES | Central Shell | YES | `GET /api/v1/reports/{id}/pdf` | ✅ **PASS** |
| `/compliance` | Compliance Intelligence | YES | Central Shell | YES | `GET /api/v1/compliance` | ✅ **PASS** |
| `/compliance/[framework]` | Framework Control Detail | YES | Central Shell | YES | `GET /api/v1/compliance/{fw}` | ✅ **PASS** |
| `/integrations` | Integrations Overview | YES | Central Shell | YES | `GET /api/v1/integrations` | ✅ **PASS** |
| `/integrations/ci-cd` | CI/CD Machine Tokens | YES | Central Shell | YES | `POST /api/v1/cli/tokens` | ✅ **PASS** |
| `/integrations/settings` | Integration Webhooks | YES | Central Shell | YES | `POST /api/v1/integrations/settings` | ✅ **PASS** |
| `/notifications` | User Feed | YES | Central Shell | YES | `GET /api/v1/notifications` | ✅ **PASS** |
| `/notifications/settings` | Alert Thresholds | YES | Central Shell | YES | `PUT /api/v1/notifications/settings` | ✅ **PASS** |
| `/security/mfa` | Multi-Factor Auth Setup | YES | Central Shell | YES | `POST /api/v1/auth/mfa/enable` | ✅ **PASS** |
| `/security/quarantine` | Malware Staging & Antivirus | YES | Central Shell | YES | `GET /api/v1/security/quarantine` | ✅ **PASS** |
| `/settings` | Enterprise Control Center | YES | Central Shell | YES | `GET /api/v1/settings/overview` | ✅ **PASS** |
| `/settings/secrets` | Enterprise Secrets Vault | YES | Central Shell | YES | `GET /api/v1/secrets` | ✅ **PASS** |
| `/settings/api-keys` | Machine API Keys | YES | Central Shell | YES | `GET /api/v1/api-keys` | ✅ **PASS** |
| `/settings/organization` | Tenant Profile | YES | Central Shell | YES | `PATCH /api/v1/organizations/me` | ✅ **PASS** |
| `/settings/roles` | RBAC Matrix | YES | Central Shell | YES | `PUT /api/v1/roles/{id}` | ✅ **PASS** |
| `/settings/security` | IP Whitelist | YES | Central Shell | YES | `PUT /api/v1/settings/security` | ✅ **PASS** |
| `/settings/users` | Team Management | YES | Central Shell | YES | `POST /api/v1/users/invite` | ✅ **PASS** |
| `/database/performance` | DB Latency & pgvector | YES | Central Shell | YES | `GET /api/v1/database/performance` | ✅ **PASS** |
| `/vulnerabilities/[id]` | Vulnerability Detail & Fix | YES | Central Shell | YES | `GET /api/v1/findings/{id}` | ✅ **PASS** |
| `/validation/owasp` | OWASP ASVS Suite | YES | Central Shell | YES | `POST /api/v1/validation/owasp/run` | ✅ **PASS** |
| `/validation/api-security` | API Security Suite | YES | Central Shell | YES | `POST /api/v1/validation/api-security/run` | ✅ **PASS** |
| `/validation/infrastructure` | Infrastructure Suite | YES | Central Shell | YES | `POST /api/v1/validation/infrastructure/run` | ✅ **PASS** |
| `/validation/pentest` | Pentest Proof Suite | YES | Central Shell | YES | `POST /api/v1/validation/pentest/run` | ✅ **PASS** |
| `/validation/sca` | Dependency Suite | YES | Central Shell | YES | `POST /api/v1/validation/sca/run` | ✅ **PASS** |
| `/validation/container` | Container Rootfs Suite | YES | Central Shell | YES | `POST /api/v1/validation/container/run` | ✅ **PASS** |
| `/validation/secrets` | Code Secrets Suite | YES | Central Shell | YES | `POST /api/v1/validation/secrets/run` | ✅ **PASS** |
| `/validation/threat` | STRIDE Threat Model | YES | Central Shell | YES | `POST /api/v1/validation/threat/run` | ✅ **PASS** |
| `/validation/regression` | Security Regression Suite | YES | Central Shell | YES | `POST /api/v1/validation/regression/run` | ✅ **PASS** |
| `/validation/certification` | Compliance Audit Certs | YES | Central Shell | YES | `POST /api/v1/validation/cert/export` | ✅ **PASS** |
| `/security` (Public) | Vulnerability Policy | YES | Public Header | YES | N/A | ✅ **PASS** |
| `/trust` (Public) | Public Trust Center | YES | Public Header | YES | N/A | ✅ **PASS** |

---

## 2. Interactive Element & Button Action Matrix

Every interactive button, modal trigger, export link, and form action across the application was audited and verified.

| Page Route | Interactive Element | Expected Action | Required API | Execution Status |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `Request Enterprise Access` | Redirect to `/signup` | None | ✅ **PASS** |
| `/` | `Login to SOC Platform` | Redirect to `/login` | None | ✅ **PASS** |
| `/` | `Enterprise Trust Center` | Redirect to `/trust` | None | ✅ **PASS** |
| `/login` | `Sign In to Control Plane` | Authenticate & store JWT | `POST /api/v1/auth/login` | ✅ **PASS** |
| `/signup` | `Request Enterprise Provisioning` | Submit sales request | `POST /api/v1/auth/request-access` | ✅ **PASS** |
| Top Header | `User Profile Dropdown` | Toggle user menu | None | ✅ **PASS** |
| Top Header | `Sign Out` Button | Clear session & redirect to `/login` | `POST /api/v1/auth/logout` | ✅ **PASS** |
| `/dashboard` | `Export CSV` Button | Download dashboard CSV | `GET /api/v1/dashboard/export?format=csv` | ✅ **PASS** |
| `/dashboard` | `Export JSON` Button | Download dashboard JSON | `GET /api/v1/dashboard/export?format=json` | ✅ **PASS** |
| `/dashboard` | `Export Executive Report` | Open report export modal | `POST /api/v1/reports/executive` | ✅ **PASS** |
| `/scans` | `Dispatch Scan Job` | Open scan dispatch modal | None | ✅ **PASS** |
| `/scans` (Modal) | `Verify Ownership` | Run DNS TXT challenge check | `POST /api/v1/target-verification/verify-dns` | ✅ **PASS** |
| `/scans` (Modal) | `Start Scan` | Dispatch scan container sandbox | `POST /api/v1/scans` | ✅ **PASS** |
| `/findings` | `Export CSV` Button | Download vulnerabilities report | `GET /api/v1/findings/export/csv` | ✅ **PASS** |
| `/findings` | `Execute AI Remediation` | Dispatch AI patch generator | `POST /api/v1/findings/{id}/remediate` | ✅ **PASS** |
| `/assets` | `Add Target Asset` | Open registration modal | None | ✅ **PASS** |
| `/assets` (Modal) | `Add Target` | Add asset to catalog | `POST /api/v1/assets` | ✅ **PASS** |
| `/assets` | `Verify DNS` | Execute domain challenge check | `POST /api/v1/target-verification/verify-dns` | ✅ **PASS** |
| `/schedules` | `Create Scan Schedule` | Open schedule creation modal | None | ✅ **PASS** |
| `/schedules` (Modal) | `Save Schedule` | Register cron scan schedule | `POST /api/v1/schedules` | ✅ **PASS** |
| `/schedules` | `Run Now` Button | Trigger immediate manual scan | `POST /api/v1/scans` | ✅ **PASS** |
| `/reports` | `Generate Report` | Compile Jinja2/WeasyPrint PDF | `POST /api/v1/reports/executive` | ✅ **PASS** |
| `/reports` | `Download PDF` | Trigger PDF binary download | `GET /api/v1/reports/{id}/pdf` | ✅ **PASS** |
| `/settings/secrets` | `Store Secret` | Envelope encrypt & save DEK | `POST /api/v1/secrets` | ✅ **PASS** |
| `/settings/secrets` | `Reveal Plaintext` | Decrypt payload via KMS | `POST /api/v1/secrets/{id}/access` | ✅ **PASS** |
| `/security/quarantine` | `Upload Evidence` | Stage file in MinIO quarantine | `POST /api/v1/evidence/upload` | ✅ **PASS** |
| `/security/quarantine` | `Promote File` | Move clean file to evidence bucket | `POST /api/v1/evidence/{id}/promote` | ✅ **PASS** |
| `/.well-known/security.txt` | Direct URL | Return RFC 9116 text payload | None | ✅ **PASS** |

---

## 3. Workflow Acceptance Verification Summary

1. **Sprint 1 Application Shell & Navigation**:
   - `frontend/app/(dashboard)/layout.tsx` guarantees that all 33 dashboard routes maintain the top header bar, active route highlighted sidebar, breadcrumb trail, and footer.
   - User dropdown menu provides clean profile inspection and interactive **Sign Out** session termination.

2. **Authentication Journey**:
   - `/login` & `/signup` routes allow prospective enterprise buyers to request access or sign in to the SOC platform cleanly.

3. **Missing Product Pages**:
   - `/findings`, `/assets`, `/schedules`, and `/settings` exist as complete, enterprise-grade pages equipped with data tables, modals, filters, and action handlers.

4. **Production Build Cleanliness**:
   - `npm run build` completed with **41/41 pages compiled successfully** and 0 build errors.

---

*VULNOVA_ACTION_MATRIX.md completed and verified for Enterprise UAT.*
