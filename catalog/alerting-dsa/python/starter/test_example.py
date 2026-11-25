from alerting import longest_compliant_window


# An example to copy. Run your tests with the My tests button.
def test_example_spike_spread_out():
    # 1% budget. Minute 1 alone is at 5%, but minutes 0-2 together are 6 errors / 600 requests = 1%.
    assert longest_compliant_window([300, 100, 200, 50], [1, 5, 0, 9], 10000) == 3
