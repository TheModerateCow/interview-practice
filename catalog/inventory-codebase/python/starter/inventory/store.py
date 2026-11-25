"""The in-memory state: bins, per-SKU counters, reservations and transfers."""

from __future__ import annotations

from typing import NamedTuple

from .expiry import ExpiryMixin
from .models import ShortPick


class StockKey(NamedTuple):
    warehouse: str
    sku: str


class BinKey(NamedTuple):
    warehouse: str
    bin: str
    sku: str

    @property
    def stock(self) -> StockKey:
        return StockKey(self.warehouse, self.sku)


class Store(ExpiryMixin):
    """Per-SKU counters are kept alongside the bins so availability checks never walk
    the shelves."""

    def __init__(self) -> None:
        self.bins: dict[BinKey, int] = {}
        self.pick_path: dict[StockKey, list[str]] = {}  # cached bins per SKU in pick order, built on first pick
        self.on_hand: dict[StockKey, int] = {}  # sum of the SKU's bins
        self.reserved: dict[StockKey, int] = {}  # held by active reservations
        self.inbound: dict[StockKey, int] = {}  # in transit toward the warehouse
        self.rules: dict[StockKey, object] = {}
        self.reservations: dict[str, object] = {}
        self.holds: list = []  # expiry queue, see expiry.py
        self.transfers: dict[str, object] = {}

    def put_away(self, k: BinKey, qty: int) -> None:
        """Add qty of a SKU to a bin."""
        self.bins[k] = self.bins.get(k, 0) + qty
        self.on_hand[k.stock] = self.on_hand.get(k.stock, 0) + qty
        if k not in self.bins:
            self.pick_path.pop(k.stock, None)

    def path(self, k: StockKey) -> list[str]:
        """The bins that hold (or held) the SKU, sorted by bin code, which is the order
        pickers walk the aisles."""
        p = self.pick_path.get(k)
        if p is None:
            p = sorted(b.bin for b in self.bins if b.stock == k)
            self.pick_path[k] = p
        return p

    def pick(self, k: StockKey, qty: int) -> None:
        """Take qty of a SKU off the shelves, emptying bins in pick order. If the bins
        hold less than qty it changes nothing and raises ShortPick."""
        path = self.path(k)
        if sum(self.bins[BinKey(k.warehouse, b, k.sku)] for b in path) < qty:
            raise ShortPick("short pick: bins hold less than requested")
        for b in path:
            bk = BinKey(k.warehouse, b, k.sku)
            take = min(qty, self.bins[bk])
            self.bins[bk] -= take
            self.on_hand[k] -= take
            qty -= take
            if qty == 0:
                break

    def end_hold(self, r, status: str, at: int) -> None:
        """Close an active reservation and give its quantity back to available stock."""
        k = StockKey(r.warehouse, r.sku)
        self.reserved[k] = self.reserved.get(k, 0) - r.qty
        r.status = status
        r.updated_at = at
