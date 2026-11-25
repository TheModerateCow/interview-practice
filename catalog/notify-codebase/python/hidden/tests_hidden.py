import time

import pytest

from notify import (
    EMAIL,
    PUSH,
    SENT,
    SMS,
    BadChannel,
    BadNotification,
    BadOffset,
    BadQuietHours,
    DuplicateUser,
    Notification,
    Service,
    UnknownUser,
)

_hidden_H = 3600
_hidden_DAY = 24 * _hidden_H


def _hidden_user(s, id, offset_min, *chans):
    s.add_user(id, offset_min)
    s.set_channels(id, list(chans))


def _hidden_result(r):
    if r.status != SENT:
        return r.status
    return "sent " + ",".join(r.channels)


def _hidden_send(s, user, at, topic, key, urgent=False):
    """Sends a notification and renders the result as "sent push,sms", "held" or "duplicate"."""
    return _hidden_result(s.send(Notification(user=user, topic=topic, key=key, title=f"{topic}:{key}", at=at, urgent=urgent)))


def _hidden_urgent(s, user, at, topic, key):
    return _hidden_send(s, user, at, topic, key, urgent=True)


def _hidden_channels(s, id):
    return s.user(id).channels


def _hidden_digest(s, id, now):
    return [f"{ln.topic}:{ln.count}:{ln.latest}" for ln in s.digest(id, now)]


# ---------------------------------------------------------------- phase 1


def test_p1_new_user_defaults():
    s = Service()
    s.add_user("ana", 0)
    assert _hidden_channels(s, "ana") == [EMAIL]
    assert _hidden_send(s, "ana", 3 * _hidden_H, "billing", "inv-1") == "sent email"


def test_p1_fan_out_in_user_order():
    s = Service()
    _hidden_user(s, "ana", 0, SMS, EMAIL, PUSH)
    assert _hidden_send(s, "ana", 1000, "security", "login-1") == "sent sms,email,push"
    _hidden_user(s, "ben", 0)
    assert _hidden_send(s, "ben", 1000, "security", "login-1") == "held"
    assert _hidden_urgent(s, "ben", 1001, "security", "login-2") == "held"


def test_p1_quiet_hours_utc():
    s = Service()
    _hidden_user(s, "ana", 0, PUSH)
    s.set_quiet_hours("ana", 22, 7)
    assert _hidden_send(s, "ana", 22 * _hidden_H - 60, "promo", "a") == "sent push"
    assert _hidden_send(s, "ana", 22 * _hidden_H, "promo", "b") == "held"
    assert _hidden_send(s, "ana", _hidden_DAY + 3 * _hidden_H, "promo", "c") == "held"
    assert _hidden_send(s, "ana", _hidden_DAY + 7 * _hidden_H - 1, "promo", "d") == "held"
    assert _hidden_send(s, "ana", _hidden_DAY + 7 * _hidden_H, "promo", "e") == "sent push"
    assert _hidden_urgent(s, "ana", _hidden_DAY + 23 * _hidden_H + 1800, "security", "f") == "sent push"


def test_p1_quiet_hours_east_of_utc():
    s = Service()
    _hidden_user(s, "kai", 8 * 60, PUSH, SMS)
    s.set_quiet_hours("kai", 22, 7)
    assert _hidden_send(s, "kai", 15 * _hidden_H, "promo", "a") == "held"  # 23:00 local
    assert _hidden_send(s, "kai", 22 * _hidden_H + 1800, "promo", "b") == "held"  # 06:30 local
    assert _hidden_send(s, "kai", 23 * _hidden_H, "promo", "c") == "sent push,sms"  # 07:00 local
    assert _hidden_send(s, "kai", _hidden_DAY + 13 * _hidden_H, "promo", "d") == "sent push,sms"  # 21:00 local


