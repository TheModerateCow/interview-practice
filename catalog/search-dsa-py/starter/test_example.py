# An example to copy. Run your tests with the My tests button.
from search_box import fewest_keystrokes


def test_example_tab_then_type():
    # Tab fills in "pizza" (the only logged query), then type "s".
    assert fewest_keystrokes(["pizza"], "pizzas") == 2
