"""The job model, the lease handed to workers, and the errors."""

from __future__ import annotations

import copy
import enum
from typing import NamedTuple


class Code(enum.Enum):
    # No live job has that id (it never existed, or it completed or was cancelled).
    NOT_FOUND = "NOT_FOUND"
    # The caller's lease is no longer the job's current lease: it ran out, or someone else holds it now.
    LEASE_LOST = "LEASE_LOST"
    # A bad argument, or an operation that doesn't apply to the job's state.
    INVALID = "INVALID"
    # A timestamp older than the queue clock.
    BACKDATED = "BACKDATED"


class QueueError(Exception):
    """Every error the job queue reports. Callers branch on ``code``."""

    def __init__(self, code: Code, message: str) -> None:
        super().__init__(f"{code.name}: {message}")
        self.code = code


class Status(enum.Enum):
    """Life cycle: SCHEDULED -> READY -> LEASED -> (COMPLETED | SCHEDULED for a retry | DEAD)."""

    SCHEDULED = "SCHEDULED"
    READY = "READY"
    LEASED = "LEASED"
    COMPLETED = "COMPLETED"
    DEAD = "DEAD"
    CANCELLED = "CANCELLED"


class Lease(NamedTuple):
    """What a worker gets from ``JobQueue.lease``: the token to ack, fail or extend with."""

    job_id: str
    token: str
    payload: str
    attempt: int
    until: int


class Job:
    """One unit of background work and where it is in its life. The queue owns these objects;
    callers only ever see copies (see ``JobQueue.job``)."""

    def __init__(self, id: str, queue: str, payload: str, priority: int, max_attempts: int, seq: int,
                 enqueued_at: int) -> None:
        self.id = id
        self.queue = queue
        self.payload = payload
        self.priority = priority
        self.max_attempts = max_attempts
        self.seq = seq
        self.enqueued_at = enqueued_at
        self.status = Status.SCHEDULED
        # Leases handed out so far; a lease that runs out without an ack counts as an attempt.
        self.attempts = 0
        # When a SCHEDULED job may run (its run time, or the end of its retry backoff).
        self.available_at = 0
        # When the job last became READY. Jobs of equal priority are leased oldest-ready first.
        self.ready_at = 0
        self.lease_until = 0
        self.lease_token = ""
        self.last_error = ""
        self.dead_at = 0

    def copy(self) -> Job:
        return copy.copy(self)

    def __str__(self) -> str:
        err = f" lastError={self.last_error}" if self.last_error else ""
        return f"{self.id} {self.status.name} attempts={self.attempts}{err}"
