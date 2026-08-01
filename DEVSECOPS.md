# Vulnova — DevSecOps Architecture & CI/CD Pipelines (DEVSECOPS.md)

This document specifies the automated CI/CD pipelines, automated security scanning gates, dependency audit workflows, container security standards, and release automation for **Vulnova**.

---

## 🔒 1. DevSecOps Security Pipeline Architecture

```
 [Developer Commit / PR]
            │
            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                GitHub Actions CI Workflow                   │
 │                                                             │
 │  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐  │
 │  │   Gitleaks    │   │    Semgrep    │   │  pip-audit /  │  │
 │  │ Secret Scan   │   │  SAST Scanner │   │  npm audit    │  │
 │  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘  │
 └──────────┼───────────────────┼───────────────────┼──────────┘
            │                   │                   │
            ▼                   ▼                   ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                 Automated Test & Build                      │
 │  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐  │
 │  │ Pytest /      │   │ Next.js Build │   │ Trivy Container│ │
 │  │ Coverage      │   │ & Lint        │   │ Vulnerability │  │
 │  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘  │
 └──────────┼───────────────────┼───────────────────┼──────────┘
            │                   │                   │
            ▼                   ▼                   ▼
 [Security Gate Threshold Check: Zero High/Critical Flaws]
            │
            ├─► FAIL ──► Block PR Merge & Page Security Team
            │
            └─► PASS ──► Build Signed Container Image & Publish
```

---

## ⚡ 2. GitHub Actions Workflow Configuration

`.github/workflows/ci-security.yml` enforces automated checks on every pull request:

```yaml
name: Vulnova DevSecOps Pipeline

on:
  push:
    branches: [ main, release/* ]
  pull_request:
    branches: [ main ]

jobs:
  security-audit:
    name: Security & Secret Scanning
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Gitleaks Secret Scanner
        uses: gitleaks/gitleaks-action@v2

      - name: Run Semgrep SAST Audit
        uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit

  backend-tests:
    name: Backend Pytest & Coverage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run Pytest
        run: poetry run pytest --cov=app --cov-report=xml

  frontend-build:
    name: Next.js Lint & Build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: npm ci --prefix frontend
      - name: Next.js Build
        run: npm run build --prefix frontend
```

---

## 🐳 3. Container Security Standards

1. **Non-Root Execution**: Container images execute under a unprivileged system user (`USER appuser`).
2. **Minimal Base Images**: Distroless or Alpine Linux base images (`python:3.12-slim`, `node:20-alpine`).
3. **Multi-Stage Builds**: Build dependencies and toolchains are stripped prior to final image assembly.
