class Network:
    def __init__(self):
        raise NotImplementedError

    def add_junction(self, ts: int, id: str) -> bool:
        raise NotImplementedError

    def add_road(self, ts: int, road: str, a: str, b: str, minutes: int) -> bool:
        raise NotImplementedError

    def roads_at(self, ts: int, junction: str) -> list[str]:
        raise NotImplementedError

    def reachable(self, ts: int, origin: str, dest: str) -> bool:
        raise NotImplementedError
