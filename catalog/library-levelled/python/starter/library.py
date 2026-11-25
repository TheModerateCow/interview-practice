class Library:
    def __init__(self):
        raise NotImplementedError

    def add_member(self, ts: int, member_id: str) -> bool:
        raise NotImplementedError

    def add_copy(self, ts: int, copy_id: str, title: str) -> bool:
        raise NotImplementedError

    def checkout(self, ts: int, member_id: str, title: str) -> str:
        raise NotImplementedError

    def return_copy(self, ts: int, copy_id: str) -> bool:
        raise NotImplementedError

    def borrower(self, ts: int, copy_id: str) -> str:
        raise NotImplementedError
