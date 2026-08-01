# Vulnova — Contributor Onboarding & Developer Guide (CONTRIBUTING.md)

Thank you for contributing to **Vulnova**! This document provides onboarding instructions, local development setup steps, coding standards, and pull request guidelines.

---

## 🚀 1. Developer Setup Checklist

### Prerequisites
- **Git** 2.40+
- **Docker** 26.0+ & Docker Compose v2
- **Python** 3.12+
- **Node.js** 20.0+ & `npm` 10+
- **Poetry** (Python dependency manager)

---

## 🛠️ 2. Local Environment Initialization

1. **Clone Repository**:
   ```bash
   git clone https://github.com/ayushsingh257/Vulnova.git
   cd Vulnova
   ```

2. **Environment Variable Files**:
   Copy `.env.example` templates in root, `frontend`, and `backend`:
   ```bash
   cp .env.example .env
   ```

3. **Start Local Docker Orchestration**:
   ```bash
   docker compose up -d
   ```
   This spins up PostgreSQL (`pgvector`), Redis, FastAPI backend, and Next.js frontend.

4. **Verify Application Health**:
   - Backend API Health: `http://localhost:8000/health`
   - API OpenAPI Documentation: `http://localhost:8000/docs`
   - Frontend Web Dashboard: `http://localhost:3000`

---

## 🔀 3. Pull Request Guidelines

1. **Create Feature Branch**:
   ```bash
   git checkout -b feat/era-1-monorepo-setup
   ```

2. **Run Verification & Tests**:
   - Ensure all linters pass (`ruff check .` and `npm run lint`).
   - Run backend test suite (`poetry run pytest`).
   - Verify Next.js build compilation (`npm run build`).

3. **Commit with Conventional Commits**:
   Follow [STYLE_GUIDE.md](STYLE_GUIDE.md) specifications.

4. **Submit Pull Request**:
   Describe changes, reference target ROADMAP phase, and confirm zero build or lint warnings.
