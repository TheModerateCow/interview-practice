import java.util.List;

public class Scheduler {
    static final int DAY = 1440;

    /** Earliest UTC start t with t + duration <= days * 1440 such that at least `quorum`
     *  attendees are free for the whole of [t, t + duration); -1 if there is none. */
    public static int earliestQuorumSlot(List<Attendee> attendees, int days, int duration, int quorum) {
        throw new UnsupportedOperationException("not implemented");
    }
}
