"""Front desk for a small hotel: rooms with nightly rates, bookings for ranges of nights,
check-in and check-out, and the history of every room's rate."""


class Hotel:
    """Every method takes `day` first: today's date as an integer. Days only ever increase."""

    def __init__(self):
        self.rooms = {}  # room_id -> {"type", "rate", "added", "rates": [(day, rate)]}
        self.bookings = {}  # booking_id -> {"guest", "room", "start", "end", "rate", "status"}
        self.next_id = 0

    def _live(self, day, b):
        """True while booking b still holds its nights: not cancelled and not a no-show."""
        if b["status"] == "cancelled":
            return False
        return not (b["status"] == "booked" and day > b["start"])

    def _free(self, day, room_id, check_in, check_out):
        for b in self.bookings.values():
            if b["room"] == room_id and self._live(day, b) and check_in < b["end"] and b["start"] < check_out:
                return False
        return True

    def _bookable(self, day, room_id, check_in, check_out):
        return (room_id in self.rooms and check_in < check_out and check_in >= day
                and self._free(day, room_id, check_in, check_out))

    # ---------------------------------------------------------------- level 1

    def add_room(self, day: int, room_id: str, room_type: str, rate: int) -> bool:
        if room_id in self.rooms or rate <= 0:
            return False
        self.rooms[room_id] = {"type": room_type, "rate": rate, "added": day, "rates": [(day, rate)]}
        return True

    def book(self, day: int, guest: str, room_id: str, check_in: int, check_out: int) -> str:
        if not self._bookable(day, room_id, check_in, check_out):
            return ""
        self.next_id += 1
        bid = f"b{self.next_id}"
        self.bookings[bid] = {"guest": guest, "room": room_id, "start": check_in, "end": check_out,
                              "rate": self.rooms[room_id]["rate"], "status": "booked"}
        return bid

    def cancel(self, day: int, booking_id: str) -> bool:
        b = self.bookings.get(booking_id)
        if b is None or b["status"] != "booked" or not self._live(day, b):
            return False
        b["status"] = "cancelled"
        return True

    def cost(self, day: int, booking_id: str) -> int:
        b = self.bookings.get(booking_id)
        if b is None or not self._live(day, b):
            return -1
        return (b["end"] - b["start"]) * b["rate"]

    # ---------------------------------------------------------------- level 2

    def available_rooms(self, day: int, room_type: str, check_in: int, check_out: int) -> list[str]:
        ids = [r for r, v in self.rooms.items()
               if v["type"] == room_type and self._bookable(day, r, check_in, check_out)]
        return sorted(ids, key=lambda r: (self.rooms[r]["rate"], r))

    def top_guests(self, day: int, n: int) -> list[str]:
        nights = {}
        for b in self.bookings.values():
            if self._live(day, b):
                nights[b["guest"]] = nights.get(b["guest"], 0) + b["end"] - b["start"]
        order = sorted(nights, key=lambda g: (-nights[g], g))
        return [f"{g}({nights[g]})" for g in order[:n]]

    # ---------------------------------------------------------------- level 3

    def check_in(self, day: int, booking_id: str) -> bool:
        b = self.bookings.get(booking_id)
        if b is None or b["status"] != "booked" or day != b["start"]:
            return False
        b["status"] = "in"
        return True

    def check_out(self, day: int, booking_id: str) -> int:
        b = self.bookings.get(booking_id)
        if b is None or b["status"] != "in":
            return -1
        b["end"] = b["start"] + max(1, min(day, b["end"]) - b["start"])
        b["status"] = "out"
        return (b["end"] - b["start"]) * b["rate"]

    # ---------------------------------------------------------------- level 4

    def set_rate(self, day: int, room_id: str, rate: int) -> bool:
        if room_id not in self.rooms or rate <= 0:
            return False
        self.rooms[room_id]["rate"] = rate
        self.rooms[room_id]["rates"].append((day, rate))
        return True

    def rate_at(self, day: int, room_id: str, at_day: int) -> int:
        room = self.rooms.get(room_id)
        if room is None:
            return -1
        rate = -1
        for d, r in room["rates"]:
            if d <= at_day:
                rate = r
        return rate
