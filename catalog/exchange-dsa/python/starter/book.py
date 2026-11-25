from dataclasses import dataclass


@dataclass
class Event:
    kind: str
    price: int
    qty: int


def run_book(events: list[Event]) -> list[int]:
    raise NotImplementedError
