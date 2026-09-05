TRUSTED_REF ?= HEAD

.DEFAULT_GOAL := help

# ── Bootstrap ────────────────────────────────────────────────────────────────

.PHONY: bootstrap
bootstrap: ## Set up a fresh development environment from scratch
	@echo "→ Installing the locked development environment..."
	uv sync --frozen --all-extras
	@echo "→ Copying .env.example → .env (if not present)..."
	@test -f .env || cp .env.example .env
	@echo "→ Wiring versioned git hooks (.githooks/)..."
	@git config core.hooksPath .githooks
	@echo "→ Bootstrap complete. Commands run through uv; activation is optional."
	@echo "→ Verify with: make check-env"

.PHONY: check-env
check-env: ## Verify the environment is correctly set up
	@uv run python --version
	@echo "→ uv: $$(uv --version)"
	@uv run python -c "import ai_ready, ai_ready_repo; print('→ Toolkit and example importable: ok')"
	@echo "→ Environment check passed"

# ── Formatting ───────────────────────────────────────────────────────────────

.PHONY: format
format: ## Auto-format all source files
	uv run ruff format src tests scripts

.PHONY: format-check
format-check: ## Check formatting without modifying files
	uv run ruff format --check src tests scripts

# ── Linting ──────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Run linter
	uv run ruff check src tests scripts

.PHONY: lint-fix
lint-fix: ## Run linter and apply safe auto-fixes
	uv run ruff check --fix src tests scripts

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

.PHONY: test-toolkit
test-toolkit: ## Test reusable tooling with its own coverage floor
	uv run pytest tests/unit/test_adoption.py tests/unit/test_audit.py tests/unit/test_toolkit_cli.py tests/unit/test_verification.py --cov=ai_ready --cov-report=term-missing

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
	@python3 scripts/ai_readiness_audit.py "$(REPO)"

.PHONY: adopt
adopt: ## Generate AI-readiness scaffold in another repo (usage: make adopt REPO=/path/to/repo)
	@python3 scripts/adopt.py "$(REPO)" --apply

.PHONY: adopt-dry-run
adopt-dry-run: ## Show what adopt would generate without writing files (usage: make adopt-dry-run REPO=/path/to/repo)
	@python3 scripts/adopt.py "$(REPO)" --dry-run

# ── Badge sync ───────────────────────────────────────────────────────────────

.PHONY: sync-badges
sync-badges: ## Recompute README's Open Items badge from docs/backlog.md and fix it in place
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
drill-import-check: ## Check import boundaries in a disposable workspace
	@uv run python -m ai_ready.verification.sandbox . python scripts/drill_imports.py deny


.PHONY: drill-import-permit
drill-import-permit: ## Check import boundaries in a disposable workspace
	@uv run python -m ai_ready.verification.sandbox . python scripts/drill_imports.py permit


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
drill-reason-swap: ## Check import boundaries in a disposable workspace
	@uv run python -m ai_ready.verification.sandbox . python scripts/drill_imports.py reason


.PHONY: drill-measurement-invalid
drill-measurement-invalid: ## Prove the eval gate treats a corpse (unrun check) as distinct from a failure (1f916 #3539)
	@bash scripts/drill_measurement_invalid.sh

drill-coverage-floor: ## Prove a green pass rate over a rotting harness is refused, not laundered (1f916 #3539)
	@bash scripts/drill_coverage_floor.sh

drill-required-axis: ## Prove a required-but-unexercised axis is rejected, not averaged into a green rate (1f916 #3595)
	@bash scripts/drill_required_axis.sh

drill-referent-liveness: ## Prove a fixture whose referent drifted away is reported STALE_OR_DRIFTED, not green (gate 3, 1f916 #3357)
	@bash scripts/drill_referent_liveness.sh

.PHONY: external-reader
external-reader: ## Run the disjoint witness: reads eval tasks independently, writes reader_witness.json (#035)
	@uv run python scripts/external_reader.py

.PHONY: stamp-manifest
stamp-manifest: ## Stamp referent_manifest.json with verified_at=now (run after external-reader)
	@uv run python scripts/referent_liveness.py --stamp

.PHONY: drill-external-witness
drill-external-witness: ## Prove freshness gate fails when the external reader's record is absent (#035, whitehat-explorer 1f916 #3714)
	@bash scripts/drill_external_witness.sh

.PHONY: verify-snapshot
verify-snapshot: ## Verify a snapshot taken at invocation time (does not protect prior edits)
	@bash scripts/verify_tamperproof.sh

.PHONY: verify-tamperproof
verify-tamperproof: verify-snapshot ## Compatibility alias for verify-snapshot

.PHONY: verify-from-git
verify-from-git: ## Run unit tests from the committed copy at HEAD, not the working tree
	@bash scripts/verify_from_git.sh "$(TRUSTED_REF)"

.PHONY: drill-verifier-isolation
drill-verifier-isolation: ## Prove committed tests ignore edits in an isolated workspace
	@bash scripts/drill_verifier_isolation.sh


.PHONY: eval
eval: ## Run verification regression tasks (does not launch agents)
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
