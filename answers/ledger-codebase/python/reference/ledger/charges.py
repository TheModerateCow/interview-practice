"""Captured charges and the per-merchant queue of unsettled ones."""

import heapq
from dataclasses import dataclass, field

DAY = 86400  # one day in ledger time (seconds)

# How long captured funds wait before they can be settled, by payment method.
HOLDS = {"card": 2 * DAY, "bank": 5 * DAY}


@dataclass
class Charge:
    """One captured payment to a merchant."""

    id: str
    merchant: str
    currency: str
    method: str  # "card" or "bank"
    amount: int  # captured amount, minor units
    captured_at: int
    available_on: int  # captured_at + the method's hold
    refunded: int = 0  # refunded so far, minor units
    batch: str = ""  # settlement batch that paid it out; empty until settled
    seq: int = field(default=0, repr=False)  # capture order


class ChargeBook:
    """Every captured charge by id, plus each merchant's unsettled charges in a min-heap
    keyed on when their funds become available (capture order breaks ties)."""

    def __init__(self) -> None:
        self.by_id: dict[str, Charge] = {}
        self.pending: dict[str, list[tuple[int, int, Charge]]] = {}

    def add(self, c: Charge) -> None:
        c.seq = len(self.by_id)
        self.by_id[c.id] = c
        heapq.heappush(self.pending.setdefault(c.merchant, []), (c.available_on, c.seq, c))

    def get(self, charge_id: str) -> Charge | None:
        return self.by_id.get(charge_id)

    def due(self, merchant: str, ts: int) -> list[Charge]:
        """The merchant's unsettled charges whose funds are available at ts, earliest
        available_on first (capture order breaks ties). Takes them off the pending set."""
        q = self.pending.get(merchant)
        out: list[Charge] = []
        while q and q[0][0] <= ts:
            out.append(heapq.heappop(q)[2])
        return out
