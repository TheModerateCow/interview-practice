"""The jobs of one named queue that can be leased now."""

from .models import Job, Status


def order(job: Job) -> tuple[int, int, int]:
    """Best first: higher priority, then the job that has been ready longest, then the job enqueued first."""
    return (-job.priority, job.ready_at, job.seq)


class ReadyQueue:
    def __init__(self) -> None:
        self._jobs: list[Job] = []

    def add(self, job: Job) -> None:
        self._jobs.append(job)

    def poll(self) -> Job | None:
        """Removes and returns the best job that is still READY, or None."""
        self._jobs = [j for j in self._jobs if j.status is Status.READY]
        if not self._jobs:
            return None
        best = min(self._jobs, key=order)
        self._jobs.remove(best)
        return best
