"""Front desk for a small hotel."""


class Hotel:
    """Every method takes `day` first: today's date as an integer. Days only ever increase."""

    def __init__(self):
        pass  # your state here

    def add_room(self, day: int, room_id: str, room_type: str, rate: int) -> bool:
        """Adds a room with a nightly rate in cents. False if room_id exists or rate <= 0."""
        raise NotImplementedError

    def book(self, day: int, guest: str, room_id: str, check_in: int, check_out: int) -> str:
        """Books nights check_in .. check_out - 1 and returns "b1", "b2", ...; "" if it can't."""
        raise NotImplementedError

    def cancel(self, day: int, booking_id: str) -> bool:
        """Cancels a booking, freeing its nights. False if unknown or already cancelled."""
        raise NotImplementedError

    def cost(self, day: int, booking_id: str) -> int:
        """Nights times the nightly rate, in cents; -1 if unknown or cancelled."""
        raise NotImplementedError
