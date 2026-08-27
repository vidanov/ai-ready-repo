.DEFAULT_GOAL := help

# ── Bootstrap ────────────────────────────────────────────────────────────────

.PHONY: bootstrap
bootstrap: ## Set up a fresh development environment from scratch
	@echo "→ Creating virtual environment..."
	uv venv
	@echo "→ Installing dependencies..."
	uv pip install -e ".[dev]"
	@echo "→ Copying .env.example → .env (if not present)..."
	@test -f .env || cp .env.example .env
	@echo "→ Bootstrap complete. Activate with: source .venv/bin/activate"
	@echo "→ Verify with: make check-env"

.PHONY: check-env
check-env: ## Verify the environment is correctly set up
	@echo "→ Python: $$(python --version)"
	@echo "→ uv: $$(uv --version)"
	@python3 -c "import ai_ready_repo; print('→ Package importable: ok')"
	@echo "→ Environment check passed"

# ── Formatting ───────────────────────────────────────────────────────────────

.PHONY: format
format: ## Auto-format all source files
	uv run ruff format src tests

.PHONY: format-check
format-check: ## Check formatting without modifying files
	uv run ruff format --check src tests

# ── Linting ──────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Run linter
	uv run ruff check src tests

.PHONY: lint-fix
lint-fix: ## Run linter and apply safe auto-fixes
	uv run ruff check --fix src tests

# ── Type checking ────────────────────────────────────────────────────────────

.PHONY: typecheck
typecheck: ## Run static type checker
	uv run mypy src

# ── Import boundaries ────────────────────────────────────────────────────────

.PHONY: import-check
import-check: ## Enforce module boundary contracts
	uv run lint-imports

# ── Tests ────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run all tests
	uv run pytest

.PHONY: test-unit
test-unit: ## Run unit tests only
	uv run pytest tests/unit -v

.PHONY: test-integration
test-integration: ## Run integration tests only (requires services)
	uv run pytest tests/integration -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# ── Security ─────────────────────────────────────────────────────────────────

.PHONY: security
security: ## Run security scan
	uv run ruff check --select S src

# ── Verification ladder ──────────────────────────────────────────────────────

.PHONY: verify
verify: format-check lint typecheck import-check test-unit validate-adrs ## Run complete verification (same as CI)
	@echo "✓ All checks passed"

.PHONY: verify-fast
verify-fast: format-check lint typecheck ## Fast verification (no tests)
	@echo "✓ Fast checks passed"

# ── ADR validation ───────────────────────────────────────────────────────────

.PHONY: validate-adrs
validate-adrs: ## Validate ADR format and required fields
	@python3 scripts/validate_adrs.py

# ── AI-readiness audit ───────────────────────────────────────────────────────

.PHONY: audit
audit: ## Run AI-readiness audit on this repository
	@python3 scripts/ai_readiness_audit.py .

.PHONY: audit-repo
audit-repo: ## Run AI-readiness audit on another repo (usage: make audit-repo REPO=/path/to/repo)
	@python3 scripts/ai_readiness_audit.py $(REPO)

# ── Lint changed files only ──────────────────────────────────────────────────

.PHONY: lint-changed
lint-changed: ## Lint only files changed since last commit
	@git diff --name-only HEAD | grep '\.py$$' | xargs --no-run-if-empty uv run ruff check

# ── Evals ────────────────────────────────────────────────────────────────────

.PHONY: eval
eval: ## Run agent evaluation tasks against this repo
	@python3 scripts/run_evals.py

# ── Utilities ────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove generated artefacts
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage dist build

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
