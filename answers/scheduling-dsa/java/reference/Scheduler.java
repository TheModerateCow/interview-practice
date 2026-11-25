import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

public class Scheduler {
    static final int DAY = 1440;

    /** Earliest UTC start t with t + duration <= days * 1440 such that at least `quorum`
     *  attendees are free for the whole of [t, t + duration); -1 if there is none. */
    public static int earliestQuorumSlot(List<Attendee> attendees, int days, int duration, int quorum) {
        int horizon = days * DAY;
        List<int[]> events = new ArrayList<>();
        for (Attendee a : attendees) {
            for (int[] f : freeIntervals(a, horizon)) {
                int s = f[0], e = f[1];
                // a meeting fits for this attendee iff it starts in [s, e - duration]
                if (e - s >= duration) { events.add(new int[]{s, 1}); events.add(new int[]{e - duration + 1, -1}); }
            }
        }
        events.sort(Comparator.comparingInt(x -> x[0]));
        int count = 0;
        for (int i = 0; i < events.size(); ) {
            int t = events.get(i)[0];
            while (i < events.size() && events.get(i)[0] == t) count += events.get(i++)[1];
            if (count >= quorum) return t;
        }
        return -1;
    }

    /** Disjoint, non-touching free intervals in UTC, sorted, inside [0, horizon). */
    static List<int[]> freeIntervals(Attendee a, int horizon) {
        List<int[]> work = new ArrayList<>();
        for (int d = -1; d <= horizon / DAY; d++) {
            int base = d * DAY - a.offset();
            int s = Math.max(0, base + a.workStart());
            int e = Math.min(horizon, base + a.workEnd());
            if (s >= e) continue;
            int[] last = work.isEmpty() ? null : work.get(work.size() - 1);
            if (last != null && s <= last[1]) last[1] = Math.max(last[1], e);
            else work.add(new int[]{s, e});
        }
        int[][] busy = a.busy().clone();
        Arrays.sort(busy, Comparator.comparingInt(x -> x[0]));
        List<int[]> free = new ArrayList<>();
        int lo = 0;
        for (int[] w : work) {
            int ws = w[0], we = w[1];
            while (lo < busy.length && busy[lo][1] <= ws) lo++;
            int cur = ws;
            for (int i = lo; i < busy.length && busy[i][0] < we; i++) {
                if (busy[i][0] > cur) free.add(new int[]{cur, busy[i][0]});
                cur = Math.max(cur, busy[i][1]);
            }
            if (cur < we) free.add(new int[]{cur, we});
        }
        return free;
    }
}