def test_p1_quiet_hours_west_and_half_hour_offsets():
    s = Service()
    _hidden_user(s, "lee", -5 * 60, EMAIL)
    s.set_quiet_hours("lee", 22, 7)
    assert _hidden_send(s, "lee", _hidden_DAY + 3 * _hidden_H, "promo", "a") == "held"  # 22:00 local
    assert _hidden_send(s, "lee", _hidden_DAY + 12 * _hidden_H - 60, "promo", "b") == "held"  # 06:59 local
    assert _hidden_send(s, "lee", _hidden_DAY + 12 * _hidden_H, "promo", "c") == "sent email"  # 07:00 local
    _hidden_user(s, "ria", 5 * 60 + 30, EMAIL)
    s.set_quiet_hours("ria", 9, 17)
    assert _hidden_send(s, "ria", 3 * _hidden_H + 1800, "promo", "a") == "held"  # 09:00 local
    assert _hidden_send(s, "ria", _hidden_DAY + 3 * _hidden_H + 1740, "promo", "b") == "sent email"  # 08:59 local
    assert _hidden_send(s, "ria", _hidden_DAY + 11 * _hidden_H + 1800, "promo", "c") == "sent email"  # 17:00 local


def test_p1_dedupe_window():
    s = Service()
    _hidden_user(s, "ana", 0, EMAIL)
    assert _hidden_send(s, "ana", 0, "billing", "pay-due") == "sent email"
    assert _hidden_send(s, "ana", 1800, "billing", "pay-due") == "duplicate"
    assert _hidden_send(s, "ana", 3599, "billing", "pay-due") == "duplicate"
    assert _hidden_send(s, "ana", 3600, "billing", "pay-due") == "sent email"
    assert _hidden_send(s, "ana", 3601, "billing", "pay-late") == "sent email"
    assert _hidden_send(s, "ana", 7200, "billing", "pay-due") == "sent email"


def test_p1_dedupe_keys_are_per_user():
    s = Service()
    for id in ("ana", "ben", "cy"):
        _hidden_user(s, id, 0, PUSH)
    assert _hidden_send(s, "ana", 100, "news", "launch-2026") == "sent push"
    assert _hidden_send(s, "ben", 101, "news", "launch-2026") == "sent push"
    assert _hidden_send(s, "cy", 102, "news", "launch-2026") == "sent push"
    assert _hidden_send(s, "ana", 200, "news", "launch-2026") == "duplicate"


def test_p1_held_notification_still_dedupes():
    s = Service()
    _hidden_user(s, "ana", 0, PUSH)
    s.set_quiet_hours("ana", 0, 6)
    assert _hidden_send(s, "ana", 5 * _hidden_H + 1800, "social", "like-9") == "held"
    assert _hidden_send(s, "ana", 6 * _hidden_H + 600, "social", "like-9") == "duplicate"
    assert _hidden_send(s, "ana", 6 * _hidden_H + 1800, "social", "like-9") == "sent push"


def test_p1_hourly_caps():
    s = Service()
    _hidden_user(s, "ana", 0, PUSH, SMS)
    got = [_hidden_send(s, "ana", 600 * i, "chat", f"m{i}") for i in range(6)]
    assert got == ["sent push,sms", "sent push,sms", "sent push", "sent push", "held", "held"]
    assert _hidden_send(s, "ana", 3600, "chat", "m6") == "sent push,sms"  # first push leaves the window
    assert _hidden_send(s, "ana", 4200, "chat", "m7") == "sent push,sms"  # second slot frees
    assert _hidden_send(s, "ana", 7800, "chat", "m8") == "sent push,sms"  # an hour later all clear


def test_p1_caps_are_per_user():
    s = Service()
    _hidden_user(s, "ana", 0, SMS)
    _hidden_user(s, "ben", 0, SMS)
    _hidden_send(s, "ana", 0, "otp", "1")
    _hidden_send(s, "ana", 1, "otp", "2")
    assert _hidden_urgent(s, "ana", 2, "otp", "3") == "held"
    assert _hidden_send(s, "ben", 3, "otp", "1") == "sent sms"


