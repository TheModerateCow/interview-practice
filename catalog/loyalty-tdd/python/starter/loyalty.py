class InvalidAmountError(Exception):
    pass


class InsufficientPointsError(Exception):
    pass


class Account:
    def __init__(self):
        raise NotImplementedError

    def earn(self, day: int, spend_cents: int) -> int:
        raise NotImplementedError

    def balance(self, day: int) -> int:
        raise NotImplementedError

    def redeem(self, day: int, points: int) -> None:
        raise NotImplementedError

    def tier(self) -> str:
        raise NotImplementedError
