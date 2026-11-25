from flags import FlagService


# An example to copy. Run your tests with the My tests button.
def test_example_flag_on_in_dev():
    s = FlagService()
    assert s.create_flag(1, "new-nav")
    assert s.set_enabled(2, "new-nav", "dev", True)
    assert s.is_enabled(3, "new-nav", "dev", "riya") is True
