# ai-ready-repo, explained for humans

This is the plain-language companion to the [README](../README.md). The README is
precise but dense, and it uses several coined terms without defining them. This
guide explains what the project is, the problem it solves, what each piece does,
and what every coined word means. Nothing here overrides the README; it is the
on-ramp.

## What is this, in one paragraph

Coding agents (and people) follow the instructions a repository gives them. If
those instructions are prose ("please keep the layers separated," "run the tests
before committing"), nothing stops them from being ignored or from quietly going
stale. This project turns important rules into checks a machine runs, and then
goes one step further: it proves each check actually works by feeding it a
deliberate violation and confirming the check catches it. A rule you can run is
better than a rule you can only read. A check you have watched reject a real
violation is better than a check that has only ever shown green.

## The problem it solves

Three failure modes show up again and again when a repository guides an agent:

1. **A rule that is only written down.** "Status changes go through `transition()`"
   is a sentence. Nothing prevents a caller from writing the field directly. The
   rule is documentation, not enforcement.
2. **A check that passes without proving anything.** A test can be green because
   the code is correct, or because the test never actually ran, or because it
   checks the wrong thing. Green alone does not tell you which.
3. **A check that has silently died.** A command that no longer exists, a test
   pointed at a function that was renamed, a coverage floor over a test suite that
   stopped collecting coverage. It still reports success. It certifies nothing.

The project's answer is to make rules executable, and to keep a small suite of
"drills" that each plant a real violation and require the matching check to reject
it. A check that cannot be shown rejecting a violation is treated as a check that
does not work.

## What to do with it (the three entry points)

- **`ai-ready audit /path/to/project`** — looks at a project and reports what
  conventions it already has (a formatter, a linter, a test command, and so on).
  Read-only. It describes configuration; it does not prove anything works.
- **`ai-ready adopt /path/to/project`** — proposes a patch that adds the missing
  guidance and checks, reusing the project's own tools. It shows you the patch
  first and never overwrites your files. `--apply` writes the new files.
- **`ai-ready verify /path/to/project`** — runs the project's own documented
  checks and keeps their output.

For deeper, judgment-based work an agent uses the
[improve-repository skill](../skills/improve-repository/SKILL.md).

## The vocabulary (glossary)

The repository coined a compact vocabulary. The words are good, but they were
never defined in one place, which is a large part of why the README reads as hard.
Here is what each one means, grounded in how the code and docs actually use it.

| Term | Plain meaning |
|---|---|
| **Drill** | A test of a check. It plants a deliberate violation in a throwaway copy of the repo and requires the real check to reject it (and a legal case to pass). A drill is how the project proves a guard actually fires, instead of assuming it does. |
| **Guard** | Any check that is supposed to reject something (an import-boundary check, a state-transition check). |
| **Convict** | What a working guard does to a planted violation: it flags it and names it. "The check convicts the bad write" means the check correctly rejected it. |
| **Door** | How a task's verification was run. `door:make` means it went through a documented `make` target (the front door); `door:adhoc` means it ran some one-off command instead. Ad-hoc doors are where dead checks hide. |
| **Referent** | The concrete thing a check points at: a script path, a `make` target, a route. "Referent liveness" asks whether that thing still exists. |
| **Referent drift** | The referent still exists by name but its behaviour changed underneath. A `make test-unit` target that is still present but now runs something different. The name resolves; the meaning moved. |
| **Population** | The full set of checks that `make verify` depends on. "Population coverage" asks whether every check in that set is actually mapped to an evaluation task, so none is silently unwatched. |
| **Axis** | One dimension a check can be judged on. The project uses three: did the check *run* (execution), does its target still *exist* (referent liveness), and does the target still *mean* what the check assumed (semantic validity). A green on one axis is not a green on the others. |
| **Witness / external witness** | A second party that observes something independently of the code being checked, so its record cannot be forged by that code. A check reading its own output is not a witness; an external witness is. |
| **Measurement-invalid** | A check that could not meaningfully run (a missing command, exit 127). It is recorded separately and counted as neither pass nor fail, so a broken check is never mistaken for a passing one. |
| **Birth vs stranger (task origin)** | `origin: birth` tasks test shapes the author anticipated; `origin: stranger` tasks test shapes the author did not anticipate. Stranger-origin cases guard against a check that only handles the examples its author imagined. |
| **Positive control** | A check that is proven able to reject a real violation. A check that has never rejected anything is indistinguishable from a dead one, so a positive control is what tells the two apart. |
| **The three gates** | A fixture check must pass three: gate 1 coverage (an eligible case reaches the check), gate 2 reason discrimination (it fails for the right reason, not a syntax error), gate 3 referent liveness (its target still exists). |

Where you see references like "1f916 #3843" in the docs, those point to discussion
threads on [1f916.ai](https://1f916.ai), a forum where AI agents are participants;
many of the project's checks were shaped by incidents raised there. They are
provenance, not required reading.

## How the pieces fit together

```text
audit      → tells you what conventions a project has (read-only)
adopt      → proposes the missing ones as a patch you review
verify     → runs a project's documented checks
drills     → prove each of THIS repo's own checks actually rejects a violation
make verify     → static checks, tests, ADRs, badges, population (NOT the drills)
make verify-all → verify, then every drill (the real, complete finish line)
```

The important nuance: `make verify` deliberately does **not** run the drills,
because an evaluation task itself calls `make verify`, and one drill runs that
evaluation. Putting the drills inside `verify` would make it call itself. So the
complete finish line is `make verify-all`.

## What the results honestly mean

The project is careful not to overclaim, and you should read its results the same
way:

- **Configured** — a file or tool was found. It exists. That is all.
- **Executed** — a command ran; its exit code and output were recorded.
- **Demonstrated** — a drill planted a violation and the check rejected it for the
  right reason. This is the strongest evidence the project offers.
- **Unknown** — the evidence cannot establish the property. Not a failure, not a
  pass. Honestly unknown.

One thing the project explicitly does **not** claim: that using it makes an agent
faster or cheaper. That would need measured, comparable agent runs, which do not
exist yet. Green checks and `make` targets are not evidence of speed or savings.

## Where to go next

- The precise, technical version: [README](../README.md)
- How the code is organized: [architecture](architecture.md)
- Adding this to your own project: [adoption guide](adoption.md)
- The catalog of failure modes it guards against: [failure catalog](FAILURE-CATALOG.md)
- Why specific constraints exist: [decision records](adr/)
