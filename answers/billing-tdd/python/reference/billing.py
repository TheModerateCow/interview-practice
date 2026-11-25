class UnknownPlanError(Exception):
    pass


class UnknownCycleError(Exception):
    pass


class InvalidSeatsError(Exception):
    pass


class OutsidePeriodError(Exception):
    pass


MAX_SEATS = 500

# Per-seat price of one period, in cents.
PRICES = {
    "monthly": {"starter": 1_299, "team": 2_499, "business": 5_999},
    "annual": {"starter": 12_990, "team": 24_990, "business": 59_990},
}
CYCLE_DAYS = {"monthly": 30, "annual": 360}


def _check(cycle: str, plan: str, seats: int) -> None:
    if plan not in PRICES[cycle]:
        raise UnknownPlanError(plan)
    if seats < 1 or seats > MAX_SEATS:
        raise InvalidSeatsError(seats)


class Subscription:
    def __init__(self):
        self.cycle = self.plan = None
        self.seats = self.start_day = self.end = self._credit = 0

    def start(self, day: int, plan: str, cycle: str, seats: int) -> None:
        if cycle not in CYCLE_DAYS:
            raise UnknownCycleError(cycle)
        _check(cycle, plan, seats)
        self.cycle, self.plan, self.seats = cycle, plan, seats
        self.start_day, self.end, self._credit = day, day + CYCLE_DAYS[cycle], 0

    def period_price(self) -> int:
        return PRICES[self.cycle][self.plan] * self.seats

    def period_end(self) -> int:
        return self.end

    def credit(self) -> int:
        return self._credit

    def _pay(self, amount: int) -> int:
        """Apply credit to a charge and return what is left to charge."""
        used = min(amount, self._credit)
        self._credit -= used
        return amount - used

    def change(self, day: int, plan: str, seats: int) -> int:
        if day < self.start_day or day >= self.end:
            raise OutsidePeriodError(day)
        _check(self.cycle, plan, seats)
        old = self.period_price()
        self.plan, self.seats = plan, seats
        diff, left, length = self.period_price() - old, self.end - day, self.end - self.start_day
        if diff > 0:
            return self._pay((diff * left + length // 2) // length)
        self._credit += (-diff) * left // length
        return 0

    def renew(self) -> int:
        length = self.end - self.start_day
        self.start_day, self.end = self.end, self.end + length
        return self._pay(self.period_price())
