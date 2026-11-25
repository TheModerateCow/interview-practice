"""Replenishment planning."""

from __future__ import annotations

from .models import Suggestion
from .store import StockKey


class ReplenishMixin:
    def replenishment(self, warehouse: str, now: int) -> list[Suggestion]:
        """Plan restocking for one warehouse at time now: one Suggestion for each SKU with
        a Rule there whose stock position has fallen to the rule's min, sorted by SKU. It
        only plans; nothing is moved or ordered."""
        self._check_warehouse(warehouse)
        self._advance(now)
        skus = sorted(k.sku for k in self.store.rules if k.warehouse == warehouse)
        out: list[Suggestion] = []
        for sku in skus:
            k = StockKey(warehouse, sku)
            rule = self.store.rules[k]
            pos = self._available(k) + self.store.inbound.get(k, 0)
            if pos > rule.min:
                continue
            qty = rule.max - pos
            if rule.pack > 1:
                qty = (qty + rule.pack - 1) // rule.pack * rule.pack
            out.append(Suggestion(sku, pos, qty, self._source(warehouse, sku, qty)))
        return out

    def _source(self, dest: str, sku: str, qty: int) -> str:
        """The other warehouse that can best spare qty units of sku: the largest surplus
        (available minus its own rule's min) that covers qty, lowest ID on a tie."""
        best, best_surplus = "", 0
        for w in self._warehouse_ids():
            if w == dest:
                continue
            k = StockKey(w, sku)
            rule = self.store.rules.get(k)
            surplus = self._available(k) - (rule.min if rule else 0)
            if surplus >= qty and (best == "" or surplus > best_surplus):
                best, best_surplus = w, surplus
        return best
