# Vulnova — Enterprise AI Application Security Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)
[![Security: OWASP ASVS](https://img.shields.io/badge/Security-OWASP_ASVS_v4.0-crimson.svg)](SECURITY.md)
[![Architecture: Clean Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20DDD-black.svg)](ARCHITECTURE.md)
[![Status: Era 0.5 Foundation](https://img.shields.io/badge/Status-Era%200.5%20Foundation-darkred.svg)](ROADMAP.md)

**Vulnova** is an enterprise-grade, AI-powered Application Security (AppSec) platform designed to continuously discover, assess, prioritize, and remediate security risks across modern cloud-native software lifecycles.

Unlike basic scanner tools, Vulnova operates as a unified AppSec operational command center—integrating dynamic application security testing (DAST), automated attack surface discovery, API security inspection, and an autonomous AI Security Analyst to drive AI-assisted false-positive reduction and vulnerability prioritization for continuous DevSecOps compliance.

---

## 🌟 Key Capabilities

### 🔎 Application & Attack Surface Discovery
- **Web Crawling & SPA Rendering**: Dynamic visual DOM crawling and single-page application navigation.
- **Endpoint & API Discovery**: Automated REST/GraphQL schema inference, OpenAPI extraction, and dynamic route enumeration.
- **Technology Fingerprinting**: Deep client/server stack detection (frameworks, web servers, third-party libraries, known CVE mapping).
- **Asset Inventory & Surface Mapping**: Enterprise asset taxonomy and continuous shadow asset discovery.

### 🛡️ Dynamic Security Assessment & Sandbox Isolation
- **Isolated Scanner Sandbox**: Containerized execution of dynamic scanning workloads isolated from platform core with egress firewalling and unprivileged execution boundaries.
- **Extensible Plugin Engine**: Modular plugin framework supporting standard `plugin.yaml` manifests for custom security checks.
- **OWASP Top 10 & API Security Top 10**: Deep automated checks for SQLi, XSS, SSRF, CSRF, IDOR, Broken Authentication, Rate Limiting bypasses, and JWT flaws.
- **Legal Target Authorization**: Mandatory ownership verification and scope confirmation prior to scan execution.

### 🤖 Autonomous AI Security Analyst
- **Contextual Risk & Impact Analysis**: Evaluates technical severity (CVSS 4.0) alongside business context and exposure path.
- **Exploit Path & Attack Scenarios**: Synthesizes multi-step attack vectors and realistic threat actor scenarios.
- **Remediation & Secure Coding**: Generates context-aware, language-specific code patches and framework configuration fixes.
- **False-Positive Mitigation Engine**: Correlates stack traces, execution context, and response behaviors to filter scanner noise.
- **Executive & Engineering Reporting**: Automated generation of CISO executive summaries, compliance audits, and developer actionable tickets.

---

## 🏛️ Architecture Overview

Vulnova is built following **Clean Architecture** and **Domain-Driven Design (DDD)** principles, supporting an event-driven evolution path and microservices migration.

```
                  ┌─────────────────────────────────────────┐
                  │   Next.js 14 Enterprise Web App         │
                  │   (shadcn/ui, Framer Motion, Red/Dark)  │
                  └────────────────────┬────────────────────┘
                                       │ HTTPS / WSS
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │    FastAPI API Gateway & Control Plane   │
                  │   (Async Python 3.12, OAuth2/JWT/RBAC)  │
                  └────────────────────┬────────────────────┘
                                       │ Task Dispatch / Event Bus
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │   Isolated Scanner Sandbox Workers      │
                  │   (Unprivileged Containers, Egress Rule)│
                  │ ┌───────────┬──────────────┬──────────┐ │
                  │ │ Crawling  │ DAST Plugins │ Browser  │ │
                  │ └───────────┴──────────────┴──────────┘ │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  PostgreSQL (pgvector) & Redis          │
                  └─────────────────────────────────────────┘
```

For full architectural details, see [ARCHITECTURE.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/ARCHITECTURE.md).

---

## 🔒 Enterprise Trust Center & Public Pages

Vulnova provides a dedicated **Trust Center** (`/trust`) to offer full transparency into enterprise security practices, compliance standards, and real-time operational status.

### Included Enterprise Public Pages:
- 🌐 **Landing & Features**: Product overview, platform demo, capability matrix.
- 🛡️ **Trust Center (`/trust`)**: Security posture, SOC 2 / ISO 27001 readiness, encryption disclosures.
- 📜 **Legal & Compliance**: Terms of Service, Privacy Policy, Cookie Policy, Authorized Security Testing Agreement.
- 📢 **Responsible Disclosure**: Vulnerability reporting guidelines and security contact details.
- 📖 **Documentation & Support**: API documentation, integration guides, support desk.

---

## 🛠️ Technology Stack

| Layer | Primary Technologies |
| :--- | :--- |
| **Frontend Platform** | Next.js 14 (App Router), React 18, TypeScript, TailwindCSS, shadcn/ui, Framer Motion |
| **Backend Core** | Python 3.12+, FastAPI, Pydantic v2, AsyncIO |
| **Task Queue & Event Bus** | Celery, Redis 7+ (Bridge path to RabbitMQ / Kafka / NATS) |
| **Sandbox Execution** | Containerized Worker Pool, Egress Firewall, Linux Namespaces |
| **Database & Vector Store** | PostgreSQL 16+ with `pgvector` extension, Alembic migrations |
| **AI & LLM Orchestration**| LangChain / LlamaIndex, OpenAI / Anthropic APIs, Local LLM fallback (Ollama) |
| **Security & DevSecOps** | Gitleaks, Semgrep, Trivy, Docker, GitHub Actions, Traefik Reverse Proxy |

See [TECH_STACK.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/TECH_STACK.md) for detailed technical decisions.

---

## 📚 Core Repository Documentation

The repository is governed by 19 enterprise-grade specification documents:

| Document | Description |
| :--- | :--- |
| 🧠 [BRAIN.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/BRAIN.md) | Permanent project memory, design axioms, and engineering rules |
| 🗺️ [ROADMAP.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/ROADMAP.md) | 12-Era roadmap spanning 100+ implementation phases |
| 📁 [PROJECT_STRUCTURE.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/PROJECT_STRUCTURE.md) | Canonical repository layout blueprint & architectural boundaries |
| 🏛️ [ARCHITECTURE.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/ARCHITECTURE.md) | System architecture diagrams, scanner sandboxing, event bus, and plugins |
| 🛡️ [SECURITY.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/SECURITY.md) | Security policy, ASVS standards, sandbox isolation, legal target authorization |
| 🎯 [THREAT_MODEL.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/THREAT_MODEL.md) | Formal STRIDE threat analysis, sandbox escape risks, and mitigations |
| 🗄️ [DATABASE.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/DATABASE.md) | PostgreSQL entity schemas, scan profiles, evidence management, pgvector |
| 📡 [API_SPEC.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/API_SPEC.md) | REST API endpoints, plugin manifest schemas, target authorization payloads |
| 🎨 [FRONTEND_GUIDELINES.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/FRONTEND_GUIDELINES.md) | UI design system, Trust Center specs, color tokens, and accessibility rules |
| ⚙️ [BACKEND_GUIDELINES.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/BACKEND_GUIDELINES.md) | FastAPI code standards, Clean Architecture guidelines, error handling |
| 🧪 [TESTING.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/TESTING.md) | Unit, integration, DAST verification, and coverage requirements |
| 🔒 [DEVSECOPS.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/DEVSECOPS.md) | CI/CD security pipelines, SAST, SCA, and image scanning |
| 🚀 [DEPLOYMENT.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/DEPLOYMENT.md) | Containerization, Docker Compose, reverse proxy, and K8s readiness |
| 📐 [STYLE_GUIDE.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/STYLE_GUIDE.md) | Code styling, linting configs, commit conventions (Conventional Commits) |
| 📝 [DECISIONS.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/DECISIONS.md) | Architectural Decision Records (ADRs 001–007) |
| 📜 [CHANGELOG.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/CHANGELOG.md) | Chronological version history and milestone tracking |
| 🤝 [CONTRIBUTING.md](file:///c:/Users/Ayush/OneDrive/Desktop/Projects/Vulnova/CONTRIBUTING.md) | Developer onboarding guide, local environment setup, PR guidelines |

---

## 📄 License

Vulnova is distributed under the MIT License. See `LICENSE` for details.
