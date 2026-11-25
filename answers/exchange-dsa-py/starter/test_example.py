# An example to copy. Run your tests with the My tests button.
from book import run_book


def test_example_two_levels():
    # 1 share at 40 is cheapest, then 1 of the 2 shares at 50.
    assert run_book([("add", 50, 2), ("add", 40, 1), ("quote", 2)]) == [90]
