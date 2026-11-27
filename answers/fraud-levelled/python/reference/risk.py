"""Transaction risk screen for a payment provider: blocklists, velocity rules, rule priorities with an
allowlist, and a manual review queue whose declines block the card for a while."""

KINDS = ("card", "merchant", "country")
OUTCOME = {"block": "decline", "velocity": "review", "allow": "approve"}
STRICTNESS = {"decline": 0, "review": 1, "approve": 2}  # priority ties: the stricter outcome wins


class RiskScreen:
    """Every method takes ts first: the time of the call. Timestamps never go down."""

    def __init__(self):
        # name -> {"type": "block"|"allow"|"velocity", "priority", "until"?, "metric"?, "limit"?, "window"?}
        # names: "block:<kind>:<value>", "allow:<kind>:<value>", or the velocity rule's id (no colon)
        self.rules = {}
        self.txns = {}  # txn_id -> {"ts", "card", "amount", "decision", "rule"}; insertion order = screen order

    def _rule(self, ts, name):
        """The rule called name, or None if there is none or it is a temporary block that has expired."""
        r = self.rules.get(name)
        if r is None or (r.get("until") is not None and ts >= r["until"]):
            return None
        return r

    # ---------------------------------------------------------------- level 1

    def block(self, ts: int, kind: str, value: str) -> bool:
        name = f"block:{kind}:{value}"
        if kind not in KINDS or self._rule(ts, name) is not None:
            return False
        self.rules[name] = {"type": "block", "priority": 0, "until": None}
        return True

    def unblock(self, ts: int, kind: str, value: str) -> bool:
        name = f"block:{kind}:{value}"
        if self._rule(ts, name) is None:
            return False
        del self.rules[name]
        return True

    def screen(self, ts: int, txn_id: str, card: str, merchant: str, amount: int, country: str) -> str:
        if txn_id in self.txns or amount <= 0:
            return ""
        txn = {"ts": ts, "card": card, "amount": amount}
        self.txns[txn_id] = txn
        hits = []  # (priority, name, outcome)
        for kind, value in (("card", card), ("merchant", merchant), ("country", country)):
            for typ in ("block", "allow"):
                name = f"{typ}:{kind}:{value}"
                r = self._rule(ts, name)
                if r is not None:
                    hits.append((r["priority"], name, OUTCOME[typ]))
        same_card = [t for t in self.txns.values() if t["card"] == card]  # includes this one
        for name, r in self.rules.items():
            if r["type"] != "velocity":
                continue
            inside = [t for t in same_card if t["ts"] > ts - r["window"]]
            used = len(inside) if r["metric"] == "count" else sum(t["amount"] for t in inside)
            if used > r["limit"]:
                hits.append((r["priority"], name, "review"))
        if hits:
            _, txn["rule"], txn["decision"] = min(hits, key=lambda h: (-h[0], STRICTNESS[h[2]], h[1]))
        else:
            txn["rule"], txn["decision"] = "", "approve"
        return txn["decision"]

    def decision(self, ts: int, txn_id: str) -> str:
        t = self.txns.get(txn_id)
        return "" if t is None else t["decision"]

    # ---------------------------------------------------------------- level 2

    def add_velocity_rule(self, ts: int, rule_id: str, metric: str, limit: int, window: int) -> bool:
        if rule_id in self.rules or metric not in ("count", "amount") or limit <= 0 or window <= 0:
            return False
        self.rules[rule_id] = {"type": "velocity", "priority": 0, "metric": metric, "limit": limit, "window": window}
        return True

    def remove_rule(self, ts: int, rule_id: str) -> bool:
        r = self.rules.get(rule_id)
        if r is None or r["type"] != "velocity":
            return False
        del self.rules[rule_id]
        return True

    # ---------------------------------------------------------------- level 3

    def allow(self, ts: int, kind: str, value: str, priority: int) -> bool:
        name = f"allow:{kind}:{value}"
        if kind not in KINDS or name in self.rules:
            return False
        self.rules[name] = {"type": "allow", "priority": priority}
        return True

    def set_priority(self, ts: int, rule: str, priority: int) -> bool:
        r = self._rule(ts, rule)
        if r is None:
            return False
        r["priority"] = priority
        return True

    def explain(self, ts: int, txn_id: str) -> str:
        t = self.txns.get(txn_id)
        return "" if t is None else t["rule"]

    # ---------------------------------------------------------------- level 4

    def pending_reviews(self, ts: int) -> list[str]:
        return [i for i, t in self.txns.items() if t["decision"] == "review"]

    def approve_review(self, ts: int, txn_id: str) -> bool:
        t = self.txns.get(txn_id)
        if t is None or t["decision"] != "review":
            return False
        t["decision"], t["rule"] = "approve", "analyst"
        return True

    def decline_review(self, ts: int, txn_id: str, block_for: int) -> bool:
        t = self.txns.get(txn_id)
        if t is None or t["decision"] != "review" or block_for <= 0:
            return False
        t["decision"], t["rule"] = "decline", "analyst"
        name = f"block:card:{t['card']}"
        r = self._rule(ts, name)
        if r is None:
            self.rules[name] = {"type": "block", "priority": 0, "until": ts + block_for}
        elif r["until"] is not None:
            r["until"] = max(r["until"], ts + block_for)
        return True
