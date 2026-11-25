"""In-memory state: every live job (scheduled, ready, leased or dead), a ready heap per named
queue, one timer heap for run times and lease deadlines, and the idempotency keys. Completed
and cancelled jobs are dropped; only a per-queue count of completions is kept."""

import heapq
from collections import defaultdict
from collections.abc import Iterable

from .models import Job, Status
from .ready import ReadyQueue


class Store:
    def __init__(self) -> None:
        # The queue clock: the latest ``now`` any call has passed.
        self.clock = 0
        # Wake-ups as (at, seq, job_id, is_lease): a run time comes, or a lease deadline passes.
        self.timers: list[tuple[int, int, str, bool]] = []
        self._job_seq = 0
        self._timer_seq = 0
        self._lease_seq = 0
        self._jobs: dict[str, Job] = {}
        self._by_queue: dict[str, dict[str, Job]] = defaultdict(dict)
        self._ready: dict[str, ReadyQueue] = defaultdict(ReadyQueue)
        self._keys: dict[str, tuple[str, int]] = {}
        self._completed: dict[str, int] = defaultdict(int)

    def add(self, queue: str, payload: str, priority: int, max_attempts: int, now: int) -> Job:
        self._job_seq += 1
        job = Job(f"job-{self._job_seq}", queue, payload, priority, max_attempts, self._job_seq, now)
        self._jobs[job.id] = job
        self._by_queue[queue][job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def jobs_in(self, queue: str) -> Iterable[Job]:
        """The live jobs of a queue, in enqueue order."""
        return self._by_queue[queue].values() if queue in self._by_queue else ()

    def completed_in(self, queue: str) -> int:
        """Lifetime number of acked jobs in a queue."""
        return self._completed.get(queue, 0)

    def drop(self, job: Job, end: Status) -> None:
        """Ends a job for good (COMPLETED or CANCELLED) and forgets it."""
        job.status = end
        del self._jobs[job.id]
        del self._by_queue[job.queue][job.id]
        if end is Status.COMPLETED:
            self._completed[job.queue] += 1

    def make_ready(self, job: Job, at: int) -> None:
        """Marks a job READY as of ``at`` and queues it for leasing."""
        job.status = Status.READY
        job.ready_at = at
        self._ready[job.queue].add(job)

    def next_ready(self, queue: str) -> Job | None:
        """Removes and returns the next job to lease from a queue, or None."""
        return self._ready[queue].poll() if queue in self._ready else None

    def schedule(self, job: Job, at: int) -> None:
        """Parks a job until ``at``."""
        job.status = Status.SCHEDULED
        job.available_at = at
        self._push_timer(at, job.id, False)

    def lease(self, job: Job, until: int) -> None:
        """Hands a job out under a fresh lease token until ``until``."""
        job.status = Status.LEASED
        job.attempts += 1
        self._lease_seq += 1
        job.lease_token = f"lease-{self._lease_seq}"
        self.set_deadline(job, until)

    def set_deadline(self, job: Job, until: int) -> None:
        """Moves the current lease's deadline."""
        job.lease_until = until
        self._push_timer(until, job.id, True)

    def find_key(self, queue: str, key: str, now: int) -> str | None:
        """The job an idempotency key still points at in this queue, or None once the key has lapsed."""
        k = self._keys.get(_key_of(queue, key))
        return k[0] if k is not None and now < k[1] else None

    def remember_key(self, queue: str, key: str, job_id: str, until: int) -> None:
        self._keys[_key_of(queue, key)] = (job_id, until)

    def _push_timer(self, at: int, job_id: str, lease: bool) -> None:
        self._timer_seq += 1
        heapq.heappush(self.timers, (at, self._timer_seq, job_id, lease))


def _key_of(queue: str, key: str) -> tuple[str, str]:
    return key
