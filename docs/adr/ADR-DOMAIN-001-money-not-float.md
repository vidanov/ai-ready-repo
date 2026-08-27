---
id: ADR-DOMAIN-001
status: accepted
scope:
  - src/ai_ready_repo/domain/**
---

# Monetary values use Money, never float

## Decision

All monetary values in the domain layer MUST use the `Money` value object.

Code MUST NOT use `float`, `int`, or bare `Decimal` for monetary values.

## Reasons

- Floating-point arithmetic produces rounding errors that compound across
  transactions. `0.1 + 0.2 != 0.3` in Python floats.
- `Money` enforces currency matching at the type level — adding EUR to USD
  raises immediately instead of silently producing a wrong result.
- Immutability prevents accidental mutation of values passed between layers.

## Verification

Search for float usage in monetary context:

```
rg "price.*float|amount.*float|float.*price|float.*amount" src/
```

Run the domain tests:

```
make test-unit
```

Any new monetary field must use `Money`. A float in a domain model is a bug.
