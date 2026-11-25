class UnknownConcessionError(Exception):
    pass


class InvalidTimeError(Exception):
    pass


class InvalidZoneError(Exception):
    pass


def is_peak(time: int) -> bool:
    raise NotImplementedError


def journey_fare(zones: int, peak: bool, concession: str) -> int:
    raise NotImplementedError


class FareCard:
    def __init__(self, concession: str):
        raise NotImplementedError

    def ride(self, time: int, from_zone: int, to_zone: int) -> int:
        raise NotImplementedError
