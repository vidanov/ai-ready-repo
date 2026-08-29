---
id: ADR-CDK-001
status: accepted
scope:
  - bin/app.ts
  - lib/**
---

# All stacks must include cdk-nag Aspects

## Decision

Every CDK app MUST apply `AwsSolutionsChecks` (or equivalent cdk-nag rule pack)
as an Aspect at the app level. Individual stacks MUST NOT opt out of cdk-nag.

Suppressions are allowed with a documented `reason` field. A suppression
without a reason is a bug.

## Reasons

- cdk-nag catches security and best-practice violations at synthesis time,
  before deployment. Removing it silently downgrades the security posture.
- App-level application ensures new stacks automatically inherit the checks.
  Stack-level application requires remembering to add it, which agents and
  humans both forget.
- Suppressions with reasons create an audit trail. A future reviewer can
  evaluate whether the reason still holds.

## Verification

Check that cdk-nag is applied in the app entry point:

```bash
grep -q "AwsSolutionsChecks" bin/app.ts && echo "cdk-nag applied" || echo "MISSING"
```

Run synthesis and check for nag output:

```bash
make cdk-synth
```

## Firing condition

Remove the `Aspects.of(app).add(new AwsSolutionsChecks())` line from `bin/app.ts`
and run `make cdk-synth`. The synthesis should still succeed, but the security
checks will be silently missing. This is the failure mode: cdk-nag removal
does not break synth, it just removes the safety net.

A behavioral drill would: remove cdk-nag, add a resource that violates a rule
(e.g., an unencrypted S3 bucket), run synth, and assert the violation is NOT
caught. Then restore cdk-nag and assert it IS caught.

## Retirement

Remove this constraint if:

- The project moves to a different security scanning tool that runs outside
  CDK synthesis (e.g., cfn-guard on the synthesized template).
- The project adopts AWS Control Tower or Service Control Policies that enforce
  the same rules at the account level.
