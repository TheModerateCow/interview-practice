SILVER_FROM = 50_000  # lifetime spend in cents
GOLD_FROM = 200_000
CAP_PER_BUY = 500  # points
LIFETIME_DAYS = 365


class InvalidAmountError(Exception):
    pass


class InsufficientPointsError(Exception):
    pass


def _tier_of(spent: int) -> str:
    if spent >= GOLD_FROM:
        return "gold"
    if spent >= SILVER_FROM:
        return "silver"
    return "base"


def _rate(spent: int) -> int:
    return {"gold": 150, "silver": 125}.get(_tier_of(spent), 100)


def _usable(lot: list, day: int) -> bool:
    return day < lot[0] + LIFETIME_DAYS


class Account:
    def __init__(self):
        self.spent = 0  # lifetime spend in cents
        self.lots: list[list[int]] = []  # [day, points], oldest first, minus what was redeemed

    def tier(self) -> str:
        return _tier_of(self.spent)

    def earn(self, day: int, spend_cents: int) -> int:
        if spend_cents <= 0:
            raise InvalidAmountError("amount must be positive")
        pts = (spend_cents * _rate(self.spent) + 5_000) // 10_000
        pts = min(pts, CAP_PER_BUY)
        self.spent += spend_cents
        if pts > 0:
            self.lots.append([day, pts])
        return pts

    def balance(self, day: int) -> int:
        return sum(l[1] for l in self.lots if _usable(l, day))

    def redeem(self, day: int, points: int) -> None:
        if points <= 0:
            raise InvalidAmountError("amount must be positive")
        if points > self.balance(day):
            raise InsufficientPointsError("not enough points")
        for l in self.lots:
            if points == 0:
                break
            if not _usable(l, day):
                continue
            take = min(points, l[1])
            l[1] -= take
            points -= take
