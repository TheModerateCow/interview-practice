"""Settlement: moving available charges from pending to available, minus fees."""

from dataclasses import dataclass, field

from .journal import (
    FEES_ACCOUNT,
    Backdated,
    Entry,
    Posting,
    UnknownMerchant,
    available_account,
    pending_account,
)


@dataclass
class Pricing:
    """What the platform charges a merchant on each settled charge: bps basis points of
    the captured amount, rounded half up to a whole minor unit, plus a fixed fee per
    currency in that currency's minor units."""

    bps: int
    fixed: dict[str, int] = field(default_factory=dict)

    def fee(self, amount: int, cur: str) -> int:
        """The platform fee on one charge of amount minor units in cur."""
        return (amount * self.bps + 5000) // 10000 + self.fixed.get(cur, 0)


@dataclass
class Batch:
    """One settlement of a merchant's charges in one currency."""

    id: str
    merchant: str
    currency: str
    ts: int
    charges: list[str] = field(default_factory=list)  # charge ids, earliest available_on first
    gross: int = 0  # captured minus refunded, over the batch's charges
    fees: int = 0
    net: int = 0  # gross - fees, credited to the merchant's available balance


class SettlementMixin:
    def settle(self, merchant: str, ts: int) -> list[Batch]:
        """Move every charge of merchant whose funds are available at ts from pending to
        available, minus fees, as one batch per currency (sorted by currency code)."""
        pricing = self.merchants.get(merchant)
        if pricing is None:
            raise UnknownMerchant(repr(merchant))
        if ts < self.store.head_ts:
            raise Backdated(f"settle at {ts}")
        due = self.charges.due(merchant, ts)
        groups: dict[str, list] = {}
        for c in due:
            groups.setdefault(c.currency, []).append(c)
        out: list[Batch] = []
        for cur in sorted(groups):
            self.batch_seq += 1
            b = Batch(f"b{self.batch_seq}", merchant, cur, ts)
            for c in groups[cur]:
                b.charges.append(c.id)
                b.gross += c.amount - c.refunded
                b.fees += pricing.fee(c.amount, cur)
                c.batch = b.id
            b.net = b.gross - b.fees
            ps = [p for p in (
                Posting(pending_account(merchant), cur, -b.gross),
                Posting(available_account(merchant), cur, b.net),
                Posting(FEES_ACCOUNT, cur, b.fees),
            ) if p.amount != 0]
            if ps:
                self.post(Entry(ts, ps, "settlement " + b.id))
            out.append(b)
        return out
