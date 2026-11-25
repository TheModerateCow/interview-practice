import random
import time

import pytest

from feed import BadCursor, DuplicatePost, FeedError, FeedService, UnknownPost, UnknownUser

_hidden_T0 = 1_750_000_000
_hidden_H = 60 * 60
_hidden_DAY = 24 * _hidden_H


def _hidden_svc(*users):
    svc = FeedService()
    for u in users:
        svc.add_user(u)
    return svc


def _hidden_all_pages(svc, viewer, now, limit):
    ids, cursor, pages = [], None, 0
    while True:
        page = svc.home_feed(viewer, now, limit, cursor)
        ids += page.post_ids
        pages += 1
        assert pages < 100, "paging never ended"
        if page.next_cursor is None:
            return ids, pages
        cursor = page.next_cursor


# ---------------------------------------------------------------- phase 1


def test_p1_feed_is_followed_and_own_posts_newest_first():
    svc = _hidden_svc("ana", "ben", "cy", "dee")
    svc.follow("ana", "ben")
    svc.follow("ana", "dee")
    svc.publish("b1", "ben", _hidden_T0)
    svc.publish("c1", "cy", _hidden_T0 + 10)
    svc.publish("a1", "ana", _hidden_T0 + 20)
    svc.publish("d1", "dee", _hidden_T0 + 30)
    svc.publish("b2", "ben", _hidden_T0 + 40)
    page = svc.home_feed("ana", _hidden_T0 + 100)
    assert page.post_ids == ["b2", "d1", "a1", "b1"]
    assert page.next_cursor is None
    assert svc.home_feed("cy", _hidden_T0 + 100).post_ids == ["c1"]


def test_p1_likes_trade_against_recency():
    svc = _hidden_svc("ana", "ben", "u1", "u2", "u3")
    svc.follow("ana", "ben")
    svc.publish("old", "ben", _hidden_T0)
    svc.publish("mid", "ben", _hidden_T0 + 11 * _hidden_H)
    svc.publish("new", "ben", _hidden_T0 + 13 * _hidden_H)
    for u in ("u1", "u2", "u3"):
        assert svc.like("old", u) >= 1
    assert svc.post("old").likes == 3
    page = svc.home_feed("ana", _hidden_T0 + 14 * _hidden_H)
    assert page.post_ids == ["new", "old", "mid"]


def test_p1_equal_scores_tie_on_post_id():
    svc = _hidden_svc("ana", "ben", "cy")
    svc.follow("ana", "ben")
    svc.follow("ana", "cy")
    svc.publish("p-c", "cy", _hidden_T0)
    svc.publish("p-a", "ben", _hidden_T0)
    svc.publish("p-b", "ben", _hidden_T0)
    assert svc.home_feed("ana", _hidden_T0 + 5).post_ids == ["p-a", "p-b", "p-c"]


def test_p1_retried_like_counts_once():
    svc = _hidden_svc("ana", "ben", "cy")
    svc.follow("ana", "ben")
    svc.publish("x", "ben", _hidden_T0)
    svc.publish("y", "ben", _hidden_T0 + 7 * _hidden_H)
    assert svc.like("x", "cy") == 1
    assert svc.like("x", "cy") == 1
    assert svc.like("x", "cy") == 1
    assert svc.post("x").likes == 1
    assert svc.home_feed("ana", _hidden_T0 + 8 * _hidden_H).post_ids == ["y", "x"]
    assert svc.like("x", "ana") == 2
    assert svc.home_feed("ana", _hidden_T0 + 8 * _hidden_H).post_ids == ["x", "y"]


def test_p1_like_errors():
    svc = _hidden_svc("ana", "ben")
    svc.publish("x", "ben", _hidden_T0)
    with pytest.raises(UnknownPost):
        svc.like("nope", "ana")
    with pytest.raises(UnknownUser):
        svc.like("x", "ghost")
    assert svc.post("x").likes == 0


