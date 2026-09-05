---
name: improve-repository
description: Assess and improve an existing repository's structure, agent guidance, adoption workflow, and verification reliability. Use for repository health reviews or authorized readiness improvements, not routine feature implementation.
---

# Improve a repository

Make the repository easier to understand and safer to change, using evidence from
its actual purpose and tools. A review request produces findings; an improvement
request includes implementation and verification within the authorized scope.

## Establish the target

Resolve the target repository to an absolute path. Read its applicable AGENTS.md,
README, build/package configuration, and relevant architectural decisions. Inspect
the working tree and recent changes before editing; preserve unrelated work.
Identify what users should accomplish with the project, its supported stacks,
and the commands contributors and CI actually run.

Distinguish the reusable product from examples, research, generated output, and
compatibility entry points. Move files only when the separation helps a real
consumer, and update callers and links together. Keep conventional root documents
where contributors and hosting tools expect them; put detailed material under docs.

## Find the smallest useful improvement

Run the existing inexpensive checks to establish a baseline. Trace a realistic
consumer path, such as fresh setup, running a check, or adopting into another repo.
Prioritize reproducible incorrect behavior, misleading success reports, broken
onboarding, or conflicting instructions before cosmetic organization.

For a verification tool, test both an intentional failure and a valid case.
Check that missing inputs and commands cannot return success, and that updating a
baseline cannot hide failures. For discovery tools, try the project's real layouts,
including colocated tests and workspaces; exclude dependencies and generated files.
Keep unknown evidence distinct from failed checks.

## Implement within the project's conventions

Use the existing package manager, commands, architecture, and test framework.
Do not impose Make, Python tooling, or the toolkit's order-domain example on an
unrelated project. Integrate into existing configuration rather than create a
competing entry point. Keep agent instructions concise and put enforceable rules
in tools; read the reasoning before changing an architectural constraint.

For a behavioral defect, add a focused regression that reproduces it, implement
the fix, and confirm the failure and success paths. Run cheap checks as you edit,
then the repository's full verification. Run mutation drills in disposable copies,
never by damaging the working tree. Do not lower thresholds or remove checks just
to make verification pass. When a check cannot run, report the limitation.

Respect existing authorization and review boundaries. This skill itself grants no
permission to publish, push, deploy, change hosted settings, or contact people.

## Optional ai-ready toolkit

The toolkit is useful for an initial inventory or additive adoption preview; it
is not required. When installed, use `ai-ready audit /absolute/target --json` or
`ai-ready adopt /absolute/target`. From a bootstrapped toolkit checkout, use
`uv run --project /absolute/toolkit ai-ready audit /absolute/target --json`.
Always pass the target explicitly so the toolkit checkout is not audited by mistake.

Audit findings describe configuration, not proven correctness. Inspect findings
against native configuration before acting: the audit does not recognize every
stack or command convention. Adoption previews do not merge existing files; finish
integration deliberately. `adopt --apply` creates files and belongs only in an
authorized implementation. `ai-ready verify` executes the target's `make verify`;
use the native verification command directly when that target does not exist.

## Deliver evidence

Explain the practical improvement, files changed, checks run and exit codes, and
anything unverified. Separate configured, executed, and demonstrated evidence.
Do not claim better agent speed, cost, or reliability from green checks alone;
those claims require comparable recorded agent runs. Identify the next material
gap without expanding the current task into an open-ended rewrite.
