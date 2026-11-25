"""Transfers of stock between warehouses."""

from __future__ import annotations

from dataclasses import replace

from .models import (
    IN_TRANSIT,
    RECEIVED,
    Duplicate,
    InsufficientStock,
    Invalid,
    NotFound,
    Transfer,
    TransferState,
)
from .store import BinKey, StockKey


class TransferMixin:
    def start_transfer(self, id: str, from_wh: str, to_wh: str, sku: str, qty: int, now: int) -> Transfer:
        """Ship qty units of sku from one warehouse to another. The units are picked from
        the source's bins now and count as inbound at the destination until
        ``receive_transfer`` puts them away."""
        for w in (from_wh, to_wh):
            self._check_warehouse(w)
        if not id or from_wh == to_wh or qty <= 0:
            raise Invalid("invalid request: transfer needs an id, two warehouses and a positive quantity")
        if id in self.store.transfers:
            raise Duplicate(f"duplicate id: transfer {id!r}")
        self._advance(now)
        src = StockKey(from_wh, sku)
        avail = self.store.on_hand.get(src, 0)
        if avail < qty:
            raise InsufficientStock(
                f"insufficient available stock: {avail} available at {from_wh}, {qty} requested"
            )
        self.store.pick(src, qty)
        t = Transfer(id, from_wh, to_wh, sku, qty, IN_TRANSIT, now)
        self.store.transfers[id] = t
        dst = StockKey(to_wh, sku)
        self.store.inbound[dst] = self.store.inbound.get(dst, 0) + qty
        return replace(t)

    def receive_transfer(self, id: str, bin: str, now: int) -> None:
        """Put an arrived transfer away into a bin at its destination."""
        if not bin:
            raise Invalid("invalid request: empty bin")
        self._advance(now)
        t = self.store.transfers.get(id)
        if t is None:
            raise NotFound(f"not found: transfer {id!r}")
        if t.status != IN_TRANSIT:
            raise TransferState("transfer is not in transit")
        self.store.inbound[StockKey(t.to_wh, t.sku)] -= t.qty
        self.store.put_away(BinKey(t.to_wh, bin, t.sku), t.qty)
        t.status, t.received_at, t.bin = RECEIVED, now, bin

    def inbound(self, warehouse: str, sku: str) -> int:
        """The quantity of sku in transit toward warehouse."""
        return self.store.inbound.get(StockKey(warehouse, sku), 0)

    def transfer(self, id: str) -> Transfer | None:
        """A copy of a transfer, or None."""
        t = self.store.transfers.get(id)
        return replace(t) if t is not None else None
