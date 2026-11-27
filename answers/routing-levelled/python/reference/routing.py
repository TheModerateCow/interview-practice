"""Delivery routing on a road network: junctions and two-way roads, closures, fastest routes and an electric van."""
import heapq


class _Road:
    def __init__(self, a: str, b: str, minutes: int):
        self.a, self.b, self.minutes = a, b, minutes
        self.open = True
        self.energy = 0


class Network:
    def __init__(self):
        self._roads: dict[str, _Road] = {}
        self._at: dict[str, list[str]] = {}   # junction -> ids of the roads touching it
        self._rate: dict[str, int] = {}        # junction -> minutes per unit at its charger

    # Level 1

    def add_junction(self, ts: int, id: str) -> bool:
        if id in self._at:
            return False
        self._at[id] = []
        return True

    def add_road(self, ts: int, road: str, a: str, b: str, minutes: int) -> bool:
        if road in self._roads or a not in self._at or b not in self._at or a == b:
            return False
        self._roads[road] = _Road(a, b, minutes)
        self._at[a].append(road)
        self._at[b].append(road)
        return True

    def roads_at(self, ts: int, junction: str) -> list[str]:
        out = []
        for rid in sorted(self._at.get(junction, [])):
            r = self._roads[rid]
            if r.open:
                out.append("%s:%s:%d" % (rid, r.b if r.a == junction else r.a, r.minutes))
        return out

    def _next(self, u: str):
        """(other junction, road) for every open road at u."""
        for rid in self._at[u]:
            r = self._roads[rid]
            if r.open:
                yield (r.b if r.a == u else r.a), r

    def _component(self, start: str) -> set[str]:
        seen, todo = {start}, [start]
        while todo:
            u = todo.pop()
            for v, _ in self._next(u):
                if v not in seen:
                    seen.add(v)
                    todo.append(v)
        return seen

    def reachable(self, ts: int, origin: str, dest: str) -> bool:
        if origin not in self._at or dest not in self._at:
            return False
        return dest in self._component(origin)

    # Level 2

    def close_road(self, ts: int, road: str) -> bool:
        r = self._roads.get(road)
        if r is None or not r.open:
            return False
        r.open = False
        return True

    def reopen_road(self, ts: int, road: str) -> bool:
        r = self._roads.get(road)
        if r is None or r.open:
            return False
        r.open = True
        return True

    def reachable_from(self, ts: int, junction: str) -> list[str]:
        if junction not in self._at:
            return []
        return sorted(self._component(junction))

    # Level 3

    def set_minutes(self, ts: int, road: str, minutes: int) -> bool:
        r = self._roads.get(road)
        if r is None:
            return False
        r.minutes = minutes
        return True

    def fastest_route(self, ts: int, origin: str, dest: str) -> int:
        if origin not in self._at or dest not in self._at:
            return -1
        best = {origin: 0}
        heap = [(0, origin)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > best[u]:
                continue
            if u == dest:
                return d
            for v, r in self._next(u):
                nd = d + r.minutes
                if v not in best or nd < best[v]:
                    best[v] = nd
                    heapq.heappush(heap, (nd, v))
        return -1

    # Level 4

    def add_charger(self, ts: int, junction: str, rate: int) -> bool:
        if junction not in self._at or junction in self._rate:
            return False
        self._rate[junction] = rate
        return True

    def set_energy(self, ts: int, road: str, units: int) -> bool:
        r = self._roads.get(road)
        if r is None:
            return False
        r.energy = units
        return True

    def fastest_delivery(self, ts: int, origin: str, dest: str, capacity: int, charge: int) -> int:
        """Fewest minutes over (junction, units in the battery) states. Charging one unit is a move to the state with
        one unit more, so every partial charge is covered."""
        if origin not in self._at or dest not in self._at:
            return -1
        best = {(origin, charge): 0}
        heap = [(0, origin, charge)]
        while heap:
            d, u, b = heapq.heappop(heap)
            if d > best[(u, b)]:
                continue
            if u == dest:
                return d
            moves = [(v, b - r.energy, d + r.minutes) for v, r in self._next(u) if r.energy <= b]
            if u in self._rate and b < capacity:
                moves.append((u, b + 1, d + self._rate[u]))
            for v, nb, nd in moves:
                if (v, nb) not in best or nd < best[(v, nb)]:
                    best[(v, nb)] = nd
                    heapq.heappush(heap, (nd, v, nb))
        return -1
