"""A smart-meter platform's home-battery fleet: tariffs, recorded actions, daily reports and best-schedule planning."""

from dataclasses import dataclass, field


@dataclass
class _Day:
    profit: int = 0
    discharged: int = 0


@dataclass
class _Battery:
    capacity: int
    wear: int
    stored: int = 0
    cash: int = 0
    last: tuple[int, int] | None = None  # (day, slot) of the latest recorded action
    days: dict[int, _Day] = field(default_factory=dict)
    limit: int | None = None  # kWh it may discharge per day


class Fleet:
    def __init__(self) -> None:
        self._batteries: dict[str, _Battery] = {}
        self._tariffs: dict[int, list[int]] = {}

    def add_battery(self, id: str, capacity: int, wear: int) -> bool:
        if id in self._batteries:
            return False
        self._batteries[id] = _Battery(capacity, wear)
        return True

    def publish_tariff(self, day: int, prices: list[int]) -> bool:
        if day in self._tariffs:
            return False
        self._tariffs[day] = list(prices)
        return True

    def _act(self, id: str, day: int, slot: int, charging: bool) -> int | None:
        b = self._batteries.get(id)
        prices = self._tariffs.get(day)
        if b is None or prices is None or not 0 <= slot < len(prices):
            return None
        if b.last is not None and (day, slot) <= b.last:
            return None
        d = b.days.get(day) or _Day()
        if charging:
            if b.stored >= b.capacity:
                return None
            b.stored += 1
            gain = -prices[slot]
        else:
            if b.stored == 0 or (b.limit is not None and d.discharged >= b.limit):
                return None
            b.stored -= 1
            d.discharged += 1
            gain = prices[slot] - b.wear
        b.cash += gain
        d.profit += gain
        b.days[day] = d
        b.last = (day, slot)
        return b.stored

    def charge(self, id: str, day: int, slot: int) -> int | None:
        return self._act(id, day, slot, True)

    def discharge(self, id: str, day: int, slot: int) -> int | None:
        return self._act(id, day, slot, False)

    def stored(self, id: str) -> int | None:
        b = self._batteries.get(id)
        return None if b is None else b.stored

    def cash(self, id: str) -> int | None:
        b = self._batteries.get(id)
        return None if b is None else b.cash

    def day_profit(self, id: str, day: int) -> int | None:
        b = self._batteries.get(id)
        if b is None:
            return None
        d = b.days.get(day)
        return d.profit if d else 0

    def top_earners(self, day: int, n: int) -> list[str]:
        profit = {i: self.day_profit(i, day) for i in self._batteries}
        ranked = sorted(profit, key=lambda i: (-profit[i], i))
        return [f"{i}:{profit[i]}" for i in ranked[:n]]

    def best_profit(self, id: str, day: int) -> int | None:
        b = self._batteries.get(id)
        prices = self._tariffs.get(day)
        if b is None or prices is None:
            return None
        n = len(prices)
        cap = min(b.capacity, n)
        lim = n if b.limit is None else min(b.limit, n)
        # best[u][c]: most cash so far holding c kWh after u kWh discharged today. Unreached states are None.
        best: list[list[int | None]] = [[None] * (cap + 1) for _ in range(lim + 1)]
        best[0][0] = 0
        for p in prices:
            nxt: list[list[int | None]] = [row[:] for row in best]  # idle
            for u in range(lim + 1):
                for c in range(cap + 1):
                    v = best[u][c]
                    if v is None:
                        continue
                    if c < cap and (nxt[u][c + 1] is None or v - p > nxt[u][c + 1]):
                        nxt[u][c + 1] = v - p
                    if c > 0 and u < lim and (nxt[u + 1][c - 1] is None or v + p - b.wear > nxt[u + 1][c - 1]):
                        nxt[u + 1][c - 1] = v + p - b.wear
            best = nxt
        return max(v for row in best for v in row if v is not None)

    def set_discharge_limit(self, id: str, kwh: int) -> bool:
        b = self._batteries.get(id)
        if b is None:
            return False
        b.limit = kwh
        return True
