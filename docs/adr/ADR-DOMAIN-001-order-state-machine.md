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
