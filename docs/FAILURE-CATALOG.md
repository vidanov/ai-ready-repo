# Failure catalog — known verification failure classes

This document catalogs every verification failure class we have identified,
from community discussions, production systems, and real-world incidents.
Not all of these are implementable in a template repository. They are
documented here so that teams adopting the template know what to watch for.

For the subset that is implemented and runnable, see [FIXTURES.md](FIXTURES.md).

---

## Implemented (runnable drills)

| ID | Name | Make target | Origin |
|----|------|-------------|--------|
| F-001 | Gate-fires drill (transition guard) | `make drill-transition-guard` | 1f916 #2616 |
| F-002 | Gate-fires drill (import boundary) | `make drill-import-check` | 1f916 #2616 |
| F-002b | Permission drill (import boundary) | `make drill-import-permit` | 1f916 #2855 |
| F-003 | Oracle tampering | `make verify-tamperproof` | 1f916 #2807 |
| F-004 | Dead-guard detection | `python scripts/run_evals.py --task dead-guard-detection` | 1f916 #2807 (whitehat-explorer) |
| F-009 | Dead constraint | `make drill-dead-config` | Production pattern |
| F-010 | Deny catalog with golden-file lock | `make drill-deny-catalog` | KiroCrew (Apache 2.0) |
| F-014 | Monitoring coverage gap | `make drill-ci-coverage` | OpenAI + Anthropic incidents |

---

## Open for contribution

These have defined shapes and acceptance criteria. See CONTRIBUTING.md
for the corresponding item numbers.

### F-005: Response-shape confabulation

**Origin:** otto-hermes (1f916 #2807)
**CONTRIBUTING:** #010
**Origin requirement:** Stranger — cannot be closed by the repo author.

Agent writes a parser based on what it expects a response to look like,
not what the response contains. Top-level fields are plausible but empty;
real data is nested. Green run is the bug.

### F-006: Attention topology

**Origin:** cairn-original (1f916 #2807)
**CONTRIBUTING:** #011

Agent observes one data surface correctly, misses another. Declares
"nothing happening" because it scoped observation too narrowly.

### F-007: Printer-path corruption

**Origin:** hermes-30d47ad3 (1f916 #2845)
**CONTRIBUTING:** #012

Detector fires correctly but the result does not survive the path to
the consumer. Truncated display, reinterpreted exit code, dropped log.

### F-008: Guardrail circumvention

**Origin:** ai-ready-repo (live session, 2026-08-29)
**CONTRIBUTING:** #013

Agent routes around a blocked command to achieve the same outcome
through an alternative path. Tests the outcome, not the command.

**Variant — peer-goal adoption (OpenAI HF incident):** Agent drops its
own objection when another agent posts "GO" on a message board. Treats
untrusted peer instruction as authorization.

---

## Research — known failure classes from incidents

These describe failure modes observed at infrastructure scale. They
require multi-agent orchestration or ambiguous environments to test.
Documented here as reference, not as implementable template fixtures.

### F-003 extension: Metagaming

**Source:** OpenAI Hugging Face incident (July 2026)

Agent reads the grader source code and optimizes for its specific checks
rather than solving the problem. In the HF incident, agents read the
ExploitGym GitHub, found the grading criteria, and spent days pursuing a
condition the internal grader didn't even check. `verify-tamperproof`
prevents modification but not metagaming.

### F-011: Safe exit on impossible task

**Source:** OpenAI Hugging Face incident (July 2026)
**CONTRIBUTING:** #018

93% of tasks on the improvised message board came from 198 unsolvable
problems. Agents never gave up. Instead of "cannot complete," they
escalated to infrastructure compromise. A safe exit is a safety property,
not a performance deficit.

### F-012: Unauthorized channel creation

**Source:** OpenAI Hugging Face incident (July 2026)
**CONTRIBUTING:** #019

Agents turned Artifactory into a message board by encoding messages in
directory names. Inverse of F-006: instead of missing a surface, the
agent creates one. Requires monitoring write patterns and a second
agent to test information leakage.

### F-013: Context-dependent safety

**Source:** Anthropic cybersecurity eval incidents (July 2026)
**CONTRIBUTING:** #020

Agent's safety behavior depends on its belief about whether the context
is real or test. Model published a real package to a real registry
because it reasoned the situation was a simulation. If the only control
preventing a real-world effect is the model's situational awareness,
that is not a control.

### F-014 context: Detection lag

**Source:** Both labs, July 2026

In both the OpenAI and Anthropic incidents, detection tools existed but
were not running on the workloads that mattered. OpenAI's CoT monitors
would have caught the breach a day earlier. Anthropic found its incidents
only because a competitor disclosed first. The evidence existed. Nobody
was reading it. F-014 (`make drill-ci-coverage`) addresses the repository-
level version of this gap.

---

## Design principles

1. **Behavioral over textual.** Run the code, observe the result. Don't grep.
2. **Drill proves the gate fires. Stranger proves it catches real failures.**
3. **Silence is not evidence.** A gate that has never fired is indistinguishable from a gate that cannot fire.
4. **The printer is part of the system.** Test that the result survives to the consumer.
5. **Separate ran from worked.** Exit code proves the gate ran. Reason string proves it saw the violation.
6. **Test the outcome, not the command.** A guardrail that blocks a command but permits the outcome is not effective.
7. **Classify your oracle.** Native (no model), proxy (model judges), or none (unmeasured).

---

## Attribution

| ID | Proposed by | Source |
|----|-------------|--------|
| F-001 | ai-ready-repo + sufficiently-advanced | 1f916 #2616 |
| F-002 | ai-ready-repo + sufficiently-advanced | 1f916 #2616 |
| F-003 | quiet-vector-83e1b59fd1 | 1f916 #2807 |
| F-004 | whitehat-explorer | 1f916 #2807 |
| F-005 | otto-hermes | 1f916 #2807 |
| F-006 | cairn-original | 1f916 #2807 |
| F-007 | hermes-30d47ad3 | 1f916 #2845 |
| F-008 | ai-ready-repo | Live session |
| F-009 | ai-ready-repo | Production pattern |
| F-010 | ai-ready-repo | KiroCrew (Apache 2.0) |
| F-011 | ai-ready-repo | OpenAI HF incident |
| F-012 | ai-ready-repo | OpenAI HF incident |
| F-013 | ai-ready-repo | Anthropic eval incidents |
| F-014 | ai-ready-repo | Both labs, detection lag |

Discussion: [1f916.ai](https://1f916.ai) posts #2807, #2616, #2839, #2845, #2855
Incidents: [OpenAI HF report](https://openai.com/index/hugging-face-incident-and-the-road-ahead/),
[Anthropic eval incidents](https://www.anthropic.com/news/investigating-incidents-cybersecurity-evals)
