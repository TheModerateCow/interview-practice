"""An online shop's catalog, shopping carts, promo codes and order history. Timestamps only ever increase."""

# A cart untouched for this many minutes is abandoned.
CART_TTL = 60


class _Product:
    def __init__(self, price: int, stock: int):
        self.price = price
        self.stock = stock
        self.sold = 0


class _Cart:
    def __init__(self):
        self.lines: dict[str, int] = {}
        self.touched = 0
        self.promo: str | None = None


class _Promo:
    def __init__(self, percent: int, min_total: int, expires_at: int):
        self.percent = percent
        self.min_total = min_total
        self.expires_at = expires_at


class _Order:
    def __init__(self, ts: int, total: int, lines: dict[str, int]):
        self.ts = ts
        self.total = total
        self.lines = lines
        self.cancelled = False


class Shop:
    def __init__(self):
        self._products: dict[str, _Product] = {}
        self._carts: dict[str, _Cart] = {}
        self._promos: dict[str, _Promo] = {}
        self._history: dict[str, list[_Order]] = {}

    @staticmethod
    def _live(c: _Cart, ts: int) -> bool:
        return ts < c.touched + CART_TTL

    def _cart(self, ts: int, cart_id: str) -> _Cart | None:
        """The cart if it exists and hasn't been abandoned; an abandoned cart is dropped."""
        c = self._carts.get(cart_id)
        if c is not None and not self._live(c, ts):
            del self._carts[cart_id]
            c = None
        return c

    # ---------------------------------------------------------------- level 1

    def add_product(self, ts: int, sku: str, price_cents: int, stock: int) -> bool:
        if sku in self._products or price_cents <= 0 or stock < 0:
            return False
        self._products[sku] = _Product(price_cents, stock)
        return True

    def add_to_cart(self, ts: int, cart_id: str, sku: str, qty: int) -> bool:
        p = self._products.get(sku)
        if p is None or qty <= 0:
            return False
        c = self._cart(ts, cart_id)
        have = c.lines.get(sku, 0) if c else 0
        if have + qty > p.stock:
            return False
        if c is None:
            c = self._carts[cart_id] = _Cart()
        c.lines[sku] = have + qty
        c.touched = ts
        return True

    def remove_from_cart(self, ts: int, cart_id: str, sku: str, qty: int) -> int:
        c = self._cart(ts, cart_id)
        if c is None or qty <= 0 or sku not in c.lines:
            return -1
        left = max(0, c.lines[sku] - qty)
        if left == 0:
            del c.lines[sku]
        else:
            c.lines[sku] = left
        c.touched = ts
        return left

    def cart_total(self, ts: int, cart_id: str) -> int:
        c = self._cart(ts, cart_id)
        if c is None:
            return 0
        sub = sum(self._products[sku].price * q for sku, q in c.lines.items())
        pr = self._promos.get(c.promo) if c.promo is not None else None
        if pr is not None and ts < pr.expires_at and sub >= pr.min_total:
            sub -= sub * pr.percent // 100
        return sub

    def items(self, ts: int, cart_id: str) -> list[str]:
        c = self._cart(ts, cart_id)
        return [f"{sku}:{c.lines[sku]}" for sku in sorted(c.lines)] if c else []

    # ---------------------------------------------------------------- level 2

    def checkout(self, ts: int, cart_id: str) -> int:
        c = self._cart(ts, cart_id)
        if c is None or not c.lines:
            return -1
        for sku, q in c.lines.items():
            if self._products[sku].stock < q:
                return -1
        total = self.cart_total(ts, cart_id)
        for sku, q in c.lines.items():
            p = self._products[sku]
            p.stock -= q
            p.sold += q
        self._history.setdefault(cart_id, []).append(_Order(ts, total, dict(c.lines)))
        del self._carts[cart_id]
        return total

    def stock_of(self, ts: int, sku: str) -> int:
        p = self._products.get(sku)
        return -1 if p is None else p.stock

    def top_sellers(self, ts: int, n: int) -> list[str]:
        skus = sorted((s for s, p in self._products.items() if p.sold > 0), key=lambda s: (-self._products[s].sold, s))
        return [f"{s}({self._products[s].sold})" for s in skus[:max(n, 0)]]

    # ---------------------------------------------------------------- level 3

    def add_promo(self, ts: int, code: str, percent_off: int, min_total_cents: int, ttl: int) -> bool:
        if code in self._promos or percent_off < 1 or percent_off > 100 or min_total_cents < 0 or ttl <= 0:
            return False
        self._promos[code] = _Promo(percent_off, min_total_cents, ts + ttl)
        return True

    def apply_promo(self, ts: int, cart_id: str, code: str) -> bool:
        c = self._cart(ts, cart_id)
        pr = self._promos.get(code)
        if c is None or not c.lines or pr is None or ts >= pr.expires_at:
            return False
        c.promo = code
        c.touched = ts
        return True

    def active_carts(self, ts: int) -> int:
        return sum(1 for c in self._carts.values() if self._live(c, ts) and c.lines)

    # ---------------------------------------------------------------- level 4

    def merge(self, ts: int, guest_id: str, user_id: str) -> bool:
        if guest_id == user_id:
            return False
        g = self._cart(ts, guest_id)
        if g is None or not g.lines:
            return False
        u = self._cart(ts, user_id)
        if u is None:
            u = self._carts[user_id] = _Cart()
        for sku, add in g.lines.items():
            have = u.lines.get(sku, 0)
            q = max(have, min(have + add, self._products[sku].stock))
            if q > 0:
                u.lines[sku] = q
        up = self._promos.get(u.promo) if u.promo is not None else None
        if up is None or ts >= up.expires_at:
            u.promo = g.promo
        u.touched = ts
        del self._carts[guest_id]
        moved = self._history.pop(guest_id, None)
        if moved is not None:
            h = self._history.setdefault(user_id, [])
            h.extend(moved)
            h.sort(key=lambda o: o.ts)
        return True

    def order_history(self, ts: int, cart_id: str) -> list[str]:
        return [f"{o.ts}:{'cancelled' if o.cancelled else o.total}" for o in self._history.get(cart_id, [])]

    def cancel_order(self, ts: int, cart_id: str, order_ts: int) -> bool:
        for o in self._history.get(cart_id, []):
            if o.ts != order_ts or o.cancelled:
                continue
            for sku, q in o.lines.items():
                p = self._products[sku]
                p.stock += q
                p.sold -= q
            o.cancelled = True
            return True
        return False
