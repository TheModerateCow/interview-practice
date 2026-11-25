"""Reservation expiry."""

from __future__ import annotations

from .models import ACTIVE, EXPIRED


class ExpiryMixin:
    """Mixed into Store. ``holds`` lists every reservation in the order it was placed."""

    def track(self, r) -> None:
        """Register a newly placed reservation for expiry."""
        self.holds.append(r)

    def expire(self, now: int) -> None:
        """End every active reservation whose hold has run out by now (expires_at <= now)
        and return its stock to available."""
        for r in self.holds:
            if r.status == ACTIVE and r.expires_at <= now:
                self.end_hold(r, EXPIRED, r.expires_at)
