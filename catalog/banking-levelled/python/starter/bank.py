class Bank:
    def __init__(self):
        raise NotImplementedError

    def open_account(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def deposit(self, ts: int, id: str, amount: int) -> int | None:
        raise NotImplementedError

    def withdraw(self, ts: int, id: str, amount: int) -> int | None:
        raise NotImplementedError

    def transfer(self, ts: int, from_: str, to: str, amount: int) -> int | None:
        raise NotImplementedError

    def balance(self, ts: int, id: str) -> int | None:
        raise NotImplementedError
