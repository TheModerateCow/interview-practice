import time

from jobqueue import JobQueue, Options, QueueError


def _hidden_code(fn):
    try:
        fn()
        return "ok"
    except QueueError as e:
        return e.code.name


def _hidden_queue(visibility, base_delay, max_delay, max_attempts):
    return JobQueue(Options(visibility, base_delay, max_delay, max_attempts, 3600))


def _hidden_lease(lease):
    return "empty" if lease is None else f"{lease.job_id}#{lease.attempt}@{lease.until}"


def _hidden_drain(q, queue, now):
    """Leases and acks every job that is ready at now; returns their payloads in lease order."""
    out = []
    lease = q.lease(queue, now)
    while lease is not None:
        out.append(lease.payload)
        q.ack(lease.job_id, lease.token, now)
        lease = q.lease(queue, now)
    return ",".join(out)


def _hidden_status(q, job_id):
    j = q.job(job_id)
    return "gone" if j is None else f"{j.status.name}/{j.attempts}"


# ---------------------------------------------------------------- phase 1


def test_p1_heartbeat_keeps_the_lease():
    q = JobQueue()
    job_id = q.enqueue("payments", "capture-981", 100)
    a = q.lease("payments", 100)
    q.extend(job_id, a.token, 60, 120)
    assert _hidden_lease(q.lease("payments", 135)) == "empty"
    q.extend(job_id, a.token, 30, 170)
    assert _hidden_lease(q.lease("payments", 185)) == "empty"
    assert _hidden_code(lambda: q.ack(job_id, a.token, 195)) == "ok"
    assert _hidden_status(q, job_id) == "gone"


def test_p1_quick_retry_keeps_the_new_lease():
    q = _hidden_queue(30, 5, 600, 3)
    job_id = q.enqueue("payments", "capture-982", 0)
    a = q.lease("payments", 0)
    q.fail(job_id, a.token, "gateway 503", 2)
    b = q.lease("payments", 10)
    assert _hidden_lease(b) == f"{job_id}#2@40"
    assert _hidden_lease(q.lease("payments", 35)) == "empty"
    assert _hidden_code(lambda: q.ack(job_id, b.token, 38)) == "ok"


def test_p1_expired_lease_moves_to_the_next_worker():
    q = JobQueue()
    job_id = q.enqueue("webhooks", "deliver-7", 0)
    a = q.lease("webhooks", 0)
    assert _hidden_lease(q.lease("webhooks", 29)) == "empty"
    b = q.lease("webhooks", 30)
    assert _hidden_lease(b) == f"{job_id}#2@60"
    assert _hidden_code(lambda: q.ack(job_id, a.token, 31)) == "LEASE_LOST"
    assert _hidden_code(lambda: q.extend(job_id, a.token, 30, 31)) == "LEASE_LOST"
    assert _hidden_code(lambda: q.fail(job_id, a.token, "late", 31)) == "LEASE_LOST"
    q.extend(job_id, b.token, 10, 40)
    assert _hidden_lease(q.lease("webhooks", 49)) == "empty"
    c = q.lease("webhooks", 50)
    assert _hidden_lease(c) == f"{job_id}#3@80"
    assert _hidden_code(lambda: q.ack(job_id, b.token, 51)) == "LEASE_LOST"
    assert _hidden_code(lambda: q.ack(job_id, c.token, 52)) == "ok"


def test_p1_crashing_job_is_dead_lettered():
    q = _hidden_queue(30, 10, 600, 2)
    a = q.enqueue("imports", "csv-1", 0)
    assert _hidden_lease(q.lease("imports", 0)) == f"{a}#1@30"
    assert _hidden_lease(q.lease("imports", 29)) == "empty"
    assert _hidden_lease(q.lease("imports", 30)) == f"{a}#2@60"
    assert _hidden_lease(q.lease("imports", 60)) == "empty"
    assert _hidden_status(q, a) == "DEAD/2"
    assert q.job(a).last_error == "lease expired"
    b = q.enqueue("imports", "csv-2", 61)
    q.fail(b, q.lease("imports", 61).token, "parse error", 62)
    q.fail(b, q.lease("imports", 72).token, "parse error", 73)
    assert [str(j) for j in q.dead_letters("imports")] == [
        f"{a} DEAD attempts=2 lastError=lease expired",
        f"{b} DEAD attempts=2 lastError=parse error",
    ]
    assert _hidden_lease(q.lease("imports", 500)) == "empty"


