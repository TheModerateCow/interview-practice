import time

import pytest

from quota import (
    BadCost,
    BadRange,
    DuplicateKey,
    DuplicatePlan,
    InvalidPlan,
    Key,
    Plan,
    Revoked,
    Service,
    UnknownKey,
    UnknownPlan,
)


def _hidden_service():
    """Plans basic (10/min, burst 4), strict (10/min, no burst) and pro (50/min, burst 20)."""
    s = Service()
    for p in (Plan("basic", 10, 60, 4), Plan("strict", 10, 60, 0), Plan("pro", 50, 60, 20)):
        s.add_plan(p)
    return s


def _hidden_allow(s, key, now, cost):
    """Run one request and render the decision as "ok R" or "no R +S"."""
    d = s.allow(key, now, cost)
    return f"ok {d.remaining}" if d.allowed else f"no {d.remaining} +{d.retry_after}"


def _hidden_usage(s, key, now):
    used, limit = s.usage(key, now)
    return f"{used}/{limit}"


def _hidden_report(s, org, start, end):
    return str([f"{l.key_id}:{l.plan}:{l.requests}/{l.units}/{l.denied}" for l in s.report(org, start, end)]).replace("'", "")


# ---------------------------------------------------------------- phase 1


def test_p1_allow_until_limit():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "strict")
    assert _hidden_allow(s, "k1", 0, 4) == "ok 6"
    assert _hidden_allow(s, "k1", 10, 6) == "ok 0"
    assert _hidden_allow(s, "k1", 45, 1) == "no 0 +15"
    assert _hidden_usage(s, "k1", 59) == "10/10"
    assert _hidden_allow(s, "k1", 60, 10) == "ok 0"


def test_p1_window_edges():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "strict")
    assert _hidden_allow(s, "k1", 119, 10) == "ok 0"
    assert _hidden_allow(s, "k1", 120, 10) == "ok 0"
    assert _hidden_allow(s, "k1", 120, 1) == "no 0 +60"
    assert _hidden_usage(s, "k1", 179) == "10/10"
    assert _hidden_usage(s, "k1", 180) == "0/10"


def test_p1_burst_from_quiet_window():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "basic")
    assert _hidden_usage(s, "k1", 0) == "0/14"  # idle before: full burst
    assert _hidden_allow(s, "k1", 5, 7) == "ok 7"
    assert _hidden_usage(s, "k1", 60) == "0/13"  # 3 unused roll over
    assert _hidden_usage(s, "k1", 120) == "0/14"  # only the window before counts


def test_p1_no_burst_after_burst_window():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "basic")
    assert _hidden_allow(s, "k1", 10, 14) == "ok 0"  # limit + burst
    assert _hidden_usage(s, "k1", 60) == "0/10"  # next window has the plain limit
    assert _hidden_allow(s, "k1", 61, 10) == "ok 0"
    assert _hidden_allow(s, "k1", 62, 1) == "no 0 +58"
    assert _hidden_usage(s, "k1", 120) == "0/10"


def test_p1_pro_burst_window():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "pro")
    assert _hidden_allow(s, "k1", 0, 65) == "ok 5"
    assert _hidden_allow(s, "k1", 60, 50) == "ok 0"
    assert _hidden_allow(s, "k1", 61, 1) == "no 0 +59"


def test_p1_denied_request_spends_nothing():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "strict")
    assert _hidden_allow(s, "k1", 0, 8) == "ok 2"
    assert _hidden_allow(s, "k1", 1, 5) == "no 2 +59"  # batch call too big
    assert _hidden_allow(s, "k1", 2, 2) == "ok 0"  # small call still fits
    assert _hidden_usage(s, "k1", 3) == "10/10"


def test_p1_denied_requests_keep_burst():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "pro")
    assert _hidden_allow(s, "k1", 0, 40) == "ok 30"
    for i in range(1, 6):
        assert _hidden_allow(s, "k1", i, 50) == f"no 30 +{60 - i}"  # retry storm
    assert _hidden_usage(s, "k1", 60) == "0/60"  # 10 unused roll over


