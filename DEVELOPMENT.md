# Vulnova — Developer Onboarding & Development Guide (DEVELOPMENT.md)

This handbook provides step-by-step instructions for initializing local development environments, executing unit and integration test suites, running code linters/formatters, and setting up pre-commit verification hooks for **Vulnova**.

---

## 📋 1. Developer Prerequisites

Before setting up Vulnova locally, ensure your workstation meets the following prerequisites:

- **Operating System**: macOS 13+, Linux (Ubuntu 22.04+ LTS), or Windows 11 with WSL2 / PowerShell.
- **Git**: `v2.40+`
- **Node.js**: `v20.0+` (LTS) & `npm v10.0+`
- **Python**: `v3.12+` (`pip`, `venv` module)
- **Docker**: `v26.0+` & **Docker Compose** `v2.25+`
- **Pre-commit**: `pip install pre-commit`

---

## 🚀 2. Local Environment Initialization

### Step 1: Clone the Repository
```bash
git clone https://github.com/ayushsingh257/Vulnova.git
cd Vulnova
```

### Step 2: Configure Environment Variables
Copy template environment files for root, backend, and frontend:
```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Step 3: Initialize Frontend Workspace
```bash
cd frontend
npm install
npm run type-check
cd ..
```

### Step 4: Initialize Backend Python Virtual Environment
```bash
cd backend
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
cd ..
```

### Step 5: Install Git Pre-commit Hooks
```bash
pre-commit install
```

---

## 🛠️ 3. Development Workflow & Commands Reference

### Running Local Development Servers

#### Next.js Web Dashboard:
```bash
npm run dev
# Dashboard accessible at http://localhost:3000
```

#### FastAPI Control Plane Backend:
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
# OpenAPI Docs accessible at http://localhost:8000/docs
```

---

## 🧪 4. Testing & Code Quality Commands

All code must pass formatting, linting, type-checking, and unit test suites prior to submitting a Pull Request.

### Command Reference Table:

| Task | Frontend Command | Backend Command | Monorepo Unified Command |
| :--- | :--- | :--- | :--- |
| **Linting** | `npm run lint` | `ruff check .` | `npm run lint` |
| **Type Checking** | `npm run type-check` | `mypy .` | `npm run type-check` |
| **Formatting** | `npm run format` | `black .` | `npm run format` |
| **Format Check** | `npm run format:check` | `black --check .` | `npm run format:check` |
| **Unit Testing** | — | `pytest` | `npm run test` |

---

## 🔒 5. Pre-commit Hooks

Pre-commit hooks automatically format and validate code before git commits are accepted:

```bash
# Run pre-commit across all files manually:
pre-commit run --all-files
```

If pre-commit detects unformatted files (e.g., Black or Prettier reformats a file), re-stage the modified files (`git add .`) and re-run the commit.

---

## 🐳 6. Local Docker Infrastructure Management

Vulnova provides a single-command Docker Compose stack hosting the Next.js frontend, FastAPI backend, PostgreSQL 16 (`pgvector`), and Redis 7 services under an isolated `vulnova_net` bridge network.

### Docker Lifecycle Commands

#### Start Complete Infrastructure:
```bash
docker compose up -d
```

#### Rebuild Containers After Code/Dependency Updates:
```bash
docker compose up --build -d
```

#### View Live Aggregated Logs:
```bash
docker compose logs -f
```

#### View Specific Service Logs (e.g., Backend):
```bash
docker compose logs -f backend
```

#### View Container Health Status:
```bash
docker compose ps
```

#### Stop & Remove Containers:
```bash
docker compose down
```

#### Stop Environment & Purge Persistent Volumes (Database Reset):
```bash
docker compose down -v
```

---

## 🗄️ 7. Database & Cache Interactive Access

### Connect to PostgreSQL (`psql` CLI inside container):
```bash
docker compose exec postgres psql -U vulnova_admin -d vulnova_db
```

### Connect to Redis (`redis-cli` inside container):
```bash
docker compose exec redis redis-cli
```

---

## 🛡️ 8. DevSecOps & Security Verification

Vulnova enforces automated security verification in GitHub Actions CI pipelines (`.github/workflows/security.yml`) and pre-commit hooks. Developers can run security checks locally before pushing commits.

### Security Tool Command Reference:

#### 1. Gitleaks (Secret Detection Scan)
Detect committed API keys, tokens, or private secrets:
```bash
gitleaks detect --verbose
```

#### 2. Semgrep (SAST Static Security Analysis)
Scan code for OWASP Top 10 vulnerabilities:
```bash
semgrep scan --config p/default --config p/security-audit
```

#### 3. Backend Dependency Vulnerability Audit (`pip-audit`)
Audit Python dependencies in `backend/requirements.txt`:
```bash
pip-audit -r backend/requirements.txt
```

#### 4. Frontend Dependency Audit (`npm audit`)
Audit Node.js packages in `frontend/`:
```bash
cd frontend
npm audit
cd ..
```

#### 5. Trivy Container Vulnerability Scan
Scan Dockerfiles for container security misconfigurations:
```bash
trivy config backend/Dockerfile
trivy config frontend/Dockerfile
```

### Security Gate Rules:
Pull requests and pushes to `main` will automatically fail if:
- Leaked secrets or credentials are detected.
- High/Critical SAST vulnerabilities are identified.
- Known critical CVEs are detected in dependencies or base container images.

### Supply Chain Security & GitHub Actions SHA Pinning:
To mitigate software supply chain attacks (such as malicious tag mutation or compromised third-party Action releases), all GitHub Actions in `.github/workflows/` are pinned to immutable 40-character commit SHAs (e.g., `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`).

When updating GitHub Actions dependencies:
1. Verify the release release tag on GitHub.
2. Obtain the full 40-character commit SHA associated with the release tag.
3. Include the original tag name as an inline comment (`# vX.Y.Z`).


