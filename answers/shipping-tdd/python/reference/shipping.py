from dataclasses import dataclass


class NoParcelsError(Exception):
    pass


class UnknownZoneError(Exception):
    pass


class UnknownPromoError(Exception):
    pass


class InvalidParcelError(Exception):
    pass


class TooHeavyError(Exception):
    pass


@dataclass
class Parcel:
    weight_grams: int
    length_cm: int
    width_cm: int
    height_cm: int


@dataclass
class Order:
    parcels: list[Parcel]
    zone: int
    subtotal_cents: int
    express: bool
    promo_code: str


MAX_BILLABLE = 30000
FREE_SHIPPING_MIN = 7500
OVERSIZE_SIDE = 100
OVERSIZE_FEE = 1500
FIRST_KG = [0, 500, 650, 800, 1100]
PER_STEP = [0, 100, 140, 180, 250]


def half_up(num: int, den: int) -> int:
    """num/den rounded half up, for num >= 0."""
    return (num + den // 2) // den


def billable_grams(p: Parcel) -> int:
    if p.weight_grams <= 0 or p.length_cm <= 0 or p.width_cm <= 0 or p.height_cm <= 0:
        raise InvalidParcelError("invalid parcel")
    dim = (p.length_cm * p.width_cm * p.height_cm + 4) // 5
    g = max(p.weight_grams, dim)
    g = (g + 499) // 500 * 500
    if g > MAX_BILLABLE:
        raise TooHeavyError("parcel too heavy")
    return g


def quote(o: Order) -> int:
    if not o.parcels:
        raise NoParcelsError("order has no parcels")
    if o.zone < 1 or o.zone > 4:
        raise UnknownZoneError("unknown zone")
    if o.promo_code != "" and o.promo_code != "SHIP10" and o.promo_code != "FLAT600":
        raise UnknownPromoError("unknown promo code")
    free = o.subtotal_cents >= FREE_SHIPPING_MIN and o.zone <= 3 and not o.express
    total = 0
    for p in o.parcels:
        g = billable_grams(p)
        rate = FIRST_KG[o.zone]
        if g > 1000:
            rate += (g - 1000) // 500 * PER_STEP[o.zone]
        if o.express:
            rate = half_up(rate * 135, 100)
        if free:
            rate = 0
        if max(p.length_cm, p.width_cm, p.height_cm) > OVERSIZE_SIDE:
            rate += OVERSIZE_FEE
        total += rate
    total = total + half_up(total * 85, 1000)
    if o.promo_code == "SHIP10":
        total -= total // 10
    elif o.promo_code == "FLAT600" and not free:
        total = max(total - 600, 0)
    return total
