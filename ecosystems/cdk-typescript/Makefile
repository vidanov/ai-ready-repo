.DEFAULT_GOAL := help

.PHONY: bootstrap
bootstrap: ## Set up development environment
	npm install

.PHONY: format
format: ## Auto-format all source files
	npx prettier --write "lib/**/*.ts" "bin/**/*.ts" "test/**/*.ts"

.PHONY: format-check
format-check: ## Check formatting without modifying files
	npx prettier --check "lib/**/*.ts" "bin/**/*.ts" "test/**/*.ts"

.PHONY: lint
lint: ## Run linter
	npx eslint "lib/**/*.ts" "bin/**/*.ts" "test/**/*.ts"

.PHONY: typecheck
typecheck: ## Run TypeScript compiler (no emit)
	npx tsc --noEmit

.PHONY: test
test: ## Run all tests
	npx jest

.PHONY: cdk-synth
cdk-synth: ## Synthesize CloudFormation template
	npx cdk synth --quiet

.PHONY: cdk-nag
cdk-nag: ## Run cdk-nag security checks (runs during synth)
	npx cdk synth --quiet 2>&1 | grep -E "(Error|Warning|Info)" || true

.PHONY: validate-adrs
validate-adrs: ## Validate ADR format
	@python3 ../../scripts/validate_adrs.py --adr-dir docs/adr

.PHONY: verify
verify: format-check lint typecheck test cdk-synth validate-adrs ## Run complete verification
	@echo "✓ All checks passed"

.PHONY: verify-fast
verify-fast: format-check lint typecheck ## Fast verification (no tests/synth)
	@echo "✓ Fast checks passed"

.PHONY: clean
clean: ## Remove generated artifacts
	rm -rf node_modules cdk.out coverage dist

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
