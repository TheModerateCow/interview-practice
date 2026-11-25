"""An example to copy. Run your tests with the My tests button."""

from inventory import Service


def test_example_receive_and_reserve():
    s = Service()
    s.add_warehouse("north")
    s.receive("north", "B-07", "MUG-RED", 12, 100)
    s.reserve("o1", "north", "MUG-RED", 5, 900, 200)
    assert s.available("north", "MUG-RED", 300) == 7
    assert s.on_hand("north", "MUG-RED") == 12
