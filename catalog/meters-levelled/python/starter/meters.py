class Fleet:
    def __init__(self):
        raise NotImplementedError

    def add_battery(self, id: str, capacity: int, wear: int) -> bool:
        raise NotImplementedError

    def publish_tariff(self, day: int, prices: list[int]) -> bool:
        raise NotImplementedError

    def charge(self, id: str, day: int, slot: int) -> int | None:
        raise NotImplementedError

    def discharge(self, id: str, day: int, slot: int) -> int | None:
        raise NotImplementedError

    def stored(self, id: str) -> int | None:
        raise NotImplementedError

    def cash(self, id: str) -> int | None:
        raise NotImplementedError
