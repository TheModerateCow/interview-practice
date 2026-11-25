"""The inventory service: warehouses, the clock, receiving and stock queries."""

from __future__ import annotations

from .models import Backdated, Duplicate, Invalid, Rule, UnknownWarehouse
from .replenish import ReplenishMixin
from .reservations import ReservationMixin
from .store import BinKey, Store, StockKey
from .transfers import TransferMixin


class Service(ReservationMixin, TransferMixin, ReplenishMixin):
    """Inventory service for a network of warehouses. Not safe for concurrent use: the
    API layer serialises calls. Every call that takes ``now`` moves the service clock
    forward (and expires holds that ran out); ``now`` may not go backwards."""

    def __init__(self) -> None:
        self.store = Store()
        self.warehouses: set[str] = set()
        self.now = 0
        self.seq = 0

    def add_warehouse(self, id: str) -> None:
        if not id:
            raise Invalid("invalid request: empty warehouse id")
        if id in self.warehouses:
            raise Duplicate(f"duplicate id: warehouse {id!r}")
        self.warehouses.add(id)

    def _check_warehouse(self, id: str) -> None:
        if id not in self.warehouses:
            raise UnknownWarehouse(f"unknown warehouse: {id!r}")

    def _warehouse_ids(self) -> list[str]:
        return sorted(self.warehouses)

    def _advance(self, now: int) -> None:
        """Move the clock to now and expire the holds that ran out."""
        if now < self.now:
            raise Backdated("timestamp is older than the last operation")
        self.now = now
        self.store.expire(now)

    def set_rule(self, warehouse: str, sku: str, rule: Rule) -> None:
        self._check_warehouse(warehouse)
        if not sku or rule.min < 0 or rule.max <= rule.min or rule.pack < 0:
            raise Invalid("invalid request: rule needs 0 <= min < max and pack >= 0")
        self.store.rules[StockKey(warehouse, sku)] = rule

    def receive(self, warehouse: str, bin: str, sku: str, qty: int, now: int) -> None:
        """Put qty units of sku from a supplier delivery away into a bin."""
        self._check_warehouse(warehouse)
        if not bin or not sku or qty <= 0:
            raise Invalid("invalid request: receive needs a bin, a SKU and a positive quantity")
        self._advance(now)
        self.store.put_away(BinKey(warehouse, bin, sku), qty)

    def on_hand(self, warehouse: str, sku: str) -> int:
        """The physical quantity of sku on the warehouse's shelves."""
        return self.store.on_hand.get(StockKey(warehouse, sku), 0)

    def bin_qty(self, warehouse: str, bin: str, sku: str) -> int:
        """The quantity of sku in one bin."""
        return self.store.bins.get(BinKey(warehouse, bin, sku), 0)

    def available(self, warehouse: str, sku: str, now: int) -> int:
        """What can still be promised: on hand minus active reservations, at now."""
        self._check_warehouse(warehouse)
        self._advance(now)
        return self._available(StockKey(warehouse, sku))

    def _available(self, k: StockKey) -> int:
        return self.store.on_hand.get(k, 0) - self.store.reserved.get(k, 0)
