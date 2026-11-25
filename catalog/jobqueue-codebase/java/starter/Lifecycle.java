/**
 * The transitions driven by time and failures: the clock sweep that starts scheduled jobs and
 * takes back leases that ran out, retry backoff, and the dead-letter queue.
 */
final class Lifecycle {
    private Lifecycle() {}

    /**
     * Moves the queue clock to {@code now} and fires every timer due by then, in time order.
     * Scheduled jobs whose time has come become READY as of their run time. A lease that ran
     * out without an ack is taken back as of its deadline: the job is READY again, or DEAD if
     * that lease was its last attempt.
     */
    static void advance(Store store, long now) {
        if (now < store.clock) {
            throw new QueueException(QueueException.Code.BACKDATED, "now " + now + " is before the queue clock " + store.clock);
        }
        store.clock = now;
        while (!store.timers.isEmpty() && store.timers.peek().at() <= now) {
            Store.Timer t = store.timers.poll();
            Job job = store.get(t.jobId());
            if (job == null) continue;
            if (!t.lease()) {
                if (job.status == Job.Status.SCHEDULED && job.availableAt <= now) store.makeReady(job, job.availableAt);
            } else if (job.status == Job.Status.LEASED) {
                expireLease(store, job);
            }
        }
    }

    private static void expireLease(Store store, Job job) {
        job.lastError = "lease expired";
        if (job.attempts >= job.maxAttempts) deadLetter(job, job.leaseUntil);
        else store.makeReady(job, job.leaseUntil);
    }

    /** Backoff before the retry that follows attempt number {@code attempts}: base, 2x base, 4x base ... capped at maxDelay. */
    static long retryDelay(JobQueue.Options o, int attempts) {
        long d = o.baseDelay();
        for (int i = 1; i < attempts && d < o.maxDelay(); i++) d *= 2;
        return Math.min(d, o.maxDelay());
    }

    /** A worker reported failure: retry after the backoff, or dead-letter the job if it is out of attempts. */
    static void recordFailure(Store store, JobQueue.Options o, Job job, String error, long now) {
        job.lastError = error;
        if (job.attempts >= job.maxAttempts) deadLetter(job, now);
        else store.schedule(job, now + retryDelay(o, job.attempts));
    }

    static void deadLetter(Job job, long at) {
        job.status = Job.Status.DEAD;
        job.deadAt = at;
    }
}
