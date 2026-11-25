from dataclasses import dataclass


@dataclass
class Job:
    consumer: int
    cold: int
    warm: int


def fastest_release(jobs: list[Job], k: int) -> int:
    raise NotImplementedError
