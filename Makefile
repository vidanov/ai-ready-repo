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
	@echo "→ Wiring versioned git hooks (.githooks/)..."
	@git config core.hooksPath .githooks
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
test-unit: ## Run unit tests only (with coverage enforcement)
	uv run pytest tests/unit -v --cov=src --cov-report=term-missing --cov-report=html

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
verify: format-check lint typecheck import-check test-unit validate-adrs sync-badges-check ## Run complete verification (same as CI)
	@echo "✓ All checks passed"

.PHONY: verify-fast
verify-fast: format-check lint typecheck import-check ## Fast verification (no tests)
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

.PHONY: adopt
adopt: ## Generate AI-readiness scaffold in another repo (usage: make adopt REPO=/path/to/repo)
	@python3 scripts/adopt.py $(REPO)

.PHONY: adopt-dry-run
adopt-dry-run: ## Show what adopt would generate without writing files (usage: make adopt-dry-run REPO=/path/to/repo)
	@python3 scripts/adopt.py $(REPO) --dry-run

# ── Badge sync ───────────────────────────────────────────────────────────────

.PHONY: sync-badges
sync-badges: ## Recompute README's Open Items badge from CONTRIBUTING.md and fix it in place
	@python3 scripts/sync_readme_badges.py

.PHONY: sync-badges-check
sync-badges-check: ## Fail if README's Open Items badge is stale (no write) — run in CI
	@python3 scripts/sync_readme_badges.py --check

# ── Lint changed files only ──────────────────────────────────────────────────

.PHONY: lint-changed
lint-changed: ## Lint only files changed since last commit
	@git diff --name-only HEAD | grep '\.py$$' | xargs --no-run-if-empty uv run ruff check

# ── Drills — prove gates can convict ─────────────────────────────────────────

.PHONY: drill-import-check
drill-import-check: ## Prove the import boundary gate fires on a real violation
	@echo "→ Planting a known forbidden import (infrastructure → domain bypass via application)..."
	@echo "from ai_ready_repo.infrastructure import InMemoryOrderRepository" >> src/ai_ready_repo/domain/__init__.py
	@echo "→ Running import-check (must reject the planted violation)..."
	@trap 'git checkout src/ai_ready_repo/domain/__init__.py 2>/dev/null' EXIT; \
	OUTPUT=$$(uv run lint-imports 2>&1); \
	RC=$$?; \
	if [ $$RC -eq 0 ]; then \
		echo "✗ drill-import-check FAILED: gate did not fire — check is miswired"; \
		exit 1; \
	fi; \
	if ! echo "$$OUTPUT" | grep -q "ai_ready_repo.domain"; then \
		echo "✗ drill-import-check FAILED: gate exited nonzero but did not name the planted module"; \
		echo "  Output was:"; \
		echo "$$OUTPUT" | head -5; \
		exit 1; \
	fi; \
	if ! echo "$$OUTPUT" | grep -q "ai_ready_repo.infrastructure"; then \
		echo "✗ drill-import-check FAILED: gate exited nonzero but did not name the forbidden dependency"; \
		echo "  Output was:"; \
		echo "$$OUTPUT" | head -5; \
		exit 1; \
	fi; \
	echo "✓ drill-import-check passed: gate rejected the violation and named the forbidden edge"

.PHONY: drill-import-permit
drill-import-permit: ## Prove the import boundary gate permits a legal cross-layer import
	@echo "→ Planting a legal import (application → domain, which the contract permits)..."
	@echo "from ai_ready_repo.domain import Order" >> src/ai_ready_repo/application/__init__.py
	@echo "→ Running import-check (must exit zero — this import is allowed)..."
	@trap 'git checkout src/ai_ready_repo/application/__init__.py 2>/dev/null' EXIT; \
	OUTPUT=$$(uv run lint-imports 2>&1); \
	RC=$$?; \
	if [ $$RC -ne 0 ]; then \
		echo "✗ drill-import-permit FAILED: gate rejected a legal import"; \
		echo "  A linter that rejects valid imports is as broken as one that misses violations."; \
		echo "  Output was:"; \
		echo "$$OUTPUT" | head -5; \
		exit 1; \
	fi; \
	echo "✓ drill-import-permit passed: gate permitted the legal cross-layer import"

.PHONY: drill-transition-guard
drill-transition-guard: ## Prove the Order.transition() guard fires on an invalid transition
	@echo "→ Attempting invalid transition (pending → shipped)..."
	@uv run python3 scripts/drill_transition_guard.py



.PHONY: drill-dead-config
drill-dead-config: ## Find config keys in pyproject.toml that nothing references
	@uv run python scripts/drill_dead_config.py

.PHONY: drill-deny-catalog
drill-deny-catalog: ## Verify deny catalog: golden-file lock, additive-only, patterns fire
	@uv run python scripts/deny_catalog.py

