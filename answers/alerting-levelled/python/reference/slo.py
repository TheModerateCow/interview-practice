"""SLO monitoring for API services: per-minute samples, error budgets, compliance stretches and burn-rate alerts."""

PPM = 1_000_000


class _Service:
    __slots__ = ("req", "err", "budget", "alert")

    def __init__(self) -> None:
        self.req: list[int] = []  # requests per minute, index = minute; gaps hold 0
        self.err: list[int] = []
        self.budget: int | None = None
        self.alert: tuple[int, int, int] | None = None  # (long window, short window, burn)


class SloMonitor:
    def __init__(self) -> None:
        self._svc: dict[str, _Service] = {}

    # ---- level 1 ----
    def add_service(self, service: str) -> bool:
        if service in self._svc:
            return False
        self._svc[service] = _Service()
        return True

    def ingest(self, service: str, first_minute: int, requests: list[int], errors: list[int]) -> bool:
        s = self._svc.get(service)
        if s is None or not requests or len(requests) != len(errors) or first_minute < len(s.req):
            return False
        if any(e > r for r, e in zip(requests, errors)):
            return False
        gap = first_minute - len(s.req)
        s.req.extend([0] * gap)
        s.err.extend([0] * gap)
        s.req.extend(requests)
        s.err.extend(errors)
        return True

    def _sums(self, s: _Service, start: int, end: int) -> tuple[int, int]:
        lo, hi = max(start, 0), end + 1
        return sum(s.req[lo:hi]), sum(s.err[lo:hi])

    def error_rate(self, service: str, start: int, end: int) -> int | None:
        s = self._svc.get(service)
        if s is None:
            return None
        r, e = self._sums(s, start, end)
        return None if r == 0 else e * PPM // r

    def latest_minute(self, service: str) -> int | None:
        s = self._svc.get(service)
        return len(s.req) - 1 if s and s.req else None

    # ---- level 2 ----
    def set_budget(self, service: str, budget_ppm: int) -> bool:
        s = self._svc.get(service)
        if s is None:
            return False
        s.budget = budget_ppm
        return True

    def budget_left(self, service: str, start: int, end: int) -> int | None:
        s = self._svc.get(service)
        if s is None or s.budget is None:
            return None
        r, e = self._sums(s, start, end)
        return r * s.budget // PPM - e

    def over_budget(self, end: int, window: int) -> list[str]:
        hits = []
        for name, s in self._svc.items():
            if s.budget is None:
                continue
            r, e = self._sums(s, end - window + 1, end)
            if r > 0 and e * PPM > r * s.budget:
                hits.append((-(e * PPM // r), name))
        hits.sort()
        return ["%s:%d" % (name, -neg) for neg, name in hits]

    # ---- level 3 ----
    def longest_within_budget(self, service: str, start: int, end: int) -> str | None:
        s = self._svc.get(service)
        if s is None or s.budget is None:
            return None
        b, req, err = s.budget, s.req, s.err
        hi = min(end, len(req) - 1)
        n = end - start + 1
        # prefix[k]: errors*1e6 - requests*budget over minutes start..start+k-1 (minutes past the data are empty)
        prefix = [0] * (n + 1)
        acc = 0
        for k in range(n):
            m = start + k
            if m <= hi:
                acc += err[m] * PPM - req[m] * b
            prefix[k + 1] = acc
        # Stretch i..j-1 is within budget when prefix[j] <= prefix[i]. Only a strict running maximum can be the
        # best start: an earlier start that is at least as high reaches every end it reaches, and is longer.
        starts: list[int] = []
        for i in range(n + 1):
            if not starts or prefix[i] > prefix[starts[-1]]:
                starts.append(i)
        best_len, best_start = 0, 0
        for j in range(n, -1, -1):
            while starts and prefix[starts[-1]] >= prefix[j]:
                i = starts.pop()
                if j - i >= best_len:  # starts pop latest first, so >= keeps the earliest of equal lengths
                    best_len, best_start = j - i, i
            if not starts:
                break
        if best_len == 0:
            return ""
        return "%d-%d" % (start + best_start, start + best_start + best_len - 1)

    # ---- level 4 ----
    def amend(self, service: str, minute: int, requests: int, errors: int) -> bool:
        s = self._svc.get(service)
        if s is None or minute >= len(s.req) or errors > requests:
            return False
        s.req[minute] = requests
        s.err[minute] = errors
        return True

    def set_alert(self, service: str, long_window: int, short_window: int, burn: int) -> bool:
        s = self._svc.get(service)
        if s is None or s.budget is None:
            return False
        s.alert = (long_window, short_window, burn)
        return True

    def alert_timeline(self, service: str, start: int, end: int) -> list[str]:
        s = self._svc.get(service)
        if s is None or s.alert is None:
            return []
        long_w, short_w, burn = s.alert
        limit = s.budget * burn
        lo = max(0, start - long_w + 1)
        n = len(s.req)
        # R[k], E[k]: requests and errors over minutes lo..lo+k-1
        R, E = [0], [0]
        for m in range(lo, end + 1):
            r, e = (s.req[m], s.err[m]) if m < n else (0, 0)
            R.append(R[-1] + r)
            E.append(E[-1] + e)

        def burning(t: int, w: int) -> bool:
            a, b = max(lo, t - w + 1) - lo, t + 1 - lo
            return (E[b] - E[a]) * PPM > (R[b] - R[a]) * limit

        out, run = [], None
        for t in range(start, end + 1):
            if burning(t, long_w) and burning(t, short_w):
                if run is None:
                    run = t
            elif run is not None:
                out.append("%d-%d" % (run, t - 1))
                run = None
        if run is not None:
            out.append("%d-%d" % (run, end))
        return out