def test_p1_redriven_job_gets_fresh_attempts():
    q = _hidden_queue(30, 10, 600, 2)
    job_id = q.enqueue("exports", "report-31", 0)
    q.fail(job_id, q.lease("exports", 0).token, "disk full", 1)
    q.fail(job_id, q.lease("exports", 11).token, "disk full", 12)
    assert _hidden_status(q, job_id) == "DEAD/2"
    q.redrive(job_id, 100)
    assert q.dead_letters("exports") == []
    lease = q.lease("exports", 100)
    assert _hidden_lease(lease) == f"{job_id}#1@130"
    q.fail(job_id, lease.token, "disk full", 101)
    assert _hidden_status(q, job_id) == "SCHEDULED/1"
    assert _hidden_lease(q.lease("exports", 111)) == f"{job_id}#2@141"


def test_p1_idempotency_keys_belong_to_their_queue():
    q = JobQueue()
    e1 = q.enqueue("emails", "welcome-42", 100, key="signup-42")
    b1 = q.enqueue("billing", "trial-42", 100, key="signup-42")
    assert e1 != b1, f"billing reused the emails job {e1}"
    assert q.enqueue("emails", "welcome-42", 105, key="signup-42") == e1
    assert q.enqueue("billing", "trial-42", 105, key="signup-42") == b1
    assert _hidden_drain(q, "billing", 110) == "trial-42"
    assert _hidden_drain(q, "emails", 110) == "welcome-42"


def test_p1_idempotency_window():
    q = JobQueue()
    a = q.enqueue("webhooks", "evt-1", 100, key="evt-1")
    lease = q.lease("webhooks", 200)
    q.ack(a, lease.token, 201)
    assert q.enqueue("webhooks", "evt-1", 3699, key="evt-1") == a
    assert _hidden_drain(q, "webhooks", 3699) == ""
    b = q.enqueue("webhooks", "evt-1", 3700, key="evt-1")
    assert a != b, "key should have lapsed at 3700"
    assert q.enqueue("webhooks", "evt-1", 3800, key="evt-1") == b
    assert _hidden_drain(q, "webhooks", 3800) == "evt-1"


def test_p1_retry_backoff_doubles_up_to_the_cap():
    q = _hidden_queue(30, 10, 25, 5)
    job_id = q.enqueue("reports", "weekly", 0)
    seen = []
    for before, at in [(0, 0), (9, 10), (29, 30), (54, 55), (79, 80)]:
        if before != at:
            seen.append(_hidden_lease(q.lease("reports", before)))
        lease = q.lease("reports", at)
        seen.append(_hidden_lease(lease))
        q.fail(job_id, lease.token, "timeout", at)
    assert ",".join(seen) == "job-1#1@30,empty,job-1#2@40,empty,job-1#3@60,empty,job-1#4@85,empty,job-1#5@110"
    assert _hidden_status(q, job_id) == "DEAD/5"
    assert q.job(job_id).last_error == "timeout"


def test_p1_lease_order():
    q = JobQueue()
    q.enqueue("jobs", "a", 0, run_at=50)
    q.enqueue("jobs", "b", 10)
    q.enqueue("jobs", "c", 20, priority=5)
    q.enqueue("jobs", "d", 30, priority=5, run_at=40)
    q.enqueue("jobs", "e", 30)
    q.enqueue("jobs", "f", 30, priority=-1)
    assert _hidden_drain(q, "jobs", 30) == "c,b,e,f"
    q.enqueue("jobs", "g", 45)
    q.enqueue("jobs", "h", 45, run_at=5)
    assert _hidden_drain(q, "jobs", 60) == "d,g,h,a"


