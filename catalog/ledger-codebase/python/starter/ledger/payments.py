"""Captures and refunds."""

import dataclasses

from .charges import HOLDS, Charge
from .journal import (
    CLEARING_ACCOUNT,
    Duplicate,
    Entry,
    Invalid,
    NotFound,
    Posting,
    UnknownMerchant,
    available_account,
    pending_account,
)


class PaymentsMixin:
    def capture(self, charge_id: str, merchant: str, cur: str, amount: int, method: str, ts: int) -> Charge:
        """Book a captured payment: the platform is now owed amount by the card network
        or bank (clearing), and owes it to the merchant once it settles (pending)."""
        if merchant not in self.merchants:
            raise UnknownMerchant(repr(merchant))
        hold = HOLDS.get(method)
        if hold is None or amount <= 0 or not charge_id:
            raise Invalid(f"capture {charge_id!r}")
        if self.charges.get(charge_id) is not None:
            raise Duplicate(f"charge {charge_id!r}")
        self.post(Entry(ts, [Posting(CLEARING_ACCOUNT, cur, -amount), Posting(pending_account(merchant), cur, amount)],
                        "capture " + charge_id))
        c = Charge(charge_id, merchant, cur, method, amount, ts, ts + hold)
        self.charges.add(c)
        return dataclasses.replace(c)

    def refund(self, charge_id: str, amount: int, ts: int) -> None:
        """Send amount of a charge back to the customer. Before the charge settles the
        money comes out of the merchant's pending balance; after, out of available, which
        may go negative. Fees are not returned."""
        c = self.charges.get(charge_id)
        if c is None:
            raise NotFound(f"charge {charge_id!r}")
        if amount <= 0 or amount > c.amount - c.refunded:
            raise Invalid(f"refund {amount} of {charge_id!r}")
        source = pending_account(c.merchant)
        if c.batch != "":
            source = available_account(c.merchant)
        self.post(Entry(ts, [Posting(source, c.currency, -amount), Posting(CLEARING_ACCOUNT, c.currency, amount)],
                        "refund " + charge_id))
        c.refunded += amount

    def charge(self, charge_id: str) -> Charge | None:
        """A copy of the charge with this id, or None."""
        c = self.charges.get(charge_id)
        return None if c is None else dataclasses.replace(c)
