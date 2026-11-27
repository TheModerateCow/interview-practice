"""Ride-share dispatch along one highway corridor: riders, drivers, trips, a dispatch radius and capacity planning."""


class Dispatcher:
    def __init__(self):
        self._idle: dict[str, int] = {}   # idle driver id -> km
        self._busy: set[str] = set()      # drivers on a trip
        self._riders: dict[str, int] = {}  # waiting rider id -> km
        self._radius: int | None = None    # None = no limit

    # Level 1

    def add_driver(self, ts: int, id: str, km: int) -> bool:
        if id in self._idle or id in self._busy:
            return False
        self._idle[id] = km
        return True

    def add_rider(self, ts: int, id: str, km: int) -> bool:
        if id in self._riders:
            return False
        self._riders[id] = km
        return True

    def move_driver(self, ts: int, id: str, km: int) -> bool:
        if id not in self._idle:
            return False
        self._idle[id] = km
        return True

    def remove_driver(self, ts: int, id: str) -> bool:
        return self._idle.pop(id, None) is not None

    def cancel_rider(self, ts: int, id: str) -> bool:
        return self._riders.pop(id, None) is not None

    def nearest_driver(self, ts: int, rider: str) -> str | None:
        x = self._riders.get(rider)
        if x is None:
            return None
        best = None
        for d, km in self._idle.items():
            if self._radius is not None and abs(km - x) > self._radius:
                continue
            key = (abs(km - x), km, d)
            if best is None or key < best:
                best = key
        return None if best is None else best[2]

    # Level 2

    def dispatch(self, ts: int, rider: str) -> str | None:
        d = self.nearest_driver(ts, rider)
        if d is None:
            return None
        del self._riders[rider]
        del self._idle[d]
        self._busy.add(d)
        return d

    def complete_trip(self, ts: int, driver: str, km: int) -> bool:
        if driver not in self._busy:
            return False
        self._busy.remove(driver)
        self._idle[driver] = km
        return True

    def idle_between(self, ts: int, lo: int, hi: int) -> list[str]:
        hits = sorted((km, d) for d, km in self._idle.items() if lo <= km <= hi)
        return ["%s:%d" % (d, km) for km, d in hits]

    # Level 3

    def set_radius(self, ts: int, radius: int) -> None:
        self._radius = radius

    def max_served(self, ts: int) -> int:
        r, d = sorted(self._riders.values()), sorted(self._idle.values())
        if self._radius is None:
            return min(len(r), len(d))
        return _served(r, d, self._radius)

    # Level 4

    def min_radius(self, ts: int, need: int) -> int:
        if need <= 0:
            return 0
        if need > len(self._riders) or need > len(self._idle):
            return -1
        r, d = sorted(self._riders.values()), sorted(self._idle.values())
        lo, hi = 0, max(r[-1], d[-1]) - min(r[0], d[0])
        while lo < hi:
            mid = (lo + hi) // 2
            if _served(r, d, mid) >= need:
                hi = mid
            else:
                lo = mid + 1
        return lo


def _served(r: list[int], d: list[int], radius: int) -> int:
    """Most riders picked up at once, every pickup within radius. Both lists sorted; each rider, left to right,
    takes the leftmost free driver in reach (drivers too far left are skipped for good)."""
    count, j = 0, 0
    for x in r:
        while j < len(d) and d[j] < x - radius:
            j += 1
        if j == len(d):
            break
        if d[j] <= x + radius:
            count += 1
            j += 1
    return count
