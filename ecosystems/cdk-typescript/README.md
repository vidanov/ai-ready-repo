# CDK TypeScript — AI-Ready Ecosystem

An AI-ready AWS CDK project template in TypeScript.

Applies the same principles as the root Python template: executable rules over
prose, behavioral verification, drills that prove gates can convict.

## Quick start

```bash
cd ecosystems/cdk-typescript
make bootstrap
make verify
```

## Stack

| Tool | Purpose |
|------|---------|
| AWS CDK v2 | Infrastructure as code |
| TypeScript | Type safety |
| jest | Unit tests |
| eslint | Linting + import boundaries |
| prettier | Formatting |
| cdk-nag | Security and best-practice checks |
| cdk synth | Synthesis verification |

## Project structure

```
ecosystems/cdk-typescript/
├── bin/                  CDK app entry point
│   └── app.ts
├── lib/                  Stack definitions
│   └── example-stack.ts
├── test/                 Tests
│   └── example-stack.test.ts
├── docs/adr/             Architecture Decision Records
├── cdk.json              CDK configuration
├── tsconfig.json         TypeScript configuration
├── package.json          Dependencies + scripts
├── .eslintrc.json        Linter configuration
├── .prettierrc           Formatter configuration
├── Makefile              Task interface (same targets as root)
└── AGENTS.md             Agent guidance (CDK-specific)
```

## Verification ladder

`make verify` runs:

```
format-check → lint → typecheck → test → cdk-synth → cdk-nag → validate-adrs
```

This is identical to what CI would run.
