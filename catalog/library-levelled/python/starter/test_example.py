"""An example to copy. Run your tests with the My tests button."""

from library import Library


def test_example_checkout():
    lib = Library()
    assert lib.add_member(1, "m-7")
    assert lib.add_copy(2, "B-1", "Beowulf")
    assert lib.checkout(3, "m-7", "Beowulf") == "B-1"
    assert lib.borrower(4, "B-1") == "m-7"
