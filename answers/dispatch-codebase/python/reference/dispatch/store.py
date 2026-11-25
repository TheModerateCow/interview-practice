"""In-memory storage for orders and couriers."""

from __future__ import annotations

from .models import Courier, DuplicateCourier, DuplicateOrder, Order, State, UnknownCourier, UnknownOrder


class Store:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._couriers: dict[str, Courier] = {}  # insertion order = the order they joined the shift

    def add_order(self, o: Order) -> None:
        if o.id in self._orders:
            raise DuplicateOrder("order already exists")
        self._orders[o.id] = o

    def add_courier(self, c: Courier) -> None:
        if c.id in self._couriers:
            raise DuplicateCourier("courier already exists")
        self._couriers[c.id] = c

    def order(self, id: str) -> Order:
        try:
            return self._orders[id]
        except KeyError:
            raise UnknownOrder("unknown order") from None

    def courier(self, id: str) -> Courier:
        try:
            return self._couriers[id]
        except KeyError:
            raise UnknownCourier("unknown courier") from None

    def couriers(self) -> list[Courier]:
        """Every courier on shift, in the order they joined."""
        return list(self._couriers.values())

    def pending_orders(self) -> list[Order]:
        """Orders still waiting for a courier, oldest first; orders placed in the same minute sort by id."""
        out = [o for o in self._orders.values() if o.state is State.PLACED]
        out.sort(key=lambda o: (o.placed_at, o.id))
        return out

    def active_orders_of(self, courier_id: str) -> list[Order]:
        """The unfinished orders assigned to a courier, sorted by id."""
        out = [o for o in self._orders.values() if o.courier_id == courier_id and not o.state.terminal]
        out.sort(key=lambda o: o.id)
        return out
