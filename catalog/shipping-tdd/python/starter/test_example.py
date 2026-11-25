"""An example to copy. Write your own tests first, run them with My tests,
then implement shipping.py."""

from shipping import Parcel, billable_grams


def test_example_billable_grams():
    assert billable_grams(Parcel(400, 30, 20, 10)) == 1500
