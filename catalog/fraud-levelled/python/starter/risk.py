"""Transaction risk screen for a payment provider."""


class RiskScreen:
    """Every method takes ts first: the time of the call. Timestamps never go down."""

    def __init__(self):
        pass  # your state here

    def block(self, ts: int, kind: str, value: str) -> bool:
        """Blocks value for kind ("card", "merchant" or "country"). False if the kind is unknown or already blocked."""
        raise NotImplementedError

    def unblock(self, ts: int, kind: str, value: str) -> bool:
        """Takes value off the blocklist for kind. False if it isn't blocked."""
        raise NotImplementedError

    def screen(self, ts: int, txn_id: str, card: str, merchant: str, amount: int, country: str) -> str:
        """Records the transaction and returns "decline" or "approve"; "" if txn_id is taken or amount <= 0."""
        raise NotImplementedError

    def decision(self, ts: int, txn_id: str) -> str:
        """The recorded decision; "" if txn_id was never screened."""
        raise NotImplementedError
