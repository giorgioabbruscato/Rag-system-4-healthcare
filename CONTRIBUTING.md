# Contributing to RAG Healthcare

Thank you for your interest in contributing to this multimodal RAG system for clinical decision support! This document provides guidelines for setting up a development environment, coding standards, and the contribution workflow.

## Prerequisites

- **Python**: 3.10–3.12 (CI matrix); check with `python --version`
- **Git**: For version control
- **pip**: Python package manager
- **OpenAI API Key**: Optional (for testing `/analyze-case` endpoint; set `OPENAI_API_KEY` in `.env`)

## Setup Development Environment

### Local Development (Recommended)

```bash
# Clone the repository
git clone https://github.com/giorgioabbruscato/Rag-system-4-healthcare.git
cd Rag-system-4-healthcare

# Create and activate virtual environment
python -m venv .venv

# Activate venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install editable package with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (runs checks before each commit)
pre-commit install

# Verify setup
make test-fast
```

### Docker Setup (Optional - For Isolated Development)

If you prefer to develop in a containerized environment:

```bash
# Build development image
docker build -f Dockerfile.api -t rag-healthcare-dev .

# Run development container with hot-reload
docker run -it \
  -v $(pwd):/app \
  -p 8000:8000 \
  -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
  rag-healthcare-dev \
  bash

# Inside container
pip install -e ".[dev]"
pre-commit install
make test-fast
```

### Verify Installation

```bash
# Should succeed without errors
make lint
python -c "import src.config; import api.main; print('✓ Setup OK')"
```

## Project Structure

```
.
├── src/                 # Core modules (config, logging)
├── api/                 # FastAPI backend
│   ├── main.py         # Entry point with 5 endpoints
│   └── services/       # Business logic (rag_service, doc_service)
├── scripts/            # Data pipeline & utilities
│   ├── build_dataset.py
│   ├── index_Qdrant.py
│   ├── multimodal_rag_openai.py
│   └── evaluate_rag.py
├── app/                # Streamlit frontend
├── tests/              # Pytest suite (target ≥80% coverage)
├── data/               # Dataset, guidelines, evaluations
├── docs/adr/           # Architecture Decision Records
├── monitoring/         # Prometheus + Grafana (optional overlay)
├── Makefile            # Task runner (test, lint, format, monitoring-up, etc.)
└── pyproject.toml      # Project metadata & tool configs
```

## Coding Standards

### Formatting & Linting

All Python code must pass automated checks. These are enforced by **pre-commit hooks** before commit:

| Tool | Purpose | Command |
|------|---------|---------|
| **black** | Code formatting | `make format` |
| **isort** | Import sorting | `make format` |
| **ruff** | Linting (PEP 8, security rules) | `make lint` |
| **mypy** | Type checking | `make lint` |
| **bandit** | Security scanning | `make security` |

### Pre-commit Workflow

```bash
# Modify code
git add .

# Commit triggers pre-commit hooks automatically
git commit -m "feat: add new feature"
# If hooks fail → fix issues → git add . → git commit again

# Or manually run all checks
make lint format
pre-commit run --all-files
```

### Type Hints

All functions must have type annotations:

```python
# ❌ Bad
def analyze_case(report):
    return result

# ✅ Good
def analyze_case(report: str) -> Dict[str, Any]:
    """Analyze clinical case with RAG."""
    return result
```

### Logging

Use **structlog** instead of `print()` for traceability:

```python
# ❌ Bad
print(f"Processing case {case_id}")
raise Exception("Failed to retrieve context")

# ✅ Good
from src.logging_config import get_logger
logger = get_logger(__name__)

logger.info("Processing case", case_id=case_id)
logger.error("Failed to retrieve context", error=str(e), case_id=case_id)
```

## Running Tests

### Test Categories

```bash
# Run all tests (includes slow integration tests)
make test

# Fast tests only (unit tests, excludes marked 'slow')
make test-fast

# With coverage report (target: 80% minimum)
make test-cov
# Output: htmlcov/index.html (open in browser)

# Privacy/anonymization tests
make test-privacy

# API integration tests
make test-api

# Vectorstore tests
make test-vectorstore
```

### Writing New Tests

1. Create test file in `tests/test_*.py`
2. Use pytest fixtures from `tests/conftest.py`
3. Mark slow tests:
   ```python
   @pytest.mark.slow
   def test_heavy_computation():
       pass
   ```
4. Ensure coverage for your code paths
5. Run: `make test-cov` to verify

### Coverage Requirements

- Target: **≥80% coverage** (configured in `pyproject.toml`)
- Critical files (security, RAG logic): aim for 100%
- Check report: `open htmlcov/index.html`

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b <type>/<description>
```

Branch naming conventions:
- `feat/`: New feature (e.g., `feat/add-evaluation-metrics`)
- `fix/`: Bug fix (e.g., `fix/cors-policy-issue`)
- `security/`: Security improvement (e.g., `security/input-validation`)
- `docs/`: Documentation (e.g., `docs/architecture-diagram`)
- `refactor/`: Code refactoring (e.g., `refactor/logging-module`)

### 2. Commit with Conventional Format

```bash
git commit -m "type(scope): short description

