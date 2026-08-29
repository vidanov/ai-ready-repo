# AGENTS.md

Terraform ecosystem. Rules that tools cannot enforce.

## Commands

| Task | Command |
|------|---------|
| Bootstrap | `make bootstrap` |
| Full verification | `make verify` |
| Fast check | `make verify-fast` |
| Tests | `make test` |
| Format | `make fmt` |
| Lint | `make lint` |
| Security scan | `make security` |

## Non-obvious constraints

- All resources MUST be inside modules, not in root configuration files.
  Root is for composition only. See ADR-TF-001.
- Do NOT use `terraform apply` from this directory. This is a module library,
  not a deployment configuration. Consumers instantiate modules in their own
  state.
- Variable defaults MUST NOT contain environment-specific values (account IDs,
  region, VPC IDs). Those come from the consumer.
- checkov suppressions require a comment with justification. A bare
  `#checkov:skip=CKV_*` is a bug.

## Completion evidence

Before claiming a task is complete:

1. Run `make verify` and confirm it passes.
2. Report every command run and its exit code.
3. If adding a resource, include the checkov output showing no new findings.
4. State anything that requires an AWS account to verify.
