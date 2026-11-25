import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * The background job queue of the web platform. Producers enqueue jobs into named queues
 * ("emails", "webhooks", ...); workers lease the next job, then ack it or report a failure.
 * A lease is a visibility timeout: if it runs out without an ack the job goes back to READY
 * for another worker. Failed jobs are retried with exponential backoff until they run out of
 * attempts, then they move to the dead-letter queue, where an operator can redrive them.
 *
 * <p>Not safe for concurrent use: the API layer serialises calls. Times are caller-supplied
 * Unix seconds. Every call that takes {@code now} moves the queue clock forward first (starting
 * due jobs and taking back expired leases); {@code now} may never go backwards.
 */
public final class JobQueue {
    /**
     * @param visibility     default lease length, seconds
     * @param baseDelay      backoff after the first failed attempt, seconds; doubles each attempt
     * @param maxDelay       cap on the backoff, seconds
     * @param maxAttempts    default attempts per job
     * @param idempotencyTtl how long an idempotency key keeps returning its first job, seconds
     */
    public record Options(long visibility, long baseDelay, long maxDelay, int maxAttempts, long idempotencyTtl) {
        public static final Options DEFAULTS = new Options(30, 10, 600, 3, 3600);

        public Options {
            if (visibility <= 0 || baseDelay < 0 || maxDelay < baseDelay || maxAttempts < 1 || idempotencyTtl < 0) {
                throw new QueueException(QueueException.Code.INVALID, "bad options");
            }
        }
    }

    /** What a worker gets from {@link #lease}: the token to ack, fail or extend with. */
    public record Lease(String jobId, String token, String payload, int attempt, long until) {}

    /** Optional settings for {@link #enqueue(String, String, long, Opts)}. */
    public static final class Opts {
        int priority;
        Long runAt;
        int maxAttempts;
        String key;

        /** Higher runs first; default 0. */
        public Opts priority(int p) { priority = p; return this; }
        /** Don't start before this time. */
        public Opts runAt(long t) { runAt = t; return this; }
        /** Overrides {@link Options#maxAttempts}. */
        public Opts maxAttempts(int n) { maxAttempts = n; return this; }
        /** Idempotency key, scoped to the named queue. */
        public Opts key(String k) { key = k; return this; }
    }

    public static Opts opts() {
        return new Opts();
    }

    private final Store store = new Store();
    private final Options options;

    public JobQueue() {
        this(Options.DEFAULTS);
    }

    public JobQueue(Options options) {
        this.options = options;
    }

    public String enqueue(String queue, String payload, long now) {
        return enqueue(queue, payload, now, opts());
    }

    /**
     * Adds a job and returns its id. If the key was used in this queue less than
     * idempotencyTtl seconds ago, nothing is added and the first job's id is returned.
     */
    public String enqueue(String queue, String payload, long now, Opts o) {
        Lifecycle.advance(store, now);
        if (queue == null || queue.isEmpty()) throw invalid("empty queue name");
        int max = o.maxAttempts == 0 ? options.maxAttempts() : o.maxAttempts;
        if (max < 1) throw invalid("maxAttempts must be at least 1");
        if (o.key != null) {
            String first = store.findKey(queue, o.key, now);
            if (first != null) return first;
        }
        Job job = store.add(queue, payload, o.priority, max, now);
        if (o.key != null) store.rememberKey(queue, o.key, job.id, now + options.idempotencyTtl());
        if (o.runAt != null && o.runAt > now) store.schedule(job, o.runAt);
        else store.makeReady(job, now);
        return job.id;
    }

    public Lease lease(String queue, long now) {
        return lease(queue, now, options.visibility());
    }

    /** Leases the next READY job of a queue for {@code visibility} seconds, or returns null if there is none. */
    public Lease lease(String queue, long now, long visibility) {
        if (visibility <= 0) throw invalid("visibility must be positive");
        Lifecycle.advance(store, now);
        Job job = store.nextReady(queue);
        if (job == null) return null;
        store.lease(job, now + visibility);
        return new Lease(job.id, job.leaseToken, job.payload, job.attempts, job.leaseUntil);
    }

    /** The job is done: it is dropped and counted as completed. */
    public void ack(String jobId, String token, long now) {
        store.drop(held(jobId, token, now), Job.Status.COMPLETED);
    }

    /** The attempt failed: the job is retried after the backoff, or dead-lettered if it is out of attempts. */
    public void fail(String jobId, String token, String error, long now) {
        Lifecycle.recordFailure(store, options, held(jobId, token, now), error, now);
    }

    /** Heartbeat: the lease now runs until {@code now + seconds}. */
    public void extend(String jobId, String token, long seconds, long now) {
        if (seconds <= 0) throw invalid("seconds must be positive");
        store.setDeadline(held(jobId, token, now), now + seconds);
    }

    /** Cancels a job that hasn't started (SCHEDULED or READY). */
    public void cancel(String jobId, long now) {
        Lifecycle.advance(store, now);
        Job job = find(jobId);
        if (job.status != Job.Status.SCHEDULED && job.status != Job.Status.READY) {
            throw invalid(jobId + " is " + job.status);
        }
        store.drop(job, Job.Status.CANCELLED);
    }

    /** Moves a dead job back to READY with a fresh set of attempts. */
    public void redrive(String jobId, long now) {
        Lifecycle.advance(store, now);
        Job job = find(jobId);
        if (job.status != Job.Status.DEAD) throw invalid(jobId + " is " + job.status);
        job.attempts = 0;
        store.makeReady(job, now);
    }

    /** The dead-letter queue of a named queue, oldest death first. */
    public List<Job> deadLetters(String queue) {
        List<Job> out = new ArrayList<>();
        for (Job j : store.jobsIn(queue)) {
            if (j.status == Job.Status.DEAD) out.add(j.copy());
        }
        out.sort(Comparator.comparingLong((Job j) -> j.deadAt).thenComparingLong(j -> j.seq));
        return out;
    }

    /** A copy of a live job, or null if there is none with that id. */
    public Job job(String id) {
        Job j = store.get(id);
        return j == null ? null : j.copy();
    }

    /** The stats of a named queue at time {@code now} (an unknown queue has all zeros). */
    public Stats stats(String queue, long now) {
        return Stats.of(store, queue, now);
    }

    /** The job, if {@code token} is its current lease. */
    private Job held(String jobId, String token, long now) {
        Lifecycle.advance(store, now);
        Job job = find(jobId);
        if (job.status != Job.Status.LEASED || !job.leaseToken.equals(token)) {
            throw new QueueException(QueueException.Code.LEASE_LOST, jobId + ": " + token + " is not the current lease");
        }
        return job;
    }

    private Job find(String id) {
        Job j = store.get(id);
        if (j == null) throw new QueueException(QueueException.Code.NOT_FOUND, "no live job " + id);
        return j;
    }

    private static QueueException invalid(String why) {
        return new QueueException(QueueException.Code.INVALID, why);
    }
}
