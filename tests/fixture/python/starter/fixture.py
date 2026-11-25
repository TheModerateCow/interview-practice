from dataclasses import dataclass


class InvalidAmountError(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class InvalidWindowError(Exception):
    pass


class WalletFrozenError(Exception):
    pass


class InvalidOwnerError(Exception):
    pass


@dataclass
class Entry:
    account_id: str
    amount_cents: int


def net_by_account(entries: list[Entry]) -> list[Entry]:
    raise NotImplementedError


def max_window(values: list[int], k: int) -> int:
    raise NotImplementedError


def first_negative(values: list[int]) -> int | None:
    raise NotImplementedError


def grid(n: int) -> list[list[int]]:
    raise NotImplementedError


class Wallet:
    def __init__(self, owner: str):
        raise NotImplementedError

    def deposit(self, cents: int) -> None:
        raise NotImplementedError

    def withdraw(self, cents: int) -> int:
        raise NotImplementedError

    def balance(self) -> int:
        raise NotImplementedError

    def owner_name(self) -> str:
        raise NotImplementedError
