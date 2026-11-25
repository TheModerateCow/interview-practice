"""A multi-storey parking garage: spots of three sizes, vehicles that park and
leave, short reservations, and the stay history behind billing."""

from dataclasses import dataclass, field

# Spot and vehicle sizes, smallest first. A vehicle fits a spot of its size or larger.
_SIZES = {"small": 0, "medium": 1, "large": 2}
# Cents per started hour, by the size of the spot used.
_RATES = [200, 300, 500]


@dataclass
class _Stay:
    """One visit of a plate to a spot; to is -1 while the vehicle is still there."""
    plate: str
    from_: int
    to: int = -1


@dataclass
class _Spot:
    id: str
    size: int
    plate: str = ""
    stays: list = field(default_factory=list)


class Garage:
    """Holds every spot. Timestamps passed to its methods only ever increase."""

    def __init__(self) -> None:
        self._spots: dict[str, _Spot] = {}
        self._parked: dict[str, str] = {}
        self._visits: dict[str, int] = {}
        self._reserved: dict[str, tuple[str, int]] = {}  # plate -> (spot id, expires_at)

    def _free(self, ts: int, s: _Spot) -> bool:
        """True if nobody is parked in s and no live reservation holds it at ts."""
        if s.plate:
            return False
        return not any(sid == s.id and ts < exp for sid, exp in self._reserved.values())

    def _pick(self, ts: int, size: int) -> "_Spot | None":
        """The free spot a vehicle of size would get: smallest fitting size, then lowest id."""
        best = None
        for s in self._spots.values():
            if s.size < size or not self._free(ts, s):
                continue
            if best is None or (s.size, s.id) < (best.size, best.id):
                best = s
        return best

    def add_spot(self, ts: int, spot_id: str, size: str) -> bool:
        if spot_id in self._spots or size not in _SIZES:
            return False
        self._spots[spot_id] = _Spot(spot_id, _SIZES[size])
        return True

    def park(self, ts: int, plate: str, size: str) -> str:
        if size not in _SIZES or plate in self._parked:
            return ""
        r = self._reserved.get(plate)
        s = self._spots[r[0]] if r and ts < r[1] else self._pick(ts, _SIZES[size])
        if s is None:
            return ""
        self._reserved.pop(plate, None)
        s.plate = plate
        s.stays.append(_Stay(plate, ts))
        self._parked[plate] = s.id
        self._visits[plate] = self._visits.get(plate, 0) + 1
        return s.id

    def leave(self, ts: int, plate: str) -> bool:
        sid = self._parked.pop(plate, None)
        if sid is None:
            return False
        s = self._spots[sid]
        s.stays[-1].to = ts
        s.plate = ""
        return True

    def spot_of(self, ts: int, plate: str) -> str:
        return self._parked.get(plate, "")

    def free_spots(self, ts: int, size: str) -> int:
        if size not in _SIZES:
            return -1
        return sum(1 for s in self._spots.values() if s.size == _SIZES[size] and self._free(ts, s))

    def top_visitors(self, ts: int, n: int) -> list[str]:
        plates = sorted(self._visits, key=lambda p: (-self._visits[p], p))
        return [f"{p}({self._visits[p]})" for p in plates[:n]]

    def reserve(self, ts: int, plate: str, size: str, ttl: int) -> str:
        r = self._reserved.get(plate)
        if size not in _SIZES or ttl <= 0 or plate in self._parked or (r and ts < r[1]):
            return ""
        s = self._pick(ts, _SIZES[size])
        if s is None:
            return ""
        self._reserved[plate] = (s.id, ts + ttl)
        return s.id

    def cancel(self, ts: int, plate: str) -> bool:
        r = self._reserved.get(plate)
        if r is None or ts >= r[1]:
            return False
        del self._reserved[plate]
        return True

    def occupant_at(self, ts: int, spot_id: str, at_ts: int) -> str:
        s = self._spots.get(spot_id)
        if s is None:
            return ""
        for st in s.stays:
            if st.from_ <= at_ts and (st.to == -1 or at_ts < st.to):
                return st.plate
        return ""

    def charges(self, ts: int, plate: str) -> int:
        return sum(
            _RATES[s.size] * ((st.to - st.from_ + 59) // 60)
            for s in self._spots.values()
            for st in s.stays
            if st.plate == plate and st.to != -1
        )
