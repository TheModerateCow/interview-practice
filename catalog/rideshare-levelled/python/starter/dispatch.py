class Dispatcher:
    def __init__(self):
        raise NotImplementedError

    def add_driver(self, ts: int, id: str, km: int) -> bool:
        raise NotImplementedError

    def add_rider(self, ts: int, id: str, km: int) -> bool:
        raise NotImplementedError

    def move_driver(self, ts: int, id: str, km: int) -> bool:
        raise NotImplementedError

    def remove_driver(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def cancel_rider(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def nearest_driver(self, ts: int, rider: str) -> str | None:
        raise NotImplementedError
