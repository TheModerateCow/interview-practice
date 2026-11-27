class TeamCalendar:
    def __init__(self):
        raise NotImplementedError

    def add_attendee(self, id: str, offset: int, work_start: int, work_end: int) -> bool:
        raise NotImplementedError

    def add_busy(self, id: str, start: int, end: int) -> str | None:
        raise NotImplementedError

    def remove_busy(self, id: str, busy_id: str) -> bool:
        raise NotImplementedError

    def is_free(self, id: str, minute: int) -> bool:
        raise NotImplementedError
