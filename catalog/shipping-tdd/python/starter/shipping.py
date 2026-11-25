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


def billable_grams(p: Parcel) -> int:
    raise NotImplementedError


def quote(o: Order) -> int:
    raise NotImplementedError
