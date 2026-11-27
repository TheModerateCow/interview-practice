"""Multi-currency wallets."""


class Wallets:
    """Every method takes `ts` first: the time of the call. Timestamps only ever increase."""

    def __init__(self):
        pass  # your state here

    def open_wallet(self, ts: int, wallet_id: str) -> bool:
        """Opens an empty wallet. False if wallet_id is already open."""
        raise NotImplementedError

    def deposit(self, ts: int, wallet_id: str, currency: str, amount: int) -> int:
        """Adds amount (minor units) of currency; returns the new balance, -1 if it can't."""
        raise NotImplementedError

    def withdraw(self, ts: int, wallet_id: str, currency: str, amount: int) -> int:
        """Takes amount of currency out; returns the new balance, -1 if it can't."""
        raise NotImplementedError

    def balance(self, ts: int, wallet_id: str, currency: str) -> int:
        """The wallet's balance in currency (0 if it holds none); -1 for an unknown wallet."""
        raise NotImplementedError

    def holdings(self, ts: int, wallet_id: str) -> list[str]:
        """Every currency the wallet holds as "CODE:amount", sorted by code."""
        raise NotImplementedError
