"""An example to copy. Write your own tests in test_fares.py and run them with My tests."""

from fares import FareCard


def test_example_one_off_peak_adult_ride_across_two_zones():
    card = FareCard("adult")
    assert card.ride(600, 1, 2) == 320  # Monday 10:00
