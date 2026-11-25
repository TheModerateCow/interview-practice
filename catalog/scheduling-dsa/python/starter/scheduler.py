from dataclasses import dataclass


@dataclass
class Attendee:
    offset: int
    work_start: int
    work_end: int
    busy: list[list[int]]


def earliest_quorum_slot(attendees: list[Attendee], days: int, duration: int, quorum: int) -> int:
    raise NotImplementedError
