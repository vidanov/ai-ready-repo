# AGENTS.md

CDK TypeScript ecosystem. Rules that tools cannot enforce.

## Commands

| Task | Command |
|------|---------|
| Bootstrap | `make bootstrap` |
| Full verification | `make verify` |
| Fast check | `make verify-fast` |
| Tests | `make test` |
| Synth | `make cdk-synth` |
| Format | `make format` |
| Lint | `make lint` |

## Non-obvious constraints

- All stacks MUST include cdk-nag Aspects. A stack without cdk-nag passes
  synth but misses security checks. See ADR-CDK-001.
- Do NOT use `cdk.CfnOutput` for sensitive values. Use SSM Parameter Store
  or Secrets Manager.
- Stack names MUST be parameterized, not hardcoded. Multiple environments
  deploy from the same code.
- `cdk.context.json` is committed. Do NOT add account-specific context
  (account IDs, VPC IDs) to this file. Use environment variables or
  CDK context lookups.

## Completion evidence

Before claiming a task is complete:

1. Run `make verify` and confirm it passes.
2. Run `npx cdk diff` and include the output.
3. Report every command run and its exit code.
4. State anything that could not be verified without an AWS account.
