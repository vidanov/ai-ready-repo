---
id: ADR-DOMAIN-001
status: accepted
scope:
  - src/ai_ready_repo/domain/**
---

# Order status changes go through transition(), never direct assignment

## Decision

All `Order` status changes MUST use `Order.transition(new_status)`.

Code MUST NOT assign `order.status = ...` directly.

## Reasons

- Direct assignment bypasses the transition table and allows impossible states
  (e.g. jumping from `pending` to `delivered`, or reopening a cancelled order).
- `transition()` encodes the allowed state machine in one place. Changing
  business rules means updating `_TRANSITIONS`, not hunting down assignments.
- Invalid transitions raise immediately with a clear message, making bugs
  visible at the point of error rather than downstream.

## Verification

Search for direct status assignment outside the domain:

```
rg "\.status\s*=" src/ --glob "!*/domain/*"
```

Run the domain tests:

```
make test-unit
```

Any new status change must go through `transition()`. A direct assignment
outside the domain layer is a bug.

## Firing condition

A guard that has never rejected a real call cannot be distinguished from a guard
that is unreachable. Run the drill to prove `transition()` can convict:

```
make drill-transition-guard
```

This executes an invalid transition attempt against a live `Order` instance and
asserts that `ValueError` is raised. A passing drill means the guard is on the
executed path, not just in the file.

Review the ADR retirement conditions if:

- The drill ran and no exception was raised (guard is unreachable or bypassed).
- The drill has not been run in 6 months (staleness signal).

## Retirement

Remove this constraint if:

- The `Order` entity is replaced by an event-sourced aggregate where status
  is derived from the event log rather than stored as a field.
- The domain model moves to a framework (e.g. Django FSM) that provides its
  own transition enforcement, making the manual state machine redundant.

Review if the transition table has not changed in 12 months — a static state
machine may indicate the domain is stable enough to simplify.
