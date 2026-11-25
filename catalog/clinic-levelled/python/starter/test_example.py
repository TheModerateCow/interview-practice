"""An example to copy. Run your tests with the My tests button."""

from clinic import Clinic


def test_example_book_and_describe():
    c = Clinic()
    c.add_clinician(1, "dr-x")
    c.add_room(2, "room-x")
    c.add_type(3, "flu-shot", 15)
    id = c.book(4, "dr-x", "pat-x", "flu-shot", 900)
    assert id == "appt1"
    assert c.appointment(5, id) == "dr-x pat-x flu-shot room-x 900-915 booked"
