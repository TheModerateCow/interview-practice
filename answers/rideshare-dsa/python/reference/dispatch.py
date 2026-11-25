"""Minimum dispatch radius: binary search on R, greedy matching on sorted positions."""


def min_dispatch_radius(riders: list[int], drivers: list[int], need: int) -> int:
    if need <= 0:
        return 0
    if need > len(riders) or need > len(drivers):
        return -1
    r, d = sorted(riders), sorted(drivers)
    lo, hi = 0, max(r[-1], d[-1]) - min(r[0], d[0])
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if _matched(r, d, mid) >= need:
            hi = mid
        else:
            lo = mid + 1
    return lo


def _matched(r: list[int], d: list[int], radius: int) -> int:
    """Most riders served when every pickup is within radius. Both lists sorted; each rider
    takes the leftmost free driver in reach."""
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
