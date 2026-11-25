"""Delivery-time estimates."""

from .geo import distance, travel_minutes
from .models import NotAssigned, OrderClosed, State
from .store import Store


def eta(store: Store, order_id: str, now: int) -> int:
    """Minutes from now until the order should reach the customer.

    An assigned order: the courier rides to the restaurant, waits there if the food is not ready yet
    (see Order.ready_at), then rides to the customer. A picked-up order: the courier rides from where
    they are to the customer. Each leg's riding time counts in whole minutes, rounded up.
    """
    o = store.order(order_id)
    if o.state is State.PLACED:
        raise NotAssigned("order has no courier yet")
    if o.state.terminal:
        raise OrderClosed("order is already finished")
    c = store.courier(o.courier_id)
    if o.state is State.PICKED_UP:
        return travel_minutes(distance(c.location, o.customer))
    pickup = max(now + travel_minutes(distance(c.location, o.restaurant)), o.ready_at)
    return pickup + travel_minutes(distance(o.restaurant, o.customer)) - now
