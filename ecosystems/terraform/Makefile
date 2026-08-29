.DEFAULT_GOAL := help

.PHONY: bootstrap
bootstrap: ## Set up development environment
	terraform -chdir=modules/example init -backend=false
	@command -v tflint >/dev/null 2>&1 || echo "⚠ tflint not installed: brew install tflint"
	@command -v checkov >/dev/null 2>&1 || echo "⚠ checkov not installed: pip install checkov"

.PHONY: fmt
fmt: ## Auto-format all Terraform files
	terraform fmt -recursive .

.PHONY: fmt-check
fmt-check: ## Check formatting without modifying files
	terraform fmt -check -recursive .

.PHONY: validate
validate: ## Validate Terraform syntax and references
	terraform -chdir=modules/example validate

.PHONY: lint
lint: ## Run tflint
	tflint --chdir=modules/example --config=../../.tflint.hcl

.PHONY: security
security: ## Run checkov security scan
	checkov -d modules/ --config-file .checkov.yml --quiet

.PHONY: test
test: ## Run Terraform native tests
	terraform -chdir=modules/example test

.PHONY: docs
docs: ## Generate module documentation
	@command -v terraform-docs >/dev/null 2>&1 && \
		terraform-docs markdown modules/example > modules/example/README.md || \
		echo "⚠ terraform-docs not installed: brew install terraform-docs"

.PHONY: validate-adrs
validate-adrs: ## Validate ADR format
	@python3 ../../scripts/validate_adrs.py --adr-dir docs/adr

.PHONY: verify
verify: fmt-check validate lint security validate-adrs ## Run complete verification
	@echo "✓ All checks passed"

.PHONY: verify-fast
verify-fast: fmt-check validate lint ## Fast verification (no security scan)
	@echo "✓ Fast checks passed"

.PHONY: clean
clean: ## Remove generated artifacts
	rm -rf modules/example/.terraform modules/example/.terraform.lock.hcl

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
