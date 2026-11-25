"""The dispatch loop's tick."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from .service import Dispatcher

# How many minutes before its food is ready an order may be handed to a courier by dispatch_pending.
DISPATCH_WINDOW = 10


class Assignment(NamedTuple):
    """One order handed to one courier."""

    order_id: str
    courier_id: str


def dispatch_pending(d: Dispatcher, now: int) -> list[Assignment]:
    """Hand out the waiting orders that are due at minute now. See problem.md for the rules."""
    due = [o for o in d.store.pending_orders() if o.ready_at - now <= DISPATCH_WINDOW]
    due.sort(key=lambda o: (o.ready_at, o.id))
    out: list[Assignment] = []
    for o in due:
        c = d.nearest_courier(o.restaurant)
        if c is not None:
            d.assign_to(o, c)
            out.append(Assignment(o.id, c.id))
    return out