def test_p1_cancel_errors_and_clock():
    q = JobQueue()
    a = q.enqueue("jobs", "a", 10)
    b = q.enqueue("jobs", "b", 10, run_at=100)
    c = q.enqueue("jobs", "c", 10)
    q.cancel(a, 11)
    q.cancel(b, 12)
    lease = q.lease("jobs", 13)
    assert lease.job_id == c
    assert _hidden_code(lambda: q.cancel(c, 14)) == "INVALID"
    assert _hidden_code(lambda: q.cancel(a, 14)) == "NOT_FOUND"
    assert _hidden_code(lambda: q.ack(c, "lease-999", 14)) == "LEASE_LOST"
    assert _hidden_code(lambda: q.redrive(c, 14)) == "INVALID"
    assert _hidden_code(lambda: q.enqueue("", "x", 14)) == "INVALID"
    assert _hidden_code(lambda: q.enqueue("jobs", "x", 14, max_attempts=-1)) == "INVALID"
    assert _hidden_code(lambda: q.lease("jobs", 14, 0)) == "INVALID"
    assert _hidden_code(lambda: q.extend(c, lease.token, 0, 14)) == "INVALID"
    assert _hidden_code(lambda: q.lease("jobs", 13)) == "BACKDATED"
    assert _hidden_code(lambda: q.ack(c, lease.token, 15)) == "ok"
    assert _hidden_code(lambda: q.ack(c, lease.token, 15)) == "NOT_FOUND"
    assert _hidden_drain(q, "jobs", 200) == ""
    assert _hidden_status(q, a) == "gone"


# ---------------------------------------------------------------- phase 2


def test_p2_counts_jobs_by_state():
    q = _hidden_queue(30, 100, 600, 2)
    q.enqueue("emails", "a", 10)
    q.enqueue("emails", "b", 12)
    q.enqueue("emails", "c", 12, run_at=500)
    q.enqueue("emails", "d", 13, priority=9)
    e = q.enqueue("emails", "e", 14, priority=8)
    f = q.enqueue("emails", "f", 15, priority=7, max_attempts=1)
    g = q.enqueue("emails", "g", 16, priority=6)
    h = q.enqueue("emails", "h", 17)
    q.enqueue("billing", "x", 17)
    q.lease("emails", 20)
    le = q.lease("emails", 20)
    lf = q.lease("emails", 20)
    lg = q.lease("emails", 20)
    q.fail(e, le.token, "500", 21)
    q.fail(f, lf.token, "400", 21)
    q.ack(g, lg.token, 22)
    q.cancel(h, 23)
    assert str(q.stats("emails", 40)) == "Stats[ready=2, scheduled=1, retrying=1, inFlight=1, dead=1, completed=1, oldestReadyAge=30, nextRunAt=121]"
    assert str(q.stats("billing", 40)) == "Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=23, nextRunAt=null]"


def test_p2_moves_the_clock_first():
    q = JobQueue()
    q.enqueue("webhooks", "a", 0)
    q.enqueue("webhooks", "b", 0, run_at=50)
    q.lease("webhooks", 5)
    assert str(q.stats("webhooks", 20)) == "Stats[ready=0, scheduled=1, retrying=0, inFlight=1, dead=0, completed=0, oldestReadyAge=0, nextRunAt=50]"
    assert str(q.stats("webhooks", 60)) == "Stats[ready=2, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=25, nextRunAt=null]"
    assert _hidden_code(lambda: q.stats("webhooks", 59)) == "BACKDATED"


def test_p2_age_counts_from_when_the_job_became_ready():
    q = _hidden_queue(30, 40, 600, 3)
    job_id = q.enqueue("reports", "monthly", 0, run_at=100)
    assert str(q.stats("reports", 150)) == "Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=50, nextRunAt=null]"
    q.fail(job_id, q.lease("reports", 150).token, "timeout", 160)
    assert str(q.stats("reports", 199)) == "Stats[ready=0, scheduled=0, retrying=1, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=200]"
    assert str(q.stats("reports", 230)) == "Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=30, nextRunAt=null]"


