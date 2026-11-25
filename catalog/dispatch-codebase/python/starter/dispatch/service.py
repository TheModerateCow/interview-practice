"""The dispatcher for one delivery zone."""

from __future__ import annotations

from dataclasses import replace

from .batch import Assignment, dispatch_pending
from .eta import eta
from .geo import distance
from .models import BadTransition, Courier, InvalidCourier, NoCourier, Order, Point, State
from .store import Store

# The furthest, in metres, a courier may be from the restaurant to be offered an order.
MAX_PICKUP_DISTANCE = 4000


class Dispatcher:
    def __init__(self) -> None:
        self.store = Store()

    def add_courier(self, id: str, at: Point, capacity: int) -> None:
        """Put a courier on shift at a location."""
        if capacity < 1:
            raise InvalidCourier("courier capacity must be at least 1")
        self.store.add_courier(Courier(id, Point(*at), capacity))

    def place_order(self, id: str, restaurant: Point, customer: Point, placed_at: int, prep_minutes: int) -> None:
        """Record a new order, waiting for a courier."""
        self.store.add_order(Order(id, Point(*restaurant), Point(*customer), placed_at, prep_minutes))

    def order(self, id: str) -> Order:
        """A copy of an order."""
        return replace(self.store.order(id))

    def assign(self, order_id: str) -> str:
        """Hand a waiting order to the nearest courier with room, right away."""
        o = self.store.order(order_id)
        if o.state is not State.PLACED:
            raise BadTransition("order cannot move to that state")
        c = self.nearest_courier(o.restaurant)
        if c is None:
            raise NoCourier("no courier available")
        self.assign_to(o, c)
        return c.id

    def advance(self, order_id: str, to: State) -> None:
        """Move an order along its lifecycle: picked_up, delivered or cancelled.

        Orders become assigned only through assign or dispatch_pending.
        """
        o = self.store.order(order_id)
        if to is State.ASSIGNED or not o.state.can_move_to(to):
            raise BadTransition("order cannot move to that state")
        o.state = to
        if not o.courier_id:
            return
        c = self.store.courier(o.courier_id)
        if to is State.PICKED_UP:
            c.location = o.restaurant
        elif to is State.DELIVERED:
            c.location = o.customer
        if to.terminal:
            c.active -= 1

    def courier_orders(self, courier_id: str) -> list[str]:
        """The ids of the unfinished orders a courier holds."""
        self.store.courier(courier_id)
        return [o.id for o in self.store.active_orders_of(courier_id)]

    def eta(self, order_id: str, now: int) -> int:
        return eta(self.store, order_id, now)

    def dispatch_pending(self, now: int) -> list[Assignment]:
        return dispatch_pending(self, now)

    def nearest_courier(self, restaurant: Point) -> Courier | None:
        """The courier closest to a restaurant who has room for another order and is within
        MAX_PICKUP_DISTANCE. Ties go to the lower id."""
        best, best_dist = None, 0
        for c in self.store.couriers():
            if len(self.store.active_orders_of(c.id)) >= c.capacity:
                continue
            dist = distance(c.location, restaurant)
            if dist > MAX_PICKUP_DISTANCE:
                continue
            if best is None or dist < best_dist or (dist == best_dist and c.id < best.id):
                best, best_dist = c, dist
        return best

    def assign_to(self, o: Order, c: Courier) -> None:
        o.state = State.ASSIGNED
        o.courier_id = c.id
        c.active += 1
