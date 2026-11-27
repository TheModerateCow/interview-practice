class Studio:
    def __init__(self):
        raise NotImplementedError

    def add_class(self, ts: int, class_id: str, start: int, capacity: int) -> bool:
        raise NotImplementedError

    def book(self, ts: int, class_id: str, member: str) -> bool:
        raise NotImplementedError

    def cancel(self, ts: int, class_id: str, member: str) -> bool:
        raise NotImplementedError

    def spots_left(self, ts: int, class_id: str) -> int:
        raise NotImplementedError

    def upcoming(self, ts: int, member: str) -> list[str]:
        raise NotImplementedError
