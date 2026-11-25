"""An example to copy. Run your tests with the My tests button."""

from configstore import Store


def test_example_set_get():
    s = Store()
    assert s.set(1, "svc-api", "replicas", "3")
    assert s.get(2, "svc-api", "replicas") == "3"
