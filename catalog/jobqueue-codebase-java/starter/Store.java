import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.PriorityQueue;

/**
 * In-memory state: every live job (scheduled, ready, leased or dead), a ready heap per named
 * queue, one timer heap for run times and lease deadlines, and the idempotency keys.
 * Completed and cancelled jobs are dropped; only a per-queue count of completions is kept.
 */
final class Store {
    /** A wake-up for one job: its run time comes ({@code lease == false}) or a lease deadline passes. */
    record Timer(long at, long seq, String jobId, boolean lease) {}

    private record Key(String jobId, long until) {}

    /** The queue clock: the latest {@code now} any call has passed. */
    long clock;
    final PriorityQueue<Timer> timers =
            new PriorityQueue<>(Comparator.comparingLong(Timer::at).thenComparingLong(Timer::seq));

    private long jobSeq;
    private long timerSeq;
    private long leaseSeq;
    private final Map<String, Job> jobs = new HashMap<>();
    private final Map<String, Map<String, Job>> byQueue = new HashMap<>();
    private final Map<String, ReadyQueue> ready = new HashMap<>();
    private final Map<String, Key> keys = new HashMap<>();
    private final Map<String, Integer> completed = new HashMap<>();

    Job add(String queue, String payload, int priority, int maxAttempts, long now) {
        long seq = ++jobSeq;
        Job job = new Job("job-" + seq, queue, payload, priority, maxAttempts, seq, now);
        jobs.put(job.id, job);
        byQueue.computeIfAbsent(queue, q -> new LinkedHashMap<>()).put(job.id, job);
        return job;
    }

    Job get(String id) {
        return jobs.get(id);
    }

    /** The live jobs of a queue, in enqueue order. */
    Collection<Job> jobsIn(String queue) {
        return byQueue.getOrDefault(queue, Map.of()).values();
    }

    /** Lifetime number of acked jobs in a queue. */
    int completedIn(String queue) {
        return completed.getOrDefault(queue, 0);
    }

    /** Ends a job for good (COMPLETED or CANCELLED) and forgets it. */
    void drop(Job job, Job.Status end) {
        job.status = end;
        jobs.remove(job.id);
        byQueue.get(job.queue).remove(job.id);
        if (end == Job.Status.COMPLETED) completed.merge(job.queue, 1, Integer::sum);
    }

    /** Marks a job READY as of {@code at} and queues it for leasing. */
    void makeReady(Job job, long at) {
        job.status = Job.Status.READY;
        job.readyAt = at;
        ready.computeIfAbsent(job.queue, q -> new ReadyQueue()).add(job);
    }

    /** Removes and returns the next job to lease from a queue, or null. */
    Job nextReady(String queue) {
        ReadyQueue r = ready.get(queue);
        return r == null ? null : r.poll();
    }

    /** Parks a job until {@code at}. */
    void schedule(Job job, long at) {
        job.status = Job.Status.SCHEDULED;
        job.availableAt = at;
        timers.add(new Timer(at, ++timerSeq, job.id, false));
    }

    /** Hands a job out under a fresh lease token until {@code until}. */
    void lease(Job job, long until) {
        job.status = Job.Status.LEASED;
        job.attempts++;
        job.leaseToken = "lease-" + (++leaseSeq);
        setDeadline(job, until);
    }

    /** Moves the current lease's deadline. */
    void setDeadline(Job job, long until) {
        job.leaseUntil = until;
        timers.add(new Timer(until, ++timerSeq, job.id, true));
    }

    /** The job an idempotency key still points at in this queue, or null once the key has lapsed. */
    String findKey(String queue, String key, long now) {
        Key k = keys.get(keyOf(queue, key));
        return k != null && now < k.until ? k.jobId : null;
    }

    void rememberKey(String queue, String key, String jobId, long until) {
        keys.put(keyOf(queue, key), new Key(jobId, until));
    }

    private static String keyOf(String queue, String key) {
        return key;
    }
}
