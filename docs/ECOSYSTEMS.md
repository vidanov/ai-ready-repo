# Ecosystems

The ai-ready-repo pattern (executable rules, behavioral verification, drills,
contribution-ready items) is not Python-specific. This document tracks the
expansion to other languages, frameworks, and infrastructure tools.

## How ecosystems are structured

Each ecosystem lives in `ecosystems/<name>/` with its own:

- `README.md` — quick start and ecosystem-specific patterns
- `Makefile` — same targets as root: `bootstrap`, `verify`, `test`, `lint`, `typecheck`
- `AGENTS.md` — ecosystem-specific agent guidance (what tools can't enforce)
- Verification toolchain — linters, formatters, type checkers native to that stack
- At least one ADR with firing condition and retirement condition
- At least one drill proving a gate can convict

The root `Makefile` provides `make verify-all` to run all ecosystems.

## Ecosystem catalog

### Implemented

| Ecosystem | Path | Stack | Status |
|-----------|------|-------|--------|
| **Python** | `src/`, `tests/` (root) | Python 3.14, uv, ruff, mypy, pytest, import-linter | ✅ Complete |

### In progress

| Ecosystem | Path | Stack | Status |
|-----------|------|-------|--------|
| **CDK TypeScript** | `ecosystems/cdk-typescript/` | AWS CDK v2, TypeScript, projen, jest, eslint, cdk-nag | 🟡 Scaffold |
| **Terraform** | `ecosystems/terraform/` | Terraform, tflint, checkov, terraform-docs | 🟡 Scaffold |

### Planned

| Ecosystem | Path | Stack | Priority | Notes |
|-----------|------|-------|----------|-------|
| **CDK Python** | `ecosystems/cdk-python/` | AWS CDK v2, Python, pytest, ruff, cdk-nag | High | Shares patterns with both Python and CDK TS |
| **React TypeScript** | `ecosystems/react-typescript/` | React 19, TypeScript, Vite, vitest, eslint, Playwright | Medium | Frontend complement to backend templates |
| **Next.js** | `ecosystems/nextjs/` | Next.js 15, TypeScript, vitest, eslint, Playwright | Medium | Fullstack frontend |
| **Go** | `ecosystems/go/` | Go 1.23, golangci-lint, go test, go vet | Medium | Strong typing reduces need for external checkers |
| **Rust** | `ecosystems/rust/` | Rust, cargo clippy, cargo test, cargo fmt | Lower | Compiler already enforces most rules |
| **Java/Spring** | `ecosystems/java-spring/` | Java 21, Gradle, Spring Boot, ArchUnit, JaCoCo | Medium | Enterprise ecosystem, ArchUnit maps to import-linter |
| **CloudFormation** | `ecosystems/cloudformation/` | cfn-lint, cfn-guard, taskcat | Lower | Simpler than CDK/Terraform |
| **Pulumi TypeScript** | `ecosystems/pulumi-typescript/` | Pulumi, TypeScript, jest, eslint | Lower | Alternative to CDK |
| **Vue TypeScript** | `ecosystems/vue-typescript/` | Vue 3, TypeScript, Vite, vitest, eslint | Lower | Alternative frontend |
| **Angular** | `ecosystems/angular/` | Angular 19, TypeScript, karma/jest, eslint | Lower | Enterprise frontend |

## Pattern mapping across ecosystems

Each ecosystem must implement the same pattern categories. The tools differ,
the principles do not.

| Pattern | Python | CDK TypeScript | Terraform | React TS |
|---------|--------|----------------|-----------|----------|
| **Version pin** | `.python-version` | `.nvmrc` + `package.json engines` | `.terraform-version` | `.nvmrc` |
| **Bootstrap** | `make bootstrap` (uv) | `make bootstrap` (npm/projen) | `make bootstrap` (terraform init) | `make bootstrap` (npm) |
| **Formatter** | ruff format | prettier | terraform fmt | prettier |
| **Linter** | ruff check | eslint | tflint | eslint |
| **Type checker** | mypy | tsc --noEmit | N/A (HCL is typed) | tsc --noEmit |
| **Import boundaries** | import-linter | eslint-plugin-import | N/A (module boundaries) | eslint-plugin-import |
| **Unit tests** | pytest | jest | terraform test | vitest |
| **Security scan** | ruff S rules, pip-audit | npm audit, eslint security | checkov, tfsec | npm audit |
| **Architecture check** | import-linter contracts | cdk-nag | checkov policies | eslint boundaries |
| **ADR validation** | `scripts/validate_adrs.py` | same (shared) | same (shared) | same (shared) |
| **Drill** | `make drill-*` | `make drill-*` | `make drill-*` | `make drill-*` |

## Contributing an ecosystem

To add a new ecosystem:

1. Create `ecosystems/<name>/` with the standard files
2. Implement at least: `make bootstrap`, `make verify`, one ADR, one drill
3. Add a row to the catalog above
4. Add contribution items to CONTRIBUTING.md
5. Submit a PR

The acceptance test: `cd ecosystems/<name> && make bootstrap && make verify`
must pass from a fresh clone.