def test_p1_paging_a_thread_shows_each_post_once():
    svc = _hidden_svc("ana", "ben")
    svc.follow("ana", "ben")
    for i in range(14):
        svc.publish(f"t{i:02d}", "ben", _hidden_T0 + i)
    svc.publish("t06b", "ben", _hidden_T0 + 6)
    now = _hidden_T0 + 60
    everything = svc.home_feed("ana", now, 100).post_ids
    assert everything[:4] == ["t13", "t12", "t11", "t10"]
    assert everything.index("t06b") == everything.index("t06") + 1
    for limit in (2, 3, 4):
        ids, pages = _hidden_all_pages(svc, "ana", now, limit)
        assert ids == everything, f"limit {limit}"
        assert pages == -(-len(everything) // limit)


def test_p1_paging_mixed_engagement():
    svc = _hidden_svc("ana", "ben", "cy", "l0", "l1", "l2")
    svc.follow("ana", "ben")
    svc.follow("ana", "cy")
    for i in range(9):
        svc.publish(f"b{i}", "ben", _hidden_T0 + 3 * i)
        svc.publish(f"c{i}", "cy", _hidden_T0 + 3 * i + 1)
    for i, liker in enumerate(("l0", "l1", "l2")):
        svc.like(f"b{i}", liker)
        svc.like(f"c{i + 4}", liker)
    now = _hidden_T0 + 100
    everything = svc.home_feed("ana", now, 50).post_ids
    assert len(everything) == 18
    ids, _ = _hidden_all_pages(svc, "ana", now, 4)
    assert ids == everything


def test_p1_last_page_and_bad_cursor():
    svc = _hidden_svc("ana")
    for i in range(4):
        svc.publish(f"a{i}", "ana", _hidden_T0 + i * 10)
    first = svc.home_feed("ana", _hidden_T0 + 100, 2)
    assert first.post_ids == ["a3", "a2"]
    assert first.next_cursor is not None
    second = svc.home_feed("ana", _hidden_T0 + 100, 2, first.next_cursor)
    assert second.post_ids == ["a1", "a0"]
    assert second.next_cursor is None
    assert svc.home_feed("ana", _hidden_T0 + 100, 4).next_cursor is None
    with pytest.raises(BadCursor):
        svc.home_feed("ana", _hidden_T0 + 100, 2, "not-a-cursor")
    with pytest.raises(ValueError):
        svc.home_feed("ana", _hidden_T0 + 100, 0)


def test_p1_feed_window_edges():
    svc = _hidden_svc("ana", "ben")
    svc.follow("ana", "ben")
    now = _hidden_T0 + 30 * _hidden_DAY
    svc.publish("too-old", "ben", now - 7 * _hidden_DAY - 1)
    svc.publish("oldest", "ben", now - 7 * _hidden_DAY)
    svc.publish("mid", "ben", now - 3 * _hidden_DAY)
    svc.publish("now", "ben", now)
    svc.publish("scheduled", "ben", now + 1)
    assert svc.home_feed("ana", now).post_ids == ["now", "mid", "oldest"]
    assert svc.home_feed("ana", now + 1).post_ids == ["scheduled", "now", "mid"]


def test_p1_permanent_mute_is_per_viewer():
    svc = _hidden_svc("ana", "ben", "cy")
    svc.follow("ana", "ben")
    svc.follow("ana", "cy")
    svc.follow("cy", "ben")
    svc.publish("b1", "ben", _hidden_T0)
    svc.publish("c1", "cy", _hidden_T0 + 1)
    svc.mute("ana", "ben", _hidden_T0 + 2)
    assert svc.home_feed("ana", _hidden_T0 + 3).post_ids == ["c1"]
    assert svc.home_feed("ana", _hidden_T0 + 6 * _hidden_DAY).post_ids == ["c1"]
    assert svc.home_feed("cy", _hidden_T0 + 3).post_ids == ["c1", "b1"]


def test_p1_timed_mute_lasts_its_hours():
    svc = _hidden_svc("ana", "ben")
    svc.follow("ana", "ben")
    svc.publish("b1", "ben", _hidden_T0)
    start = _hidden_T0 + _hidden_H
    svc.mute("ana", "ben", start, hours=24)
    assert svc.home_feed("ana", start + 2 * _hidden_H).post_ids == []
    assert svc.home_feed("ana", start + 24 * _hidden_H - 1).post_ids == []
    assert svc.home_feed("ana", start + 24 * _hidden_H).post_ids == ["b1"]


def test_p1_short_mute_and_remute():
    svc = _hidden_svc("ana", "ben")
    svc.follow("ana", "ben")
    svc.publish("b1", "ben", _hidden_T0)
    svc.mute("ana", "ben", _hidden_T0, hours=1.5)
    assert svc.home_feed("ana", _hidden_T0 + 89 * 60).post_ids == []
    assert svc.home_feed("ana", _hidden_T0 + 90 * 60).post_ids == ["b1"]
    svc.mute("ana", "ben", _hidden_T0 + 2 * _hidden_H, hours=3)
    assert svc.home_feed("ana", _hidden_T0 + 4 * _hidden_H).post_ids == []
    assert svc.home_feed("ana", _hidden_T0 + 5 * _hidden_H).post_ids == ["b1"]


def test_p1_unfollow_and_account_errors():
    svc = _hidden_svc("ana", "ben")
    svc.follow("ana", "ben")
    svc.publish("b1", "ben", _hidden_T0, "first")
    svc.unfollow("ana", "ben")
    assert svc.home_feed("ana", _hidden_T0 + 1).post_ids == []
    with pytest.raises(FeedError):
        svc.follow("ana", "ana")
    with pytest.raises(UnknownUser):
        svc.follow("ana", "ghost")
    with pytest.raises(UnknownUser):
        svc.home_feed("ghost", _hidden_T0)
    with pytest.raises(UnknownUser):
        svc.publish("g1", "ghost", _hidden_T0)
    svc.like("b1", "ana")
    with pytest.raises(DuplicatePost):
        svc.publish("b1", "ben", _hidden_T0 + 5, "retry")
    assert svc.post("b1").text == "first"
    assert svc.post("b1").likes == 1


# ---------------------------------------------------------------- phase 2


def _hidden_away():
    svc = _hidden_svc("ana", "ben", "cy", "dee", "l1", "l2", "l3")
    for f in ("ben", "cy", "dee"):
        svc.follow("ana", f)
    since = _hidden_T0 + 10 * _hidden_H
    svc.publish("a-own", "ana", since + 50)
    svc.publish("b-before", "ben", since - 100)
    svc.publish("b-at", "ben", since)
    svc.publish("b1", "ben", since + 1)
    svc.publish("b2", "ben", since + 2 * _hidden_H)
    svc.publish("b3", "ben", since + 3 * _hidden_H)
    svc.publish("c1", "cy", since + 30 * 60)
    svc.publish("d1", "dee", since + 4 * _hidden_H)
    svc.publish("d2", "dee", since + 5 * _hidden_H)
    return svc, since


def test_p2_catch_up_ranks_new_posts_from_followed_accounts():
    svc, since = _hidden_away()
    now = since + 6 * _hidden_H
    assert svc.catch_up("ana", since, now, limit=10) == ["d2", "d1", "b3", "b2", "c1"]


def test_p2_catch_up_two_per_account_by_rank():
    svc, since = _hidden_away()
    now = since + 6 * _hidden_H
    for liker in ("l1", "l2", "l3"):
        svc.like("b1", liker)
    assert svc.catch_up("ana", since, now, limit=10) == ["b1", "d2", "d1", "b3", "c1"]
    assert svc.catch_up("ana", since - 200, now, limit=10) == ["b1", "d2", "d1", "b3", "c1"]


def test_p2_catch_up_limit_and_default():
    svc, since = _hidden_away()
    now = since + 6 * _hidden_H
    svc.publish("c2", "cy", since + 5 * _hidden_H + 30 * 60)
    assert svc.catch_up("ana", since, now) == ["c2", "d2", "d1", "b3", "b2"]
    assert svc.catch_up("ana", since, now, limit=2) == ["c2", "d2"]
    assert svc.catch_up("ana", since, now, limit=1) == ["c2"]


def test_p2_catch_up_skips_muted_unfollowed_and_future():
    svc, since = _hidden_away()
    now = since + 4 * _hidden_H
    svc.mute("ana", "dee", since)
    svc.unfollow("ana", "cy")
    svc.publish("b-later", "ben", now + 1)
    assert svc.catch_up("ana", since, now, limit=10) == ["b3", "b2"]


def test_p2_catch_up_never_reaches_past_the_feed_window():
    svc = _hidden_svc("ana", "ben", "cy")
    svc.follow("ana", "ben")
    svc.follow("ana", "cy")
    now = _hidden_T0 + 20 * _hidden_DAY
    svc.publish("ancient", "cy", now - 7 * _hidden_DAY - 1)
    svc.publish("edge", "ben", now - 7 * _hidden_DAY)
    svc.publish("recent", "ben", now - _hidden_DAY)
    assert svc.catch_up("ana", _hidden_T0, now) == ["recent", "edge"]
    assert svc.catch_up("ana", now - 7 * _hidden_DAY, now) == ["recent"]


def test_p2_catch_up_empty_and_errors():
    svc, since = _hidden_away()
    late = since + 10 * _hidden_H
    assert svc.catch_up("ana", late, late + _hidden_H) == []
    assert svc.catch_up("cy", since, late) == []
    with pytest.raises(UnknownUser):
        svc.catch_up("ghost", since, late)
    with pytest.raises(ValueError):
        svc.catch_up("ana", since, late, limit=0)


# ---------------------------------------------------------------- phase 3


def _hidden_rush():
    rng = random.Random(42)
    svc = FeedService()
    users = [f"u{i:04d}" for i in range(2000)]
    for u in users:
        svc.add_user(u)
    n = 0
    for day in range(30):
        for u in users:
            pid = f"p{n:06d}"
            n += 1
            svc.publish(pid, u, _hidden_T0 + day * _hidden_DAY + rng.randrange(_hidden_DAY))
            for liker in rng.sample(users, rng.randrange(6)):
                svc.like(pid, liker)
    viewers = users[:40]
    for v in viewers:
        for f in rng.sample(users[40:], 150):
            svc.follow(v, f)
    return svc, viewers, _hidden_T0 + 30 * _hidden_DAY


def test_p3_morning_peak_home_feeds():
    svc, viewers, now = _hidden_rush()
    start = time.perf_counter()
    pages = [svc.home_feed(v, now, 20) for v in viewers]
    elapsed = time.perf_counter() - start
    assert [len(p.post_ids) for p in pages] == [20] * 40
    assert pages[0].post_ids[:3] == ["p058049", "p059645", "p059940"]
    assert pages[21].post_ids[7] == "p058817"
    assert pages[39].post_ids[-1] == "p059483"
    assert elapsed < 0.5, f"40 home feeds took {elapsed:.2f}s, budget 0.5s"


def test_p3_morning_peak_catch_up():
    svc, viewers, now = _hidden_rush()
    start = time.perf_counter()
    lists = [svc.catch_up(v, now - 2 * _hidden_DAY, now) for v in viewers]
    elapsed = time.perf_counter() - start
    assert lists[0] == ["p058049", "p059645", "p059940", "p058445", "p058800"]
    assert lists[17] == ["p059940", "p059519", "p058281", "p058573", "p059656"]
    assert lists[39] == ["p058618", "p059197", "p058619", "p059157", "p059138"]
    assert elapsed < 0.5, f"40 catch-ups took {elapsed:.2f}s, budget 0.5s"
