class Shop:
    def __init__(self):
        raise NotImplementedError

    def add_product(self, ts: int, sku: str, price_cents: int, stock: int) -> bool:
        raise NotImplementedError

    def add_to_cart(self, ts: int, cart_id: str, sku: str, qty: int) -> bool:
        raise NotImplementedError

    def remove_from_cart(self, ts: int, cart_id: str, sku: str, qty: int) -> int:
        raise NotImplementedError

    def cart_total(self, ts: int, cart_id: str) -> int:
        raise NotImplementedError

    def items(self, ts: int, cart_id: str) -> list[str]:
        raise NotImplementedError
