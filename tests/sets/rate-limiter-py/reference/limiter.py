from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window log limiter: at most `limit` allowed calls per key in any window of `window` seconds."""

    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self._hits = defaultdict(deque)

    def _prune(self, key, ts):
        q = self._hits[key]
        while q and q[0] <= ts - self.window:
            q.popleft()
        return q

    def allow(self, key, ts):
        q = self._prune(key, ts)
        if len(q) >= self.limit:
            return False
        q.append(ts)
        return True

    def remaining(self, key, ts):
        return self.limit - len(self._prune(key, ts))

    def reset(self, key):
        self._hits.pop(key, None)