def test_p2_dead_letters_and_redrive():
    q = _hidden_queue(30, 10, 600, 1)
    a = q.enqueue("payments", "a", 0)
    q.enqueue("payments", "b", 0)
    la = q.lease("payments", 0)
    q.lease("payments", 0)
    q.fail(a, la.token, "card declined", 5)
    assert str(q.stats("payments", 40)) == "Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=2, completed=0, oldestReadyAge=0, nextRunAt=null]"
    q.redrive(a, 50)
    assert str(q.stats("payments", 70)) == "Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=1, completed=0, oldestReadyAge=20, nextRunAt=null]"


def test_p2_completed_per_queue_and_unknown_queue():
    q = JobQueue()
    for i in range(3):
        q.enqueue("emails", f"e{i}", i, key=f"k{i}")
    q.enqueue("emails", "e0-again", 3, key="k0")
    q.enqueue("billing", "b0", 3)
    for _ in range(2):
        lease = q.lease("emails", 10)
        q.ack(lease.job_id, lease.token, 10)
    lease = q.lease("billing", 12)
    q.ack(lease.job_id, lease.token, 12)
    assert str(q.stats("emails", 20)) == "Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=2, oldestReadyAge=18, nextRunAt=null]"
    assert str(q.stats("billing", 20)) == "Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=0, completed=1, oldestReadyAge=0, nextRunAt=null]"
    assert str(q.stats("nope", 20)) == "Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=null]"


# ---------------------------------------------------------------- phase 3


def test_p3_backlog_after_an_outage():
    q = _hidden_queue(30, 30, 600, 3)
    backlog, steps = 16_000, 22_400
    # A partner endpoint was down for two hours: webhook events piled up, a few of them
    # delivered twice, some deferred by ten minutes, a quarter flagged urgent.
    for i in range(backlog):
        run_at = i // 10 + 600 if i % 10 == 3 else None
        key = f"evt-{i - 1 if i % 25 == 24 else i}"
        q.enqueue("webhooks", f"evt-{i}", i // 10, key=key, priority=1 if i % 4 == 0 else 0, run_at=run_at)
    # It's back. Workers drain the backlog while live traffic keeps arriving.
    start = time.perf_counter()
    acked = failed = abandoned = cancelled = refused = idle = 0
    checksum = 0
    for s in range(steps):
        now = 10_000 + s // 20
        if s % 3 == 0:
            q.enqueue("webhooks", f"live-{s}", now, priority=2 if s % 9 == 0 else 0)
        if s % 97 == 0:
            victim = f"job-{1 + (s * 31) % backlog}"
            try:
                q.cancel(victim, now)
                cancelled += 1
            except QueueError:
                refused += 1
        lease = q.lease("webhooks", now)
        if lease is None:
            idle += 1
        else:
            n = int(lease.job_id[4:])
            if n % 41 == 0:
                abandoned += 1
            elif (n + lease.attempt) % 7 == 0:
                q.fail(lease.job_id, lease.token, "502", now)
                failed += 1
            else:
                q.ack(lease.job_id, lease.token, now)
                acked += 1
        if s % 500 == 499:
            st = q.stats("webhooks", now)
            checksum = (checksum * 31 + st.ready + 7 * st.retrying + 13 * st.in_flight + 17 * st.dead
                        + st.oldest_ready_age) % (1 << 61)
            assert time.perf_counter() - start < 10, "far too slow: giving up after 10 s (budget 2 s)"
    elapsed = time.perf_counter() - start
    got = (f"acked={acked} failed={failed} abandoned={abandoned} cancelled={cancelled} refused={refused} "
           f"idle={idle} checksum={checksum} {q.stats('webhooks', 10_000 + steps // 20 + 1000)}")
    assert got == (
        "acked=18632 failed=2840 abandoned=928 cancelled=113 refused=118 idle=0 checksum=1297322307213073607 "
        "Stats[ready=3932, scheduled=0, retrying=0, inFlight=0, dead=150, completed=18632, oldestReadyAge=1529, nextRunAt=null]"
    ), got
    assert elapsed < 2.0, f"draining took {elapsed:.2f}s, budget 2s"