def test_p1_channels_are_not_shared_between_users():
    s = Service()
    s.add_user("ana", 0)
    s.add_user("ben", 0)
    row = [PUSH, SMS]
    s.set_channels("ana", row)
    row[0], row[1] = EMAIL, PUSH  # the import tool reuses its row buffer
    s.set_channels("ben", row)
    assert _hidden_channels(s, "ana") == [PUSH, SMS]
    assert _hidden_send(s, "ana", 10, "security", "new-device") == "sent push,sms"
    assert _hidden_send(s, "ben", 10, "security", "new-device") == "sent email,push"


def test_p1_errors():
    s = Service()
    _hidden_user(s, "ana", 60, PUSH)
    s.set_quiet_hours("ana", 23, 6)
    with pytest.raises(DuplicateUser):
        s.add_user("ana", 0)
    with pytest.raises(BadOffset):
        s.add_user("x", 841)
    with pytest.raises(BadOffset):
        s.add_user("x", -721)
    s.add_user("e", 840)
    s.add_user("w", -720)
    with pytest.raises(BadChannel):
        s.set_channels("ana", [PUSH, "fax"])
    with pytest.raises(BadChannel):
        s.set_channels("ana", [SMS, SMS])
    with pytest.raises(UnknownUser):
        s.set_channels("nope", [])
    with pytest.raises(BadQuietHours):
        s.set_quiet_hours("ana", 22, 24)
    with pytest.raises(BadQuietHours):
        s.set_quiet_hours("ana", -1, 6)
    with pytest.raises(UnknownUser):
        s.set_quiet_hours("nope", 1, 2)
    with pytest.raises(UnknownUser):
        s.send(Notification(user="nope", topic="t", key="k", at=1))
    with pytest.raises(BadNotification):
        s.send(Notification(user="ana", topic="", key="k", at=1))
    with pytest.raises(BadNotification):
        s.send(Notification(user="ana", topic="t", key="", at=1))
    with pytest.raises(UnknownUser):
        s.user("nope")
    u = s.user("ana")
    assert (u.id, u.offset_min, u.channels, u.quiet_from, u.quiet_to) == ("ana", 60, [PUSH], 23, 6)


# ---------------------------------------------------------------- phase 2


def test_p2_digest_groups_by_topic():
    s = Service()
    _hidden_user(s, "ana", 0)
    _hidden_send(s, "ana", 100, "billing", "b1")
    _hidden_send(s, "ana", 200, "promo", "p1")
    _hidden_send(s, "ana", 300, "security", "s1")
    _hidden_send(s, "ana", 400, "promo", "p2")
    _hidden_send(s, "ana", 500, "billing", "b2")
    _hidden_send(s, "ana", 600, "promo", "p3")
    assert _hidden_digest(s, "ana", _hidden_DAY + 9 * _hidden_H) == ["promo:3:promo:p3", "billing:2:billing:b2", "security:1:security:s1"]


def test_p2_digest_covers_only_the_day_before():
    s = Service()
    _hidden_user(s, "ana", 0)
    _hidden_send(s, "ana", 10, "news", "d0")
    _hidden_send(s, "ana", _hidden_DAY - 1, "news", "d0-late")
    _hidden_send(s, "ana", _hidden_DAY, "news", "d1")
    _hidden_send(s, "ana", 2 * _hidden_DAY - 1, "social", "d1-late")
    _hidden_send(s, "ana", 2 * _hidden_DAY, "news", "d2")
    assert _hidden_digest(s, "ana", _hidden_DAY + 5) == ["news:2:news:d0-late"]
    assert _hidden_digest(s, "ana", 2 * _hidden_DAY + 20 * _hidden_H) == ["news:1:news:d1", "social:1:social:d1-late"]
    assert _hidden_digest(s, "ana", 2 * _hidden_DAY) == ["news:1:news:d1", "social:1:social:d1-late"]
    assert _hidden_digest(s, "ana", 50) == []
    assert _hidden_digest(s, "ana", 4 * _hidden_DAY) == []