def test_p1_errors():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "basic")
    with pytest.raises(UnknownKey):
        s.allow("nope", 0, 1)
    with pytest.raises(BadCost):
        s.allow("k1", 0, 0)
    with pytest.raises(DuplicateKey):
        s.issue_key("k1", "org-b", "pro")
    with pytest.raises(UnknownPlan):
        s.issue_key("k2", "org-a", "gold")
    with pytest.raises(DuplicatePlan):
        s.add_plan(Plan("pro", 1, 1))
    with pytest.raises(InvalidPlan):
        s.add_plan(Plan("x", 0, 60))
    with pytest.raises(InvalidPlan):
        s.add_plan(Plan("x", 5, 0))
    with pytest.raises(InvalidPlan):
        s.add_plan(Plan("x", 5, 60, -1))
    with pytest.raises(UnknownPlan):
        s.change_plan("k1", "gold")
    with pytest.raises(UnknownKey):
        s.change_plan("nope", "pro")
    with pytest.raises(UnknownKey):
        s.revoke("nope")
    assert s.key("k1") == Key("k1", "org-a", "basic")  # untouched by the failed calls


def test_p1_revoked_key_rejected():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "pro")
    assert _hidden_allow(s, "k1", 0, 1) == "ok 69"
    s.revoke("k1")
    with pytest.raises(Revoked):
        s.allow("k1", 1, 1)
    assert _hidden_usage(s, "k1", 2) == "1/70"  # usage of a revoked key


def test_p1_revoked_key_stays_revoked_after_plan_change():
    s = _hidden_service()
    s.issue_key("leaked", "org-a", "basic")
    s.revoke("leaked")
    s.change_plan("leaked", "pro")
    with pytest.raises(Revoked):
        s.allow("leaked", 100, 1)
    assert s.key("leaked") == Key("leaked", "org-a", "pro", True)


def test_p1_plan_change_applies_to_next_request():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "strict")
    assert _hidden_allow(s, "k1", 0, 10) == "ok 0"
    assert _hidden_allow(s, "k1", 1, 5) == "no 0 +59"  # strict is full
    s.change_plan("k1", "pro")
    assert _hidden_allow(s, "k1", 2, 5) == "ok 55"  # on pro, same window
    assert _hidden_usage(s, "k1", 3) == "15/70"


def test_p1_keys_are_independent():
    s = _hidden_service()
    s.issue_key("a", "org-a", "strict")
    s.issue_key("b", "org-a", "strict")
    assert _hidden_allow(s, "a", 0, 10) == "ok 0"
    assert _hidden_allow(s, "b", 1, 3) == "ok 7"
    assert _hidden_allow(s, "a", 2, 1) == "no 0 +58"
    assert _hidden_usage(s, "b", 2) == "3/10"


# ---------------------------------------------------------------- phase 2


def test_p2_report_counts():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "strict")
    for at, cost in ((0, 4), (10, 3), (20, 2), (30, 5), (70, 6)):
        s.allow("k1", at, cost)
    assert _hidden_report(s, "org-a", 0, 120) == "[k1:strict:4/15/1]"


def test_p2_report_order():
    s = _hidden_service()
    for k, plan in (("mid", "pro"), ("big", "pro"), ("tie-b", "basic"), ("tie-a", "strict")):
        s.issue_key(k, "org-a", plan)
    for k, at, cost in (("mid", 0, 20), ("big", 0, 30), ("big", 1, 1), ("tie-b", 2, 5), ("tie-a", 3, 2), ("tie-a", 4, 3)):
        s.allow(k, at, cost)
    # most units first, ties by key id
    assert _hidden_report(s, "org-a", 0, 60) == "[big:pro:2/31/0, mid:pro:1/20/0, tie-a:strict:2/5/0, tie-b:basic:1/5/0]"


def test_p2_report_range_is_half_open():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "pro")
    for at in (99, 100, 150, 199, 200):
        s.allow("k1", at, 1)
    assert _hidden_report(s, "org-a", 100, 200) == "[k1:pro:3/3/0]"
    assert _hidden_report(s, "org-a", 200, 201) == "[k1:pro:1/1/0]"
    assert _hidden_report(s, "org-a", 0, 99) == "[]"


