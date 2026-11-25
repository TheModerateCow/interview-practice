from pipeline import Job, fastest_release


def test_example():
    assert fastest_release([Job(consumer=-1, cold=7, warm=1), Job(consumer=0, cold=4, warm=2)], 0) == 11
