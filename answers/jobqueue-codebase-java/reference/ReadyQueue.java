import java.util.Comparator;
import java.util.PriorityQueue;

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

    private final PriorityQueue<Job> heap = new PriorityQueue<>(ORDER);

    void add(Job job) {
        heap.add(job);
    }

    /**
     * Removes and returns the best job that is still READY, or null. A job cancelled while it
     * waits stays in the heap until it reaches the top, and is dropped then.
     */
    Job poll() {
        for (Job j = heap.poll(); j != null; j = heap.poll()) {
            if (j.status == Job.Status.READY) return j;
        }
        return null;
    }
}
