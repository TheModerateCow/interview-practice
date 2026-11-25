"""A point-in-time view of one named queue, for the ops dashboard and the worker autoscaler."""

from __future__ import annotations

from dataclasses import dataclass

from . import lifecycle
from .models import Status
from .store import Store


@dataclass(frozen=True)
class Stats:
    ready: int  # jobs a lease would hand out now
    scheduled: int  # jobs waiting for their first run time
    retrying: int  # jobs waiting out a retry backoff
    in_flight: int  # jobs under a lease
    dead: int  # jobs in the dead-letter queue
    completed: int  # jobs acked in this queue, ever
    oldest_ready_age: int  # how long the longest-waiting READY job has been ready, 0 if none
    next_run_at: int | None  # the earliest time a scheduled or retrying job becomes ready, None if none

    def __str__(self) -> str:
        nxt = "null" if self.next_run_at is None else self.next_run_at
        return (f"Stats[ready={self.ready}, scheduled={self.scheduled}, retrying={self.retrying}, "
                f"inFlight={self.in_flight}, dead={self.dead}, completed={self.completed}, "
                f"oldestReadyAge={self.oldest_ready_age}, nextRunAt={nxt}]")


def stats_of(store: Store, queue: str, now: int) -> Stats:
    """Computes the stats of ``queue`` at time ``now``. See problem.md for the rules."""
    lifecycle.advance(store, now)
    ready = scheduled = retrying = in_flight = dead = 0
    oldest: int | None = None
    nxt: int | None = None
    for j in store.jobs_in(queue):
        if j.status is Status.READY:
            ready += 1
            oldest = j.ready_at if oldest is None else min(oldest, j.ready_at)
        elif j.status is Status.SCHEDULED:
            if j.attempts == 0:
                scheduled += 1
            else:
                retrying += 1
            nxt = j.available_at if nxt is None else min(nxt, j.available_at)
        elif j.status is Status.LEASED:
            in_flight += 1
        elif j.status is Status.DEAD:
            dead += 1
    return Stats(ready, scheduled, retrying, in_flight, dead, store.completed_in(queue),
                 0 if oldest is None else now - oldest, nxt)