def test_p2_report_only_active_keys_of_the_org():
    s = _hidden_service()
    for k, org in (("a1", "org-a"), ("a2", "org-a"), ("b1", "org-b")):
        s.issue_key(k, org, "pro")
    s.allow("a1", 10, 2)
    s.allow("a2", 500, 2)
    s.allow("b1", 10, 9)
    assert _hidden_report(s, "org-a", 0, 60) == "[a1:pro:1/2/0]"
    assert _hidden_report(s, "org-b", 0, 1000) == "[b1:pro:1/9/0]"


def test_p2_report_revoked_and_denied_only_keys():
    s = _hidden_service()
    s.issue_key("old", "org-a", "basic")
    s.issue_key("noisy", "org-a", "strict")
    s.allow("old", 0, 3)
    s.revoke("old")
    with pytest.raises(Revoked):
        s.allow("old", 1, 3)
    s.allow("noisy", 2, 11)
    s.allow("noisy", 3, 12)
    s.change_plan("noisy", "pro")
    # a revoked key is still billed; a denied-only key is listed with its current plan
    assert _hidden_report(s, "org-a", 0, 60) == "[old:basic:1/3/0, noisy:pro:0/0/2]"


def test_p2_report_empty_and_bad_range():
    s = _hidden_service()
    s.issue_key("k1", "org-a", "pro")
    s.allow("k1", 10, 1)
    got = s.report("org-z", 0, 100)
    assert isinstance(got, list) and got == []
    with pytest.raises(BadRange):
        s.report("org-a", 50, 50)
    with pytest.raises(BadRange):
        s.report("org-a", 60, 0)


# ---------------------------------------------------------------- phase 3


def _hidden_busy_day(s, n, seconds):
    """Replay a busy day for one customer: n keys on "standard" sending one
    request a second, plus a "hog" key on "metered" that hammers its limit, for
    the given number of seconds. Returns allowed and denied counts and the sum
    of Remaining over the allowed decisions."""
    s.add_plan(Plan("standard", 600, 60, 100))
    s.add_plan(Plan("metered", 100, 60, 0))
    ids = [f"k{i}" for i in range(n)]
    for i in ids:
        s.issue_key(i, "org-big", "standard")
    s.issue_key("hog", "org-big", "metered")
    seed = 2024
    allowed = denied = remaining = 0
    for now in range(seconds):
        for key in ids + ["hog"]:
            if key == "hog":
                cost = 7
            else:
                seed = (seed * 1664525 + 1013904223) % 2**32
                cost = 1 + (seed >> 8) % 9
            d = s.allow(key, now, cost)
            if d.allowed:
                allowed += 1
                remaining += d.remaining
            else:
                denied += 1
    return allowed, denied, remaining


def test_p3_busy_day_traffic():
    s = Service()
    start = time.perf_counter()
    allowed, denied, remaining = _hidden_busy_day(s, 1, 20000)
    elapsed = time.perf_counter() - start
    assert allowed == 24676
    assert denied == 15324
    assert remaining == 11161623  # sum of Remaining over the allowed calls
    assert _hidden_usage(s, "k0", 19999) == "116/700"
    assert elapsed < 1.5, f"40,000 Allow calls took {elapsed:.2f}s, budget 1.5s"


def test_p3_hourly_reports():
    s = Service()
    start = time.perf_counter()
    _hidden_busy_day(s, 1, 20000)
    hours = [_hidden_report(s, "org-big", h * 3600, (h + 1) * 3600) for h in range(5)]
    day = _hidden_report(s, "org-big", 0, 20000)
    elapsed = time.perf_counter() - start
    assert hours[0] == "[k0:standard:3600/18030/0, hog:metered:840/5880/2760]"
    assert hours[4] == "[k0:standard:3600/18003/0, hog:metered:840/5880/2760]"
    assert day == "[k0:standard:20000/100344/0, hog:metered:4676/32732/15324]"
    assert elapsed < 1.5, f"40,000 Allow calls plus 6 reports took {elapsed:.2f}s, budget 1.5s"
