# An example to copy. Run your tests with the My tests button.
from book import Event, run_book


def test_example_two_levels():
    # 1 share at 40 is cheapest, then 1 of the 2 shares at 50.
    assert run_book([Event("add", 50, 2), Event("add", 40, 1), Event("quote", 0, 2)]) == [90]
