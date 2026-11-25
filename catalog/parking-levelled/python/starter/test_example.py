"""An example to copy. Run your tests with the My tests button."""

from parking import Garage


def test_example_park():
    g = Garage()
    assert g.add_spot(1, "P1", "medium")
    assert g.park(2, "AB-123", "small") == "P1"
    assert g.spot_of(3, "AB-123") == "P1"
