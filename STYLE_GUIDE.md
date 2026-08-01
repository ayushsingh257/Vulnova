# Vulnova — Code Style Guide & Git Conventions (STYLE_GUIDE.md)

This document establishes the code style standards, linters, formatters, and Git commit guidelines (Conventional Commits) for **Vulnova**.

---

## 🐍 1. Python Code Standards (Backend)

- **Formatter**: `Black` (line length 88).
- **Linter**: `Ruff` (enforcing PEP 8, ISort, Pyflakes, and security rules).
- **Type Checking**: `mypy --strict`.
- **Naming Conventions**:
  - Modules & Packages: `snake_case` (e.g., `scan_orchestrator.py`)
  - Classes: `PascalCase` (e.g., `AssessmentPluginPort`)
  - Functions & Variables: `snake_case` (e.g., `calculate_cvss_score()`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_CRAWL_DEPTH = 5`)

---

## 🟦 2. TypeScript & React Code Standards (Frontend)

- **Formatter & Linter**: `ESLint` + `Prettier` (semi: true, singleQuote: false, tabWidth: 2).
- **Naming Conventions**:
  - Components: `PascalCase` (e.g., `RiskScoreCard.tsx`)
  - Hooks: `camelCase` starting with `use` (e.g., `useScanWebSocket.ts`)
  - Utilities: `camelCase` (e.g., `formatCvssScore.ts`)
  - Types / Interfaces: `PascalCase` prefixed with `T` or `I` if helpful (e.g., `FindingSummary`).

---

## 🔀 3. Git Commit Conventions (Conventional Commits)

Commit messages MUST follow the [Conventional Commits v1.0.0](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <short summary>

[optional detailed description]

[optional breaking change warning or issue reference]
```

### Allowed Commit Types:
- `feat`: A new feature added to the platform.
- `fix`: A bug fix or patch.
- `docs`: Documentation changes only (`README.md`, `ARCHITECTURE.md`).
- `style`: Formatting, missing semi-colons, no code logic change.
- `refactor`: Code change that neither fixes a bug nor adds a feature.
- `test`: Adding missing tests or refactoring test suites.
- `chore`: Infrastructure updates, dependency bumps, build scripts.

### Examples:
- `feat(assessment): add OWASP SSRF vulnerability detection plugin`
- `fix(auth): resolve JWT token expiration refresh loop bug`
- `docs(roadmap): finalize Era 0 phase specifications`
