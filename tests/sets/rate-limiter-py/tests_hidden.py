from limiter import RateLimiter


def test_p1_basic_limit():
    rl = RateLimiter(2, 10)
    assert [rl.allow("a", t) for t in (0, 1, 2)] == [True, True, False]


def test_p1_window_slides():
    rl = RateLimiter(2, 10)
    assert [rl.allow("a", t) for t in (0, 5, 9, 10, 14, 15)] == [True, True, False, True, False, True]


def test_p1_keys_independent():
    rl = RateLimiter(1, 10)
    assert rl.allow("a", 0) is True
    assert rl.allow("b", 0) is True
    assert rl.allow("a", 1) is False


def test_p1_rejected_not_recorded():
    rl = RateLimiter(1, 10)
    assert rl.allow("a", 0) is True
    assert rl.allow("a", 5) is False
    assert rl.allow("a", 10) is True


def test_p2_remaining():
    rl = RateLimiter(3, 10)
    assert rl.remaining("a", 0) == 3
    rl.allow("a", 0); rl.allow("a", 4)
    assert rl.remaining("a", 5) == 1
    assert rl.remaining("a", 10) == 2


def test_p2_remaining_never_negative_after_rejects():
    rl = RateLimiter(1, 10)
    rl.allow("a", 0); rl.allow("a", 1)
    assert rl.remaining("a", 2) == 0


def test_p2_reset_one_key():
    rl = RateLimiter(1, 10)
    rl.allow("a", 0); rl.allow("b", 0)
    rl.reset("a")
    assert rl.allow("a", 1) is True
    assert rl.allow("b", 1) is False


def test_p2_reset_unknown_key_ok():
    rl = RateLimiter(1, 10)
    rl.reset("zzz")
    assert rl.remaining("zzz", 0) == 1
