"""Build pipeline: fan-in DP over the release tree; inputs run in parallel, so merging a child is a min-max split."""
from dataclasses import dataclass


@dataclass
class Job:
    consumer: int
    cold: int
    warm: int


def fastest_release(jobs: list[Job], k: int) -> int:
    n = len(jobs)
    k = min(k, n)
    inputs: list[list[int]] = [[] for _ in range(n)]
    root = -1
    for i, job in enumerate(jobs):
        if job.consumer < 0:
            root = i
        else:
            inputs[job.consumer].append(i)
    if root < 0:
        return -1
    # BFS from the release over inputs; a job on a cycle is never reached.
    order = [root]
    for v in order:  # appending while iterating is fine: the loop sees the new entries
        order.extend(inputs[v])
    if len(order) != n:
        return -1
    # f[v][b]: fewest minutes to finish v using at most b warm caches in v's subtree.
    f: list[list[int] | None] = [None] * n
    for v in reversed(order):
        g = [0] * (k + 1)  # inputs ready with at most b warm: 0 with no inputs
        for c in inputs[v]:
            fc = f[c]
            g = [min(map(max, g[b::-1], fc[: b + 1])) for b in range(k + 1)]
            f[c] = None
        job = jobs[v]
        f[v] = [job.cold + g[0]] + [min(job.cold + g[b], job.warm + g[b - 1]) for b in range(1, k + 1)]
    return f[root][k]
