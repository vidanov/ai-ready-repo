# Concept: testing drills against faults the author did not imagine

Status: concept for discussion, revision 2. No code written. This document states
a problem, a candidate approach, how it could be built, and its limits, so the
idea can be reviewed before anyone commits to scoping it. It corresponds to
[backlog #040](../backlog.md). Revision 2 incorporates a colleague review
(2026-09-14): the fixture-vs-estimator split, grammar totality as the stronger
path for enumerable checks, the corpus as a falsifier only, the surprise metric,
and the Just et al. prior art.

Origin: a public discussion on the 1f916 agent board (post #5287), where the
claim "a second reviewer only helps if its failures are uncorrelated with the
first" was challenged down to this specific gap by several reviewers.

---

## The problem

The repository's mutation drills (`make drill-import-check`,
`drill-transition-guard`, `drill-reason-swap`, and the others) each plant a fault
and require the matching check to reject it. This proves the check *can* fire.

Every planted fault is written by the same hand that wrote the check being
tested. So the drill measures one quantity:

```
P(fire | a fault the author imagined)
```

The quantity that actually matters for trust is a different one:

```
P(fire | a fault that ships)
```

These agree only if the author's fault model matches the world's. The drill
cannot test whether it does, because it cannot plant a fault outside the model it
was built from. A drill that has never failed is exactly what this blind spot
looks like from the inside. Its green is not evidence against the blind spot; it
is silence about it.

This is the same self-attribution trap the repository already documents one level
down. In [backlog #039](../backlog.md) the *expected-set* of an audit was
self-authored, so an empty result could not distinguish "not present" from "my
scan never reached it." Here it is the *fault-set* that is self-authored, so a
passing drill cannot distinguish "the check is strong" from "the author only
imagined faults the check already handles."

## Two instruments, not one: regression fixture vs. strength estimator

A review of an earlier draft (colleague, 2026-09-14) pointed out that the drills
are being judged against a job they were not built for, and the distinction
changes the rest of the document.

A mutation drill that plants a fault and requires rejection is a **regression
fixture**. Its purpose is to fail loudly when someone narrows the check. For that
purpose a self-authored, stable fault set is exactly right, and a green result is
genuinely informative: the check has not regressed. Judged as a fixture, the
drills are correct and should stay as they are.

The gap in the opening sections is real only if the drills are read as
**estimators of check strength**, and any regression fixture is a poor estimator
for the same reason. So the two roles must be reported, sized, and maintained
separately:

- The fixture stays self-authored and stable. It is maintenance, not a study.
- The estimator is a separate, one-off measurement: assemble a fault set the
  author did not shape, measure once, publish, and do not maintain.

This already answers open question 5 below. The rest of the document is about the
estimator only.

## For these checks, evasion is the likelier gap than imagination

The same review noted that for the properties these checks decide, the realistic
failure is not a fault shape nobody imagined. Import direction is a decidable
property over a finite syntactic surface. The realistic miss is an *evasion* of
the parser: `importlib.import_module`, `__import__`, an import inside a function
body, a `TYPE_CHECKING` block, a re-export laundered through `__init__.py`, a
relative import with enough dots, a conditional import in a `try/except`.

A foreign fix-commit corpus will almost never contain these, because other
projects' bugs are about their semantics, not about evading *our* parser. Where a
property is formally specifiable, **totality over its grammar is a stronger result
than a sampled catch rate**:

- Import direction: enumerate the ways the language expresses an import and assert
  the checker's decision on each form, including the dynamic and laundered ones.
- `transition()`: enumerate the state product and assert the guard's decision on
  every ordered pair.

Exhaustive generation over the grammar is cheaper than corpus sourcing and attacks
the actual gap for these checks. The foreign corpus is worth considering only for
checks whose fault space is *not* finitely enumerable (semantic properties, the
secret scanner's open-ended pattern space), where sampling real faults is the best
available move.

## Candidate approach for the non-enumerable checks: a foreign fault corpus

Where the fault space cannot be enumerated, draw planted faults from a source the
drill author did not shape: fix commits from *other* repositories. A commit that
fixes a bug contains both states; inverting it reconstructs the fault, selected by
neither our check author nor our drill operators.

**The corpus only falsifies, and that reframes the value.** Fix commits are faults
someone *caught*, usually because some instrument or reviewer caught them. The
corpus is therefore enriched for *detectable* faults, close to the opposite of the
population we care about. Consequently:

- A high catch rate on the corpus is weak evidence of anything. It largely
  restates that detectable faults are detectable.
- A drop is strong evidence of a real gap: the check missed a fault that another
  project's process was able to catch.

So the instrument is a falsifier, not a reassurance. It is worth running only if
we would act on a drop. If a good result would not change anything and a bad
result would, that asymmetry is the whole case for running it.

## Measure surprise, not catch rate

The porting step is where anchor independence leaks back in, and care does not fix
that. What does: the porter records a **per-item prediction before the drill
runs** (will this check catch this ported fault, yes or no). Items where
prediction and outcome agree carry almost no information. The informative quantity
is the **disagreement rate** (a check that fired where the porter expected a miss,
or missed where the porter expected a catch). Counting surprises rather than
stating a rate also makes the sample size tractable.

Applicability must be adjudicated *before* the run, as a three-way outcome:
**caught / missed / inapplicable**. Deciding after a miss that an item "did not
really apply" is the hole that swallows the whole exercise, so the inapplicable
verdict has to be committed before the drill result is known.

## How the corpus could be sourced

From least to most tooling:

1. **Invert fix commits from selected repositories.** `git log --grep` over
   fix/bug keywords or linked issue-and-PR pairs, then reconstruct the fault by
   reverse-applying the diff. Traceable to a real commit; highest manual effort.
2. **Reuse a curated bug dataset.** BugsInPy (real Python bugs, each with broken
   and fixed revisions plus a triggering test) is closest to this stack;
   Defects4J is the Java equivalent; SWE-bench packages GitHub issue-and-fix
   pairs. Less sourcing work, but the faults sit in other projects' shapes.
3. **Security advisory fix commits.** The GitHub Advisory Database links CVEs to
   fixing commits, useful for the secret scanner rather than the import or
   state-machine drills.
4. **Model-generated candidate faults, filtered by a human.** For *generation*,
   the requirement is weaker than the independence needed in the reviewer case
   (see the note below): a fault generator needs *novelty relative to the drill
   author's set*, not statistical independence from it. A model prompted with the
   check's specification but not its implementation, run at volume with a human
   filter, may beat corpus sourcing on cost per applicable item. It shares the
   corpus's port-independence problem and the surprise metric applies unchanged.

## What kinds of fault actually apply

Not every foreign fault maps onto these drills. The checks are narrow by design:
import direction, transitions through `transition()`, syntax-versus-boundary,
secret patterns. A foreign bug about a race condition is not *expressible* as a
violation any of these checks reject, so importing it tests nothing. The corpus
should be drawn from fix commits about layer, boundary, and invariant violations
in projects with a comparable architecture. Fewer commits qualify, but only those
honestly exercise these instruments.

## Note on the reviewer-independence argument

An earlier draft imported the correlated-failure argument from the reviewer case
into fault *generation*. That was an over-application. In the reviewer case the
requirement is detector *independence* (two checkers whose misses do not
correlate). In fault generation the requirement is only *novelty*: candidate
faults the drill author did not already enumerate. A generator does not need to be
independent of the author to be useful; it needs to reach shapes the author's set
did not. This is why the model-generated option above is admissible despite
sharing training lineage with the reviewers it might later test.

## Prior art

Just, Jalali, Inozemtseva, Ernst, Holmes, and Fraser, "Are Mutants a Valid
Substitute for Real Faults in Software Testing?" (FSE 2014, pp. 654-665; ACM
Distinguished Paper) ran essentially this experiment one level up: they tested
whether a suite's mutant-detection rate correlates with its real-fault-detection
rate, using Defects4J real faults. Their headline is that the two *are*
correlated (which supports mutation testing generally), but with the caveat this
document depends on: a subset of real faults were **not coupled** to mutants
generated by common operators. Their coupling methodology and their measured
magnitude of the uncoupled subset are a defensible prior for what a drop here
would look like, and reading it first would likely save a round on open
question 3.

## Limits (do not overclaim if this is built)

- The corpus is a *sample* enriched for detectable faults, not the world. It can
  falsify a drill's reach; it cannot certify `P(fire | a fault that ships)`.
- Selection bias is asymmetric (see above): a good result is weak, a bad result
  is strong. Interpret accordingly.
- Porting a foreign fault is an authored step that can reintroduce the local fault
  model. The pre-registered per-item prediction and the source-commit record are
  what make "we did not reshape the fault to fit the check" checkable rather than
  asserted.
- Liveness precondition: a drill reporting a low miss rate because it stopped
  exercising the check is indistinguishable from one genuinely catching faults.
  Prove each drill fired on each item before reading catch and miss counts. Same
  positive-control rule as elsewhere: a pre-registered zero is evidence only if
  some path could have emitted a one.

## Open questions for discussion

1. Split confirmed: keep the drills as regression fixtures (unchanged), and treat
   the estimator as a separate one-off study. Does anyone want the estimator at
   all, given it can only falsify?
2. For the enumerable checks (import direction, `transition()`), is grammar
   totality the better spend than any corpus? It looks strictly stronger for those
   two.
3. For the non-enumerable checks (secret scanner, semantic properties), which
   source (hand-inverted commits, BugsInPy, advisories, model-generated) gives the
   best applicable-faults-per-unit-effort?
4. Is the surprise metric (pre-registered prediction, disagreement rate, three-way
   applicability committed before the run) the right instrument, and who acts as
   the porter whose predictions are recorded?
5. Read Just et al. before scoping: does their uncoupled-fault magnitude justify
   running our version at all, or does it already answer the question for us?
