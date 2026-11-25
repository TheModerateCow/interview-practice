# Background job queue

You've joined the platform team that owns the **job queue** behind a web product. Request handlers don't send emails, call webhooks or build reports themselves: they **enqueue** a job into a named queue (`emails`, `webhooks`, `billing`, ...) and a pool of workers does the work.

A worker **leases** the next job of a queue. The lease is a visibility timeout: while it lasts no other worker gets that job, and the worker can **extend** it as a heartbeat. The worker then **acks** the job (done, and it's dropped) or reports a **failure**, after which the job is retried with exponential backoff. A lease that runs out without an ack also counts as a failed attempt, and the job goes back to the queue for another worker. A job that runs out of attempts moves to the **dead-letter queue**, where an operator can **redrive** it. Jobs have a **priority**, may be **scheduled** for later, and may carry an **idempotency key** so a producer that retries an enqueue doesn't create the job twice. Keys belong to their queue.

Times are caller-supplied Unix seconds. Every call that takes `now` moves the queue clock forward first, which starts the jobs whose time has come and takes back leases that ran out. `now` may never go backwards (`BACKDATED`). Errors are `QueueException`s with a `code`.

The code is a small Java 21 package (default package, standard library only): the `JobQueue` API, the job model and errors, an in-memory store with a ready queue per named queue and a timer heap, the lifecycle rules (clock sweep, backoff, dead-lettering), stats, and a stdin driver in `Main.java`. Read around before you change anything.

The round has **3 phases**: fix the bugs below, build queue stats, then a third part that opens once phase 2 passes (or with 15 minutes left, or when you press **Next part**).

## Phase 1: bug report

> **JOBS-412 · three incidents from this week's on-call log**
>
> 1. **Card captures charged twice.** Some `payments` jobs were processed by two workers at once. Worker logs show the first worker heartbeating (extending its lease) the whole time, yet a second worker leased the same job about 30 seconds in, and the first worker's ack then failed with `LEASE_LOST`. It also happened once to a job that had failed and been retried within a few seconds, with no heartbeat involved.
> 2. **Redrive doesn't stick.** After the export bucket was fixed, ops redrove the dead `exports` jobs. The few that hit one more transient error went straight back to the dead-letter queue, with no retry and no backoff.
> 3. **Missing welcome emails.** Signup enqueues a `billing` job and an `emails` job, both with the key `signup-<user>`. Since then no new user gets a welcome email, and the `emails` enqueue returns the id of the billing job.

This test reproduces item 1 and fails today. Paste it into a `*Test.java` file to use it:

```java
public class HeartbeatTest {
    static void testHeartbeatKeepsTheLease() {
        JobQueue q = new JobQueue();                    // 30-second leases by default
        String id = q.enqueue("payments", "capture-1", 100);
        JobQueue.Lease a = q.lease("payments", 100);    // until 130
        q.extend(id, a.token(), 60, 120);               // heartbeat: now until 180
        Expect.eq(null, q.lease("payments", 135));      // nobody else may get it
        q.ack(id, a.token(), 170);
    }
}
```

Fix the cause of each one, not just the symptom.

## Phase 2: queue stats

Implement `Stats.of` in `Stats.java` (it backs `JobQueue.stats`):

```java
public Stats stats(String queue, long now)
public record Stats(int ready, int scheduled, int retrying, int inFlight, int dead, int completed,
                    long oldestReadyAge, Long nextRunAt)
```

It's what the ops dashboard and the worker autoscaler read. It only reports; it changes no job.

- **Clock.** Like every call that takes `now`, it moves the clock forward first, so a job whose run time has come is ready, and a lease that ran out is no longer in flight (the job is ready again, or dead if that was its last attempt). A `now` older than the clock throws `BACKDATED`.
- **Counts**, for the jobs of this queue only:
  - `ready`: jobs a lease would hand out now.
  - `scheduled`: jobs waiting for their first run (`runAt` in the future).
  - `retrying`: jobs waiting out a retry backoff.
  - `inFlight`: jobs under a lease.
  - `dead`: jobs in the dead-letter queue (a redriven job is no longer dead).
  - `completed`: jobs ever acked in this queue. Cancelled jobs count nowhere.
- **`oldestReadyAge`**: `now` minus the time the longest-waiting ready job *became ready*, 0 if no job is ready. A job becomes ready when it's enqueued, at its `runAt` if it was scheduled, at the end of its backoff if it's a retry, at its lease deadline if its lease ran out, and when it's redriven. It is not when the clock happened to notice.
- **`nextRunAt`**: the earliest time a scheduled or retrying job becomes ready, `null` if there is none.
- A queue that has never been used has all zeros and `nextRunAt` null.

### Example

```
q = new JobQueue()                                     // 30 s leases, backoff starts at 10 s
enqueue("reports", "monthly", 0, opts().runAt(100))    // job-1
enqueue("reports", "weekly", 0, opts().priority(5))    // job-2
lease("reports", 10)                                   // job-2, until 40
fail("job-2", token, "timeout", 20)                    // retry at 30
stats("reports", 25)  -> Stats[ready=0, scheduled=1, retrying=1, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=30]
lease("reports", 150)                                  // job-2 again (priority 5), until 180
stats("reports", 150) -> Stats[ready=1, scheduled=0, retrying=0, inFlight=1, dead=0, completed=0, oldestReadyAge=50, nextRunAt=null]
```

## Checking your work

- **Run** runs `Main.java`, which reads commands from stdin (`enqueue`, `lease`, `ack`, `fail`, `extend`, `cancel`, `redrive`, `job`, `dead`, `stats`; see the top of the file). Extend it as you like.
- **My tests** runs your own `*Test.java` files: every `static void` method whose name starts with `test`, checked with `Expect.eq`, `Expect.isTrue` and `Expect.raises` (no JUnit). `ExampleTest.java` is an example to copy.
- **Submit** runs the hidden tests for every phase you've unlocked.
