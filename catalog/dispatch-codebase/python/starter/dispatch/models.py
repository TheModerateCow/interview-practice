"""Dispatch entities and the errors the service raises."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple


class DispatchError(Exception):
    """Base class for every error the dispatcher raises."""


class DuplicateOrder(DispatchError):
    pass


class DuplicateCourier(DispatchError):
    pass


class UnknownOrder(DispatchError):
    pass


class UnknownCourier(DispatchError):
    pass


class NoCourier(DispatchError):
    pass


class BadTransition(DispatchError):
    pass


class InvalidCourier(DispatchError):
    pass


class NotAssigned(DispatchError):
    pass


class OrderClosed(DispatchError):
    pass


class Point(NamedTuple):
    """A position on the city grid, in metres east (x) and north (y) of the zone's origin."""

    x: int
    y: int


class State(Enum):
    """Where an order is in its lifecycle."""

    PLACED = "placed"  # waiting for a courier
    ASSIGNED = "assigned"  # a courier is riding to the restaurant
    PICKED_UP = "picked_up"  # the courier has the food
    DELIVERED = "delivered"  # handed to the customer
    CANCELLED = "cancelled"  # cancelled by the customer or support

    def can_move_to(self, nxt: State) -> bool:
        return nxt in _TRANSITIONS.get(self, ())

    @property
    def terminal(self) -> bool:
        """The order is finished: the courier no longer carries it."""
        return self is State.DELIVERED


_TRANSITIONS = {
    State.PLACED: (State.ASSIGNED, State.CANCELLED),
    State.ASSIGNED: (State.PICKED_UP, State.CANCELLED),
    State.PICKED_UP: (State.DELIVERED,),
}


@dataclass
class Order:
    """One customer order from one restaurant. Times are whole minutes of the shift."""

    id: str
    restaurant: Point
    customer: Point
    placed_at: int
    prep_minutes: int
    state: State = State.PLACED
    courier_id: str = ""  # set once assigned

    @property
    def ready_at(self) -> int:
        """The minute the kitchen expects the food to be ready."""
        return self.placed_at + self.prep_minutes


@dataclass
class Courier:
    """A rider on shift."""

    id: str
    location: Point
    capacity: int  # most orders carried at once
    active: int = 0  # orders currently assigned to or carried by the courier
