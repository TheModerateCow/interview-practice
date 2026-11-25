class Store:
    def __init__(self):
        raise NotImplementedError

    def set(self, ts: int, key: str, field: str, value: str) -> bool:
        raise NotImplementedError

    def get(self, ts: int, key: str, field: str) -> str | None:
        raise NotImplementedError

    def delete(self, ts: int, key: str, field: str) -> bool:
        raise NotImplementedError

    def compare_and_set(self, ts: int, key: str, field: str, expected: str, value: str) -> bool:
        raise NotImplementedError
