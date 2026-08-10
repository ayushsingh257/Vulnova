# Vulnova Enterprise Security Platform — Product Completion & Release Roadmap

**Document Version**: v1.0-RELEASE-PLAN  
**Date**: August 10, 2026  
**Authors**: Enterprise Product Manager, Senior Frontend Architect, UX Engineer  
**Status**: APPROVED ARCHITECTURAL ROADMAP (**Implementation Pending User Signal**)

---

## Executive Overview & Product Positioning

Vulnova's backend control plane is fully realized: FastAPI endpoints, PostgreSQL database, MinIO quarantine staging, ClamAV antivirus daemon, YARA static inspection, and ECDSA plugin validation are operational. 

However, product discovery and user acceptance testing revealed that **the frontend acts as an engine without a unified cockpit**:
1. Critical navigation items in the sidebar (`/findings`, `/assets`, `/schedules`, `/settings`) return **404 Not Found**.
2. Eight dashboard subpages lack the `<DashboardLayout>` wrapper, causing top header and sidebar navigation to disappear.
3. Users bypass authentication entirely, accessing `/dashboard` anonymously without a `/login` interface.
4. The homepage positioning uses generic messaging instead of clear value propositions for enterprise security buyers.

This roadmap transforms Vulnova into a **commercial-grade, production-ready enterprise security platform** across 6 structured execution phases.

---

## PHASE 1: Application Usability Foundation

### 1. Central Dashboard Layout Architecture (`app/(dashboard)/layout.tsx`)
- **Objective**: Create `frontend/app/(dashboard)/layout.tsx` using Next.js 14 App Router layout hierarchy.
- **Inheritance Structure**:
  ```
  app/(dashboard)/layout.tsx
  ├── <DashboardLayout>
  │   ├── <TopHeaderBar> (Logo, Global Search, Active Stream Indicator, User Dropdown, Notifications)
  │   ├── <SidebarNav> (Active Route Highlight, Section Groupings)
  │   ├── <main className="flex-1 p-6 max-w-7xl mx-auto">
  │   │   └── {children} (Page Content)
  │   └── <Footer> (Product Version, Status Badge, Security Policy Links)
  ```
- **Impact**: All 33 dashboard routes automatically inherit the top header, sidebar navigation, and footer without manual wrapper duplication.

### 2. Header & Sidebar Consistency
- **Active Route Highlighting**: Automatically highlight active sidebar items matching `usePathname()`.
- **Navigation Resilience**: Ensure sub-routes (`/settings/secrets`, `/validation/owasp`, `/scans/[id]`) preserve sidebar state.
- **Top Header User Dropdown**: Add user profile widget displaying user email, tenant organization, and `Logout` menu action.

### 3. Global Error Handling & Loading States
- **Error Boundaries**: Create `frontend/app/(dashboard)/error.tsx` catching client-side rendering exceptions with clean recovery options (`Try Again`, `Return to Dashboard`).
- **Loading Skeletons**: Create `frontend/app/(dashboard)/loading.tsx` providing skeleton loader cards during async API fetches.
- **Toast Notifications**: Integrate global toast notification provider for background API success/failure alerts.

---

## PHASE 2: Authentication & Enterprise Access Management

### 1. Enterprise Login Page (`/login`)
- **Route**: `frontend/app/(public)/login/page.tsx`
- **Purpose**: Authenticate enterprise security personnel using email/password and optional TOTP MFA.
- **UI Components**: Logo, Email Input, Password Input, TOTP Code Input (if MFA enabled), `Remember Me` checkbox, `Sign In` button.
- **API Integration**: `POST /api/v1/auth/login`
- **Behavior**: On HTTP 200, save JWT access token to `localStorage` / HttpOnly cookie, initialize `AuthContext`, and redirect user to `/dashboard`. On HTTP 401, display `Invalid email or password` alert.

### 2. Enterprise Access Request & Demo Page (`/signup`)
- **Route**: `frontend/app/(public)/signup/page.tsx`
- **Purpose**: Allow prospective enterprise customers to request access or schedule an enterprise SOC demo.
- **UI Components**: Full Name, Work Email, Company Name, Team Size Selector, Target Environment Count, `Request Enterprise Access` button.
- **Behavior**: Submits contact payload to sales webhook (`POST /api/v1/auth/request-access`) and displays confirmation modal.

### 3. Session Management & Logout
- **Logout Action**: User profile dropdown in top header bar triggers session termination.
- **Behavior**: Calls `POST /api/v1/auth/logout`, removes tokens from `localStorage`, resets `AuthContext` state, and redirects user to `/login`.

