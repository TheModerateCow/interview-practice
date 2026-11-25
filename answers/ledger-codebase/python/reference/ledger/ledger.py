"""The Ledger service the payment flows call. Not safe for concurrent use."""

import dataclasses

from .charges import ChargeBook
from .journal import Backdated, Duplicate, Entry, Invalid
from .payments import PaymentsMixin
from .payouts import PayoutsMixin
from .settlement import Pricing, SettlementMixin
from .store import Line, Store


class Ledger(PaymentsMixin, PayoutsMixin, SettlementMixin):
    def __init__(self) -> None:
        self.store = Store()
        self.charges = ChargeBook()
        self.merchants: dict[str, Pricing] = {}
        self.batch_seq = 0

    def add_merchant(self, merchant_id: str, pricing: Pricing) -> None:
        """Onboard a merchant with its pricing."""
        if not merchant_id or pricing.bps < 0:
            raise Invalid(f"merchant {merchant_id!r}")
        if merchant_id in self.merchants:
            raise Duplicate(f"merchant {merchant_id!r}")
        self.merchants[merchant_id] = pricing

    def post(self, e: Entry) -> Entry:
        """Validate and book a journal entry. Entries must arrive in time order."""
        e.validate()
        if e.ts < self.store.head_ts:
            raise Backdated(f"entry at {e.ts}")
        return self.store.append(dataclasses.replace(e, postings=list(e.postings)))

    def balance(self, account: str, cur: str) -> int:
        """The current balance of account in cur."""
        return self.store.balance((account, cur))

    def balance_at(self, account: str, cur: str, ts: int) -> int:
        """The balance of account in cur as of time ts (inclusive)."""
        return self.store.balance_at((account, cur), ts)

    def statement(self, account: str, cur: str, start: int, end: int) -> list[Line]:
        """The account's lines with start <= ts <= end, newest first, as the merchant
        dashboard shows them."""
        lines = self.store.history((account, cur))
        lines.reverse()
        return [x for x in lines if start <= x.ts <= end]

    def trial_balance(self, cur: str) -> int:
        """Sum of every account's balance in cur. A healthy ledger always returns 0."""
        return sum(self.store.balance(b) for b in self.store.lines if b[1] == cur)
