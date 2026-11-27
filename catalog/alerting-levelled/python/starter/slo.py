class SloMonitor:
    def __init__(self):
        raise NotImplementedError

    def add_service(self, service: str) -> bool:
        raise NotImplementedError

    def ingest(self, service: str, first_minute: int, requests: list[int], errors: list[int]) -> bool:
        raise NotImplementedError

    def error_rate(self, service: str, start: int, end: int) -> int | None:
        raise NotImplementedError

    def latest_minute(self, service: str) -> int | None:
        raise NotImplementedError
