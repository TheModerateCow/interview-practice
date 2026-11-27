"""A monorepo release pipeline: jobs linked to the one job that consumes their artifact, a run tracker, cycle checks,
finish-time estimates and choosing which caches to pre-warm."""

import heapq


class Pipeline:
    def __init__(self) -> None:
        self._minutes: dict[str, int] = {}
        self._warm: dict[str, int] = {}
        self._consumer: dict[str, str] = {}
        self._inputs: dict[str, set[str]] = {}
        self._done: set[str] = set()

    def add_job(self, job: str, minutes: int) -> bool:
        if job in self._minutes:
            return False
        self._minutes[job] = minutes
        self._inputs[job] = set()
        return True

    def set_consumer(self, job: str, consumer: str) -> bool:
        if job not in self._minutes or consumer not in self._minutes or consumer in self._done:
            return False
        old = self._consumer.get(job)
        if old is not None:
            self._inputs[old].discard(job)
        self._consumer[job] = consumer
        self._inputs[consumer].add(job)
        return True

    def inputs(self, job: str) -> list[str]:
        return sorted(self._inputs.get(job, ()))

    def _ready(self, job: str) -> bool:
        return job not in self._done and all(i in self._done for i in self._inputs[job])

    def ready(self) -> list[str]:
        return sorted(j for j in self._minutes if self._ready(j))

    def finish(self, job: str) -> bool:
        if job not in self._minutes or not self._ready(job):
            return False
        self._done.add(job)
        return True

    def stuck(self) -> list[str]:
        # Each job has at most one consumer: follow the links from every job; a walk that meets itself found a cycle.
        state: dict[str, int] = {}  # 1 = on the current walk, 2 = settled
        out = []
        for start in self._minutes:
            walk = []
            v: str | None = start
            while v is not None and v not in state:
                state[v] = 1
                walk.append(v)
                v = self._consumer.get(v)
            if v is not None and state[v] == 1:
                out.extend(walk[walk.index(v):])
            for w in walk:
                state[w] = 2
        return sorted(out)

    def run_order(self) -> list[str]:
        waiting = {j: sum(i not in self._done for i in self._inputs[j]) for j in self._minutes if j not in self._done}
        heap = [j for j, w in waiting.items() if w == 0]
        heapq.heapify(heap)
        out = []
        while heap:
            j = heapq.heappop(heap)
            out.append(j)
            c = self._consumer.get(j)
            if c in waiting:
                waiting[c] -= 1
                if waiting[c] == 0:
                    heapq.heappush(heap, c)
        return out

    def _upstream(self, job: str) -> list[str] | None:
        """Unfinished jobs feeding job (job first, each before its inputs); None if job is on a cycle."""
        order = [job]
        for v in order:  # the loop also visits what it appends
            for i in self._inputs[v]:
                if i in self._done:
                    continue
                if i == job:
                    return None
                order.append(i)
        return order

    def _times(self, job: str) -> dict[str, int] | None:
        order = self._upstream(job)
        if order is None:
            return None
        t: dict[str, int] = {}
        for v in reversed(order):
            t[v] = self._minutes[v] + max((t[i] for i in self._inputs[v] if i not in self._done), default=0)
        return t

    def finish_time(self, job: str) -> int | None:
        if job not in self._minutes:
            return None
        if job in self._done:
            return 0
        t = self._times(job)
        return None if t is None else t[job]

    def critical_path(self, job: str) -> list[str]:
        if job not in self._minutes or job in self._done:
            return []
        t = self._times(job)
        if t is None:
            return []
        path = [job]
        while True:
            live = [i for i in self._inputs[path[-1]] if i not in self._done]
            if not live:
                return path[::-1]
            path.append(min(live, key=lambda i: (-t[i], i)))

    def set_warm(self, job: str, minutes: int) -> bool:
        if job not in self._minutes or minutes > self._minutes[job]:
            return False
        self._warm[job] = minutes
        return True

    def fastest_finish(self, job: str, k: int) -> int | None:
        if job not in self._minutes:
            return None
        if job in self._done:
            return 0
        order = self._upstream(job)
        if order is None:
            return None
        k = min(k, len(order))
        # f[v][b]: fewest minutes to finish v with at most b of its upstream jobs warmed.
        f: dict[str, list[int]] = {}
        for v in reversed(order):
            g = [0] * (k + 1)  # when v's inputs are all done, with at most b warmed among them
            for c in self._inputs[v]:
                if c in self._done:
                    continue
                fc = f.pop(c)
                # inputs run in parallel: split b between those so far and c, and wait for the slower side
                g = [min(map(max, g[b::-1], fc[: b + 1])) for b in range(k + 1)]
            cold = self._minutes[v]
            warm = self._warm.get(v, cold)
            f[v] = [cold + g[0]] + [min(cold + g[b], warm + g[b - 1]) for b in range(1, k + 1)]
        return f[job][k]
