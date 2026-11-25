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
        raise NotImplementedError
