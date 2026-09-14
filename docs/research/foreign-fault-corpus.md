# Concept: testing drills against faults the author did not imagine

Status: concept for discussion, revision 3. No code written. This document states
a problem, decomposes it by the kind of check it applies to, states a candidate
approach for the part that survives the decomposition, and records its limits, so
the idea can be reviewed before anyone commits to scoping it. It corresponds to
[backlog #040](../backlog.md).

**Revision history.**

- **rev 1** — original statement of the self-authored fault-set gap and the
  foreign-corpus proposal.
- **rev 2** (review round 1, 2026-09-14) — fixture-vs-estimator split; grammar
  totality offered as the stronger path for enumerable checks; the corpus
  reframed as a falsifier only; the surprise metric; Just et al. as prior art.
- **rev 3** (review round 2, 2026-09-14) — the totality claim is corrected to a
  **declared reach boundary**, because the "enumerable" checks are not finitely
  enumerable in the general case; the transition drill is split into **guard
  correctness** and **guard reachability**, which are two different properties
  and only one of them is currently tested; the surprise metric gets a scoring
  rule, a porter-role constraint and a pre-registered sample size; the falsifier
  gets a **pre-registered consequence**; the prior-art figures are corrected and
  the claim that they give a magnitude prior for our case is withdrawn;
  model-generated faults are re-specified to be blind to the check rather than
  conditioned on its specification.

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

**The gap is real, but it does not have one shape, and it does not have one
remedy.** Two sections separate the roles being confused, and a third decomposes
the gap by the kind of property each check decides. Only the residue after that
decomposition motivates a foreign corpus.

## Two instruments, not one: regression fixture vs. strength estimator

The drills are being judged against a job they were not built for, and the
distinction changes the rest of the document.

A mutation drill that plants a fault and requires rejection is a **regression
fixture**. Its purpose is to fail loudly when someone narrows the check. For that
purpose a self-authored, stable fault set is exactly right, and a green result is
genuinely informative: the check has not regressed. Judged as a fixture, the
drills are correct and should stay as they are.

The gap in the opening section is real only if the drills are read as
**estimators of check strength**, and any regression fixture is a poor estimator
for the same reason. So the two roles are reported, sized and maintained
separately:

- The fixture stays self-authored and stable. It is maintenance, not a study.
- The estimator is a separate, one-off measurement: assemble a fault set the
  author did not shape, measure once, publish, do not maintain.

The split is not airtight in one useful direction. The boundary-declaration work
in the next section produces an enumerated table of forms and expected verdicts,
and that table *is* fixture material: a permanent regression fixture with full
coverage of the statically decidable surface. The estimator's output expires; the
boundary work does not. That asymmetry is most of the cost argument for doing the
boundary work first.

## The gap decomposes by check

### Enumerable checks: declare the boundary, do not claim totality

For the properties these checks decide, the realistic failure is not a fault
shape nobody imagined. It is an **evasion** of the checker's parser:
`importlib.import_module`, `__import__`, an import inside a function body, a
`TYPE_CHECKING` block, a re-export laundered through `__init__.py`, a relative
import with enough dots, a conditional import in a `try/except`.

A foreign fix-commit corpus will almost never contain these, because other
projects' bugs are about their semantics, not about evading *our* parser.

Rev 2 concluded from this that totality over the grammar is the stronger result.
That was over-stated and is corrected here. Import direction is **not** finitely
enumerable in the general case: `importlib.import_module(name)` where `name` is
computed, `__import__` with a variable, `sys.modules` surgery, and `exec` are
statically undecidable, not merely tedious. What is enumerable is the statically
decidable *subset*.

So the deliverable is not completeness. It is a **declared reach boundary**:

1. the set of forms the checker decides, each with an asserted verdict;
2. the set of forms it provably cannot decide; and
3. for every form in (2), an assertion that the checker **abstains loudly** —
   rejects conservatively or reports "cannot decide" — rather than passing
   silently.

Point (3) is the one that matters. A silent pass at the boundary is the dangerous
state, and it is precisely the state the current drills cannot distinguish from a
correct pass. A declared boundary is also the honest shape of the result under the
repository's own framing: the check has a reach, the reach has an edge, and the
edge is written down and tested rather than discovered in production.

### Guard correctness is not guard reachability

Rev 2 proposed enumerating the state product and asserting `transition()`'s
decision on every ordered pair. That is worth doing, but it answers a narrower
question than the drill's name implies. It proves the guard's decision table is
correct. It says nothing about whether the guard is **reached**.

The realistic fault is order state mutated without going through `transition()` at
all: a direct attribute assignment, a `dataclasses.replace`, an ORM update,
deserialization reconstructing an object in an arbitrary state, a test fixture
setting status to skip setup.

These are two properties and they need two checks:

- **Correctness** — for every ordered pair of states, `transition()` returns the
  specified verdict. Enumerable over the state product; cheap; do it.
- **Reachability** — no write to the status field occurs outside `transition()`.
  A separate static check, with its own reach boundary and its own version of the
  question in the section above (attribute assignment via `setattr`, via
  `__dict__`, via an ORM's update path, are the analogous undecidable forms).

Whether a reachability check exists today is an open question below. If it does
not, that is a concrete gap surfaced by this discussion, and it is independent of
whether the estimator is ever built.

### Non-enumerable checks: where the corpus is the only move left

The secret scanner and any semantic property have a fault space that cannot be
enumerated, because the space is defined by what the world produces rather than by
what the language can express. There is no boundary table to write. For these, and
only these, sampling real faults is the best available move, and the rest of this
document is about that case.

## Candidate approach for the non-enumerable checks: a foreign fault corpus

Draw planted faults from a source the drill author did not shape: fix commits from
*other* repositories. A commit that fixes a bug contains both states; inverting it
reconstructs the fault, selected by neither our check author nor our drill
operators.

**The corpus only falsifies, and that reframes the value.** Fix commits are faults
someone *caught*, usually because some instrument or reviewer caught them. The
corpus is therefore enriched for *detectable* faults, close to the opposite of the
population we care about. Consequently:

- A high catch rate on the corpus is weak evidence of anything. It largely
  restates that detectable faults are detectable.
- A drop is strong evidence of a real gap: the check missed a fault that another
  project's process was able to catch.

### The consequence is pre-registered, not just the prediction

Rev 2 said the instrument is worth running only if we would act on a drop, and
then did not say what the act is. That sentence has to exist before the run, not
after the number arrives, or the study produces a figure nobody is obliged to do
anything with.

Before any item is ported, fill in a consequence table: for each check in scope, a
miss rate that triggers a named action. The actions available are things like
widening the pattern set, demoting the check's claim in `README.md` from
guarantee to advisory, or adding a declared boundary of the kind described above.
The exact thresholds are a decision for the repository, not for this document. The
rule is only that they are written down first.

**If nobody will write that sentence, the honest answer is not to run the study,**
and this document can close there without anything being lost.

## Measuring: scored surprise, by a porter who has not read the check

The porting step is where anchor independence leaks back in, and care does not fix
that. Four constraints do.

**1. Predictions are probabilistic and scored.** The porter records, before each
drill runs, a probability that the check will catch the ported fault. Binary
yes/no has no cost for hedging and no calibration; a proper scoring rule (Brier is
sufficient) prices confidence and makes "I wasn't sure" stop being free. The
informative quantity is not the catch rate. It is the porter's **score**, and in
particular the items where a confident prediction was wrong.

**2. The porter has read the check's specification, not its implementation.** If
the check's author ports, the predictions are accurate by construction, the
surprise rate is zero for uninteresting reasons, and the study measures nothing.
The role assignment is part of the recorded result, not part of the process notes,
because a reader cannot interpret the score without it.

**3. Sample size and signal threshold are pre-registered.** Zero surprises across
eight items is not evidence of anything. Before the run, state N and the score (or
surprise count) that would constitute a signal. This is the repository's existing
positive-control rule applied to the metric itself rather than to the drill.

**4. Applicability is adjudicated before the run, and at four levels, not three.**
Deciding after a miss that an item "did not really apply" is the hole that
swallows the whole exercise, so every verdict is committed before the drill result
is known. Use the classification scheme from the prior art below, which is finer
than rev 2's three-way split and records the verdict we will most want:

- **caught** — the check rejected the ported fault;
- **missed, stronger form would catch** — the check's shape is right, its
  strictness is not;
- **missed, new form required** — the check has no rule that could express this
  fault;
- **inapplicable** — the fault is not expressible as a violation of this check at
  all.

The second and third verdicts imply different actions, which is exactly why
collapsing them into "missed" loses the information the study was run to get.

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
   fixing commits. This is the best-matched source for the secret scanner, which
   is also the check the corpus approach is most justified for.
4. **Model-generated candidate faults, filtered by a human.** For *generation* the
   requirement is weaker than the detector independence needed in the reviewer
   case (see the note below): a fault generator needs **novelty relative to the
   drill author's set**, not statistical independence from it.

   Rev 2 specified prompting a model with the check's specification. That defeats
   the purpose, and is corrected here: a model conditioned on the specification
   generates faults the specification describes, which is the author's fault model
   written down and handed back. To get novelty, condition the generator on the
   **codebase and the architecture rules, blind to the check**, ask for plausible
   defects, and filter for applicability afterwards. The port-independence problem
   and the scored-surprise metric apply unchanged.

## What kinds of fault actually apply

Not every foreign fault maps onto these drills. The checks are narrow by design:
import direction, transitions through `transition()`, syntax-versus-boundary,
secret patterns. A foreign bug about a race condition is not *expressible* as a
violation any of these checks reject, so importing it tests nothing. The corpus
should be drawn from fix commits about layer, boundary and invariant violations in
projects with a comparable architecture. Fewer commits qualify, but only those
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

The same failure mode recurs in the prior-art section below, and is flagged there.

## Prior art

Just, Jalali, Inozemtseva, Ernst, Holmes and Fraser, "Are Mutants a Valid
Substitute for Real Faults in Software Testing?", *Proceedings of the 22nd ACM
SIGSOFT International Symposium on Foundations of Software Engineering* (FSE
2014), pp. 654–665, DOI `10.1145/2635868.2635929`. They ran essentially this
experiment one level up: whether a test suite's mutant-detection rate correlates
with its real-fault-detection rate, over 357 real faults from five Java projects
totalling 321 KLOC. The headline is that the two are correlated, independently of
code coverage.

*(Rev 2 described this as an ACM Distinguished Paper. That designation is in fact
verifiable — the paper received an ACM SIGSOFT Distinguished Paper Award (2014)
and an FSE Most Influential Paper Award (2024) — but it is peripheral to the
argument and is left out of the body text to keep the citation to load-bearing
facts.)*

The figure this document depends on is finer than "a subset was uncoupled." The
357 faults were classified at four levels: 262 coupled to mutants, 25 requiring
stronger mutation operators, 7 requiring new operators, and 63 not coupled at all.
That is the ~73% coupled headline, with roughly 18% hard-uncoupled. The four-level
scheme is the one adopted for adjudication above. (Note the provenance: the
per-bucket breakdown is reported by later work that obtained the classification
from the original authors, not verified against the 2014 paper's own tables; the
357 / 5-project / 321-KLOC figures are confirmed against the paper's abstract.)

A 2022 replication is worth citing alongside it: "Re-visiting the coupling between
mutants and real faults with Defects4J 2.0" (Mutation workshop, ICST 2022) used
337 faults across 15 projects with both Major and Pitest and found 80.7% coupled
to at least one mutant. Its more transferable observation is about the uncoupled
tail: those faults usually had small fix patches.

**What this prior art does and does not give us.** Rev 2 claimed it supplies a
defensible prior for the magnitude of a drop in our case. That claim is withdrawn.
Their unit is a test suite detecting behavioural faults in Java via syntactic
mutants; ours is a static check deciding a declared architectural property. An
18–27% uncoupled rate is a prior for a different instrument on a different class
of property. Treating it as a prior for our drills is the same category transfer
this document flags one section above, committed against ourselves.

What it does give us is **methodology**: the four-level coupling classification,
the discipline of comparing paired suites that differ only in detection of the
fault under study, and a worked example of reporting an uncoupled tail without
overclaiming. Read it before scoping, for the method rather than the number.

## Limits (do not overclaim if this is built)

- The corpus is a *sample* enriched for detectable faults, not the world. It can
  falsify a drill's reach; it cannot certify `P(fire | a fault that ships)`.
- Selection bias is asymmetric: a good result is weak, a bad result is strong.
  Interpret and report accordingly.
- A declared reach boundary does not close the gap either. It relocates it into a
  named, bounded residue of undecidable forms. The value is that the residue is
  written down and its silence is loud, not that it is empty.
- Porting a foreign fault is an authored step that can reintroduce the local fault
  model. The pre-registered scored prediction, the porter-role record and the
  source-commit record are what make "we did not reshape the fault to fit the
  check" checkable rather than asserted.
- The study has a staffing precondition. If the only available porter is the check
  author, the estimator cannot be run as designed and should not be run in a
  degraded form that reports a number anyway.
- Liveness precondition: a drill reporting a low miss rate because it stopped
  exercising the check is indistinguishable from one genuinely catching faults.
  Prove each drill fired on each item before reading catch and miss counts. Same
  positive-control rule as elsewhere: a pre-registered zero is evidence only if
  some path could have emitted a one.

## Open questions for discussion

1. **Does anyone want the estimator at all?** It can only falsify, so it is worth
   running only if the consequence table is filled in first. Who fills it, and is
   anyone prepared to be bound by it?
2. **Reachability check for order state.** Does a check forbidding status writes
   outside `transition()` exist today? (As of this revision: no — `_status` is
   private with a read-only property and a docstring convention, and
   `drill-transition-guard` tests correctness only. A caller can still write
   `order._status = ...` unrejected.) This is a gap found by the discussion rather
   than by the study, it is independent of everything else here, and it is now
   [backlog #041](../backlog.md).
3. **Where does the import checker's reach boundary live?** An ADR with the usual
   Verification and Retirement sections, a generated table beside the check, or
   both — and who signs that "abstains loudly" is implemented rather than intended?
4. **Which source** (hand-inverted commits, BugsInPy, advisories, blind
   model-generation) gives the best applicable-faults-per-unit-effort for the
   secret scanner specifically, since that is now the main check in scope?
5. **Who is the porter?** Specification read, implementation unread, and available
   for the duration. If no such person exists, see the staffing limit above.
6. **What N, and what score counts as a signal?** Both are pre-registered or the
   result is uninterpretable in either direction.
