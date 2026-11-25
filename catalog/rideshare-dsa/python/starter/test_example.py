from dispatch import min_dispatch_radius


# An example to copy. Run your tests with the My tests button.
def test_example_two_pickups():
    # Riders at 0 and 10, drivers at 3 and 12: pairs (0,3) and (10,12), so R = 3.
    assert min_dispatch_radius([0, 10], [3, 12], 2) == 3
