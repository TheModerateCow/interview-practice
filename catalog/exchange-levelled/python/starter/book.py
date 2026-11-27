class OrderBook:
    def __init__(self):
        raise NotImplementedError

    def add_order(self, order_id: str, price: int, qty: int) -> bool:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    def best_ask(self) -> int | None:
        raise NotImplementedError

    def depth_at(self, price: int) -> int:
        raise NotImplementedError
