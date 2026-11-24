# Rate limiter

Implement `RateLimiter(limit, window)` in `limiter.py`.

`allow(key, ts) -> bool` records a call for `key` at timestamp `ts` (seconds, an int; calls arrive in non-decreasing
order) and returns `True` if it is allowed. A call is allowed when fewer than `limit` allowed calls for that key fall in
the sliding window `(ts - window, ts]`. Rejected calls are not recorded. Keys are independent.

Example with `RateLimiter(2, 10)`: `allow("a", 0)` True, `allow("a", 5)` True, `allow("a", 9)` False,
`allow("a", 10)` True (the call at 0 has left the window).

`main.py` reads `key ts` lines from stdin and prints `True`/`False` per line.
