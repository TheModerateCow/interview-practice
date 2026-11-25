# Background job queue

You've joined the platform team that owns the **job queue** behind a web product. Request handlers don't send emails, call webhooks or build reports themselves: they **enqueue** a job into a named queue (`emails`, `webhooks`, `billing`, ...) and a pool of workers does the work.

A worker **leases** the next job of a queue. The lease is a visibility timeout: while it lasts no other worker gets that job, and the worker can **extend** it as a heartbeat. The worker then **acks** the job (done, and it's dropped) or reports a **failure**, after which the job is retried with exponential backoff. A lease that runs out without an ack also counts as a failed attempt, and the job goes back to the queue for another worker. A job that runs out of attempts moves to the **dead-letter queue**, where an operator can **redrive** it. Jobs have a **priority**, may be **scheduled** for later, and may carry an **idempotency key** so a producer that retries an enqueue doesn't create the job twice. Keys belong to their queue.

Times are caller-supplied Unix seconds. Every call that takes `now` moves the queue clock forward first, which starts the jobs whose time has come and takes back leases that ran out. `now` may never go backwards (`BACKDATED`). Errors are `*QueueError`s with a `Code` (`NotFound`, `LeaseLost`, `Invalid`, `Backdated`).

The code is a small Go package (module and package `jobqueue`, standard library only): the `JobQueue` API (`service.go`), the job model and errors (`models.go`), an in-memory store with a timer heap (`store.go`) and a ready queue per named queue (`ready.go`), the lifecycle rules (clock sweep, backoff, dead-lettering in `lifecycle.go`), stats (`stats.go`), and a stdin driver in `cmd/run/main.go`. Read around before you change anything.

The round has **3 phases**: fix the bugs below, build queue stats, then a third part that opens once phase 2 passes (or with 15 minutes left, or when you press **Next part**).

## Phase 1: bug report

> **JOBS-412 · three incidents from this week's on-call log**
>
> 1. **Card captures charged twice.** Some `payments` jobs were processed by two workers at once. Worker logs show the first worker heartbeating (extending its lease) the whole time, yet a second worker leased the same job about 30 seconds in, and the first worker's ack then failed with `LEASE_LOST`. It also happened once to a job that had failed and been retried within a few seconds, with no heartbeat involved.
> 2. **Redrive doesn't stick.** After the export bucket was fixed, ops redrove the dead `exports` jobs. The few that hit one more transient error went straight back to the dead-letter queue, with no retry and no backoff.
> 3. **Missing welcome emails.** Signup enqueues a `billing` job and an `emails` job, both with the key `signup-<user>`. Since then no new user gets a welcome email, and the `emails` enqueue returns the id of the billing job.

This test reproduces item 1 and fails today. Paste it into a `*_test.go` file to use it:

```go
func TestHeartbeatKeepsTheLease(t *testing.T) {
	q := New()                                              // 30-second leases by default
	id, _ := q.Enqueue("payments", "capture-1", 100, EnqueueOptions{})
	a, _ := q.Lease("payments", 100)                        // until 130
	q.Extend(id, a.Token, 60, 120)                          // heartbeat: now until 180
	if l, _ := q.Lease("payments", 135); l != nil {         // nobody else may get it
		t.Fatalf("second worker got %+v", l)
	}
	if err := q.Ack(id, a.Token, 170); err != nil {
		t.Fatal(err)
	}
}
```

Fix the cause of each one, not just the symptom.

## Phase 2: queue stats

Implement `statsOf` in `stats.go` (it backs `JobQueue.Stats`):

```go
func (q *JobQueue) Stats(queue string, now int64) (Stats, error)
type Stats struct {
	Ready, Scheduled, Retrying, InFlight, Dead, Completed int
	OldestReadyAge int64
	NextRunAt      *int64 // nil if none
}
```

It's what the ops dashboard and the worker autoscaler read. It only reports; it changes no job.

- **Clock.** Like every call that takes `now`, it moves the clock forward first, so a job whose run time has come is ready, and a lease that ran out is no longer in flight (the job is ready again, or dead if that was its last attempt). A `now` older than the clock returns a `Backdated` error.
- **Counts**, for the jobs of this queue only:
  - `ready`: jobs a lease would hand out now.
  - `scheduled`: jobs waiting for their first run (`RunAt` in the future).
  - `retrying`: jobs waiting out a retry backoff.
  - `InFlight`: jobs under a lease.
  - `dead`: jobs in the dead-letter queue (a redriven job is no longer dead).
  - `completed`: jobs ever acked in this queue. Cancelled jobs count nowhere.
- **`OldestReadyAge`**: `now` minus the time the longest-waiting ready job *became ready*, 0 if no job is ready. A job becomes ready when it's enqueued, at its `RunAt` if it was scheduled, at the end of its backoff if it's a retry, at its lease deadline if its lease ran out, and when it's redriven. It is not when the clock happened to notice.
- **`NextRunAt`**: the earliest time a scheduled or retrying job becomes ready, `nil` if there is none.
- A queue that has never been used has all zeros and `NextRunAt` `nil`.

### Example

```
q := New()                                                       // 30 s leases, backoff starts at 10 s
q.Enqueue("reports", "monthly", 0, EnqueueOptions{RunAt: 100})   // job-1
q.Enqueue("reports", "weekly", 0, EnqueueOptions{Priority: 5})   // job-2
q.Lease("reports", 10)                                           // job-2, until 40
q.Fail("job-2", token, "timeout", 20)                            // retry at 30
q.Stats("reports", 25)  -> Stats[ready=0, scheduled=1, retrying=1, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=30]
q.Lease("reports", 150)                                          // job-2 again (priority 5), until 180
q.Stats("reports", 150) -> Stats[ready=1, scheduled=0, retrying=0, inFlight=1, dead=0, completed=0, oldestReadyAge=50, nextRunAt=null]
```

(`stats.String()` prints in that form, with `nextRunAt=null` for `nil`.)

## Checking your work

- **Run** runs `cmd/run/main.go`, which reads commands from stdin (`enqueue`, `lease`, `ack`, `fail`, `extend`, `cancel`, `redrive`, `job`, `dead`, `stats`; see the top of the file). Extend it as you like.
- **My tests** runs your own `*_test.go` files. `jobqueue_example_test.go` is an example to copy.
- **Submit** runs the hidden tests for every phase you've unlocked.
