import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * The jobs of one named queue that can be leased now, best first: higher priority, then the
 * job that has been ready longest, then the job enqueued first.
 */
final class ReadyQueue {
    static final Comparator<Job> ORDER = (a, b) -> {
        if (a.priority != b.priority) return Integer.compare(b.priority, a.priority);
        if (a.readyAt != b.readyAt) return Long.compare(a.readyAt, b.readyAt);
        return Long.compare(a.seq, b.seq);
    };

    private final List<Job> jobs = new ArrayList<>();

    void add(Job job) {
        jobs.add(job);
    }

    /** Removes and returns the best job that is still READY, or null. */
    Job poll() {
        jobs.removeIf(j -> j.status != Job.Status.READY);
        Job best = null;
        for (Job j : jobs) {
            if (best == null || ORDER.compare(j, best) < 0) best = j;
        }
        if (best != null) jobs.remove(best);
        return best;
    }
}
