"""The quota service for one gateway region."""

from __future__ import annotations

from .models import (
    BadCost,
    BadRange,
    Decision,
    DuplicateKey,
    DuplicatePlan,
    Event,
    InvalidPlan,
    Key,
    Plan,
    Revoked,
    UnknownKey,
    UnknownPlan,
    UsageLine,
)
from .store import Store
from .window import capacity, reset_in, window_start


class Service:
    def __init__(self) -> None:
        self._store = Store()

    def add_plan(self, p: Plan) -> None:
        """Register a pricing tier."""
        if p.limit <= 0 or p.window <= 0 or p.burst < 0:
            raise InvalidPlan
        if self._store.plan(p.name) is not None:
            raise DuplicatePlan
        self._store.add_plan(p)

    def issue_key(self, id: str, org: str, plan: str) -> None:
        """Create an API key for org on the named plan."""
        if self._store.plan(plan) is None:
            raise UnknownPlan
        if self._store.key(id) is not None:
            raise DuplicateKey
        self._store.add_key(Key(id, org, plan))

    def key(self, id: str) -> Key:
        """A key's current record."""
        k = self._store.key(id)
        if k is None:
            raise UnknownKey
        return k

    def revoke(self, id: str) -> None:
        """Disable a key for good. Its usage stays in the log."""
        self.key(id)
        self._store.revoke(id)

    def change_plan(self, id: str, plan: str) -> None:
        """Move a key to another plan; the new limit applies from the next request on."""
        self.key(id)
        if self._store.plan(plan) is None:
            raise UnknownPlan
        self._store.set_plan(id, plan)

    def allow(self, id: str, now: int, cost: int) -> Decision:
        """Decide whether a request costing `cost` units, made at `now`, fits
        the key's plan, and log the decision. A denied request spends nothing."""
        k = self.key(id)
        if k.revoked:
            raise Revoked
        if cost <= 0:
            raise BadCost
        p = self._store.plan(k.plan)
        used, limit = self._window(id, p, now)
        if used + cost > limit:
            self._store.record(id, Event(now, cost))
            return Decision(False, limit - used, reset_in(now, p.window))
        self._store.record(id, Event(now, cost, True))
        return Decision(True, limit - used - cost)

    def usage(self, id: str, now: int) -> tuple[int, int]:
        """(units spent in the window containing now, total it may spend there)."""
        k = self.key(id)
        return self._window(id, self._store.plan(k.plan), now)

    def report(self, org: str, start: int, end: int) -> list[UsageLine]:
        """Summarise an organisation's traffic with start <= at < end, one line
        per key that made a request in that range. See problem.md for the rules."""
        if end <= start:
            raise BadRange
        out: list[UsageLine] = []
        for id in self._store.keys_of(org):
            events = self._store.events_between(id, start, end)
            if not events:
                continue
            allowed = [e for e in events if e.allowed]
            out.append(
                UsageLine(
                    id,
                    self._store.key(id).plan,
                    len(allowed),
                    sum(e.cost for e in allowed),
                    len(events) - len(allowed),
                )
            )
        out.sort(key=lambda l: (-l.units, l.key_id))
        return out

    def _window(self, id: str, p: Plan, now: int) -> tuple[int, int]:
        """Units a key has spent in the window containing now, and that window's capacity."""
        start = window_start(now, p.window)
        used = self._store.units_between(id, start, start + p.window)
        prev = self._store.units_between(id, start - p.window, start)
        return used, capacity(p, prev)