### 4. Protected Route Middleware (`middleware.ts`)
- **Objective**: Intercept requests to `/(dashboard)/*` routes.
- **Behavior**: Check for valid JWT token. If missing or expired, redirect request to `/login?redirect={target_path}`.

---

## PHASE 3: Missing Product Pages Implementation

### Page 1: Vulnerabilities & Finding Queue (`/findings`)
- **Purpose**: Provide security analysts with an enterprise triage queue for all discovered vulnerability findings across target assets.
- **User Journey**: Analyst navigates to `/findings` $\rightarrow$ filters by severity (`CRITICAL`, `HIGH`) $\rightarrow$ views finding detail modal $\rightarrow$ approves AI remediation patch or marks false positive.
- **Required APIs**: `GET /api/v1/findings`, `PATCH /api/v1/findings/{id}/status`, `POST /api/v1/findings/{id}/remediate`.
- **UI Sections**:
  1. Severity Summary Counter Bar (Critical, High, Medium, Low counts)
  2. Search & Multi-Filter Toolbar (Search title/CVE, Severity Filter, Target Filter, Status Filter)
  3. Finding List Data Table (Finding Title, CVE ID, Target Asset, CVSS Score, Status Badge, Actions)
  4. Finding Detail Modal (Evidence Proof, HTTP Trace, AI Confidence Analysis, Remediation Patch)
- **Buttons & Expected Behavior**:
  - `Export CSV`: Trigger download of `vulnerabilities-report.csv`.
  - `View Evidence`: Open finding detail modal.
  - `Approve AI Fix`: Submit `POST /api/v1/findings/{id}/remediate` and update status badge to `REMEDIATING`.

---

### Page 2: Attack Surface & Asset Inventory (`/assets`)
- **Purpose**: Centralized asset management catalog tracking registered domains, API endpoints, microservices, and cloud targets.
- **User Journey**: Analyst views target assets $\rightarrow$ clicks `Add Target Asset` $\rightarrow$ submits domain URL $\rightarrow$ initiates DNS TXT verification challenge (`vulnova-verify`).
- **Required APIs**: `GET /api/v1/assets`, `POST /api/v1/assets`, `POST /api/v1/target-verification/verify-dns`, `DELETE /api/v1/assets/{id}`.
- **UI Sections**:
  1. Target Environment Stats Cards (Total Assets, Verified Production Targets, Staging Targets)
  2. Add Target Asset Action Bar
  3. Asset Catalog Table (Target Name, URL, Environment, Ownership Verification Badge, Composite Risk Score, Actions)
  4. Target Registration Modal (Domain URL, Environment, Asset Owner Email)
- **Buttons & Expected Behavior**:
  - `Add Target Asset`: Open Target Registration Modal.
  - `Verify Ownership`: Trigger DNS/HTTP verification check and update badge to `VERIFIED`.
  - `Run Immediate Scan`: Launch new scan job for asset on `/scans`.

---

### Page 3: Recurring Scan Schedules (`/schedules`)
- **Purpose**: Manage automated recurring DAST scan schedules (Daily, Weekly, Monthly, Continuous Cron).
- **User Journey**: SecOps engineer views active schedules $\rightarrow$ clicks `Create Scan Schedule` $\rightarrow$ configures cron expression and profile $\rightarrow$ enables automated schedule.
- **Required APIs**: `GET /api/v1/schedules`, `POST /api/v1/schedules`, `PUT /api/v1/schedules/{id}`, `DELETE /api/v1/schedules/{id}`.
- **UI Sections**:
  1. Schedules Telemetry Bar (Active Schedules, Next Execution Timer, Success Rate)
  2. Schedule List Table (Schedule Name, Target Asset, Scan Profile, Recurrence Cron, Last Run, Status Toggle, Actions)
  3. Schedule Creation Modal (Name, Target, Profile, Cron Selector)
- **Buttons & Expected Behavior**:
  - `Create Schedule`: Open Schedule Creation Modal.
  - `Toggle Active`: Enable/disable schedule execution (`PUT /api/v1/schedules/{id}`).
  - `Trigger Now`: Execute immediate manual scan execution.

---

