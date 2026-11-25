"""Replenishment planning."""

from __future__ import annotations

from .models import Suggestion


class ReplenishMixin:
    def replenishment(self, warehouse: str, now: int) -> list[Suggestion]:
        """Plan restocking for one warehouse at time now: one Suggestion for each SKU with
        a Rule there whose stock position has fallen to the rule's min, sorted by SKU. It
        only plans; nothing is moved or ordered. See problem.md for the full rules."""
        raise NotImplementedError
