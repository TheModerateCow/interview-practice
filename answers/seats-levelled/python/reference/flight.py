"""The business-class desk for one multi-stop flight: bookings, the upgrade waitlist,
busiest-leg queries and the best possible upgrade plan."""

import heapq

_FAR = 1 << 62


class Flight:
    """Stops 0..n; leg k flies stop k -> k+1 and has seats[k] free business seats."""

    def __init__(self, seats: list[int]) -> None:
        n = len(seats)
        size, h = 1, 0
        while size < n:
            size, h = size * 2, h + 1
        self._n, self._size, self._h = n, size, h
        self._seats = list(seats)
        # Segment tree over legs. Node p covers a run of legs: _hi[p] is the most seats taken on one of them,
        # _lo[p] the fewest free seats. _add[p] (internal nodes) counts seats taken on every leg under p that
        # p's children don't show yet.
        self._hi = [0] * (2 * size)
        self._lo = [0] * (2 * size)
        self._add = [0] * size
        self._lo[size:size + n] = seats
        for p in range(size - 1, 0, -1):
            self._hi[p] = max(self._hi[2 * p], self._hi[2 * p + 1])
            self._lo[p] = min(self._lo[2 * p], self._lo[2 * p + 1])
        self._trips: dict[str, list] = {}  # passenger -> [board, alight, status]
        self._waiting: dict[str, None] = {}  # waitlisted passengers, oldest request first

    # ---- segment tree: add seats taken on legs [l, r), read (most taken, fewest free) on legs [l, r)

    def _apply(self, p: int, v: int) -> None:
        self._hi[p] += v
        self._lo[p] -= v
        if p < self._size:
            self._add[p] += v

    def _pull(self, p: int) -> None:
        hi, lo, add = self._hi, self._lo, self._add
        while p > 1:
            p >>= 1
            a = add[p]
            hi[p] = max(hi[2 * p], hi[2 * p + 1]) + a
            lo[p] = min(lo[2 * p], lo[2 * p + 1]) - a

    def _push(self, p: int) -> None:
        add = self._add
        for s in range(self._h, 0, -1):
            i = p >> s
            a = add[i]
            if a:
                self._apply(2 * i, a)
                self._apply(2 * i + 1, a)
                add[i] = 0

    def _take(self, l: int, r: int, v: int) -> None:
        l += self._size
        r += self._size
        l0, r0 = l, r - 1
        while l < r:
            if l & 1:
                self._apply(l, v)
                l += 1
            if r & 1:
                r -= 1
                self._apply(r, v)
            l >>= 1
            r >>= 1
        self._pull(l0)
        self._pull(r0)

    def _range(self, l: int, r: int) -> tuple[int, int]:
        hi_, lo_ = self._hi, self._lo
        l += self._size
        r += self._size
        self._push(l)
        self._push(r - 1)
        hi, lo = 0, _FAR
        while l < r:
            if l & 1:
                hi = max(hi, hi_[l])
                lo = min(lo, lo_[l])
                l += 1
            if r & 1:
                r -= 1
                hi = max(hi, hi_[r])
                lo = min(lo, lo_[r])
            l >>= 1
            r >>= 1
        return hi, lo

    def _valid(self, board: int, alight: int) -> bool:
        return 0 <= board < alight <= self._n

    def _fits(self, board: int, alight: int) -> bool:
        return self._range(board, alight)[1] >= 1

    # ---- level 1

    def book(self, passenger: str, board: int, alight: int) -> bool:
        if passenger in self._trips or not self._valid(board, alight) or not self._fits(board, alight):
            return False
        self._take(board, alight, 1)
        self._trips[passenger] = [board, alight, "booked"]
        return True

    def cancel(self, passenger: str) -> bool:
        t = self._trips.pop(passenger, None)
        if t is None:
            return False
        if t[2] == "waitlisted":
            del self._waiting[passenger]
        else:
            self._take(t[0], t[1], -1)
        return True

    def free_seats(self, leg: int) -> int | None:
        if not 0 <= leg < self._n:
            return None
        return self._range(leg, leg + 1)[1]

    # ---- level 2

    def request_upgrade(self, passenger: str, board: int, alight: int) -> str:
        if passenger in self._trips or not self._valid(board, alight):
            return ""
        if self._fits(board, alight):
            self._take(board, alight, 1)
            self._trips[passenger] = [board, alight, "upgraded"]
            return "upgraded"
        self._trips[passenger] = [board, alight, "waitlisted"]
        self._waiting[passenger] = None
        return "waitlisted"

    def status(self, passenger: str) -> str:
        t = self._trips.get(passenger)
        return t[2] if t else ""

    def promote(self) -> list[str]:
        done = []
        for p in list(self._waiting):
            t = self._trips[p]
            if self._fits(t[0], t[1]):
                self._take(t[0], t[1], 1)
                t[2] = "upgraded"
                del self._waiting[p]
                done.append(p)
        return done

    # ---- level 3

    def busiest(self, from_stop: int, to_stop: int) -> int | None:
        if not self._valid(from_stop, to_stop):
            return None
        return self._range(from_stop, to_stop)[0]

    # ---- level 4

    def best_plan(self) -> int:
        # Seats left once paid bookings are seated, leg by leg.
        n = self._n
        diff = [0] * (n + 1)
        starts = [[] for _ in range(n)]
        m = 0
        for board, alight, st in self._trips.values():
            if st == "booked":
                diff[board] += 1
                diff[alight] -= 1
            else:
                starts[board].append(alight)
                m += 1
        # Sweep the legs left to right, taking each request as its boarding leg comes up. When a leg is over its
        # seats, drop the taken request that alights latest: it blocks the most legs still to come.
        ends = [0] * (n + 1)  # taken requests alighting at each stop
        taken = []  # max-heap of alight stops (negated)
        active = paid = dropped = 0
        for k in range(n):
            paid += diff[k]
            active -= ends[k]
            for alight in starts[k]:
                heapq.heappush(taken, -alight)
                ends[alight] += 1
                active += 1
            while active > self._seats[k] - paid:
                alight = -heapq.heappop(taken)
                ends[alight] -= 1
                active -= 1
                dropped += 1
        return m - dropped
