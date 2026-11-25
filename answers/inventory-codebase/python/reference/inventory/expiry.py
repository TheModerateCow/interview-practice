"""Reservation expiry."""

from __future__ import annotations

import heapq

from .models import ACTIVE, EXPIRED


class ExpiryMixin:
    """Mixed into Store. ``holds`` is a min-heap of (expires_at, seq, reservation), so the
    hold that runs out first is on top. Released and committed holds stay in it until
    their time comes."""

    def track(self, r) -> None:
        """Register a newly placed reservation for expiry."""
        heapq.heappush(self.holds, (r.expires_at, r.seq, r))

    def expire(self, now: int) -> None:
        """End every active reservation whose hold has run out by now (expires_at <= now)
        and return its stock to available."""
        while self.holds and self.holds[0][0] <= now:
            r = heapq.heappop(self.holds)[2]
            if r.status == ACTIVE:
                self.end_hold(r, EXPIRED, r.expires_at)
