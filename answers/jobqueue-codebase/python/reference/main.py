"""Drives the job queue from stdin, one command per line, and prints each result
(or "error: ..."):

    enqueue <ts> <queue> <payload> [priority=N] [runAt=N] [attempts=N] [key=K]
    lease <ts> <queue> [visibility]
    ack <ts> <job> <token>
    fail <ts> <job> <token> <error>
    extend <ts> <job> <token> <seconds>
    cancel <ts> <job>
    redrive <ts> <job>
    job <job>
    dead <queue>
    stats <ts> <queue>

Times are Unix seconds. The queue uses the default options. Add your own commands as you need them.
"""

import sys

from jobqueue import JobQueue, QueueError


def run(q: JobQueue, f: list[str]) -> str:
    cmd = f[0]
    if cmd == "enqueue":
        kw: dict = {}
        for opt in f[4:]:
            k, _, v = opt.partition("=")
            if k == "priority":
                kw["priority"] = int(v)
            elif k == "runAt":
                kw["run_at"] = int(v)
            elif k == "attempts":
                kw["max_attempts"] = int(v)
            elif k == "key":
                kw["key"] = v
            else:
                raise ValueError(f"unknown option {k}")
        return q.enqueue(f[2], f[3], int(f[1]), **kw)
    if cmd == "lease":
        lease = q.lease(f[2], int(f[1]), int(f[3]) if len(f) > 3 else None)
        if lease is None:
            return "empty"
        return f"{lease.job_id} {lease.token} attempt={lease.attempt} until={lease.until} {lease.payload}"
    if cmd == "ack":
        q.ack(f[2], f[3], int(f[1]))
    elif cmd == "fail":
        q.fail(f[2], f[3], f[4], int(f[1]))
    elif cmd == "extend":
        q.extend(f[2], f[3], int(f[4]), int(f[1]))
    elif cmd == "cancel":
        q.cancel(f[2], int(f[1]))
    elif cmd == "redrive":
        q.redrive(f[2], int(f[1]))
    elif cmd == "job":
        j = q.job(f[1])
        return "none" if j is None else str(j)
    elif cmd == "dead":
        return "[" + ", ".join(str(j) for j in q.dead_letters(f[1])) + "]"
    elif cmd == "stats":
        return str(q.stats(f[2], int(f[1])))
    else:
        raise ValueError(f"unknown command {cmd}")
    return "ok"


def main() -> None:
    q = JobQueue()
    for line in sys.stdin:
        f = line.split()
        if not f:
            continue
        try:
            print(run(q, f))
        except (QueueError, ValueError, IndexError) as e:
            print("error:", e)


if __name__ == "__main__":
    main()