.PHONY: drill-ci-coverage
drill-ci-coverage: ## Verify every verification target runs in CI (no monitoring gaps)
	@uv run python scripts/drill_ci_coverage.py

.PHONY: drill-reason-swap
drill-reason-swap: ## Prove drill assertions test the specific violation, not just any failure	@echo "→ Testing that drill-import-check's reason assertion discriminates..."
	@echo "→ Injecting a SYNTAX error (not an import violation) into domain..."
	@echo "this is not valid python" >> src/ai_ready_repo/domain/__init__.py
	@trap 'git checkout src/ai_ready_repo/domain/__init__.py 2>/dev/null' EXIT; \
	OUTPUT=$$(uv run lint-imports 2>&1); \
	RC=$$?; \
	if [ $$RC -eq 0 ]; then \
		echo "✓ linter did not fire on syntax error (exits zero) — reason-swap not applicable"; \
		exit 0; \
	fi; \
	if echo "$$OUTPUT" | grep -q "ai_ready_repo.infrastructure"; then \
		echo "✗ drill-reason-swap FAILED: linter reported an import violation on a syntax-only error"; \
		echo "  The reason assertion would pass on the wrong failure class."; \
		echo "  Output was:"; \
		echo "$$OUTPUT" | head -5; \
		exit 1; \
	fi; \
	echo "✓ drill-reason-swap passed: syntax error produces different output than import violation"

.PHONY: drill-measurement-invalid
drill-measurement-invalid: ## Prove the eval gate treats a corpse (unrun check) as distinct from a failure (1f916 #3539)
	@bash scripts/drill_measurement_invalid.sh

drill-coverage-floor: ## Prove a green pass rate over a rotting harness is refused, not laundered (1f916 #3539)
	@bash scripts/drill_coverage_floor.sh

.PHONY: verify-tamperproof
verify-tamperproof: ## Run verification from a trusted copy (oracle-tampering protection)
	@bash scripts/verify_tamperproof.sh

.PHONY: verify-from-git
verify-from-git: ## Run unit tests from the committed copy at HEAD, not the working tree
	@bash scripts/verify_from_git.sh

.PHONY: drill-verifier-isolation
drill-verifier-isolation: ## Prove the verifier reads from outside the agent's write path (credit: hermes-voyager, 1f916 #3385)
	@echo "→ The property under test: an uncommitted edit to a test file must NOT"
	@echo "  change the verdict of a verifier that sources tests from git HEAD."
	@echo "→ Planting a weakened assertion into the working-tree test file..."
	@# Replace a real assertion with one that can never fail. A verifier that
	@# reads the working tree would accept this; one reading git HEAD ignores it.
	@printf '\n\ndef test_planted_always_passes() -> None:\n    assert True  # planted by drill-verifier-isolation\n' >> tests/unit/test_domain_order.py
	@# Also weaken an existing assertion so the working tree is genuinely tampered.
	@python3 -c "import pathlib; p = pathlib.Path('tests/unit/test_domain_order.py'); t = p.read_text(); p.write_text(t.replace('assert order.customer_id == \"cust-1\"', 'assert order.customer_id == order.customer_id  # weakened by drill'))"
	@trap 'git checkout tests/unit/test_domain_order.py 2>/dev/null' EXIT; \
	echo "→ [1/2] Working-tree pytest sees the weakened file (control)..."; \
	if ! grep -q "weakened by drill" tests/unit/test_domain_order.py; then \
		echo "✗ drill-verifier-isolation FAILED: could not plant the tamper"; \
		exit 1; \
	fi; \
	echo "  ✓ working tree is tampered (assertion weakened, dummy test added)"; \
	echo "→ [2/2] Git-sourced verifier must ignore the working-tree edit..."; \
	OUTPUT=$$(bash scripts/verify_from_git.sh 2>&1); \
	RC=$$?; \
	if [ $$RC -ne 0 ]; then \
		echo "✗ drill-verifier-isolation FAILED: git-sourced verifier errored"; \
		echo "$$OUTPUT" | tail -10; \
		exit 1; \
	fi; \
	if echo "$$OUTPUT" | grep -q "test_planted_always_passes"; then \
		echo "✗ drill-verifier-isolation FAILED: verifier picked up the PLANTED test"; \
		echo "  This means it read the working tree, not git HEAD — inside the write path."; \
		exit 1; \
	fi; \
	echo "  ✓ verifier ran the committed tests; the planted test is absent from its run"; \
	echo "✓ drill-verifier-isolation passed: the checker is outside the agent's uncommitted write path"

.PHONY: eval
eval: ## Run agent evaluation tasks against this repo
	@python3 scripts/run_evals.py

# ── Utilities ────────────────────────────────────────────────────────────────

.PHONY: setup-tools
setup-tools: ## Create config bridges for Cursor, Claude Code, Copilot, Aider, Gemini, Windsurf
	@bash scripts/setup_tool_bridges.sh

.PHONY: clean
clean: ## Remove generated artefacts
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage dist build

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
