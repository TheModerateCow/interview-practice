"""An example to copy. Write your own tests in test_billing.py and run them with My tests."""

from billing import Subscription


def test_example_renew():
    s = Subscription()
    s.start(0, "starter", "monthly", 2)
    assert s.renew() == 2598  # 2 seats x 12.99
    assert s.period_end() == 60
