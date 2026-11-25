DAY = 1440
TRANSFER_WINDOW = 90
MAX_RIDES = 3
_BASE = (250, 320, 410, 480, 550, 620)  # by number of zones, 1..6
# concession: share of the fare paid, daily cap, weekly cap (cents)
_CONCESSIONS = {"adult": (100, 1200, 4800), "child": (50, 600, 2400), "senior": (70, 840, 3360)}


class UnknownConcessionError(Exception):
    pass


class InvalidTimeError(Exception):
    pass


class InvalidZoneError(Exception):
    pass


def _parse(s) -> tuple:
    if isinstance(s, str) and s.lower() in _CONCESSIONS:
        return _CONCESSIONS[s.lower()]
    raise UnknownConcessionError("unknown concession")


def is_peak(time: int) -> bool:
    """True when a ride at `time` (minutes since Monday 00:00 of week 0) is in a peak window."""
    weekday = (time // DAY) % 7 <= 4
    m = time % DAY
    return weekday and ((420 <= m < 570) or (960 <= m < 1140))


def _journey_fare(zones: int, peak: bool, c: tuple) -> int:
    fare = _BASE[zones - 1]
    if peak:
        fare = (fare * 130 + 999) // 1000 * 10
    return fare * c[0] // 500 * 5


def journey_fare(zones: int, peak: bool, concession: str) -> int:
    """Fare in cents for a journey covering `zones` zones (1-6), after the peak uplift and the concession discount."""
    return _journey_fare(zones, peak, _parse(concession))


class FareCard:
    """One rider's travel card. Rides arrive in time order."""

    def __init__(self, concession: str):
        self._c = _parse(concession)
        self._last_time = -1
        self._rides = 0  # rides in the current journey; 0 = no journey yet
        self._start = self._lo = self._hi = 0
        self._peak = False
        self._by_day = {}
        self._by_week = {}

    def ride(self, time: int, from_zone: int, to_zone: int) -> int:
        """Records a ride and returns the cents charged for it."""
        if time < 0 or time < self._last_time:
            raise InvalidTimeError("invalid time")
        if not (1 <= from_zone <= 6 and 1 <= to_zone <= 6):
            raise InvalidZoneError("invalid zone")
        self._last_time = time

        ride_lo, ride_hi = min(from_zone, to_zone), max(from_zone, to_zone)
        before = 0
        if self._rides > 0 and time - self._start < TRANSFER_WINDOW and self._rides < MAX_RIDES:
            before = _journey_fare(self._hi - self._lo + 1, self._peak, self._c)
            self._lo = min(self._lo, ride_lo)
            self._hi = max(self._hi, ride_hi)
            self._rides += 1
        else:
            self._start = time
            self._peak = is_peak(time)
            self._lo, self._hi = ride_lo, ride_hi
            self._rides = 1
        due = _journey_fare(self._hi - self._lo + 1, self._peak, self._c) - before

        day = (time - 240) // DAY
        week = day // 7
        today, this_week = self._by_day.get(day, 0), self._by_week.get(week, 0)
        charge = max(0, min(due, self._c[1] - today, self._c[2] - this_week))
        self._by_day[day] = today + charge
        self._by_week[week] = this_week + charge
        return charge
