"""Reservation book for a restaurant."""


class Restaurant:
    """Every method takes `ts` first: the time of the call, in minutes. Times only ever increase."""

    def __init__(self):
        pass  # your state here

    def add_table(self, ts: int, table_id: str, seats: int) -> bool:
        """Adds a table with `seats` seats. False if table_id exists or seats <= 0."""
        raise NotImplementedError

    def book(self, ts: int, name: str, size: int, slot: int) -> str:
        """Books the smallest free table that fits at `slot`; returns "r1", "r2", ... or "" if none fits."""
        raise NotImplementedError

    def cancel(self, ts: int, reservation_id: str) -> bool:
        """Cancels a reservation, freeing its table. False if unknown or already cancelled."""
        raise NotImplementedError

    def table_of(self, ts: int, reservation_id: str) -> str:
        """The table the reservation holds; "" if unknown or cancelled."""
        raise NotImplementedError

    def party_at(self, ts: int, table_id: str, slot: int) -> str:
        """The name of the party holding the table at `slot`; "" if none."""
        raise NotImplementedError
