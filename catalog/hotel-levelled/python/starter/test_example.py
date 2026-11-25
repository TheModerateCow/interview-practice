from hotel import Hotel


# An example to copy. Run your tests with the My tests button.
def test_example_booking_cost():
    h = Hotel()
    assert h.add_room(1, "7", "twin", 5000)
    assert h.book(2, "kit", "7", 30, 32) == "b1"
    assert h.cost(3, "b1") == 10000
