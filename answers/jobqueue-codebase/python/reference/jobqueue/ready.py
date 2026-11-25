"""The jobs of one named queue that can be leased now."""

import heapq

from .models import Job, Status


def order(job: Job) -> tuple[int, int, int]:
    """Best first: higher priority, then the job that has been ready longest, then the job enqueued first."""
    return (-job.priority, job.ready_at, job.seq)


class ReadyQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[tuple[int, int, int], Job]] = []

    def add(self, job: Job) -> None:
        heapq.heappush(self._heap, (order(job), job))

    def poll(self) -> Job | None:
        """Removes and returns the best job that is still READY, or None. A job cancelled while it
        waits stays in the heap until it reaches the top, and is dropped then."""
        while self._heap:
            _, job = heapq.heappop(self._heap)
            if job.status is Status.READY:
                return job
        return None
