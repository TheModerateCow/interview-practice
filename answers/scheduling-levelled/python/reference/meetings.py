"""A team calendar's "find a time" core: attendees in their own time zones, busy blocks in UTC,
and searches for the earliest slot that everyone, or a quorum, can make."""

DAY = 1440


class _Attendee:
    def __init__(self, offset: int, work_start: int, work_end: int) -> None:
        self.offset = offset  # local = UTC + offset
        self.work_start = work_start
        self.work_end = work_end
        self.busy: dict[str, tuple[int, int, int]] = {}  # busy id -> (start, end, sequence number)

    def working(self, minute: int) -> bool:
        local = (minute + self.offset) % DAY
        if self.work_start < self.work_end:
            return self.work_start <= local < self.work_end
        return local >= self.work_start or local < self.work_end  # overnight shift

    def free(self, lo: int, hi: int) -> list[tuple[int, int]]:
        """Sorted, disjoint, non-touching UTC intervals inside [lo, hi) where this attendee is free."""
        span = self.work_end - self.work_start if self.work_start < self.work_end else self.work_end + DAY - self.work_start
        work: list[list[int]] = []
        d = (lo + self.offset) // DAY - 1  # the local day before lo's: an overnight shift can run into lo
        while True:
            s = d * DAY + self.work_start - self.offset
            if s >= hi:
                break
            e = min(s + span, hi)
            s = max(s, lo)
            if s < e:
                if work and s <= work[-1][1]:
                    work[-1][1] = max(work[-1][1], e)  # back-to-back working days join up
                else:
                    work.append([s, e])
            d += 1
        busy = sorted((s, e) for s, e, _ in self.busy.values() if e > lo and s < hi)
        out: list[tuple[int, int]] = []
        i = 0
        for ws, we in work:
            while i < len(busy) and busy[i][1] <= ws:
                i += 1
            cur = ws
            j = i
            while j < len(busy) and busy[j][0] < we:
                if busy[j][0] > cur:
                    out.append((cur, busy[j][0]))
                cur = max(cur, busy[j][1])
                j += 1
            if cur < we:
                out.append((cur, we))
        return out


def _intersect(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        s, e = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if s < e:
            out.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


class TeamCalendar:
    """Attendees by id. All times are integer minutes; busy blocks and searches are in UTC."""

    def __init__(self) -> None:
        self._people: dict[str, _Attendee] = {}
        self._issued = 0

    # level 1

    def add_attendee(self, id: str, offset: int, work_start: int, work_end: int) -> bool:
        if id in self._people:
            return False
        self._people[id] = _Attendee(offset, work_start, work_end)
        return True

    def add_busy(self, id: str, start: int, end: int) -> str | None:
        a = self._people.get(id)
        if a is None or start >= end:
            return None
        self._issued += 1
        bid = "busy%d" % self._issued
        a.busy[bid] = (start, end, self._issued)
        return bid

    def remove_busy(self, id: str, busy_id: str) -> bool:
        a = self._people.get(id)
        if a is None or busy_id not in a.busy:
            return False
        del a.busy[busy_id]
        return True

    def is_free(self, id: str, minute: int) -> bool:
        a = self._people.get(id)
        if a is None or not a.working(minute):
            return False
        return not any(s <= minute < e for s, e, _ in a.busy.values())

    # level 2

    def set_offset(self, id: str, offset: int) -> bool:
        a = self._people.get(id)
        if a is None:
            return False
        a.offset = offset
        return True

    def set_hours(self, id: str, work_start: int, work_end: int) -> bool:
        a = self._people.get(id)
        if a is None:
            return False
        a.work_start, a.work_end = work_start, work_end
        return True

    def agenda(self, id: str, from_: int, to: int) -> list[str]:
        a = self._people.get(id)
        if a is None:
            return []
        hits = sorted((s, e, n, bid) for bid, (s, e, n) in a.busy.items() if s < to and e > from_)
        return ["%s:%d-%d" % (bid, s, e) for s, e, _, bid in hits]

    # level 3

    def earliest_meeting(self, ids: list[str], duration: int, from_: int, to: int) -> int:
        people = [self._people.get(i) for i in ids]
        if any(p is None for p in people):
            return -1
        common = [(from_, to)]
        for p in people:
            common = _intersect(common, p.free(from_, to))
        for s, e in common:
            if e - s >= duration:
                return s
        return -1

    # level 4

    def earliest_quorum_meeting(self, ids: list[str], quorum: int, duration: int, from_: int, to: int) -> int:
        people = [self._people.get(i) for i in ids]
        if any(p is None for p in people):
            return -1
        events: list[tuple[int, int]] = []
        for p in people:
            for s, e in p.free(from_, to):
                if e - s >= duration:  # the meeting can start anywhere in [s, e - duration]
                    events.append((s, 1))
                    events.append((e - duration + 1, -1))
        events.sort()
        count = 0
        i = 0
        while i < len(events):
            t = events[i][0]
            while i < len(events) and events[i][0] == t:
                count += events[i][1]
                i += 1
            if count >= quorum:
                return t
        return -1

    def free_for(self, ids: list[str], start: int, duration: int) -> list[str]:
        end = start + duration
        return sorted(i for i in ids if i in self._people and self._people[i].free(start, end) == [(start, end)])
