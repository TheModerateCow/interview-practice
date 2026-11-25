"""An example to copy. Run your tests with the My tests button."""

from bank import Bank


def test_example_deposit_balance():
    b = Bank()
    assert b.open_account(1, "acc-x")
    b.deposit(2, "acc-x", 40)
    assert b.balance(3, "acc-x") == 40
