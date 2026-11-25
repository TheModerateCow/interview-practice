import pytest

from invoice import Invoice


# An example to copy. Write your own tests in test_invoice.py and run them with My tests.
def test_example_single_line():
    inv = Invoice(0, "net30")
    assert inv.add_line(1000, 2, "standard") == 2000  # 2 x 10.00, no discount
    assert inv.total() == 2400  # plus 20% tax


def test_example_unknown_terms():
    with pytest.raises(ValueError):
        Invoice(0, "net7")
