from scheduler import Attendee, earliest_quorum_slot


# An example to copy. Run your tests with the My tests button.
def test_example_one_attendee():
    alex = [Attendee(offset=0, work_start=540, work_end=1020, busy=[])]
    assert earliest_quorum_slot(alex, 1, 30, 1) == 540
