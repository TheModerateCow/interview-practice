from dataclasses import dataclass

DAY = 1440


@dataclass
class Attendee:
    """offset: minutes east of UTC (local = UTC + offset). work_start, work_end: local minutes of the day,
    [work_start, work_end), the same every day. busy: UTC blocks [start, end), in any order, may overlap."""

    offset: int
    work_start: int
    work_end: int
    busy: list[list[int]]


def earliest_quorum_slot(attendees: list[Attendee], days: int, duration: int, quorum: int) -> int:
    """Earliest UTC start t with t + duration <= days * 1440 such that at least quorum attendees are free for the
    whole of [t, t + duration); -1 if there is none."""
    horizon = days * DAY
    events: list[tuple[int, int]] = []
    for a in attendees:
        for s, e in free_intervals(a, horizon):
            # a meeting fits for this attendee iff it starts in [s, e - duration]
            if e - s >= duration:
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


def free_intervals(a: Attendee, horizon: int) -> list[tuple[int, int]]:
    """Disjoint, non-touching free intervals in UTC, sorted, inside [0, horizon)."""
    work: list[list[int]] = []
    for d in range(-1, horizon // DAY + 1):
        base = d * DAY - a.offset
        s = max(0, base + a.work_start)
        e = min(horizon, base + a.work_end)
        if s >= e:
            continue
        if work and s <= work[-1][1]:
            work[-1][1] = max(work[-1][1], e)
        else:
            work.append([s, e])
    busy = sorted(a.busy)
    free: list[tuple[int, int]] = []
    lo = 0
    for ws, we in work:
        while lo < len(busy) and busy[lo][1] <= ws:
            lo += 1
        cur = ws
        for i in range(lo, len(busy)):
            bs, be = busy[i]
            if bs >= we:
                break
            if bs > cur:
                free.append((cur, bs))
            cur = max(cur, be)
        if cur < we:
            free.append((cur, we))
    return free
