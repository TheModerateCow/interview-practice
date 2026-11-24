class RateLimiter:
    def __init__(self, limit, window):
        raise NotImplementedError

    def allow(self, key, ts):
        raise NotImplementedError
