# Adopting AI-ready practices in an existing repository

This guide walks through upgrading an existing Python repository to Level 2–3
of the AI-readiness maturity model. Each step is independent. Stop at any point
and the repository is better than it was.

---

## How to use this guide

Run the audit first. It tells you which steps are already done.

```bash
python scripts/ai_readiness_audit.py
```

Then work through the steps in order. Each step has:
- A **goal** — what you are trying to achieve
- **Commands** — exactly what to run
- A **done condition** — how you know it worked

Estimated time per step: 15–45 minutes.

---

## Step 0: Run the audit

```bash
# From your repository root
curl -O https://raw.githubusercontent.com/vidanov/ai-ready-repo/main/scripts/ai_readiness_audit.py
python ai_readiness_audit.py
```

The audit checks 20 items across the maturity levels and prints a score with
specific gaps. Start with whatever it flags as missing at your current level.

---

## Step 1: Pin your toolchain

**Goal:** Any developer or agent gets the same Python version automatically.

**Check if already done:**
```bash
ls .python-version .nvmrc mise.toml 2>/dev/null
cat pyproject.toml | grep requires-python 2>/dev/null
```

**Do it:**
```bash
# Record the Python version you are currently using
python --version  # e.g. Python 3.12.4

# Write it to .python-version
echo "3.12" > .python-version

# If using uv, also set in pyproject.toml:
# requires-python = ">=3.12"
```

**Done condition:** `cat .python-version` prints a version, and a fresh clone
with `uv venv` or `pyenv install` picks it up automatically.

---

## Step 2: Create a bootstrap command

**Goal:** `make bootstrap` (or equivalent) takes a fresh clone to a working
state with one command.

**Check if already done:**
```bash
make help 2>/dev/null | grep -i bootstrap
```

**Do it:**

Add to your `Makefile` (create one if it does not exist):

```makefile
.PHONY: bootstrap
bootstrap:
	uv venv --python 3.12
	uv pip install -e ".[dev]"
	@test -f .env || cp .env.example .env
	@echo "Bootstrap complete. Run: make verify"
```

If you use a different tool (npm, poetry, gradle), the command changes but
the principle does not: one command, documented, tested in CI.

**Test it:**
```bash
# In a temporary directory
git clone <your-repo> /tmp/test-clone && cd /tmp/test-clone
make bootstrap
make verify
```

**Done condition:** The CI job for a fresh clone completes without manual
intervention.

---

## Step 3: Add a verification command

**Goal:** `make verify` runs the complete local check suite, identical to CI.

**Check if already done:**
```bash
make help 2>/dev/null | grep verify
# Check if CI calls the same target
grep "make verify" .github/workflows/*.yml 2>/dev/null
```

**Do it:**

Add to `Makefile`:

```makefile
.PHONY: verify
verify: format-check lint typecheck test
	@echo "✓ All checks passed"

.PHONY: format-check
format-check:
	uv run ruff format --check src tests

.PHONY: lint
lint:
	uv run ruff check src tests

.PHONY: typecheck
typecheck:
	uv run mypy src

.PHONY: test
test:
	uv run pytest
```

Update your CI workflow to call this target:
```yaml
- name: Verify
  run: make verify
```

**Done condition:** `make verify` passes locally and CI calls the same command.
A change that breaks locally also breaks CI — they are the same check.

---

## Step 4: Add a formatter

**Goal:** Formatting is automatic and never a review comment.

**Check if already done:**
```bash
cat pyproject.toml | grep -A5 "\[tool.ruff\]" 2>/dev/null
cat .pre-commit-config.yaml 2>/dev/null | grep -i format
```

**Do it (ruff):**

Add to `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP"]
```

Add to dev dependencies:
```bash
uv pip install "ruff==0.9.10"
uv pip freeze | grep ruff >> requirements-dev.txt
# or add to pyproject.toml [project.optional-dependencies] dev
```

Run once to format everything:
```bash
uv run ruff format src tests
git commit -m "style: apply ruff formatter to all files"
```

**Done condition:** `make format-check` passes on a clean checkout with no
unstaged changes.

---

## Step 5: Add strict type checking

**Goal:** Type errors are caught before tests run.

**Check if already done:**
```bash
cat pyproject.toml | grep -A5 "\[tool.mypy\]" 2>/dev/null
```

**Do it:**

Add to `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
```

Run mypy and fix errors iteratively:
```bash
uv run mypy src
```

**Tip for large codebases:** Start with `ignore_errors = true` on files you
are not ready to fix, and remove the ignores file by file:
```toml
[[tool.mypy.overrides]]
module = ["myapp.legacy.*"]
ignore_errors = true
```

**Done condition:** `mypy src` exits 0 with no `--ignore-missing-imports` flag.

---

## Step 6: Enforce module boundaries

**Goal:** Architecture rules are executable, not advisory.

**When to do this:** When your codebase has layers (domain/application/
infrastructure, or similar) that should not import each other.

**Check if already done:**
```bash
cat pyproject.toml | grep importlinter 2>/dev/null
cat .importlinter 2>/dev/null
```

**Do it:**

Install:
```bash
uv pip install "import-linter==2.3"
```

Map your current import structure:
```bash
uv run lint-imports --show-timings 2>&1 | head -30
```

