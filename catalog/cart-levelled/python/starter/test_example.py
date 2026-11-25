"""An example to copy. Run your tests with the My tests button."""

from shop import Shop


def test_example_cart():
    s = Shop()
    assert s.add_product(1, "scarf", 1250, 4)
    assert s.add_to_cart(2, "cart-9", "scarf", 2)
    assert s.cart_total(3, "cart-9") == 2500
    assert s.items(4, "cart-9") == ["scarf:2"]
