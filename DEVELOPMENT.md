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

## 🐳 6. Local Docker Infrastructure

To run PostgreSQL (`pgvector`) and Redis containers locally:
```bash
docker compose up -d postgres redis
```

Verify service health:
```bash
docker compose ps
```
