"""Settlement service for a marketplace."""


class Payouts:
    """Every method takes `day` first: today's date as an integer. Days never decrease."""

    def __init__(self):
        pass  # your state here

    def add_merchant(self, day: int, merchant_id: str, fee_bps: int) -> bool:
        """Signs up a merchant paying fee_bps per sale. False if it exists or fee_bps is outside 0..10000."""
        raise NotImplementedError

    def record_sale(self, day: int, merchant_id: str, amount: int) -> str:
        """Records a sale and returns "s1", "s2", ...; "" if the merchant is unknown or amount <= 0."""
        raise NotImplementedError

    def fee(self, day: int, sale_id: str) -> int:
        """The platform's fee on the sale, in cents (half a cent rounds up); -1 if unknown."""
        raise NotImplementedError

    def balance(self, day: int, merchant_id: str) -> int:
        """The sum of the merchant's sale nets (amount minus fee); 0 for an unknown merchant."""
        raise NotImplementedError