### Page 4: Settings Hub (`/settings`)
- **Purpose**: Centralized enterprise settings navigation index linking to Secrets Vault, API Keys, Users, Roles, Security Policies, and Organization Details.
- **User Journey**: Admin opens `/settings` $\rightarrow$ views settings grid $\rightarrow$ selects target settings category.
- **Required APIs**: `GET /api/v1/settings/overview`.
- **UI Sections**:
  1. Settings Category Cards Grid (Enterprise Secrets Vault, API Keys, Team Users, Role RBAC, Security Governance, Organization Profile).
  2. Organization Usage & Plan Summary Panel.
- **Buttons & Expected Behavior**:
  - `Manage Secrets`: Navigate to `/settings/secrets`.
  - `Manage API Keys`: Navigate to `/settings/api-keys`.
  - `Manage Team`: Navigate to `/settings/users`.

---

## PHASE 4: Complete Functional Action Matrix (All 35 Routes)

Below is the complete testing and functional contract matrix for every route across the Vulnova application.

| Route | Main Components | Key Buttons & Actions | Expected Behavior | API Contract | Success Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | `TrustHeader`, Hero Banner, Feature Cards, Footer CTA | `Request Demo`, `Analyst Portal` | Redirect to `/signup` or `/dashboard` | None | Clean render, 0 console errors |
| `/login` | Login Form, TOTP Input, Logo Header | `Sign In` | Authenticate user, store JWT token | `POST /api/v1/auth/login` | Redirects to `/dashboard` on 200 OK |
| `/signup` | Enterprise Access Form | `Submit Request` | Register enterprise demo lead | `POST /api/v1/auth/request-access` | Displays success confirmation modal |
| `/dashboard` | Posture Summary, Velocity Chart, Active Scan Monitor, Vulnerability Chart, Asset Risk Overview | `Export CSV`, `Export JSON`, `Executive Report` | Generate & download CSV/JSON/PDF exports | `GET /api/v1/dashboard/overview`, `POST /api/v1/reports/executive` | File downloaded in browser |
| `/scans` | Status Filter, Search Bar, `ScanListTable`, `ScanDispatchModal` | `Dispatch Scan Job`, `Start Scan`, `Cancel Scan` | Open modal, launch container sandbox, abort job | `GET /api/v1/scans`, `POST /api/v1/scans`, `POST /api/v1/scans/{id}/cancel` | Table updates, new scan job created |
| `/scans/[id]` | Sandbox Panel, Terminal WebSocket Stream, Findings Table | `Back to Scans`, `Cancel Job`, `View Finding` | Live log streaming, scan termination | `GET /api/v1/scans/{id}`, WS `/api/v1/scans/{id}/stream` | WS messages render in terminal view |
| `/findings` | Severity Bar, Search/Filter, Findings Table, Finding Modal | `Export CSV`, `View Evidence`, `Approve Fix` | Filter findings, trigger AI code fix | `GET /api/v1/findings`, `POST /api/v1/findings/{id}/remediate` | Status changes to `REMEDIATING` |
| `/assets` | Stats Bar, Asset Table, Target Registration Modal | `Add Target Asset`, `Verify Ownership` | Register domain, run DNS TXT challenge | `GET /api/v1/assets`, `POST /api/v1/target-verification/verify-dns` | Badge changes to `VERIFIED` |
| `/schedules` | Schedule Table, Schedule Creation Modal | `Create Schedule`, `Toggle Active`, `Trigger Now` | Add recurring cron schedule | `GET /api/v1/schedules`, `POST /api/v1/schedules` | Schedule added to execution queue |
| `/reports` | Overview Cards, Search Bar, Reports Grid, Report Modal | `Generate Report`, `Download PDF` | Compile WeasyPrint PDF binary | `GET /api/v1/reports`, `GET /api/v1/reports/{id}/pdf` | Browser downloads `Report.pdf` |
| `/reports/[id]` | Report Header, Executive Summary, Remediation List | `Download PDF Report`, `Back to Reports` | Download PDF document | `GET /api/v1/reports/{id}/pdf` | PDF downloaded |
| `/compliance` | Framework Score Cards, Control Mapping Table | `Explore Framework`, `Export Evidence` | Navigate to framework detail | `GET /api/v1/compliance`, `GET /api/v1/compliance/export` | Evidence zip downloaded |
| `/compliance/[framework]` | Control Accordion, Gap Analysis List | `Back to Compliance` | Navigate back | `GET /api/v1/compliance/{framework}` | Detailed controls rendered |
| `/integrations` | Category Cards, Status List | `Configure CI/CD`, `Integration Settings` | Navigate to sub-settings | `GET /api/v1/integrations` | Status active |
| `/integrations/ci-cd` | Token Generator, YAML Snippet Selector | `Generate Token`, `Copy YAML` | Create machine token, copy snippet | `POST /api/v1/cli/tokens` | Token displayed |
| `/integrations/settings` | Webhook Form | `Save Webhook Settings` | Update webhook endpoint | `POST /api/v1/integrations/settings` | Toast notification `Saved` |
| `/notifications` | Notification Feed List | `Mark All Read` | Clear unread notifications | `POST /api/v1/notifications/mark-read` | Unread badge clears |
| `/notifications/settings` | Threshold Form | `Save Preferences` | Update notification triggers | `PUT /api/v1/notifications/settings` | Toast notification `Saved` |
| `/security/mfa` | QR Code Display, Code Input | `Verify & Enable MFA` | Enable PyOTP 2FA | `POST /api/v1/auth/mfa/enable` | Badge updates to `MFA ENABLED` |
| `/security/quarantine` | Dropzone, Quarantine Log, Metric Cards | `Upload Evidence`, `Promote Evidence` | Stage in MinIO, promote clean file | `POST /api/v1/evidence/upload`, `POST /api/v1/evidence/{id}/promote` | File promoted to evidence bucket |
| `/settings` | Settings Grid Cards | `Manage Secrets`, `Manage API Keys` | Navigate to settings subpage | `GET /api/v1/settings/overview` | Cards render cleanly |
| `/settings/secrets` | Provider Status, Secret Table, Store Modal | `Store Secret`, `Reveal Value`, `Rotate DEK` | Envelope encrypt, decrypt payload | `GET /api/v1/secrets`, `POST /api/v1/secrets`, `POST /api/v1/secrets/{id}/access` | Plaintext decrypted in modal |
| `/settings/api-keys` | API Key Table, Creation Modal | `Create API Key`, `Revoke Key` | Issue machine token | `GET /api/v1/api-keys`, `POST /api/v1/api-keys` | Plaintext API key shown once |
| `/settings/organization` | Org Form | `Save Organization` | Update domain & name | `PATCH /api/v1/organizations/me` | Org details updated |
| `/settings/roles` | RBAC Matrix Table | `Update Permissions` | Save role permissions | `PUT /api/v1/roles/{id}` | Role matrix updated |
| `/settings/security` | IP Whitelist Form | `Save Security Policy` | Update IP whitelist | `PUT /api/v1/settings/security` | Settings saved |
| `/settings/users` | User Table, Invite Modal | `Invite User`, `Deactivate User` | Send invitation email | `POST /api/v1/users/invite` | User added to table |
| `/validation/owasp` | ASVS Coverage Table | `Run OWASP Suite` | Execute ASVS v4.0 tests | `POST /api/v1/validation/owasp/run` | ASVS score updated |
| `/validation/api-security` | API Test Matrix | `Run API Tests` | Execute BOLA/BFLA tests | `POST /api/v1/validation/api-security/run` | Test results render |
| `/validation/infrastructure` | Infra Test Matrix | `Run Infra Scan` | Execute port/TLS checks | `POST /api/v1/validation/infrastructure/run` | Infra status clean |
| `/validation/pentest` | Pentest Verification | `Verify Exploits` | Validate exploit proofs | `POST /api/v1/validation/pentest/run` | Verification complete |
| `/validation/sca` | Dependency Tree | `Scan Dependencies` | Check CVE vulnerability database | `POST /api/v1/validation/sca/run` | Dependency tree updated |
| `/validation/container` | Container Rootfs Panel | `Audit Sandbox` | Check UID 10001 rootfs | `POST /api/v1/validation/container/run` | Rootfs read-only verified |
| `/validation/secrets` | Entropy Scanner | `Scan Repos` | Check code for cleartext keys | `POST /api/v1/validation/secrets/run` | 0 cleartext keys found |
| `/validation/threat` | STRIDE Matrix | `Generate Threat Model` | Synthesize STRIDE model | `POST /api/v1/validation/threat/run` | Threat model updated |
| `/validation/regression` | Regression Queue | `Run Regression` | Verify fixed CVEs | `POST /api/v1/validation/regression/run` | 0 regressions detected |
| `/validation/certification` | Compliance Certs | `Download Audit Package` | Download SOC 2 evidence | `POST /api/v1/validation/certification/export` | Evidence zip downloaded |
| `/database/performance` | Query Latency Chart, pgvector HNSW Panel | `Analyze Queries` | Probe DB index hit ratio | `GET /api/v1/database/performance` | Query metrics updated |
| `/vulnerabilities/[id]` | CVSS 4.0 Score, AI Fix Recommendation | `Approve Remediation`, `Mark False Positive` | Apply AI code patch | `POST /api/v1/findings/{id}/remediate` | Status updated |
| `/security` (Public) | Disclosure Policy text | `Download Policy` | Public disclosure policy | None | Clean render |
| `/trust` (Public) | Certification Cards | `Download SOC 2 Report` | Download public cert | None | Clean render |

