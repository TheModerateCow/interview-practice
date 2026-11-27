"""Card issuer's authorisation service: cards with credit limits, holds that are captured,
voided or expire, refunds and statements, per-category daily limits and frozen cards."""

HOLD_DAYS = 7


class Issuer:
    """Every method takes `day` first: today's date as an integer. Days never decrease."""

    def __init__(self):
        self.cards = {}  # card_id -> {"limit", "frozen", "cat_limits": {category: limit}, "entries": [str]}
        self.auths = {}  # auth_id -> {"card", "category", "amount", "day", "status", "captured", "refunded"}
        self.next_id = 0

    def _status(self, day, a):
        """open, captured, voided or expired: an open hold expires HOLD_DAYS days after approval."""
        if a["status"] == "open" and day >= a["day"] + HOLD_DAYS:
            return "expired"
        return a["status"]

    def _of(self, card_id):
        return [a for a in self.auths.values() if a["card"] == card_id]

    def _held(self, day, card_id):
        return sum(a["amount"] for a in self._of(card_id) if self._status(day, a) == "open")

    def _posted(self, card_id):
        return sum(a["captured"] - a["refunded"] for a in self._of(card_id))

    def _spent(self, day, card_id, category):
        """Today's spending in a category: open holds at their amount, captures at what was captured."""
        total = 0
        for a in self._of(card_id):
            if a["category"] == category and a["day"] == day:
                s = self._status(day, a)
                if s == "open":
                    total += a["amount"]
                elif s == "captured":
                    total += a["captured"]
        return total

    # ---------------------------------------------------------------- level 1

    def issue_card(self, day: int, card_id: str, limit: int) -> bool:
        if card_id in self.cards or limit <= 0:
            return False
        self.cards[card_id] = {"limit": limit, "frozen": False, "cat_limits": {}, "entries": []}
        return True

    def authorize(self, day: int, card_id: str, category: str, amount: int) -> str:
        c = self.cards.get(card_id)
        if c is None or c["frozen"] or amount <= 0 or amount > self.available(day, card_id):
            return ""
        cap = c["cat_limits"].get(category)
        if cap is not None and self._spent(day, card_id, category) + amount > cap:
            return ""
        self.next_id += 1
        aid = f"a{self.next_id}"
        self.auths[aid] = {"card": card_id, "category": category, "amount": amount, "day": day,
                           "status": "open", "captured": 0, "refunded": 0}
        return aid

    def capture(self, day: int, auth_id: str, amount: int) -> bool:
        a = self.auths.get(auth_id)
        if a is None or self._status(day, a) != "open" or amount <= 0 or amount > a["amount"]:
            return False
        a["status"] = "captured"
        a["captured"] = amount
        self.cards[a["card"]]["entries"].append(f"{day}:{auth_id}:charge:{amount}")
        return True

    def void_auth(self, day: int, auth_id: str) -> bool:
        a = self.auths.get(auth_id)
        if a is None or self._status(day, a) != "open":
            return False
        a["status"] = "voided"
        return True

    def available(self, day: int, card_id: str) -> int:
        c = self.cards.get(card_id)
        if c is None:
            return -1
        return c["limit"] - self._posted(card_id) - self._held(day, card_id)

    # ---------------------------------------------------------------- level 2

    def holds(self, day: int, card_id: str) -> list[str]:
        return [f"{aid}:{a['amount']}" for aid, a in self.auths.items()
                if a["card"] == card_id and self._status(day, a) == "open"]

    def auth_status(self, day: int, auth_id: str) -> str:
        a = self.auths.get(auth_id)
        return "" if a is None else self._status(day, a)

    # ---------------------------------------------------------------- level 3

    def refund(self, day: int, auth_id: str, amount: int) -> bool:
        a = self.auths.get(auth_id)
        if a is None or a["status"] != "captured" or amount <= 0 or amount > a["captured"] - a["refunded"]:
            return False
        a["refunded"] += amount
        self.cards[a["card"]]["entries"].append(f"{day}:{auth_id}:refund:{amount}")
        return True

    def balance(self, day: int, card_id: str) -> int:
        return self._posted(card_id) if card_id in self.cards else -1

    def statement(self, day: int, card_id: str) -> list[str]:
        c = self.cards.get(card_id)
        return [] if c is None else list(c["entries"])

    # ---------------------------------------------------------------- level 4

    def set_category_limit(self, day: int, card_id: str, category: str, limit: int) -> bool:
        c = self.cards.get(card_id)
        if c is None or limit < 0:
            return False
        c["cat_limits"][category] = limit
        return True

    def freeze(self, day: int, card_id: str) -> bool:
        c = self.cards.get(card_id)
        if c is None or c["frozen"]:
            return False
        c["frozen"] = True
        return True

    def unfreeze(self, day: int, card_id: str) -> bool:
        c = self.cards.get(card_id)
        if c is None or not c["frozen"]:
            return False
        c["frozen"] = False
        return True
