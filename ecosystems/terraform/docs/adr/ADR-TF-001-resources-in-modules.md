---
id: ADR-TF-001
status: accepted
scope:
  - modules/**
---

# All resources must live inside modules

## Decision

All Terraform resources MUST be defined inside `modules/<name>/`.
Root-level `.tf` files are for module composition and backend
configuration only. No `resource` blocks at root level.

## Reasons

- Modules enforce input/output contracts. A resource at root level has
  implicit access to all variables and locals, making dependencies invisible.
- Modules are independently testable with `terraform test`.
- Consumers can instantiate modules with different configurations for
  different environments without duplicating resource definitions.
- An agent adding infrastructure is constrained to a module boundary,
  which limits blast radius.

## Verification

Search for resource blocks outside modules:

```bash
grep -rn "^resource " *.tf 2>/dev/null && echo "VIOLATION: resources at root" || echo "OK"
```

Run the full verification:

```bash
make verify
```

## Firing condition

Add a `resource "aws_s3_bucket" "test"` block to a root-level `.tf` file.
Run `make verify`. The lint or structure check should flag the violation.
If it passes silently, the gate is not enforcing the boundary.

## Retirement

Remove this constraint if:

- The project becomes a single-environment deployment where module
  boundaries add ceremony without protecting anything.
- The project adopts Terragrunt, which enforces module boundaries
  at a different layer.
