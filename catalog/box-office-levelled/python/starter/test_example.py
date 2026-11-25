"""An example to copy. Run your tests with the My tests button."""

from tickets import Office


def test_example_buy():
    o = Office()
    assert o.create_event(1, "jazz-night", 3)
    assert o.buy(2, "jazz-night", "maya", 2)
    assert o.available(3, "jazz-night") == 1
