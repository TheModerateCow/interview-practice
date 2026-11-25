class Garage:
    def __init__(self):
        raise NotImplementedError

    def add_spot(self, ts: int, spot_id: str, size: str) -> bool:
        raise NotImplementedError

    def park(self, ts: int, plate: str, size: str) -> str:
        raise NotImplementedError

    def leave(self, ts: int, plate: str) -> bool:
        raise NotImplementedError

    def spot_of(self, ts: int, plate: str) -> str:
        raise NotImplementedError
