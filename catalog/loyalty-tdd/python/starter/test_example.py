"""An example to copy. Write your own tests in test_loyalty.py and run them with My tests."""

from loyalty import Account


def test_example_earn():
    a = Account()
    assert a.earn(1, 2000) == 20  # a 20.00 purchase
    assert a.balance(1) == 20
