import time

from search_box import fewest_keystrokes


def _hidden_rng(seed):
    x = seed

    def nxt(k):
        nonlocal x
        x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (x >> 33) % k

    return nxt


def _hidden_word(nxt, letters, lo, hi):
    return "".join(letters[nxt(len(letters))] for _ in range(lo + nxt(hi - lo + 1)))


def _hidden_small_cases(n, seed):
    # tiny logs on 2-3 letters, so prefixes collide and suggestions tie often
    nxt, cases = _hidden_rng(seed), []
    for i in range(n):
        letters = "ab" if i % 2 else "abc"
        pool = [_hidden_word(nxt, letters, 1, 6) for _ in range(1 + nxt(6))]
        log = [pool[nxt(len(pool))] for _ in range(1 + nxt(12))]
        if nxt(10) < 3:
            p = pool[nxt(len(pool))]
            target = p[: 1 + nxt(len(p))]
        else:
            target = _hidden_word(nxt, letters, 1, 7)
        cases.append((log, target))
    return cases


def _hidden_large():
    # 12,000 distinct queries (~290k characters) on 4 letters, a few hundred searched many times
    nxt = _hidden_rng(2026)
    pool = [_hidden_word(nxt, "abcd", 12, 30) for _ in range(12_000)]
    log = list(pool)
    for _ in range(1_500):
        log.append(pool[nxt(1 + nxt(400))])
    target = pool[4321][:24] + _hidden_word(nxt, "abcd", 6, 6)
    return log, target


def _hidden_digest(out):
    return len(out), sum(out), sum((i + 1) * v for i, v in enumerate(out))


def test_p1_worked_example():
    log = ["shoes", "shirts", "shoes", "shirt", "shirts", "shorts", "shirts"]
    assert fewest_keystrokes(log, "shirtless") == 6


def test_p1_target_is_the_top_suggestion():
    assert fewest_keystrokes(["cat", "cat", "car"], "cat") == 1


def test_p1_log_does_not_help():
    assert fewest_keystrokes(["zebra"], "cat") == 3
    assert fewest_keystrokes(["dog"], "dogs") == 2


def test_p1_repeated_searches_count_as_popularity():
    log = ["apple", "apply", "apply"]
    assert fewest_keystrokes(log, "apply") == 1
    assert fewest_keystrokes(log, "apple") == 3


def test_p1_ties_go_to_the_alphabetically_first_query():
    assert fewest_keystrokes(["beta", "alpha"], "alpha") == 1
    assert fewest_keystrokes(["beta", "alpha"], "beta") == 2


def test_p1_target_is_a_prefix_of_a_popular_query():
    assert fewest_keystrokes(["searching", "searching", "sea"], "search") == 4


def test_p1_type_past_the_end_of_a_suggestion():
    assert fewest_keystrokes(["head", "headphones", "headphones"], "headphonesx") == 2


def test_p1_chain_of_tabs():
    log = ["kayak", "kayak", "kayak", "kayaking", "kayakingtrips", "kettle", "kettle", "kettle", "kettle"]
    assert fewest_keystrokes(log, "kayakingtrips") == 7


def test_p1_long_backspace_run():
    log = ["internationalization", "internationalization", "in"]
    assert fewest_keystrokes(log, "international") == 8


def test_p1_single_letters():
    assert fewest_keystrokes(["a", "b", "a"], "b") == 1
    assert fewest_keystrokes(["a", "b", "a"], "a") == 1


def test_p1_many_small_logs():
    out = [fewest_keystrokes(log, target) for log, target in _hidden_small_cases(400, 7)]
    assert _hidden_digest(out) == (400, 1219, 243692)


def test_p1_large_log_is_fast():
    log, target = _hidden_large()
    t = time.perf_counter()
    got = fewest_keystrokes(log, target)
    took = time.perf_counter() - t
    assert got == 15
    assert took < 3.0, f"13,500 logged queries took {took:.1f}s (limit 3s)"