Add contracts to `pyproject.toml` based on what you find:
```toml
[tool.importlinter]
root_packages = ["myapp"]

[[tool.importlinter.contracts]]
name = "Domain must not import infrastructure"
type = "forbidden"
source_modules = ["myapp.domain"]
forbidden_modules = ["myapp.infrastructure"]
```

Fix any violations before CI enforces the contract:
```bash
uv run lint-imports
# Fix the imports it flags, then re-run until clean
```

**Done condition:** `lint-imports` exits 0. Add `make import-check` to `verify`.

---

## Step 7: Write a minimal AGENTS.md

**Goal:** An agent can find the key commands and constraints without reading
the entire codebase.

**What to include:**

1. The exact commands: bootstrap, verify, test-unit, focused test
2. Non-obvious architectural constraints (things the linter cannot catch)
3. Protected paths that require human review before modification
4. What "done" looks like (evidence to provide before claiming completion)

**What to leave out:**

Everything the tools already enforce. If ruff catches it, do not write it
in AGENTS.md. If the import linter catches it, do not write it. The file
should contain only what a tool cannot check.

**Template:** Copy [AGENTS.md](./AGENTS.md) from this repository and replace
the examples with your actual commands and constraints.

**Done condition:** The file is under 60 lines. Every sentence answers a
question the tools cannot.

---

## Step 8: Add Architecture Decision Records

**Goal:** Constraints that look like bugs are documented with the reason they
exist, and an agent can verify they are still in force.

**Do it:**

Create `docs/adr/`. Copy
[ADR-DOMAIN-001-money-not-float.md](./docs/adr/ADR-DOMAIN-001-money-not-float.md)
as a template.

For each significant constraint in your codebase, write one ADR:
- What is the rule
- Why it exists (the incident or reasoning that established it)
- A `## Verification` section: a command to run or a pattern to search

Add ADR validation to CI:
```bash
# Copy the validator
cp scripts/validate_adrs.py your-repo/scripts/
# Add to Makefile
validate-adrs:
	python scripts/validate_adrs.py
# Add to verify target
verify: format-check lint typecheck test validate-adrs
```

**Start with three ADRs** that cover your most-violated constraints. Add more
after agent sessions reveal what gets misunderstood.

**Done condition:** `make validate-adrs` passes. Every ADR has a Verification
section you could give to an agent as a check command.

---

## Step 9: Add safety boundaries

**Goal:** An agent cannot silently merge a high-risk change.

**Do it:**

Create `.github/CODEOWNERS`:
```
/.github/workflows/    @your-platform-team
/infra/                @your-platform-team
/db/migrations/        @your-dba
/src/payments/         @your-payments-team
```

Enable branch protection on `main` in GitHub Settings → Branches:
- Require status checks to pass before merging
- Require pull request reviews
- Do not allow bypassing the above settings

Add secret scanning if not already on:
```
GitHub Settings → Security → Code security → Secret scanning → Enable
```

**Done condition:** A PR that fails CI cannot be merged. A change to
`.github/workflows/` requires a review from `@platform-team`.

---

## Step 10: Add an evaluation baseline

**Goal:** You can measure whether a change to AGENTS.md, tooling, or code
structure makes agent behaviour better or worse.

**Do it:**

Copy `scripts/run_evals.py` and `scripts/eval_tasks/` from this repository.

Write 5 representative tasks based on your first agent sessions. Each task
should be something the agent does regularly:

```yaml
# scripts/eval_tasks/add-field-to-model.yaml
description: >
  Add a `tax_rate` field (Decimal, 0–1) to the Order model
  with validation and a migration.

verification: "make verify"
expected_exit_code: 0
```

Run once to set the baseline:
```bash
python scripts/run_evals.py --baseline
```

Add the daily eval workflow:
```bash
cp .github/workflows/eval-daily.yml your-repo/.github/workflows/
```

**Done condition:** `python scripts/run_evals.py` runs, produces a success
rate, and the daily workflow is scheduled.

---

## Maturity checklist

After completing each step, your repository level:

| Steps completed | Level | What agents can do |
|---|---|---|
| 1–3 | Level 1: Runnable | Small local tasks |
| 1–6 | Level 2: Verifiable | Bounded changes with evidence |
| 1–9 | Level 3: Agent-safe | Meaningful autonomy in controlled boundaries |
| 1–10 | Level 4: Measured | Improve agent workflow from evidence |

---

## Common issues

**`make verify` passes locally but fails in CI**

The most common cause: CI installs a different version of a tool. Pin all
dev dependencies with exact versions in `pyproject.toml` and use `uv.lock`.

**import-linter finds violations I cannot fix right now**

Add a temporary `exclude_modules` to the contract and create a task to
remove it. Do not disable the contract entirely.

**mypy strict is too noisy for an existing codebase**

Use `[[tool.mypy.overrides]]` with `ignore_errors = true` on legacy modules.
Add a test that counts the overrides and fails if the number increases:
```python
# tests/unit/test_mypy_overrides.py
import toml
config = toml.load("pyproject.toml")
overrides = config.get("tool", {}).get("mypy", {}).get("overrides", [])
ignored = sum(1 for o in overrides if o.get("ignore_errors"))
assert ignored <= 12, f"mypy overrides grew to {ignored} — fix some before adding more"
```

**AGENTS.md keeps growing**

Run the writing-lab check: for each sentence, ask "can a tool enforce this?"
If yes, remove the sentence and add the tool rule instead.