Optional longer description explaining the why.

Fixes #123"
```

Types: `feat`, `fix`, `security`, `docs`, `refactor`, `test`, `perf`, `chore`

Examples:
```
feat(rag): add Precision@K evaluation metric
fix(api): resolve CORS policy vulnerability
security(upload): add DICOM file validation
docs(readme): add architecture diagram
test(evaluation): increase coverage to 85%
```

### 3. Ensure All Checks Pass

CI enforces the same checks as pre-commit; lint failures **block** the pipeline (no `continue-on-error`).

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Run tests locally
make test-cov

# Run security scan
make security

# Run linting (must pass before merge)
make lint
```

GitHub Actions on push/PR to `main` / `develop`:

| Job | Workflow | Notes |
|-----|----------|-------|
| Tests | `ci.yml` | Matrix: Python 3.10, 3.11, 3.12 |
| Lint | `ci.yml` | ruff, black, isort (blocking) |
| Docker build + Trivy | `docker-build.yml` | Hadolint → build → fail on HIGH/CRITICAL |
| Dependencies & secrets | `security-scan.yml` | pip-audit, Gitleaks, Bandit |

### 4. Push and Open PR

```bash
git push origin <your-branch>
```

On GitHub:
- Link related issues (e.g., "Fixes #42")
- Describe what changed and why
- Reference any HIPAA/GDPR compliance considerations if applicable

### 5. Code Review

- Respond to review comments
- Push additional commits (pre-commit will auto-check them)
- Once approved, maintainer will merge to `main`
- For durable architecture changes, add or update an ADR in `docs/adr/`

## Releases

Maintainers cut releases with a semver Git tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The `release.yml` workflow:

1. Generates the release notes from git history using **git-cliff** (`cliff.toml`, Conventional Commits)
2. Publishes a GitHub Release with that body

The `docker-build.yml` workflow also builds and tags container images on the same `v*.*.*` tags.

## Development Workflows

### Modifying RAG Pipeline

```bash
# Make changes to scripts/multimodal_rag_openai.py
# Test locally with sample data
make test-fast

# Run full evaluation
python scripts/evaluate_rag.py
# Review results in data/evaluations/

# If adding new evaluation queries
# Edit data/evaluation/eval_queries.json and commit with your PR
```

### Adding API Endpoint

```bash
# 1. Add route in api/main.py
# 2. Add service logic in api/services/
# 3. Add types and validation
# 4. Write test in tests/test_api.py
# 5. Run: make test-api
# 6. Verify in OpenAPI docs: http://localhost:8000/docs
```

### Security & Privacy Changes

All changes involving:
- Data anonymization
- File uploads (DICOM validation)
- Authentication/authorization
- API rate limiting

Must include:
- Security test in `tests/test_*.py`
- Updated threat model in code comments
- Run: `make security && make test-privacy`

## Troubleshooting

### Virtual Environment Issues

```bash
# Python not found or wrong version?
python3 --version  # Should be 3.10, 3.11, or 3.12

# Re-create venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Import Errors

```bash
# Reinstall in editable mode
pip install -e ".[dev]"

# Verify package structure
python -c "import src; import api; print('✓')"
```

### Pre-commit Hook Failures

```bash
# See what hooks are installed
pre-commit run --all-files --verbose

# Fix issues (e.g., formatting)
make format

# Re-commit
git add . && git commit -m "fix: formatting"
```

### Test Failures

```bash
# Run with verbose output
pytest tests/test_rag_service.py -vv

# Run single test
pytest tests/test_rag_service.py::test_retrieve_similar_cases -vv

# Show print statements
pytest tests/ -vv -s

# Stop on first failure
pytest tests/ -x
```

### OpenAI API Issues

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
EOF

# Test API key
python -c "import openai; print(openai.api_key[:10])"
```

## Development Tools

### Makefile Targets

```bash
make help              # Show all available commands
make install-dev      # Install dev dependencies
make test             # Run all tests
make test-cov         # Tests with coverage
make lint             # Run all linters
make format           # Auto-format code
make security         # Run security checks
make clean            # Remove caches
make run              # Start FastAPI server
make evaluate         # Run RAG evaluation
make mlflow-ui        # Start MLflow experiment tracker
make monitoring-up  # Prometheus + Grafana (requires app running)
make monitoring-down
```

### Useful Commands

```bash
# Start backend in development mode
make run
# API available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs

# Start Streamlit app (separate terminal)
streamlit run app/streamlit_app.py

# Monitor code changes and re-run tests
pytest tests/ --looponfail

# Profile performance
python -m cProfile -s cumulative scripts/index_Qdrant.py
```

## Questions or Need Help?

- Check existing GitHub issues
- Open a new issue with detailed description
- Review Architecture Decision Records in `docs/adr/`

## Code of Conduct

Be respectful, inclusive, and constructive. All contributors are expected to adhere to professional standards.

---

**Happy contributing! 🚀**
