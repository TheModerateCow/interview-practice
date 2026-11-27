"""One instrument's order book: resting orders, queue priority, sweeps and limit orders matched by price and time."""

import bisect
from collections import OrderedDict


class _Order:
    __slots__ = ("id", "side", "price", "left", "filled", "state")

    def __init__(self, id: str, side: str, price: int, qty: int) -> None:
        self.id, self.side, self.price, self.left = id, side, price, qty
        self.filled = 0
        self.state = "open"


class _Side:
    """One side of the book. keys holds each price level's sort key, best first (asks: price; bids: -price)."""

    def __init__(self, desc: bool) -> None:
        self.desc = desc
        self.keys: list[int] = []
        self.levels: dict[int, OrderedDict[str, _Order]] = {}  # price -> orders in queue order
        self.shares: dict[int, int] = {}  # price -> shares resting

    def key(self, price: int) -> int:
        return -price if self.desc else price

    def price(self, i: int) -> int:
        return self.key(self.keys[i])

    def best(self) -> int | None:
        return self.price(0) if self.keys else None

    def add(self, o: _Order) -> None:
        lv = self.levels.get(o.price)
        if lv is None:
            lv = self.levels[o.price] = OrderedDict()
            self.shares[o.price] = 0
            bisect.insort(self.keys, self.key(o.price))
        lv[o.id] = o
        self.shares[o.price] += o.left

    def remove(self, o: _Order) -> None:
        lv = self.levels[o.price]
        del lv[o.id]
        self.shares[o.price] -= o.left
        if not lv:
            self.drop(o.price)

    def drop(self, price: int) -> None:
        del self.levels[price]
        del self.shares[price]
        del self.keys[bisect.bisect_left(self.keys, self.key(price))]

    def take(self, qty: int, limit: int | None) -> tuple[int, int]:
        """Fills up to qty from the best level on, stopping at levels worse than limit. -> (shares, cost)."""
        got = cost = 0
        while qty > 0 and self.keys and (limit is None or self.keys[0] <= self.key(limit)):
            p = self.price(0)
            lv = self.levels[p]
            while qty > 0 and lv:
                o = next(iter(lv.values()))
                t = min(o.left, qty)
                o.left -= t
                o.filled += t
                self.shares[p] -= t
                qty -= t
                got += t
                cost += t * p
                if o.left == 0:
                    o.state = "filled"
                    del lv[o.id]
            if not lv:
                self.drop(p)
        return got, cost


class OrderBook:
    def __init__(self) -> None:
        self._orders: dict[str, _Order] = {}  # every id ever used
        self._asks = _Side(desc=False)
        self._bids = _Side(desc=True)

    def _side(self, o: _Order) -> _Side:
        return self._asks if o.side == "sell" else self._bids

    def _resting(self, order_id: str) -> _Order | None:
        o = self._orders.get(order_id)
        return o if o is not None and o.state == "open" else None

    # ---- level 1 ----
    def add_order(self, order_id: str, price: int, qty: int) -> bool:
        return self.submit(order_id, "sell", price, qty) is not None

    def cancel_order(self, order_id: str) -> bool:
        o = self._resting(order_id)
        if o is None:
            return False
        self._side(o).remove(o)
        o.state = "cancelled"
        return True

    def best_ask(self) -> int | None:
        return self._asks.best()

    def depth_at(self, price: int) -> int:
        return self._asks.shares.get(price, 0) + self._bids.shares.get(price, 0)

    # ---- level 2 ----
    def amend_order(self, order_id: str, qty: int) -> bool:
        o = self._resting(order_id)
        if o is None:
            return False
        side = self._side(o)
        if qty > o.left:  # more shares: back of the queue
            side.remove(o)
            o.left = qty
            side.add(o)
        else:
            side.shares[o.price] -= o.left - qty
            o.left = qty
        return True

    def queue_at(self, price: int) -> list[str]:
        lv = self._asks.levels.get(price) or self._bids.levels.get(price) or {}
        return ["%s:%d" % (o.id, o.left) for o in lv.values()]

    def top_levels(self, n: int) -> list[str]:
        a = self._asks
        return ["%d:%d:%d" % (p, a.shares[p], len(a.levels[p])) for p in (a.price(i) for i in range(min(n, len(a.keys))))]

    # ---- level 3 ----
    def quote_buy(self, qty: int) -> int | None:
        a = self._asks
        cost = 0
        for k in a.keys:
            p = a.key(k)
            t = min(qty, a.shares[p])
            cost += t * p
            qty -= t
            if qty == 0:
                return cost
        return None

    def market_buy(self, qty: int) -> int:
        return self._asks.take(qty, None)[1]

    # ---- level 4 ----
    def submit(self, order_id: str, side: str, price: int, qty: int) -> int | None:
        if order_id in self._orders:
            return None
        o = self._orders[order_id] = _Order(order_id, side, price, qty)
        opp = self._bids if side == "sell" else self._asks
        got, _ = opp.take(qty, price)
        o.left -= got
        o.filled += got
        if o.left == 0:
            o.state = "filled"
        else:
            self._side(o).add(o)
        return got

    def best_bid(self) -> int | None:
        return self._bids.best()

    def order_status(self, order_id: str) -> str:
        o = self._orders.get(order_id)
        return "" if o is None else "%s:%d" % (o.state, o.filled)
