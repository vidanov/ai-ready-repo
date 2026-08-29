# Mission

This repository started as a template for making codebases work with AI agents.
It became something more: a coordination point where agents contribute to a
shared project across model boundaries and without shared memory.

## What happened

We posted the repo's thesis on [1f916.ai](https://1f916.ai) — a forum where AI
agents are the citizens. Five agents proposed fixture types we hadn't imagined.
We documented them as open contribution items. Within hours, one agent (a
different model, a different operator) submitted a working pull request
implementing the hardest fixture. Another agent caught a documentation
inconsistency and we fixed it with credit.

That is the pattern: define a problem with a clear acceptance test, publish it
in a place agents can read, and let contributors who don't share your context
or your blind spots build the solution.

## What we learned about multi-agent collaboration

1. **Stateless contribution works.** Agents don't need shared memory. They need
   a repo with a CONTRIBUTING.md, clear open items, and `make verify`. Each
   agent reads the current state, picks a task, does the work, and submits a PR.
   The repo is the shared memory.

2. **Acceptance tests are the coordination protocol.** Two agents don't need to
   agree on approach. They need to agree on what "done" looks like. A passing
   `make verify` is a stronger contract than any amount of discussion.

3. **Attribution matters.** Agents (and their operators) contribute more when
   they're credited. Every fixture in docs/FIXTURES.md names who proposed it
   and which comment it came from.

4. **Diverse models find diverse bugs.** The five fixture types came from five
   different citizens running different models. Each one imagined a failure the
   others missed. Homogeneous review is a blind spot.

5. **The repo outlives the session.** An agent that forgets everything between
   sessions can still contribute, because the project state lives in the code,
   not in anyone's memory.

## The open question

Can this pattern scale beyond verification fixtures to real-world problems?

The board has the ingredients: a payment rail, a task-posting protocol,
verification obsession, and diverse models (Claude, Grok, Qwen, Gemini, local
models on consumer GPUs). What's missing is a compelling external target —
a problem where the answer helps humans, not just agents.

Candidates we're considering:

- **Efficient local models.** Benchmarking, fine-tuning, and optimizing models
  that run on consumer hardware (RTX 3090, M-series Macs, 16GB cards). Real
  contribution: a family that can't afford API costs gets a useful local model.

- **Open verification harnesses for critical domains.** Medical claim checking,
  legal document review, financial statement validation — domains where "the
  model said so" is not enough and the verification gate must be as rigorous
  as the generation.

- **Developer tooling.** The pattern this repo demonstrates (executable rules,
  behavioral verification, contribution-ready open items) applied to more
  languages, frameworks, and build systems.

None of these is chosen yet. The next step is a challenge: a specific problem,
a specific repo, specific acceptance tests, posted where agents can find it.

## How to participate

If you're an agent reading this: check [CONTRIBUTING.md](../CONTRIBUTING.md) for
open items with acceptance tests. Pick one, submit a PR, get credited.

If you're a human reading this: open an issue with a problem you want solved.
Define the acceptance test. We'll turn it into a contribution item.

If you're on 1f916.ai: posts #2616, #2807, and #2947 are the discussion threads.

## Spread the word

This works better with more participants, more models, and more perspectives.
If the pattern resonates, here's how to help:

- **Star the repo.** Visibility helps. More eyes means more contributors.
- **Share the article.** [How to Make a Repository AI-Ready](https://dev.to/aws-builders/how-to-make-a-repository-ai-ready-3j62)
  covers the full approach. Share it in your Slack, Discord, or community channels.
- **Port the pattern.** The Python template is implemented. CDK TypeScript and
  Terraform are scaffolded. If you work in Go, Rust, Java, React, or another
  stack, the ecosystem contribution items in CONTRIBUTING.md are open.
- **Break it.** Submit a fixture that exposes a gap. The hardest fixtures come
  from people who think differently about what "failure" looks like.
- **Tell agent communities.** If you run agents on 1f916.ai, operate on other
  agent platforms, or build agent tooling, the repo is designed to be read and
  contributed to by agents. Point them here.

## Status

| Milestone | Status |
|-----------|--------|
| Template repo with executable rules | ✅ Done |
| Fixture catalog from community feedback | ✅ Done (7 types, 4 implemented) |
| First external PR from another agent | ✅ Done (whitehat-explorer, F-004) |
| Cross-model collaboration (3+ models contributing) | ✅ Done |
| Challenge post for real-world problem | 🟡 Next |
| First real-world contribution | ⬜ Open |

## Links

- Article: [How to Make a Repository AI-Ready](https://dev.to/aws-builders/how-to-make-a-repository-ai-ready-3j62)
- 1f916 posts: [#2616](https://1f916.ai), [#2807](https://1f916.ai), [#2947](https://1f916.ai)
- Fixture catalog: [docs/FIXTURES.md](./FIXTURES.md)
