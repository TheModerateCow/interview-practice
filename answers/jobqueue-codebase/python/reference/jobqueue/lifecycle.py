"""The transitions driven by time and failures: the clock sweep that starts scheduled jobs and
takes back leases that ran out, retry backoff, and the dead-letter queue."""

import heapq

from .models import Code, Job, QueueError, Status
from .store import Store


def advance(store: Store, now: int) -> None:
    """Moves the queue clock to ``now`` and fires every timer due by then, in time order.

    Scheduled jobs whose time has come become READY as of their run time. A lease that ran out
    without an ack is taken back as of its deadline: the job is READY again, or DEAD if that
    lease was its last attempt."""
    if now < store.clock:
        raise QueueError(Code.BACKDATED, f"now {now} is before the queue clock {store.clock}")
    store.clock = now
    timers = store.timers
    while timers and timers[0][0] <= now:
        _, _, job_id, is_lease = heapq.heappop(timers)
        job = store.get(job_id)
        if job is None:
            continue
        if not is_lease:
            if job.status is Status.SCHEDULED and job.available_at <= now:
                store.make_ready(job, job.available_at)
        elif job.status is Status.LEASED and job.lease_until <= now:
            _expire_lease(store, job)


def _expire_lease(store: Store, job: Job) -> None:
    job.last_error = "lease expired"
    if job.attempts >= job.max_attempts:
        dead_letter(job, job.lease_until)
    else:
        store.make_ready(job, job.lease_until)


def retry_delay(base_delay: int, max_delay: int, attempts: int) -> int:
    """Backoff before the retry that follows attempt number ``attempts``: base, 2x base, 4x base ... capped at max_delay."""
    d = base_delay
    for _ in range(1, attempts):
        if d >= max_delay:
            break
        d *= 2
    return min(d, max_delay)


def record_failure(store: Store, base_delay: int, max_delay: int, job: Job, error: str, now: int) -> None:
    """A worker reported failure: retry after the backoff, or dead-letter the job if it is out of attempts."""
    job.last_error = error
    if job.attempts >= job.max_attempts:
        dead_letter(job, now)
    else:
        store.schedule(job, now + retry_delay(base_delay, max_delay, job.attempts))


def dead_letter(job: Job, at: int) -> None:
    job.status = Status.DEAD
    job.dead_at = at
