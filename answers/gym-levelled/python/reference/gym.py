"""The class booking desk of a gym: classes with a fixed number of spots, members
who book them, waitlists, class credits and weekly series."""

from dataclasses import dataclass, field

REFUND_WINDOW = 60  # minutes before the start a cancellation still gets its credits back
WEEK = 7 * 24 * 60


@dataclass
class _Class:
    start: int
    capacity: int
    price: int = 0
    booked: dict = field(default_factory=dict)  # member -> credits paid
    waiting: list = field(default_factory=list)
    cancelled: bool = False


class Studio:
    """Holds every class. Timestamps (minutes) passed to its methods only ever increase."""

    def __init__(self) -> None:
        self._classes: dict[str, _Class] = {}
        self._credits: dict[str, int] = {}
        self._series: dict[str, list[str]] = {}

    def _open(self, ts: int, class_id: str):
        """The class if it exists, isn't cancelled and hasn't started."""
        c = self._classes.get(class_id)
        if c is None or c.cancelled or ts >= c.start:
            return None
        return c

    def _promote(self, c: _Class) -> None:
        while c.waiting and len(c.booked) < c.capacity:
            m = c.waiting.pop(0)
            if self._credits.get(m, 0) >= c.price:
                self._credits[m] = self._credits.get(m, 0) - c.price
                c.booked[m] = c.price

    def _member_classes(self, member: str, keep) -> list[str]:
        ids = [i for i, c in self._classes.items() if not c.cancelled and member in c.booked and keep(c)]
        return sorted(ids, key=lambda i: (self._classes[i].start, i))

    def add_class(self, ts: int, class_id: str, start: int, capacity: int) -> bool:
        if class_id in self._classes or capacity <= 0 or start <= ts:
            return False
        self._classes[class_id] = _Class(start, capacity)
        return True

    def book(self, ts: int, class_id: str, member: str) -> bool:
        c = self._open(ts, class_id)
        if c is None or member in c.booked or len(c.booked) >= c.capacity:
            return False
        if self._credits.get(member, 0) < c.price:
            return False
        self._credits[member] = self._credits.get(member, 0) - c.price
        c.booked[member] = c.price
        return True

    def cancel(self, ts: int, class_id: str, member: str) -> bool:
        c = self._open(ts, class_id)
        if c is None:
            return False
        if member in c.waiting:
            c.waiting.remove(member)
            return True
        if member not in c.booked:
            return False
        paid = c.booked.pop(member)
        if c.start - ts >= REFUND_WINDOW:
            self._credits[member] = self._credits.get(member, 0) + paid
        self._promote(c)
        return True

    def spots_left(self, ts: int, class_id: str) -> int:
        c = self._classes.get(class_id)
        if c is None or c.cancelled:
            return -1
        return c.capacity - len(c.booked)

    def upcoming(self, ts: int, member: str) -> list[str]:
        return self._member_classes(member, lambda c: c.start > ts)

    def join_waitlist(self, ts: int, class_id: str, member: str) -> int:
        c = self._open(ts, class_id)
        if c is None or member in c.booked or member in c.waiting or len(c.booked) < c.capacity:
            return -1
        c.waiting.append(member)
        return len(c.waiting)

    def waitlist(self, ts: int, class_id: str) -> list[str]:
        c = self._classes.get(class_id)
        if c is None or c.cancelled:
            return []
        return list(c.waiting)

    def add_credits(self, ts: int, member: str, n: int) -> int:
        if n <= 0:
            return -1
        self._credits[member] = self._credits.get(member, 0) + n
        return self._credits[member]

    def credits(self, ts: int, member: str) -> int:
        return self._credits.get(member, 0)

    def set_price(self, ts: int, class_id: str, price: int) -> bool:
        c = self._open(ts, class_id)
        if c is None or price < 0:
            return False
        c.price = price
        return True

    def add_series(self, ts: int, series_id: str, first_start: int, capacity: int, weeks: int) -> bool:
        ids = [f"{series_id}-{i}" for i in range(1, weeks + 1)]
        if series_id in self._series or weeks <= 0 or capacity <= 0 or first_start <= ts:
            return False
        if any(i in self._classes for i in ids):
            return False
        for k, i in enumerate(ids):
            self._classes[i] = _Class(first_start + k * WEEK, capacity)
        self._series[series_id] = ids
        return True

    def cancel_class(self, ts: int, class_id: str) -> bool:
        c = self._open(ts, class_id)
        if c is None:
            return False
        for m, paid in c.booked.items():
            self._credits[m] = self._credits.get(m, 0) + paid
        c.booked.clear()
        c.waiting.clear()
        c.cancelled = True
        return True

    def cancel_series(self, ts: int, series_id: str) -> int:
        ids = self._series.get(series_id)
        if ids is None:
            return -1
        return sum(1 for i in ids if self.cancel_class(ts, i))

    def history(self, ts: int, member: str) -> list[str]:
        return self._member_classes(member, lambda c: c.start <= ts)
