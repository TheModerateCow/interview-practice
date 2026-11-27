class SearchBox:
    def __init__(self):
        raise NotImplementedError

    def log_query(self, query: str) -> int:
        raise NotImplementedError

    def popularity(self, query: str) -> int:
        raise NotImplementedError

    def suggest(self, prefix: str) -> str | None:
        raise NotImplementedError
