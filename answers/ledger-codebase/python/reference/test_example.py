"""An example to copy. Run your tests with the My tests button."""

from ledger import Ledger, Pricing, pending_account


def test_example_capture():
    l = Ledger()
    l.add_merchant("m1", Pricing(250))
    l.capture("ch1", "m1", "USD", 1999, "card", 100)
    assert l.balance(pending_account("m1"), "USD") == 1999
    assert l.trial_balance("USD") == 0
