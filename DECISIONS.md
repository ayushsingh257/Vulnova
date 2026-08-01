# Vulnova — Architectural Decision Records (DECISIONS.md)

This document records the key architectural decisions (ADRs) made during the design and development of **Vulnova**.

---

## 📝 ADR Index

- [ADR-001: Selection of Next.js 14 App Router for Frontend Platform](#adr-001)
- [ADR-002: FastAPI & Python 3.12 for API Control Plane](#adr-002)
- [ADR-003: PostgreSQL with pgvector as Unified Relational & Vector Store](#adr-003)
- [ADR-004: Celery & Redis for Distributed Task Queuing](#adr-004)
- [ADR-005: Scanner Sandbox Container Isolation Strategy](#adr-005)
- [ADR-006: Extensible Security Plugin Specification & `plugin.yaml` Architecture](#adr-006)
- [ADR-007: Event-Driven System Evolution (Celery to Message Bus Bridge)](#adr-007)

---

## <a id="adr-001"></a> 🏛️ ADR-001: Selection of Next.js 14 App Router for Frontend Platform

- **Status**: Approved (Era 0)
- **Context**: Need a modern, scalable, SEO-friendly, and highly responsive web application framework to build both public enterprise pages and a complex cybersecurity dashboard.
- **Decision**: Select **Next.js 14 (App Router)** with React 18, TypeScript, TailwindCSS, and `shadcn/ui`.
- **Consequences**:
  - *Positive*: Excellent performance via React Server Components (RSC), built-in routing, dynamic rendering, strong TypeScript integration.
  - *Negative*: Requires adhering to client vs server component boundaries (`"use client"` directive).

---

## <a id="adr-002"></a> 🏛️ ADR-002: FastAPI & Python 3.12 for API Control Plane

- **Status**: Approved (Era 0)
- **Context**: Require a high-performance backend API framework with native async support, seamless integration with AI/LLM tools (LangChain, LlamaIndex), and automated OpenAPI docs.
- **Decision**: Select **FastAPI** on Python 3.12+ with Pydantic v2.
- **Consequences**:
  - *Positive*: High asynchronous throughput, automatic request validation, instant OpenAPI specs, native Python AI ecosystem compatibility.
  - *Negative*: Python CPU-bound tasks must be offloaded to Celery workers to avoid blocking the main event loop.

---

## <a id="adr-003"></a> 🏛️ ADR-003: PostgreSQL with `pgvector` as Unified Relational & Vector Store

- **Status**: Approved (Era 0)
- **Context**: Vulnova requires both relational storage (multi-tenancy, scans, findings) and vector similarity storage for RAG vulnerability intelligence.
- **Decision**: Use **PostgreSQL 16+** with the **`pgvector`** extension instead of maintaining a separate standalone vector database (e.g., Pinecone, Qdrant).
- **Consequences**:
  - *Positive*: Simplified infrastructure topology, single database backup/restore pipeline, transactional integrity between findings and embeddings.
  - *Negative*: Sub-second similarity search requires HNSW index tuning at massive vector scale (>1M vectors).

---

## <a id="adr-004"></a> 🏛️ ADR-004: Celery & Redis for Distributed Task Queuing

- **Status**: Approved (Era 0)
- **Context**: DAST security scanning and AI analysis jobs are long-running background workloads that must not block HTTP API responses.
- **Decision**: Select **Celery** backed by **Redis 7** as the distributed task broker.
- **Consequences**:
  - *Positive*: Proven enterprise stability, task retry management, rate-limiting support, distributed worker scaling.
  - *Negative*: Requires maintaining Redis instance and monitoring task queue health.

---

## <a id="adr-005"></a> 🏛️ ADR-005: Scanner Sandbox Container Isolation Strategy

- **Status**: Approved (Era 0.5)
- **Context**: Security scanning workloads process untrusted responses from target applications, introducing risks of container escape or internal network scanning.
- **Decision**: Run scanner workers in unprivileged Linux containers (`UID 10001`, `read_only_rootfs: true`, capabilities dropped) with strict resource limits (1 vCPU, 512MB RAM) and an outbound Egress Filtering Proxy blocking internal subnets (`10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.1`, `169.254.169.254`).
- **Consequences**:
  - *Positive*: Complete platform protection against malicious target response exploits or scanner worker compromise.
  - *Negative*: Egress proxy requires maintenance of IP exclusion lists.

---

## <a id="adr-006"></a> 🏛️ ADR-006: Extensible Security Plugin Specification & `plugin.yaml` Architecture

- **Status**: Approved (Era 0.5)
- **Context**: Security assessment capabilities must evolve without requiring constant architectural redesigns or core engine code modifications.
- **Decision**: Build a modular plugin framework where each security check is self-describing via a `plugin.yaml` manifest containing CWE/OWASP mappings, severity, required permissions, and execution timeouts.
- **Consequences**:
  - *Positive*: Security engineers can develop and register custom enterprise security checks independently.
  - *Negative*: Plugin manifests require strict validation on boot.

---

## <a id="adr-007"></a> 🏛️ ADR-007: Event-Driven System Evolution (Celery to Message Bus Bridge)

- **Status**: Approved (Era 0.5)
- **Context**: As platform scale increases, task workflows require event-driven broadcasting (`ScanCreatedEvent`, `FindingCreatedEvent`, `AIAnalysisCompletedEvent`).
- **Decision**: Implement an abstract `EventBusPort` allowing initial Celery/Redis execution to transition seamlessly to RabbitMQ (AMQP), Apache Kafka, or NATS JetStream without core code refactoring.
- **Consequences**:
  - *Positive*: Future microservices and event streaming integration enabled from day one.
  - *Negative*: Event payloads must be standardized early.
