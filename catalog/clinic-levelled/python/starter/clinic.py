class Clinic:
    def __init__(self):
        raise NotImplementedError

    def add_clinician(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def add_room(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def add_type(self, ts: int, name: str, minutes: int) -> bool:
        raise NotImplementedError

    def book(self, ts: int, clinician: str, patient: str, kind: str, start: int) -> str | None:
        raise NotImplementedError

    def cancel(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def appointment(self, ts: int, id: str) -> str | None:
        raise NotImplementedError