---

## PHASE 5: Enterprise Product Identity & UX Elevation

### 1. Homepage Positioning Overhaul (`/`)
- **Current Headline**: *"Enterprise Security Platform"* (Generic)
- **New Value Proposition**:
  > **Vulnova: AI-Powered Continuous Security Validation Platform**  
  > *Discover exposed attack surfaces. Detect vulnerabilities. Validate security controls. Generate enterprise remediation intelligence—engineered for organizations that cannot afford blind spots.*

### 2. Homepage CTA Button Alignment
- Replace generic buttons with clear commercial actions:
  - Primary CTA: `Request Enterprise Access` $\rightarrow$ Navigates to `/signup`
  - Secondary CTA: `Login to SOC Platform` $\rightarrow$ Navigates to `/login`

### 3. Static RFC 9116 File (`public/.well-known/security.txt`)
- Create `frontend/public/.well-known/security.txt` containing RFC 9116 security contact information:
  ```text
  Contact: mailto:security@vulnova.com
  Expires: 2027-12-31T23:59:59.000Z
  Preferred-Languages: en
  Canonical: https://vulnova.com/.well-known/security.txt
  Policy: https://vulnova.com/security
  ```

---

## PHASE 6: Production Launch Readiness Checklist

Before final commercial domain deployment, the following 10 validation gates must pass:

