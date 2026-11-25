"""An example to copy. Run your tests with the My tests button."""

from feed import FeedService


def test_example_feed_shows_followed_accounts():
    svc = FeedService()
    for user in ("ana", "ben", "cy"):
        svc.add_user(user)
    svc.follow("ana", "ben")
    svc.publish("b1", "ben", 1_000, "hello")
    svc.publish("c1", "cy", 1_100, "not followed")
    page = svc.home_feed("ana", now=2_000)
    assert page.post_ids == ["b1"]
    assert page.next_cursor is None
