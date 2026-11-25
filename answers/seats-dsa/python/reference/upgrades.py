import heapq


def max_upgrades(cap: list[int], requests: list[list[int]]) -> int:
    # Sweep the legs left to right. A request is taken when its boarding leg comes up. A leg over
    # its free seats drops the taken request that alights latest, since it blocks the most later legs.
    n = len(cap)
    starts = [[] for _ in range(n)]
    for board, alight in requests:
        starts[board].append(alight)
    ends = [0] * (n + 1)  # taken requests alighting at each stop
    taken = []  # max-heap of alight stops (negated)
    active = 0  # taken requests on the current leg
    dropped = 0
    for k in range(n):
        active -= ends[k]
        for alight in starts[k]:
            heapq.heappush(taken, -alight)
            ends[alight] += 1
            active += 1
        while active > cap[k]:
            alight = -heapq.heappop(taken)
            ends[alight] -= 1
            active -= 1
            dropped += 1
    return len(requests) - dropped
