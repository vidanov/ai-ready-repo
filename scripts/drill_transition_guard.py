"""Drill: prove Order.transition() guard fires on an invalid transition."""
from ai_ready_repo.domain import Order, OrderStatus

o = Order(customer_id="drill", items=["x"])
raised = False
try:
    o.transition(OrderStatus.SHIPPED)
except ValueError:
    raised = True

assert raised, "transition() did not raise — guard is unreachable or bypassed"
print("✓ drill-transition-guard passed: guard correctly rejected the invalid transition")
