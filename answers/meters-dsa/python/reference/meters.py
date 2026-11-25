"""Best battery profit: dynamic programme over the energy held (0..capacity) as the prices go by."""


def best_battery_profit(prices: list[int], capacity: int, wear: int) -> int:
    # best[c] = most money made so far while holding c kWh. Levels above 0 start unreachable.
    unreachable = -(10**18)
    best = [unreachable] * (capacity + 1)
    best[0] = 0
    for p in prices:
        nxt = [0] * (capacity + 1)
        for c in range(capacity + 1):
            v = best[c]
            if c > 0:
                v = max(v, best[c - 1] - p)
            if c < capacity:
                v = max(v, best[c + 1] + p - wear)
            nxt[c] = v
        best = nxt
    return max(best)
