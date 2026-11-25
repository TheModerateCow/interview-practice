"""The background job queue of the web platform. Producers enqueue jobs into named queues
("emails", "webhooks", ...); workers lease the next job, then ack it or report a failure.
A lease is a visibility timeout: if it runs out without an ack the job goes back to READY
for another worker. Failed jobs are retried with exponential backoff until they run out of
attempts, then they move to the dead-letter queue, where an operator can redrive them.

Not safe for concurrent use: the API layer serialises calls. Times are caller-supplied Unix
seconds. Every call that takes ``now`` moves the queue clock forward first (starting due jobs
and taking back expired leases); ``now`` may never go backwards."""

from __future__ import annotations

from dataclasses import dataclass

from . import lifecycle
from .models import Code, Job, Lease, QueueError, Status
from .stats import Stats, stats_of
from .store import Store


@dataclass(frozen=True)
class Options:
    visibility: int = 30  # default lease length, seconds
    base_delay: int = 10  # backoff after the first failed attempt, seconds; doubles each attempt
    max_delay: int = 600  # cap on the backoff, seconds
    max_attempts: int = 3  # default attempts per job
    idempotency_ttl: int = 3600  # how long an idempotency key keeps returning its first job, seconds

    def __post_init__(self) -> None:
        if (self.visibility <= 0 or self.base_delay < 0 or self.max_delay < self.base_delay
                or self.max_attempts < 1 or self.idempotency_ttl < 0):
            raise _invalid("bad options")


class JobQueue:
    def __init__(self, options: Options | None = None) -> None:
        self._store = Store()
        self._options = options or Options()

    def enqueue(self, queue: str, payload: str, now: int, *, priority: int = 0, run_at: int | None = None,
                max_attempts: int = 0, key: str | None = None) -> str:
        """Adds a job and returns its id. ``priority``: higher runs first. ``run_at``: don't start before
        this time. ``max_attempts`` overrides the default (0 = default). ``key``: idempotency key, scoped
        to the named queue: if it was used in this queue less than idempotency_ttl seconds ago, nothing is
        added and the first job's id is returned."""
        lifecycle.advance(self._store, now)
        if not queue:
            raise _invalid("empty queue name")
        limit = self._options.max_attempts if max_attempts == 0 else max_attempts
        if limit < 1:
            raise _invalid("max_attempts must be at least 1")
        if key is not None:
            first = self._store.find_key(queue, key, now)
            if first is not None:
                return first
        job = self._store.add(queue, payload, priority, limit, now)
        if key is not None:
            self._store.remember_key(queue, key, job.id, now + self._options.idempotency_ttl)
        if run_at is not None and run_at > now:
            self._store.schedule(job, run_at)
        else:
            self._store.make_ready(job, now)
        return job.id

    def lease(self, queue: str, now: int, visibility: int | None = None) -> Lease | None:
        """Leases the next READY job of a queue for ``visibility`` seconds, or returns None if there is none."""
        if visibility is None:
            visibility = self._options.visibility
        if visibility <= 0:
            raise _invalid("visibility must be positive")
        lifecycle.advance(self._store, now)
        job = self._store.next_ready(queue)
        if job is None:
            return None
        self._store.lease(job, now + visibility)
        return Lease(job.id, job.lease_token, job.payload, job.attempts, job.lease_until)

    def ack(self, job_id: str, token: str, now: int) -> None:
        """The job is done: it is dropped and counted as completed."""
        self._store.drop(self._held(job_id, token, now), Status.COMPLETED)

    def fail(self, job_id: str, token: str, error: str, now: int) -> None:
        """The attempt failed: the job is retried after the backoff, or dead-lettered if it is out of attempts."""
        o = self._options
        lifecycle.record_failure(self._store, o.base_delay, o.max_delay, self._held(job_id, token, now), error, now)

    def extend(self, job_id: str, token: str, seconds: int, now: int) -> None:
        """Heartbeat: the lease now runs until ``now + seconds``."""
        if seconds <= 0:
            raise _invalid("seconds must be positive")
        self._store.set_deadline(self._held(job_id, token, now), now + seconds)

    def cancel(self, job_id: str, now: int) -> None:
        """Cancels a job that hasn't started (SCHEDULED or READY)."""
        lifecycle.advance(self._store, now)
        job = self._find(job_id)
        if job.status not in (Status.SCHEDULED, Status.READY):
            raise _invalid(f"{job_id} is {job.status.name}")
        self._store.drop(job, Status.CANCELLED)

    def redrive(self, job_id: str, now: int) -> None:
        """Moves a dead job back to READY with a fresh set of attempts."""
        lifecycle.advance(self._store, now)
        job = self._find(job_id)
        if job.status is not Status.DEAD:
            raise _invalid(f"{job_id} is {job.status.name}")
        job.attempts = 0
        self._store.make_ready(job, now)

    def dead_letters(self, queue: str) -> list[Job]:
        """The dead-letter queue of a named queue, oldest death first."""
        dead = [j.copy() for j in self._store.jobs_in(queue) if j.status is Status.DEAD]
        dead.sort(key=lambda j: (j.dead_at, j.seq))
        return dead

    def job(self, job_id: str) -> Job | None:
        """A copy of a live job, or None if there is none with that id."""
        j = self._store.get(job_id)
        return None if j is None else j.copy()

    def stats(self, queue: str, now: int) -> Stats:
        """The stats of a named queue at time ``now`` (an unknown queue has all zeros)."""
        return stats_of(self._store, queue, now)

    def _held(self, job_id: str, token: str, now: int) -> Job:
        """The job, if ``token`` is its current lease."""
        lifecycle.advance(self._store, now)
        job = self._find(job_id)
        if job.status is not Status.LEASED or job.lease_token != token:
            raise QueueError(Code.LEASE_LOST, f"{job_id}: {token} is not the current lease")
        return job

    def _find(self, job_id: str) -> Job:
        j = self._store.get(job_id)
        if j is None:
            raise QueueError(Code.NOT_FOUND, f"no live job {job_id}")
        return j


def _invalid(why: str) -> QueueError:
    return QueueError(Code.INVALID, why)
