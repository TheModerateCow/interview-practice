"""Multi-currency wallets: balances per currency, published exchange rates with a fee,
rate history with expiry, and standing conversion orders."""

SCALE = 1_000_000  # a rate of 920_000 means 1 minor unit of source buys 0.92 minor units of target
FEE_PERCENT = 1
RATE_TTL = 100  # a rate published at t is in force until t + RATE_TTL (exclusive)


def _code(c):
    return len(c) == 3 and all("A" <= ch <= "Z" for ch in c)


class Wallets:
    """Every method takes `ts` first: the time of the call. Timestamps only ever increase."""

    def __init__(self):
        self.wallets = {}  # wallet_id -> {currency: amount}
        self.rates = {}  # (source, target) -> [(ts, rate)], oldest first
        self.orders = {}  # order_id -> {"wallet", "source", "target", "amount", "min_rate", "status"}

    def _rate_at(self, source, target, at_ts):
        rate = -1
        for t, r in self.rates.get((source, target), []):
            if t <= at_ts:
                rate = r if at_ts < t + RATE_TTL else -1
        return rate

    def _quote(self, source, target, amount, at_ts):
        if not (_code(source) and _code(target)) or source == target or amount <= 0:
            return -1
        rate = self._rate_at(source, target, at_ts)
        if rate < 0:
            return -1
        d = SCALE * 100
        return (amount * rate * (100 - FEE_PERCENT) + d // 2) // d

    # ---------------------------------------------------------------- level 1

    def open_wallet(self, ts: int, wallet_id: str) -> bool:
        if wallet_id in self.wallets:
            return False
        self.wallets[wallet_id] = {}
        return True

    def deposit(self, ts: int, wallet_id: str, currency: str, amount: int) -> int:
        w = self.wallets.get(wallet_id)
        if w is None or not _code(currency) or amount <= 0:
            return -1
        w[currency] = w.get(currency, 0) + amount
        return w[currency]

    def withdraw(self, ts: int, wallet_id: str, currency: str, amount: int) -> int:
        w = self.wallets.get(wallet_id)
        if w is None or amount <= 0 or w.get(currency, 0) < amount:
            return -1
        w[currency] -= amount
        return w[currency]

    def balance(self, ts: int, wallet_id: str, currency: str) -> int:
        w = self.wallets.get(wallet_id)
        return -1 if w is None else w.get(currency, 0)

    def holdings(self, ts: int, wallet_id: str) -> list[str]:
        w = self.wallets.get(wallet_id, {})
        return [f"{c}:{a}" for c, a in sorted(w.items()) if a > 0]

    # ---------------------------------------------------------------- level 2

    def set_rate(self, ts: int, source: str, target: str, rate: int) -> bool:
        if not (_code(source) and _code(target)) or source == target or rate <= 0:
            return False
        self.rates.setdefault((source, target), []).append((ts, rate))
        for o in self.orders.values():  # dict keeps creation order
            if o["status"] == "open" and o["source"] == source and o["target"] == target and rate >= o["min_rate"]:
                got = self.convert(ts, o["wallet"], source, target, o["amount"])
                o["status"] = "cancelled" if got < 0 else f"filled:{got}"
        return True

    def quote(self, ts: int, source: str, target: str, amount: int) -> int:
        return self._quote(source, target, amount, ts)

    def convert(self, ts: int, wallet_id: str, source: str, target: str, amount: int) -> int:
        w = self.wallets.get(wallet_id)
        got = self._quote(source, target, amount, ts)
        if w is None or got <= 0 or w.get(source, 0) < amount:
            return -1
        w[source] -= amount
        w[target] = w.get(target, 0) + got
        return got

    def transfer(self, ts: int, sender: str, receiver: str, currency: str, amount: int) -> bool:
        s, r = self.wallets.get(sender), self.wallets.get(receiver)
        if s is None or r is None or sender == receiver or amount <= 0 or s.get(currency, 0) < amount:
            return False
        s[currency] -= amount
        r[currency] = r.get(currency, 0) + amount
        return True

    # ---------------------------------------------------------------- level 3

    def quote_at(self, ts: int, source: str, target: str, amount: int, at_ts: int) -> int:
        return self._quote(source, target, amount, at_ts)

    def total_value(self, ts: int, wallet_id: str, currency: str) -> int:
        w = self.wallets.get(wallet_id)
        if w is None or not _code(currency):
            return -1
        total = 0
        for c, a in w.items():
            if a == 0:
                continue
            v = a if c == currency else self._quote(c, currency, a, ts)
            if v < 0:
                return -1
            total += v
        return total

    # ---------------------------------------------------------------- level 4

    def place_order(self, ts: int, wallet_id: str, source: str, target: str, amount: int, min_rate: int) -> str:
        if (wallet_id not in self.wallets or not (_code(source) and _code(target)) or source == target
                or amount <= 0 or min_rate <= 0):
            return ""
        oid = f"o{len(self.orders) + 1}"
        self.orders[oid] = {"wallet": wallet_id, "source": source, "target": target, "amount": amount,
                            "min_rate": min_rate, "status": "open"}
        return oid

    def cancel_order(self, ts: int, order_id: str) -> bool:
        o = self.orders.get(order_id)
        if o is None or o["status"] != "open":
            return False
        o["status"] = "cancelled"
        return True

    def order_status(self, ts: int, order_id: str) -> str:
        o = self.orders.get(order_id)
        return "" if o is None else o["status"]
