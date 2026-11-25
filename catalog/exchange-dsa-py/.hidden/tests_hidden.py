import time

from book import run_book

B = 10**9


def _hidden_rng(seed):
    x = seed

    def nxt(k):
        nonlocal x
        x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        return (x >> 33) % k

    return nxt


def _hidden_mixed(m, seed):
    # adds, cancels, quotes and buys on a small price range, so levels collide and refill
    nxt, book, ev = _hidden_rng(seed), {}, []
    for _ in range(m):
        r = nxt(100)
        if r < 40 or not book:
            p, q = 500 + nxt(60), 1 + nxt(50)
            ev.append(("add", p, q))
            book[p] = book.get(p, 0) + q
        elif r < 55:
            p = sorted(book)[nxt(len(book))]
            q = 1 + nxt(book[p])
            ev.append(("cancel", p, q))
            book[p] -= q
            if not book[p]:
                del book[p]
        elif r < 80:
            ev.append(("quote", 1 + nxt(sum(book.values()) * 5 // 4 + 1)))
        else:
            q = 1 + nxt(120)
            ev.append(("buy", q))
            for p in sorted(book):
                t = min(q, book[p])
                book[p] -= t
                q -= t
                if not book[p]:
                    del book[p]
    return ev


def _hidden_large(m):
    # deep book on prices up to ~1.7e8; quotes reach far into it
    nxt, total, ev = _hidden_rng(12345), 0, []
    for _ in range(m):
        r = nxt(100)
        if r < 50:
            q = 1 + nxt(1000)
            ev.append(("add", 10**8 + 7 * nxt(10**7), q))
            total += q
        elif r < 90:
            ev.append(("quote", 1 + nxt(total + total // 10 + 1)))
        else:
            q = 1 + nxt(1000)
            ev.append(("buy", q))
            total -= min(q, total)
    return ev


def _hidden_digest(out):
    return len(out), sum(out), sum((i + 1) * v for i, v in enumerate(out))


def test_p1_worked_example():
    ev = [("add", 101, 5), ("add", 100, 3), ("add", 103, 4), ("quote", 6), ("cancel", 101, 2),
          ("quote", 7), ("buy", 4), ("quote", 7), ("buy", 10)]
    assert run_book(ev) == [603, 706, 401, -1, 614]


def test_p1_empty_book():
    assert run_book([("quote", 1), ("buy", 5)]) == [-1, 0]


def test_p1_quote_exactly_the_whole_book():
    assert run_book([("add", 20, 3), ("add", 10, 2), ("quote", 5), ("quote", 6)]) == [80, -1]


def test_p1_quote_leaves_book_unchanged():
    ev = [("add", 7, 4), ("add", 9, 4), ("quote", 6), ("quote", 6), ("buy", 6), ("quote", 2)]
    assert run_book(ev) == [46, 46, 46, 18]


def test_p1_buy_takes_part_of_a_level():
    ev = [("add", 50, 10), ("add", 60, 10), ("buy", 4), ("quote", 6), ("quote", 7), ("buy", 6), ("quote", 10)]
    assert run_book(ev) == [200, 300, 360, 300, 600]


def test_p1_buy_larger_than_book_fills_what_is_there():
    ev = [("add", 30, 2), ("add", 31, 3), ("buy", 9), ("quote", 1), ("buy", 1), ("add", 40, 1), ("quote", 1)]
    assert run_book(ev) == [153, -1, 0, 40]


def test_p1_cancels():
    ev = [("add", 5, 4), ("add", 6, 4), ("add", 8, 4), ("cancel", 5, 4), ("quote", 4), ("cancel", 6, 1),
          ("quote", 4), ("quote", 9), ("cancel", 8, 4), ("quote", 3)]
    assert run_book(ev) == [24, 26, -1, 18]


def test_p1_cancel_whole_book():
    assert run_book([("add", 100, 5), ("cancel", 100, 5), ("quote", 1), ("buy", 1)]) == [-1, 0]


def test_p1_adds_at_same_price_merge():
    ev = [("add", 12, 1), ("add", 11, 2), ("add", 12, 3), ("add", 11, 4), ("quote", 7), ("quote", 10)]
    assert run_book(ev) == [78, 114]


def test_p1_level_refilled_after_buy():
    ev = [("add", 3, 2), ("add", 4, 2), ("buy", 3), ("add", 3, 5), ("quote", 6), ("buy", 7), ("quote", 1)]
    assert run_book(ev) == [10, 19, 19, -1]


def test_p1_new_best_price_after_buys():
    ev = [("add", 90, 3), ("add", 95, 3), ("buy", 2), ("add", 80, 1), ("add", 85, 2), ("quote", 4),
          ("buy", 5), ("quote", 2)]
    assert run_book(ev) == [180, 340, 435, 190]


def test_p1_big_prices_and_sizes():
    ev = [("add", B, B), ("add", B - 1, B), ("quote", 2 * B), ("quote", B + 1), ("buy", 3 * B), ("quote", 1)]
    assert run_book(ev) == [1999999999000000000, 1000000000000000000, 1999999999000000000, -1]


def test_p1_mixed_stream():
    assert _hidden_digest(run_book(_hidden_mixed(3000, 99))) == (1279, 34647817, 22199190105)


def test_p1_large_deep_book_is_fast():
    ev = _hidden_large(150_000)
    t = time.perf_counter()
    out = run_book(ev)
    took = time.perf_counter() - t
    assert _hidden_digest(out) == (75266, 53701169676459947028, 2699924865782277310518546)
    assert took < 4.0, f"150000 events took {took:.1f}s (limit 4s)"
