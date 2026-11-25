"""In-memory scheduling core of an outpatient clinic. Timestamps passed to its methods only ever increase."""

import bisect

GRACE = 10  # minutes after its start that a booked appointment waits before it becomes a no-show
CHECK_IN_OPENS = 30  # minutes before its start that an appointment can be checked in


class _Appt:
    def __init__(self, id, clinician, patient, kind, room, start, end):
        self.id, self.clinician, self.patient, self.kind = id, clinician, patient, kind
        self.room, self.start, self.end = room, start, end
        self.status = "booked"  # booked, checked-in, cancelled, no-show
        self.log: list[str] = []

    def record(self, ts, event):
        self.log.append(f"{ts}:{event}")

    def occupied(self):
        """The (start, end) the appointment holds its clinician and room, or None."""
        if self.status == "cancelled":
            return None
        if self.status == "no-show":
            return self.start, self.start + GRACE
        return self.start, self.end

    def active(self):
        return self.status in ("booked", "checked-in")


class Clinic:
    def __init__(self):
        self.clinicians: set[str] = set()
        self.rooms: list[str] = []  # sorted
        self.types: dict[str, int] = {}
        self.appts: list[_Appt] = []  # in booking order
        self.by_id: dict[str, _Appt] = {}
        self.waiting: dict[str, list[tuple[str, str]]] = {}

    def _free(self, clinician, room, s, e, skip):
        """Whether nothing but skip holds the clinician (or, if room is set, the room) during [s, e)."""
        for a in self.appts:
            if a is skip:
                continue
            o = a.occupied()
            if o is None or not (s < o[1] and o[0] < e):
                continue
            if (room is None and a.clinician == clinician) or (room is not None and a.room == room):
                return False
        return True

    def _place(self, clinician, s, e, skip):
        """The smallest room free during [s, e) if the clinician is free too, else None."""
        if not self._free(clinician, None, s, e, skip):
            return None
        for r in self.rooms:
            if self._free(None, r, s, e, skip):
                return r
        return None

    def _book(self, t, clinician, patient, kind, start):
        d = self.types.get(kind)
        if clinician not in self.clinicians or d is None or start < t:
            return None
        room = self._place(clinician, start, start + d, None)
        if room is None:
            return None
        a = _Appt(f"appt{len(self.appts) + 1}", clinician, patient, kind, room, start, start + d)
        a.record(t, "booked")
        self.appts.append(a)
        self.by_id[a.id] = a
        return a

    def _fill(self, t, clinician, start):
        """Offers a slot starting at start to the clinician's waitlist at time t, first in line first."""
        q = self.waiting.get(clinician, [])
        for i, (patient, kind) in enumerate(q):
            a = self._book(t, clinician, patient, kind, start)
            if a is not None:
                del q[i]
                return a
        return None

    def _settle(self, ts):
        """Turns every booked appointment whose grace period ended by ts into a no-show, in time order."""
        due = sorted((a for a in self.appts if a.status == "booked" and a.start + GRACE <= ts), key=lambda a: a.start)
        for a in due:
            t = a.start + GRACE
            a.status = "no-show"
            a.record(t, "no-show")
            n = self._fill(t, a.clinician, t)
            if n is not None:
                n.status = "checked-in"
                n.record(t, "checked-in")

    # ---------------------------------------------------------------- level 1

    def add_clinician(self, ts: int, id: str) -> bool:
        self._settle(ts)
        if id in self.clinicians:
            return False
        self.clinicians.add(id)
        return True

    def add_room(self, ts: int, id: str) -> bool:
        self._settle(ts)
        i = bisect.bisect_left(self.rooms, id)
        if i < len(self.rooms) and self.rooms[i] == id:
            return False
        self.rooms.insert(i, id)
        return True

    def add_type(self, ts: int, name: str, minutes: int) -> bool:
        self._settle(ts)
        if name in self.types:
            return False
        self.types[name] = minutes
        return True

    def book(self, ts: int, clinician: str, patient: str, kind: str, start: int) -> str | None:
        self._settle(ts)
        a = self._book(ts, clinician, patient, kind, start)
        return None if a is None else a.id

    def cancel(self, ts: int, id: str) -> bool:
        self._settle(ts)
        a = self.by_id.get(id)
        if a is None or a.status != "booked" or ts >= a.start:
            return False
        a.status = "cancelled"
        a.record(ts, "cancelled")
        self._fill(ts, a.clinician, a.start)
        return True

    def appointment(self, ts: int, id: str) -> str | None:
        self._settle(ts)
        a = self.by_id.get(id)
        if a is None:
            return None
        st = "completed" if a.status == "checked-in" and ts >= a.end else a.status
        return f"{a.clinician} {a.patient} {a.kind} {a.room} {a.start}-{a.end} {st}"

    # ---------------------------------------------------------------- level 2

    def schedule(self, ts: int, clinician: str) -> list[str]:
        self._settle(ts)
        mine = sorted((a for a in self.appts if a.clinician == clinician and a.active()), key=lambda a: a.start)
        return [f"{a.id}@{a.start}-{a.end}" for a in mine]

    def busiest_clinicians(self, ts: int, n: int) -> list[str]:
        self._settle(ts)
        mins = {c: 0 for c in self.clinicians}
        for a in self.appts:
            if a.active():
                mins[a.clinician] += a.end - a.start
        ids = sorted(mins, key=lambda c: (-mins[c], c))
        return [f"{c}:{mins[c]}" for c in ids[:n]]

    def next_free(self, ts: int, clinician: str, kind: str, after: int) -> int | None:
        self._settle(ts)
        d = self.types.get(kind)
        if clinician not in self.clinicians or d is None or not self.rooms:
            return None
        lb = max(after, ts)
        cands = {lb}
        for a in self.appts:
            o = a.occupied()
            if o is not None and o[1] > lb:
                cands.add(o[1])
        for s in sorted(cands):
            if self._place(clinician, s, s + d, None) is not None:
                return s
        return None  # unreachable: the last end always fits

    # ---------------------------------------------------------------- level 3

    def check_in(self, ts: int, id: str) -> bool:
        self._settle(ts)
        a = self.by_id.get(id)
        if a is None or a.status != "booked" or ts < a.start - CHECK_IN_OPENS:
            return False
        a.status = "checked-in"
        a.record(ts, "checked-in")
        return True

    def join_waitlist(self, ts: int, patient: str, clinician: str, kind: str) -> bool:
        self._settle(ts)
        if kind not in self.types or clinician not in self.clinicians:
            return False
        q = self.waiting.setdefault(clinician, [])
        if any(p == patient for p, _ in q):
            return False
        q.append((patient, kind))
        return True

    def waitlist(self, ts: int, clinician: str) -> list[str]:
        self._settle(ts)
        return [f"{p}:{k}" for p, k in self.waiting.get(clinician, [])]

    # ---------------------------------------------------------------- level 4

    def reschedule(self, ts: int, id: str, new_start: int) -> bool:
        self._settle(ts)
        a = self.by_id.get(id)
        if a is None or a.status != "booked" or ts >= a.start or new_start < ts:
            return False
        d = a.end - a.start
        room = self._place(a.clinician, new_start, new_start + d, a)
        if room is None:
            return False
        old = a.start
        a.end, a.start, a.room = new_start + d, new_start, room
        a.record(ts, f"rescheduled:{new_start}")
        self._fill(ts, a.clinician, old)
        return True

    def hand_over(self, ts: int, from_clinician: str, to_clinician: str) -> list[str] | None:
        self._settle(ts)
        if from_clinician not in self.clinicians or to_clinician not in self.clinicians or from_clinician == to_clinician:
            return None
        moving = sorted((a for a in self.appts if a.clinician == from_clinician and a.status == "booked"),
                        key=lambda a: a.start)
        clashed = []
        for a in moving:
            if self._free(to_clinician, None, a.start, a.end, a):
                a.clinician = to_clinician
                a.record(ts, f"handed-over:{to_clinician}")
                continue
            a.status = "cancelled"
            a.record(ts, "cancelled")
            clashed.append(a.id)
        dest = self.waiting.setdefault(to_clinician, [])
        for w in self.waiting.pop(from_clinician, []):
            if not any(x[0] == w[0] for x in dest):
                dest.append(w)
        return clashed

    def history(self, ts: int, id: str) -> list[str]:
        self._settle(ts)
        a = self.by_id.get(id)
        return [] if a is None else list(a.log)
