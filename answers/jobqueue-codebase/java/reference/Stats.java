/**
 * A point-in-time view of one named queue, for the ops dashboard and the worker autoscaler.
 *
 * @param ready          jobs a lease would hand out now
 * @param scheduled      jobs waiting for their first run time
 * @param retrying       jobs waiting out a retry backoff
 * @param inFlight       jobs under a lease
 * @param dead           jobs in the dead-letter queue
 * @param completed      jobs acked in this queue, ever
 * @param oldestReadyAge how long the longest-waiting READY job has been ready, 0 if none
 * @param nextRunAt      the earliest time a scheduled or retrying job becomes ready, null if none
 */
public record Stats(int ready, int scheduled, int retrying, int inFlight, int dead, int completed,
                    long oldestReadyAge, Long nextRunAt) {

    /** Computes the stats of {@code queue} at time {@code now}. See problem.md for the rules. */
    static Stats of(Store store, String queue, long now) {
        Lifecycle.advance(store, now);
        int ready = 0, scheduled = 0, retrying = 0, inFlight = 0, dead = 0;
        long oldest = Long.MAX_VALUE, next = Long.MAX_VALUE;
        for (Job j : store.jobsIn(queue)) {
            switch (j.status) {
                case READY -> {
                    ready++;
                    oldest = Math.min(oldest, j.readyAt);
                }
                case SCHEDULED -> {
                    if (j.attempts == 0) scheduled++;
                    else retrying++;
                    next = Math.min(next, j.availableAt);
                }
                case LEASED -> inFlight++;
                case DEAD -> dead++;
                default -> { }
            }
        }
        return new Stats(ready, scheduled, retrying, inFlight, dead, store.completedIn(queue),
                ready == 0 ? 0 : now - oldest, next == Long.MAX_VALUE ? null : next);
    }
}
