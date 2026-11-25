from meters import best_battery_profit


# An example to copy. Run your tests with the My tests button.
def test_example_one_cycle():
    # Charge at 3, discharge at 7 and pay 1 of wear: 7 - 1 - 3 = 3.
    assert best_battery_profit([3, 7], 1, 1) == 3
