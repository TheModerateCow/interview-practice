"""Fleet desk for a car-rental company."""


class RentalDesk:
    """Every method takes `ts` first: the time of the call in hours. Timestamps only ever increase."""

    def __init__(self):
        pass  # your state here

    def add_car(self, ts: int, car_id: str, car_class: str, branch: str) -> bool:
        """Adds a car parked at branch. False if car_id exists or car_class is invalid."""
        raise NotImplementedError

    def rent(self, ts: int, customer: str, branch: str, car_class: str, days: int) -> str:
        """Rents the lowest-id free car of car_class at branch for days; returns its id, "" if it can't."""
        raise NotImplementedError

    def return_car(self, ts: int, car_id: str) -> bool:
        """The car comes back to the branch it was rented from. False if it isn't rented."""
        raise NotImplementedError

    def status(self, ts: int, car_id: str) -> str:
        """"available:<branch>", "rented:<customer>", or "" for an unknown car."""
        raise NotImplementedError
