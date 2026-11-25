"""An example to copy. Run your tests with the My tests button."""

from quota import Plan, Service


def test_example_allow_within_limit():
    s = Service()
    s.add_plan(Plan("starter", limit=5, window=60, burst=0))
    s.issue_key("key-1", "org-1", "starter")
    d = s.allow("key-1", 30, 2)
    assert d.allowed and d.remaining == 3
