"""Loan servicing for a consumer lender."""


class Lender:
    """Every method takes `day` first: today's date as an integer. Days only ever increase."""

    def __init__(self):
        pass  # your state here

    def originate(self, day: int, loan_id: str, principal: int, months: int, rate_bp: int) -> bool:
        """Lends principal (cents) over `months` monthly instalments at a flat rate_bp per month. False if it can't."""
        raise NotImplementedError

    def schedule(self, day: int, loan_id: str) -> list[str]:
        """Every instalment in order as "due_day:amount"; [] for an unknown loan."""
        raise NotImplementedError

    def amount_due(self, day: int, loan_id: str) -> int:
        """Total still unpaid on instalments due on or before day; -1 for an unknown loan."""
        raise NotImplementedError
