"""Payouts of available funds to the merchant's bank."""

import dataclasses
from dataclasses import dataclass

from .journal import (
    BANK_ACCOUNT,
    IN_TRANSIT_ACCOUNT,
    Duplicate,
    Entry,
    InsufficientFunds,
    Invalid,
    PayoutState,
    Posting,
    available_account,
)


@dataclass
class Payout:
    """A transfer of a merchant's available funds to their bank account. The status is
    "pending" until the bank's webhook says it was "paid" or it "failed"."""

    id: str
    merchant: str
    currency: str
    amount: int
    status: str
    updated_at: int


class PayoutsMixin:
    def request_payout(self, payout_id: str, merchant: str, cur: str, amount: int, ts: int) -> Payout:
        """Move amount from the merchant's available balance to in-transit."""
        if not payout_id or amount <= 0:
            raise Invalid(f"payout {payout_id!r}")
        if payout_id in self.store.payouts:
            raise Duplicate(f"payout {payout_id!r}")
        if self.balance(available_account(merchant), cur) < amount:
            raise InsufficientFunds("insufficient available balance")
        self.post(Entry(ts, [Posting(available_account(merchant), cur, -amount),
                             Posting(IN_TRANSIT_ACCOUNT, cur, amount)], "payout " + payout_id))
        p = Payout(payout_id, merchant, cur, amount, "pending", ts)
        self.store.payouts[payout_id] = p
        return dataclasses.replace(p)

    def payout_paid(self, payout_id: str, ts: int) -> None:
        """The bank's "paid" webhook. The bank retries webhooks, so a repeat of the same
        outcome is accepted and changes nothing."""
        self._finish_payout(payout_id, "paid", ts)

    def payout_failed(self, payout_id: str, ts: int) -> None:
        """The bank's "failed" webhook: the money goes back to available. Repeats are
        accepted and change nothing."""
        self._finish_payout(payout_id, "failed", ts)

    def _finish_payout(self, payout_id: str, to: str, ts: int) -> None:
        def apply(p: Payout) -> None:
            if p.status == to:
                return
            if p.status != "pending":
                raise PayoutState(f"{p.status} payout {payout_id!r} cannot become {to}")
            dest = available_account(p.merchant) if to == "failed" else BANK_ACCOUNT
            self.post(Entry(ts, [Posting(IN_TRANSIT_ACCOUNT, p.currency, -p.amount),
                                 Posting(dest, p.currency, p.amount)], f"payout {payout_id} {to}"))
            p.status, p.updated_at = to, ts

        self.store.update_payout(payout_id, apply)

    def payout(self, payout_id: str) -> Payout | None:
        """A copy of the payout with this id, or None."""
        p = self.store.payouts.get(payout_id)
        return None if p is None else dataclasses.replace(p)
