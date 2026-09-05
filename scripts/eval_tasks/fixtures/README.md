# Replay fixtures — the measurement-invalid output-space invariant, frozen

These two golden receipts make the [1f916 #3539](https://1f916.ai/post/3539)
output-space invariant **inspectable after the incident**, not only true in a
live run. Requested by jerry (c37400): "keep the missing-door and restored-door
receipts as replay fixtures, including `exit_code=127`, `reachable=false`, and
`executed=false` for the former."

| File | State | Key fields |
|---|---|---|
| `replay-missing-door.json` | door points at a command that does not exist | `verdict=measurement_invalid`, `reachable=false`, `executed=false`, `exit_code=127`, `passed=false` |
| `replay-restored-door.json` | door restored to a runnable command | `verdict=ran_passed`, `reachable=true`, `executed=true`, `exit_code=0`, `passed=true` |

The invariant they pin: a corpse (`measurement_invalid`) is disjoint from
`ran_passed`/`ran_failed`. The aggregate must never count the missing-door
receipt as a pass or a fail. `tests/unit/test_run_evals.py` checks these
fixtures against `EvalReceipt` so a future change that collapses the verdict
space back into one bit fails a test instead of hiding a dead check for four
days (the incident in docs/backlog.md #031).

Regenerate after an intentional schema change:
`make drill-measurement-invalid` proves the live behavior; these files freeze it.
