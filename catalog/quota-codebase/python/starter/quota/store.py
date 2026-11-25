"""In-memory storage: plans, keys and each key's request log."""

from __future__ import annotations

import bisect

from .models import Event, Key, Plan


class Store:
    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}
        self._keys: dict[str, Key] = {}
        self._events: dict[str, list[Event]] = {}  # per key, oldest first
        self._times: dict[str, list[int]] = {}  # the same log's `at` values, for bisecting

    def plan(self, name: str) -> Plan | None:
        return self._plans.get(name)

    def add_plan(self, p: Plan) -> None:
        self._plans[p.name] = p

    def key(self, id: str) -> Key | None:
        return self._keys.get(id)

    def add_key(self, k: Key) -> None:
        self._keys[k.id] = k

    def set_plan(self, id: str, plan: str) -> None:
        """Move a key to another plan."""
        k = self._keys[id]
        self._keys[id] = Key(k.id, k.org, plan)

    def revoke(self, id: str) -> None:
        k = self._keys[id]
        self._keys[id] = Key(k.id, k.org, k.plan, True)

    def keys_of(self, org: str) -> list[str]:
        """Ids of an organisation's keys, sorted."""
        return sorted(id for id, k in self._keys.items() if k.org == org)

    def record(self, id: str, e: Event) -> None:
        """Append a decision to the key's log. Requests for one key arrive in
        time order, so the log stays sorted by `at`."""
        self._events.setdefault(id, []).append(e)
        self._times.setdefault(id, []).append(e.at)

    def events_between(self, id: str, start: int, end: int) -> list[Event]:
        """The key's events with start <= at < end."""
        return [e for e in self._events.get(id, []) if start <= e.at < end]

    def units_between(self, id: str, start: int, end: int) -> int:
        """Units the key spent with start <= at < end."""
        return sum(e.cost for e in self.events_between(id, start, end))
