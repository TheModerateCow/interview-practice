class UnknownPlanError(Exception):
    pass


class UnknownCycleError(Exception):
    pass


class InvalidSeatsError(Exception):
    pass


class OutsidePeriodError(Exception):
    pass


class Subscription:
    def __init__(self):
        raise NotImplementedError

    def start(self, day: int, plan: str, cycle: str, seats: int) -> None:
        raise NotImplementedError

    def period_price(self) -> int:
        raise NotImplementedError

    def period_end(self) -> int:
        raise NotImplementedError

    def credit(self) -> int:
        raise NotImplementedError

    def change(self, day: int, plan: str, seats: int) -> int:
        raise NotImplementedError

    def renew(self) -> int:
        raise NotImplementedError
