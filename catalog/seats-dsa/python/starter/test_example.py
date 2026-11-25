from upgrades import max_upgrades


# An example to copy. Run your tests with the My tests button.
def test_example_two_passengers_one_seat():
    # One leg with a single free seat, two passengers want it.
    assert max_upgrades([1], [[0, 1], [0, 1]]) == 1
