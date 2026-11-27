"""Reservation book for a restaurant: tables with seat counts, reservations per seating slot, a walk-in waitlist,
joined tables for large parties, and no-shows with a booking ban for repeat offenders."""

GRACE = 15  # minutes after its slot an unseated reservation is still held
BAN = 1440  # minutes a repeat no-show can't book ahead


class Restaurant:
    """Every method takes `ts` first: the time of the call, in minutes. Times only ever increase."""

    def __init__(self):
        self.tables = {}  # table_id -> seats
        self.links = set()  # (lower id, higher id) pairs that can be pushed together
        self.res = {}  # reservation_id -> {"name", "size", "slot", "tables": tuple, "status"}
        self.waiting = {}  # slot -> [(name, size)], front first
        self.next_id = 0

    def _live(self, ts, r):
        """True while reservation r holds its tables: not cancelled and not a no-show."""
        if r["status"] == "cancelled":
            return False
        return not (r["status"] == "booked" and ts >= r["slot"] + GRACE)

    def _taken(self, ts, slot):
        return {t for r in self.res.values() if r["slot"] == slot and self._live(ts, r) for t in r["tables"]}

    def _fit(self, ts, size, slot):
        """The tables the booking rule gives a party of `size` at `slot`, or None."""
        taken = self._taken(ts, slot)
        singles = [(seats, t) for t, seats in self.tables.items() if t not in taken and seats >= size]
        if singles:
            return (min(singles)[1],)
        pairs = [
            (self.tables[a] + self.tables[b], a, b)
            for a, b in self.links
            if a not in taken and b not in taken and self.tables[a] + self.tables[b] >= size
        ]
        if pairs:
            _, a, b = min(pairs)
            return (a, b)
        return None

    def _add(self, name, size, slot, tables):
        self.next_id += 1
        rid = f"r{self.next_id}"
        self.res[rid] = {"name": name, "size": size, "slot": slot, "tables": tables, "status": "booked"}
        return rid

    def _walk(self, ts, slot):
        """Books every waiting party at `slot` that now fits, front first."""
        keep = []
        for name, size in self.waiting.get(slot, []):
            tables = self._fit(ts, size, slot)
            if tables:
                self._add(name, size, slot, tables)
            else:
                keep.append((name, size))
        self.waiting[slot] = keep

    def _no_show_times(self, ts, name):
        return [
            r["slot"] + GRACE
            for r in self.res.values()
            if r["name"] == name and r["status"] == "booked" and ts >= r["slot"] + GRACE
        ]

    # ---------------------------------------------------------------- level 1

    def add_table(self, ts: int, table_id: str, seats: int) -> bool:
        if table_id in self.tables or seats <= 0:
            return False
        self.tables[table_id] = seats
        return True

    def book(self, ts: int, name: str, size: int, slot: int) -> str:
        if size <= 0 or ts >= slot + GRACE:
            return ""
        times = self._no_show_times(ts, name)
        if len(times) >= 2 and ts < max(times) + BAN:
            return ""
        tables = self._fit(ts, size, slot)
        return self._add(name, size, slot, tables) if tables else ""

    def cancel(self, ts: int, reservation_id: str) -> bool:
        r = self.res.get(reservation_id)
        if r is None or r["status"] != "booked" or not self._live(ts, r):
            return False
        r["status"] = "cancelled"
        self._walk(ts, r["slot"])
        return True

    def table_of(self, ts: int, reservation_id: str) -> str:
        r = self.res.get(reservation_id)
        if r is None or not self._live(ts, r):
            return ""
        return "+".join(r["tables"])

    def party_at(self, ts: int, table_id: str, slot: int) -> str:
        for r in self.res.values():
            if r["slot"] == slot and table_id in r["tables"] and self._live(ts, r):
                return r["name"]
        return ""

    # ---------------------------------------------------------------- level 2

    def join_waitlist(self, ts: int, name: str, size: int, slot: int) -> bool:
        queue = self.waiting.setdefault(slot, [])
        if size <= 0 or ts >= slot + GRACE or any(n == name for n, _ in queue):
            return False
        tables = self._fit(ts, size, slot)
        if tables:
            self._add(name, size, slot, tables)
        else:
            queue.append((name, size))
        return True

    def waitlist(self, ts: int, slot: int) -> list[str]:
        return [f"{n}({s})" for n, s in self.waiting.get(slot, [])]

    def free_tables(self, ts: int, slot: int) -> list[str]:
        taken = self._taken(ts, slot)
        return sorted((t for t in self.tables if t not in taken), key=lambda t: (self.tables[t], t))

    # ---------------------------------------------------------------- level 3

    def link_tables(self, ts: int, table_a: str, table_b: str) -> bool:
        pair = (min(table_a, table_b), max(table_a, table_b))
        if table_a not in self.tables or table_b not in self.tables or table_a == table_b or pair in self.links:
            return False
        self.links.add(pair)
        return True

    # ---------------------------------------------------------------- level 4

    def seat(self, ts: int, reservation_id: str) -> bool:
        r = self.res.get(reservation_id)
        if r is None or r["status"] != "booked" or not self._live(ts, r):
            return False
        r["status"] = "seated"
        return True

    def no_shows(self, ts: int, name: str) -> int:
        return len(self._no_show_times(ts, name))
