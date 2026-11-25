from dataclasses import dataclass


@dataclass
class Road:
    a: int
    b: int
    minutes: int
    energy: int


def fastest_delivery(n: int, capacity: int, charge: int, rate: list[int], roads: list[Road]) -> int:
    raise NotImplementedError