def test_p2_digest_uses_the_users_local_day():
    s = Service()
    _hidden_user(s, "kai", 9 * 60)
    _hidden_user(s, "lee", -7 * 60)
    for id in ("kai", "lee"):
        _hidden_send(s, id, _hidden_DAY + 14 * _hidden_H, "news", id + "-a")
        _hidden_send(s, id, _hidden_DAY + 16 * _hidden_H, "news", id + "-b")
        _hidden_send(s, id, 2 * _hidden_DAY + 6 * _hidden_H, "news", id + "-c")
        _hidden_send(s, id, 2 * _hidden_DAY + 8 * _hidden_H, "news", id + "-d")
    assert _hidden_digest(s, "kai", 2 * _hidden_DAY + 10 * _hidden_H) == ["news:1:news:kai-a"]
    assert _hidden_digest(s, "kai", 2 * _hidden_DAY + 16 * _hidden_H) == ["news:3:news:kai-d"]
    assert _hidden_digest(s, "lee", 3 * _hidden_DAY + 10 * _hidden_H) == ["news:1:news:lee-d"]
    assert _hidden_digest(s, "lee", 3 * _hidden_DAY + 6 * _hidden_H) == ["news:3:news:lee-c"]


def test_p2_digest_has_only_held_notifications():
    s = Service()
    _hidden_user(s, "ana", 0, SMS)
    _hidden_send(s, "ana", 100, "otp", "c1")
    _hidden_send(s, "ana", 200, "otp", "c2")
    _hidden_send(s, "ana", 300, "otp", "c3")
    _hidden_send(s, "ana", 400, "otp", "c3")
    _hidden_send(s, "ana", 500, "alerts", "a1")
    _hidden_urgent(s, "ana", 600, "alerts", "a2")
    _hidden_send(s, "ana", 3700, "alerts", "a3")
    assert _hidden_digest(s, "ana", _hidden_DAY) == ["alerts:2:alerts:a2", "otp:1:otp:c3"]


def test_p2_digest_latest_title_and_ties():
    s = Service()
    _hidden_user(s, "ana", 60)
    for i, topic in enumerate(["zeta", "alpha", "mid", "alpha", "zeta", "mid"]):
        _hidden_send(s, "ana", 1000 + i, topic, f"k{i}")
    s.send(Notification(user="ana", topic="mid", key="same-second", title="last in", at=1005))
    assert _hidden_digest(s, "ana", _hidden_DAY) == ["mid:3:last in", "alpha:2:alpha:k3", "zeta:2:zeta:k4"]


def test_p2_digest_empty_and_unknown():
    s = Service()
    _hidden_user(s, "ana", 0, EMAIL)
    _hidden_send(s, "ana", 100, "billing", "b1")
    got = s.digest("ana", _hidden_DAY)
    assert got == [] and isinstance(got, list)
    with pytest.raises(UnknownUser):
        s.digest("nope", _hidden_DAY)


# ---------------------------------------------------------------- phase 3


def _hidden_chatty_users(s, n, days):
    """Replays days of traffic for n users on every channel, with quiet hours 23 -> 6 UTC: each sends
    a notification every 5 seconds and every key is sent twice in a row. Returns the count of each
    status and the total number of channel deliveries."""
    count = {"sent": 0, "held": 0, "duplicate": 0}
    deliveries = 0
    ids = [f"u{u}" for u in range(n)]
    for id in ids:
        _hidden_user(s, id, 0, PUSH, EMAIL, SMS)
        s.set_quiet_hours(id, 23, 6)
    topics = ["chat", "social", "billing", "security", "promo"]
    for i in range(days * _hidden_DAY // 5):
        for id in ids:
            r = s.send(Notification(user=id, topic=topics[(i // 2) % 5], key=f"{id}-{i // 2}", at=i * 5, urgent=i % 97 == 0))
            count[r.status] += 1
            deliveries += len(r.channels)
    return f"sent {count['sent']} held {count['held']} duplicate {count['duplicate']} deliveries {deliveries}"


def test_p3_chatty_user_two_days():
    s = Service()
    start = time.perf_counter()
    got = _hidden_chatty_users(s, 1, 2)
    elapsed = time.perf_counter() - start
    assert got == "sent 257 held 17023 duplicate 17280 deliveries 541"
    assert elapsed < 0.6, f"34,560 sends took {elapsed:.2f}s, budget 0.6s"
