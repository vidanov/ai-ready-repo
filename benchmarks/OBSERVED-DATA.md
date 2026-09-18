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

An append-only ledger from a step-runner, one project, 612 steps. Each step
declares a re-runnable done condition and is retried until the condition passes or
a human intervenes.

- 610 of 612 steps carry a mechanically-checkable done condition.
- Attempts to reach green: median 2, mean 3.4, max 71.
- 488 of 597 attempted steps (81%) took more than one attempt.
- 27 steps needed ten or more attempts.
- Total: **2043 attempts across the ledger.**
- 193 of 612 steps (32%) were human-overridden after being flagged.

This is a measurement of the *cost* of a verification regime. It is not a
measurement of the regime's *value*, because the ledger records how many attempts
a green took, not how many of those attempts caught a real defect versus re-ran a
check that was flaky, mis-specified, or already true. See
[backlog #042](../docs/backlog.md) (the cost side has no positive control).

## Three ways the number does not mean what it looks like

The raw attempts count is pushed in different directions by three properties the
ledger does not surface on its own.

- **It double-counts intent.** Near-duplicate task titles (over 0.6 token
  overlap with an earlier step) covered 86 of the 612 steps (14%). The runner's
  exact-match and tree-fingerprint dedup guards do not catch *near*-duplicates
  (same intent, reworded), so one intent produced several checked tasks and
  several bills. The figure is threshold-sensitive: an earlier looser pass on a
  smaller snapshot reported 21%, so treat this as order-of-magnitude, not exact,
  and as an upper bound on waste rather than a measure of it (some repeats are
  legitimate instrument re-firing, not re-emitted intent).

- **Its behavioural oracles are declared, not proven.** An earlier version of
  this doc reported "83% of done-conditions were existence-style, 18% exercised
  behaviour." That figure is withdrawn: it came from string-matching done-command
  text and did not survive re-derivation. By the runner's actual oracle fields,
  610 of 612 steps declare a behaviour-bearing oracle (a pre-existing test run
  plus a scope match), so the split does not exist as stated. The corrected and
  sharper reading: near every step *claims* a behavioural check, but whether that
  test actually exercises the change (rather than re-running a suite that never
  covered it) is the pseudo-tested-method question the tags cannot answer. This is
  why the oracle-gap metric matters here, not a hand count of conditions. See
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

## Related literature (verified 2026-09-17)

Three of the four gaps this ledger surfaces have named, dated, citable prior work;
the two cross-checks derived on the discussion thread appear genuinely unpublished.

- **Presence vs behaviour** has a re-runnable metric. *Pseudo-tested methods*
  (Niedermayr, Juergens, Wagner 2016, arXiv:1611.07163; Descartes/PITest,
  arXiv:1811.03045) and the *oracle gap*, coverage minus mutation score
  (arXiv:2309.02395), both measure "how much green is presence rather than
  behaviour" without hand-classifying conditions. See backlog #043.
- **Weak oracles inflating green** is measured and model-relevant: PatchDiff, +6.2
  absolute points of SWE-bench resolution inflation with 28.6% of divergent
  patches certainly incorrect (arXiv:2503.15223); SWE-ABS, ~one in five top-agent
  patches semantically incorrect under strengthened suites (arXiv:2603.00520);
  UTBoost, 345 erroneous patches passing insufficient tests, 26 of 500 even in
  SWE-bench Verified (arXiv:2506.09289, ACL 2025).
- **Duplicates as a behaviour** are named: MAST, the multi-agent failure taxonomy,
  scores step repetition among its failure modes (arXiv:2503.13657), a figure in
  the same range as the 14 to 21% observed here (threshold-dependent), though
  studied as a planner pathology
  rather than as a consequence of oracle class.

Not verified this pass and therefore not cited: a 2026 SWE-bench-hackability
meta-analysis, a "verification horizon" theory paper, and specific CI-cost and
token-share figures referenced in a research digest. They may be accurate; they
are omitted until confirmed.

**Two cross-checks that appear unpublished (worth running, not citing).** No
located work correlates the *oracle class of the first task in a duplicate
cluster* against the cluster's re-emit rate — the hypothesis that presence-greens
cause intent-duplicates by decoupling "green" from "resolved." And no located work
frames the *calibration-versus-intent* distinction as a ledger-disambiguation
problem: mutation testing re-fires instruments by design (replication is the
point) while re-checking an intent is waste, yet nothing tells a step ledger which
repeat it is looking at. Both are cheap to test on the ledger shape above and
would join the duplicate literature to the weak-oracle literature, which currently
sit apart.