- [ ] **1. Authentication Gate**: User login (`/login`), access request (`/signup`), and logout functions operate cleanly.
- [ ] **2. Route Health Gate**: 0 404 pages across all 35 routes and subpages.
- [ ] **3. Navigation Contract Gate**: Sidebar navigation and top header bar present on 100% of dashboard routes via `app/(dashboard)/layout.tsx`.
- [ ] **4. Button Action Gate**: Every button across all 35 pages executes its specified API call or modal trigger.
- [ ] **5. Report Generation Gate**: PDF executive reports generate and download cleanly in the browser.
- [ ] **6. Secrets Vault Gate**: Secrets store cleanly with AES-256-GCM envelope encryption and reveal plaintext only upon authorized click.
- [ ] **7. Evidence Quarantine Gate**: Files stage in `vulnova-quarantine-bucket` and promote to `vulnova-evidence-bucket` upon clean scan verdict.
- [ ] **8. Console Error Gate**: 0 JavaScript runtime errors or Next.js SSR date hydration warnings in browser DevTools.
- [ ] **9. Code Quality Gate**: `npm run lint`, `npm run type-check`, `npm run build`, `black --check app tests`, `ruff check app`, `pytest` pass with 100% success.
- [ ] **10. RFC Compliance Gate**: `/.well-known/security.txt` returns `200 OK` text payload.

---

## Recommended Execution Sprint Plan

```
┌────────────────────────────────────────────────────────────────────────┐
│ SPRINT 1: FOUNDATION & NAVIGATION (P0)                                │
│ ├─ Create app/(dashboard)/layout.tsx wrapper                          │
│ ├─ Implement missing pages: /findings, /assets, /schedules, /settings  │
│ └─ Create /login and /signup authentication routes                     │
├────────────────────────────────────────────────────────────────────────┤
│ SPRINT 2: FUNCTIONAL COMPLETENESS & BUTTON MATRIX (P1)                │
│ ├─ Wire up all button actions & modals across 35 pages                 │
│ ├─ Implement CSV/JSON dashboard data export                            │
│ └─ Add Logout menu handler to top header user profile                  │
├────────────────────────────────────────────────────────────────────────┤
│ SPRINT 3: PRODUCT POLISH & LAUNCH READINESS (P2)                       │
│ ├─ Update homepage messaging & CTA buttons                             │
│ ├─ Add public/.well-known/security.txt                                 │
│ └─ Fix SSR date hydration warning toast & run final verification       │
└────────────────────────────────────────────────────────────────────────┘
```

*Roadmap generated for User Review and Approval.*
