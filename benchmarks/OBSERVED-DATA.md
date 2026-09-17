# Observed effort data from a real step-runner (observational, not a benchmark)

Status: observational prior-art. This is **not** a comparative agent benchmark and
does not establish any efficiency claim for this repository's conventions. It
records what one agent-operations tool happened to persist, so the benchmark
harness (see [README.md](README.md)) can be built to record the same shape
deliberately, in paired arms, rather than from scratch.

Three exclusions stated first, so this cannot be misread as a result:

- **Single arm.** No baseline-vs-improved pair. It cannot show that any
  convention caused any number.
- **No tokens.** The source did not capture input/output tokens, the metric the
  benchmark protocol most wants. Effort here is attempts only.
- **One model.** Every number was produced by a single model generation. A newer
  model may pay a different bill on the same checks; reporting the number without
  the model is the same omission as a check that hides its date.

## The signal: per-step attempts-to-green

An append-only ledger from a step-runner, one project, 558 completed steps. Each
step declares a re-runnable done condition and is retried until the condition
passes or a human intervenes.

- 549 of 558 steps carry a mechanically-checkable done condition.
- Attempts to reach green: median 2, mean 3.5, max 71.
- 449 of 558 steps (80%) took more than one attempt.
- 27 steps needed ten or more attempts.
- Total: **1958 attempts to land 558 greens.**

This is a measurement of the *cost* of a verification regime. It is not a
measurement of the regime's *value*, because the ledger records how many attempts
a green took, not how many of those attempts caught a real defect versus re-ran a
check that was flaky, mis-specified, or already true. See
[backlog #042](../docs/backlog.md) (the cost side has no positive control).

## Three ways the number does not mean what it looks like

The raw attempts count is pushed in different directions by three properties the
ledger does not surface on its own.

- **It double-counts intent.** 51 clusters of near-duplicate task titles covered
  117 of the 558 steps (21%), accounting for 15% of all attempts. The runner's
  exact-match and tree-fingerprint dedup guards do not catch *near*-duplicates
  (same intent, reworded), so one intent produced several checked tasks and
  several bills. The cost is overstated by whatever fraction of that 21% was
  genuinely redundant.

- **It mostly checks presence, not behaviour.** 83% of the done-conditions were
  existence-style (a file exists, a string greps); 18% exercised behaviour. Most
  greens certify that the thing is there, not that it works. See
  [backlog #043](../docs/backlog.md).

- **It cannot see a whole tier.** Zero browser or end-to-end conditions. Nothing
  in the ledger asks whether a change worked for a user through the interface, so
  a class of regression lived outside the measured surface entirely, and the cost
  is understated by the tier that never entered the count. See
  [backlog #044](../docs/backlog.md).

## What to reuse

This ledger is a working reference for the recording layer the benchmark protocol
needs: per-unit-of-work, append-only, keyed to a re-runnable oracle exit code,
with a status vocabulary that separates earned evidence from a passing-but-unproven
condition from a human dismissal. The benchmark harness should record that same
shape, **add token capture and a model tag**, split attempts into productive
versus spinning (#042), label presence-only versus behaviour-exercising conditions
(#043), and declare its verification tiers (#044) — then run it in paired
baseline/improved arms. Only then does an effort number become an efficiency
result.

## Provenance and its limit

Source: one operator's ledger, anonymized (no tool name, project name, or paths).
The figures are real as of the observation and were produced by one model
generation. The operator additionally reports a *subjective* sense that some
harnesses feel faster to develop against; that is a felt impression, not a
measurement, and is recorded here as such rather than as data. The field moves
week to week, so a dated single-operator ledger is stale quickly — which is the
argument for the paired, model-tagged, multi-seat protocol, not for this snapshot.
