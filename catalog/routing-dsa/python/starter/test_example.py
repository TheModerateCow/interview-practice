from route import Road, fastest_delivery


# An example to copy. Run your tests with the My tests button.
def test_example():
    # Two junctions, one road that needs 3 units; the van has 5.
    assert fastest_delivery(2, 5, 5, [0, 0], [Road(a=0, b=1, minutes=12, energy=3)]) == 12
