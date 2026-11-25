import heapq
from dataclasses import dataclass


@dataclass
class Road:
    a: int
    b: int
    minutes: int
    energy: int


def fastest_delivery(n: int, capacity: int, charge: int, rate: list[int], roads: list[Road]) -> int:
    """Dijkstra over (junction, battery) states: n * (capacity + 1) states; charging one unit at a time
    covers every partial charge. O(states log states + roads * capacity)."""
    adj: list[list[tuple[int, int, int]]] = [[] for _ in range(n)]
    for r in roads:
        adj[r.a].append((r.b, r.minutes, r.energy))
        adj[r.b].append((r.a, r.minutes, r.energy))
    w = capacity + 1
    dist = [-1] * (n * w)
    heap: list[tuple[int, int]] = []

    def push(s: int, d: int) -> None:
        if dist[s] == -1 or d < dist[s]:
            dist[s] = d
            heapq.heappush(heap, (d, s))

    push(charge, 0)
    while heap:
        d, s = heapq.heappop(heap)
        if d != dist[s]:
            continue
        u, b = divmod(s, w)
        if u == n - 1:
            return d
        if rate[u] > 0 and b < capacity:
            push(u * w + b + 1, d + rate[u])
        for v, minutes, energy in adj[u]:
            if b >= energy:
                push(v * w + b - energy, d + minutes)
    return -1
