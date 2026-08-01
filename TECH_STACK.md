# Vulnova — Technology Stack & Infrastructure Specification (TECH_STACK.md)

This document specifies the complete technology stack, frameworks, database systems, vector stores, containerization standards, and security tooling selected for **Vulnova**.

---

## 💻 1. Technology Matrix Overview

| Layer | Primary Technology | Version Constraint | Selection Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | Next.js (App Router) | 14.2+ | Server-side rendering, React 18 Server Components, routing & SEO excellence |
| **Frontend Language** | TypeScript | 5.4+ | Strict type safety, refactoring safety across complex UI state models |
| **UI Styling & Tokens** | TailwindCSS + Vanilla CSS | 3.4+ | Utility-first styling with custom CSS variables for light/dark themes |
| **UI Components** | shadcn/ui primitives | Latest | Unstyled, accessible, fully customizable React components |
| **Animations** | Framer Motion | 11.0+ | Micro-animations, dynamic transitions, interactive cybersecurity visuals |
| **Backend Gateway** | FastAPI | 0.111+ | Asynchronous Python I/O, auto OpenAPI 3.1 docs, Pydantic v2 validation speed |
| **Backend Language** | Python | 3.12+ | Rich ecosystem for security automation, async performance, LLM integrations |
| **Task Queue & Broker** | Celery + Redis | Celery 5.4+ / Redis 7.2+ | Distributed job execution, retry management, background DAST scaling |
| **Relational Database** | PostgreSQL | 16.3+ | Acid compliance, robust indexing, JSONB support, enterprise reliability |
| **Vector Engine** | `pgvector` extension | 0.7+ | Unified DB management; high-performance vector search directly in PostgreSQL |
| **ORM & Migrations** | SQLAlchemy + Alembic | SQLAlchemy 2.0+ | Async ORM, migration tracking, type hinting support |
| **AI / LLM Integration**| OpenAI / Anthropic / Ollama | Latest APIs | Hybrid RAG + multi-provider fallback for vulnerability intelligence |
| **Browser Automation**| Playwright Python | 1.44+ | Dynamic SPA DOM crawling and JavaScript execution inspection |
| **Containerization** | Docker & Docker Compose | 26.0+ | Multi-stage production builds, local orchestrations |
| **Reverse Proxy / TLS** | Traefik / Nginx | Traefik v3+ | Automatic SSL/TLS provisioning, HTTP/2 & WebSocket routing |

---

## 🎨 2. Frontend Design Tokens & Aesthetics Strategy

Vulnova implements a custom design system tailored for high-end enterprise security software.

### Color Palette Strategy
- **Light Mode Theme**: Clean white background (`#FFFFFF`), slate structural borders (`#E2E8F0`), obsidian typography (`#0F172A`), and Crimson Red accents (`#DC2626`).
- **Dark Mode Theme**: Obsidian black background (`#09090B`), zinc card containers (`#18181B`), crisp light typography (`#FAFAFA`), and Crimson Red glowing accents (`#EF4444`, shadow red glow).

### Typography
- Primary Sans-serif: `Inter` (Google Fonts) for high legibility across data grids.
- Display & Metrics: `Outfit` (Google Fonts) for dashboard numbers, severity badges, and headers.
- Code & Payloads: `JetBrains Mono` for HTTP dumps, code patches, and terminal logs.

---

## ⚡ 3. Backend & Core Engine Architecture Stack

### FastAPI & Pydantic v2
FastAPI serves as the API Gateway handling HTTP REST routes and WebSockets. Pydantic v2 (Rust-backed) enforces strict request and response schema validation with minimal serialization overhead.

### Celery Worker Cluster & Redis
Scans are offloaded from the web server thread onto a scalable pool of Celery workers:
- `discovery_queue`: Web crawling, JS parsing, SPA rendering tasks.
- `assessment_queue`: OWASP plugin execution and HTTP fuzzing.
- `ai_queue`: LLM prompts, RAG retrieval, code patch generation.

---

## 🤖 4. AI & Vector Database Layer Architecture

### `pgvector` PostgreSQL Integration
To avoid adding complexity with separate vector databases (e.g., Pinecone/Milvus), Vulnova uses the `pgvector` extension natively inside PostgreSQL:
- Vector Dimension: `1536` (OpenAI `text-embedding-3-small`) or `768` (Local Ollama embeddings).
- Indexing: `HNSW` (Hierarchical Navigable Small World) index for sub-millisecond similarity queries.

---

## 🔒 5. DevSecOps & Security Tooling

- **Static Analysis (SAST)**: `Semgrep` rules for Python/JS security flaws.
- **Secret Scanning**: `Gitleaks` in pre-commit and CI workflows.
- **Container Scanning**: `Trivy` scanning base images for CVEs.
- **Dependency Audit**: `pip-audit` and `npm audit` enforced in GitHub Actions pipelines.
