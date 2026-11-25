class Office:
    def __init__(self):
        raise NotImplementedError

    def create_event(self, ts: int, event_id: str, capacity: int) -> bool:
        raise NotImplementedError

    def buy(self, ts: int, event_id: str, buyer: str, qty: int) -> bool:
        raise NotImplementedError

    def refund(self, ts: int, event_id: str, buyer: str, qty: int) -> bool:
        raise NotImplementedError

    def available(self, ts: int, event_id: str) -> int:
        raise NotImplementedError
