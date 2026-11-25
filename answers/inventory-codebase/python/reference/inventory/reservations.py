"""Reservations: holds on stock for open orders."""

from __future__ import annotations

from dataclasses import replace

from .models import (
    ACTIVE,
    COMMITTED,
    EXPIRED,
    RELEASED,
    Duplicate,
    InsufficientStock,
    Invalid,
    NotActive,
    NotFound,
    Reservation,
)
from .store import StockKey


class ReservationMixin:
    def reserve(self, id: str, warehouse: str, sku: str, qty: int, ttl: int, now: int) -> Reservation:
        """Hold qty units of sku in warehouse for an order, for ttl seconds from now. The
        hold is active while the clock is before ``expires_at = now + ttl``."""
        self._check_warehouse(warehouse)
        if not id or qty <= 0 or ttl <= 0:
            raise Invalid("invalid request: reserve needs an id, a positive quantity and ttl")
        if id in self.store.reservations:
            raise Duplicate(f"duplicate id: reservation {id!r}")
        self._advance(now)
        k = StockKey(warehouse, sku)
        avail = self._available(k)
        if avail < qty:
            raise InsufficientStock(f"insufficient available stock: {avail} available, {qty} requested")
        self.seq += 1
        r = Reservation(id, warehouse, sku, qty, now, now + ttl, ACTIVE, now, self.seq)
        self.store.reservations[id] = r
        self.store.reserved[k] = self.store.reserved.get(k, 0) + qty
        self.store.track(r)
        return replace(r)

    def release(self, id: str, now: int) -> None:
        """Cancel a reservation and return its stock to available. Releasing a hold that
        is already released or has expired is a no-op, so order-service retries are safe."""
        self._advance(now)
        r = self.store.reservations.get(id)
        if r is None:
            raise NotFound(f"not found: reservation {id!r}")
        if r.status == COMMITTED:
            raise NotActive(f"reservation is not active: {r.status}")
        if r.status in (RELEASED, EXPIRED):
            return
        self.store.end_hold(r, RELEASED, now)

    def commit(self, id: str, now: int) -> None:
        """Pick a reservation's quantity from the warehouse's bins for shipping and end
        the hold. A hold that expired or was released can't be committed: place a new one."""
        self._advance(now)
        r = self.store.reservations.get(id)
        if r is None:
            raise NotFound(f"not found: reservation {id!r}")
        if r.status != ACTIVE:
            raise NotActive(f"reservation is not active: {r.status}")
        self.store.pick(StockKey(r.warehouse, r.sku), r.qty)
        self.store.end_hold(r, COMMITTED, now)

    def reservation(self, id: str) -> Reservation | None:
        """A copy of a reservation, or None."""
        r = self.store.reservations.get(id)
        return replace(r) if r is not None else None
