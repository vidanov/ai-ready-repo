# Comparative agent benchmark protocol

No comparative agent runs are included yet. `make eval` is a verification
regression suite: it executes checks against code that already exists.

## Experiment

1. Select representative coding tasks with deterministic acceptance checks.
2. Pin an initial repository commit, task prompt, model/version, model settings,
   tool permissions, dependency environment, verifier revision, and time budget.
3. Prepare two workspaces from the same initial code: baseline conventions and
   improved repository conventions. Keep the actual task and acceptance checks
   identical; record the setup diff.
4. Run each pair with the same agent settings and independent fresh sessions.
   Repeat pairs and alternate order to reduce warm-cache and ordering effects.
5. Run acceptance checks from a trusted revision against each produced patch.
   Retain failures, timeouts, and missing measurements rather than dropping them.
6. Compare correctness first, then time, retries, tool calls, and observed token
   usage. Report sample counts and uncertainty; do not infer token savings from
   whether a command starts with `make`.

## Required run record

Store an individual JSON record for every attempted run:

- `run_id`, `pair_id`, `task_id`, `variant` (`baseline` or `improved`)
- `initial_commit`, `setup_diff`, `verifier_commit`
- `model`, `model_settings`, `environment`, `budget`, `started_at`
- `outcome` (`passed`, `failed`, `timeout`, `measurement_invalid`)
- `elapsed_seconds`, `verify_attempts`, `tool_calls`
- `input_tokens`, `output_tokens` (null when unavailable, never assumed zero)
- `patch_path`, `acceptance_output_path`, `transcript_path`

Store raw evidence beside the records. Agent execution and token collection depend
on the chosen runner; this protocol deliberately does not fabricate measurements
from task YAML metadata. Actual runner integration and comparative runs remain
follow-up work, and performance claims remain a hypothesis until then.
