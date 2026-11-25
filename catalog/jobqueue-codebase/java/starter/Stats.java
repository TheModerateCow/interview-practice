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
        throw new UnsupportedOperationException("not implemented");
    }
}
