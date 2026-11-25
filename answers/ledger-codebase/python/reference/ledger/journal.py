"""Double-entry journal types, account names and errors."""

from dataclasses import dataclass, field

from .money import format_amount, valid_currency

# Account names used by the payment flows. Balances are signed: a positive merchant
# balance is money the platform owes that merchant.
CLEARING_ACCOUNT = "platform:clearing"  # funds due from card networks and banks
FEES_ACCOUNT = "platform:fees"  # platform revenue
IN_TRANSIT_ACCOUNT = "platform:payouts-in-transit"  # payouts sent, not yet confirmed by the bank
BANK_ACCOUNT = "platform:bank-paid-out"  # payouts the bank confirmed


def pending_account(merchant: str) -> str:
    """A merchant's captured funds that have not been settled yet."""
    return f"merchant:{merchant}:pending"


def available_account(merchant: str) -> str:
    """A merchant's settled funds, ready to be paid out."""
    return f"merchant:{merchant}:available"


class LedgerError(Exception):
    """Base class of every error the ledger raises."""


class Invalid(LedgerError):
    """invalid request"""


class Unbalanced(LedgerError):
    """entry does not balance"""


class UnknownCurrency(LedgerError):
    """unknown currency"""


class Backdated(LedgerError):
    """entry is older than the ledger head"""


class NotFound(LedgerError):
    """not found"""


class Duplicate(LedgerError):
    """already exists"""


class UnknownMerchant(LedgerError):
    """unknown merchant"""


class InsufficientFunds(LedgerError):
    """insufficient available balance"""


class PayoutState(LedgerError):
    """payout cannot make that transition"""


@dataclass(frozen=True)
class Posting:
    """Moves amount minor units of currency into (positive) or out of (negative) account."""

    account: str
    currency: str
    amount: int


@dataclass
class Entry:
    """One double-entry journal entry. id is assigned when the entry is posted."""

    ts: int
    postings: list[Posting] = field(default_factory=list)
    memo: str = ""
    id: str = ""

    def validate(self) -> None:
        """Check that this is a well-formed double entry: at least two postings, no empty
        accounts or zero amounts, only booked currencies, and debits equal to credits."""
        if len(self.postings) < 2:
            raise Invalid("an entry needs at least two postings")
        sums: dict[str, int] = {}
        for p in self.postings:
            if not p.account or p.amount == 0:
                raise Invalid("empty account or zero amount")
            if not valid_currency(p.currency):
                raise UnknownCurrency(repr(p.currency))
            sums[p.currency] = sums.get(p.currency, 0) + p.amount
        for p in self.postings:
            if sums[p.currency] != 0:
                raise Unbalanced(f"entry does not balance: off by {format_amount(sums[p.currency], p.currency)}")
