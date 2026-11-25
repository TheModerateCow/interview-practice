"""The box office for a concert promoter: events with a fixed number of seats,
buyers who own tickets, and short seat holds at checkout."""

from dataclasses import dataclass, field


@dataclass
class _Hold:
    event_id: str
    buyer: str
    qty: int
    expires_at: int
    confirmed: bool = False


@dataclass
class _Event:
    capacity: int
    owned: dict = field(default_factory=dict)
    sold: int = 0
    log: list = field(default_factory=list)  # (ts, buyer, delta) for the history queries


class Office:
    """Holds every event. Timestamps passed to its methods only ever increase."""

    def __init__(self) -> None:
        self._events: dict[str, _Event] = {}
        self._holds: dict[str, _Hold] = {}
        self._next_id = 0

    def _own(self, ts: int, e: _Event, buyer: str, delta: int) -> None:
        e.owned[buyer] = e.owned.get(buyer, 0) + delta
        e.sold += delta
        e.log.append((ts, buyer, delta))

    def _held(self, ts: int, event_id: str) -> int:
        return sum(h.qty for h in self._holds.values()
                   if h.event_id == event_id and not h.confirmed and ts < h.expires_at)

    def create_event(self, ts: int, event_id: str, capacity: int) -> bool:
        if event_id in self._events or capacity <= 0:
            return False
        self._events[event_id] = _Event(capacity)
        return True

    def buy(self, ts: int, event_id: str, buyer: str, qty: int) -> bool:
        e = self._events.get(event_id)
        if e is None or qty <= 0 or qty > self.available(ts, event_id):
            return False
        self._own(ts, e, buyer, qty)
        return True

    def refund(self, ts: int, event_id: str, buyer: str, qty: int) -> bool:
        e = self._events.get(event_id)
        if e is None or qty <= 0 or e.owned.get(buyer, 0) < qty:
            return False
        self._own(ts, e, buyer, -qty)
        return True

    def available(self, ts: int, event_id: str) -> int:
        e = self._events.get(event_id)
        if e is None:
            return -1
        return e.capacity - e.sold - self._held(ts, event_id)

    def top_buyers(self, ts: int, event_id: str, n: int) -> list[str]:
        e = self._events.get(event_id)
        if e is None:
            return []
        names = sorted((b for b, q in e.owned.items() if q > 0), key=lambda b: (-e.owned[b], b))
        return [f"{b}({e.owned[b]})" for b in names[:max(n, 0)]]

    def busiest_events(self, ts: int, n: int) -> list[str]:
        ids = sorted(self._events, key=lambda i: (-self._events[i].sold, i))
        return [f"{i}({self._events[i].sold})" for i in ids[:max(n, 0)]]

    def hold(self, ts: int, event_id: str, buyer: str, qty: int, ttl: int) -> str:
        if event_id not in self._events or qty <= 0 or ttl <= 0 or qty > self.available(ts, event_id):
            return ""
        self._next_id += 1
        hid = f"h{self._next_id}"
        self._holds[hid] = _Hold(event_id, buyer, qty, ts + ttl)
        return hid

    def confirm(self, ts: int, hold_id: str) -> bool:
        h = self._holds.get(hold_id)
        if h is None or h.confirmed or ts >= h.expires_at:
            return False
        h.confirmed = True
        self._own(ts, self._events[h.event_id], h.buyer, h.qty)
        return True

    def owned_at(self, ts: int, event_id: str, buyer: str, at_ts: int) -> int:
        e = self._events.get(event_id)
        if e is None:
            return -1
        return sum(d for t, b, d in e.log if t <= at_ts and b == buyer)

    def sold_at(self, ts: int, event_id: str, at_ts: int) -> int:
        e = self._events.get(event_id)
        if e is None:
            return -1
        return sum(d for t, _, d in e.log if t <= at_ts)
