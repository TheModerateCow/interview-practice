"""An example to copy. Run your tests with the My tests button."""

from notify import EMAIL, SENT, Notification, Service


def test_example_send_goes_to_email():
    s = Service()
    s.add_user("ana", 0)
    res = s.send(Notification(user="ana", topic="welcome", key="welcome-1", title="Hi", at=1000))
    assert res.status == SENT
    assert res.channels == [EMAIL]
