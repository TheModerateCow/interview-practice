class Flight:
    def __init__(self, seats: list[int]):
        raise NotImplementedError

    def book(self, passenger: str, board: int, alight: int) -> bool:
        raise NotImplementedError

    def cancel(self, passenger: str) -> bool:
        raise NotImplementedError

    def free_seats(self, leg: int) -> int | None:
        raise NotImplementedError
