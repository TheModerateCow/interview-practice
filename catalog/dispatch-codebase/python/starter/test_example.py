"""An example to copy. Run your tests with the My tests button."""

from dispatch import Dispatcher, Point


def test_example_assign_nearest():
    d = Dispatcher()
    d.add_courier("near", Point(100, 0), 1)
    d.add_courier("far", Point(900, 900), 1)
    d.place_order("o1", Point(0, 0), Point(500, 0), 0, 5)
    assert d.assign("o1") == "near"
