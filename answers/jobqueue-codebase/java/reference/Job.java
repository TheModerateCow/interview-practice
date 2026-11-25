/**
 * One unit of background work and where it is in its life. The queue owns these objects;
 * callers only ever see copies (see {@link JobQueue#job}).
 */
public final class Job {
    /** Life cycle: SCHEDULED -> READY -> LEASED -> (COMPLETED | SCHEDULED for a retry | DEAD). */
    public enum Status { SCHEDULED, READY, LEASED, COMPLETED, DEAD, CANCELLED }

    final String id;
    final String queue;
    final String payload;
    final int priority;
    final int maxAttempts;
    final long seq;
    final long enqueuedAt;

    Status status;
    /** Leases handed out so far; a lease that runs out without an ack counts as an attempt. */
    int attempts;
    /** When a SCHEDULED job may run (its run time, or the end of its retry backoff). */
    long availableAt;
    /** When the job last became READY. Jobs of equal priority are leased oldest-ready first. */
    long readyAt;
    long leaseUntil;
    String leaseToken = "";
    String lastError = "";
    long deadAt;

    Job(String id, String queue, String payload, int priority, int maxAttempts, long seq, long enqueuedAt) {
        this.id = id;
        this.queue = queue;
        this.payload = payload;
        this.priority = priority;
        this.maxAttempts = maxAttempts;
        this.seq = seq;
        this.enqueuedAt = enqueuedAt;
    }

    public String id() { return id; }
    public String queue() { return queue; }
    public String payload() { return payload; }
    public int priority() { return priority; }
    public Status status() { return status; }
    public int attempts() { return attempts; }
    public String lastError() { return lastError; }

    Job copy() {
        Job c = new Job(id, queue, payload, priority, maxAttempts, seq, enqueuedAt);
        c.status = status;
        c.attempts = attempts;
        c.availableAt = availableAt;
        c.readyAt = readyAt;
        c.leaseUntil = leaseUntil;
        c.leaseToken = leaseToken;
        c.lastError = lastError;
        c.deadAt = deadAt;
        return c;
    }

    @Override
    public String toString() {
        return id + " " + status + " attempts=" + attempts + (lastError.isEmpty() ? "" : " lastError=" + lastError);
    }
}
