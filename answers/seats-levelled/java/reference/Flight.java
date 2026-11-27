import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The business-class desk for one multi-stop flight: bookings, the upgrade waitlist, busiest-leg queries
 * and the best possible upgrade plan. Stops 0..n; leg k flies stop k -> k+1 and has seats[k] seats.
 */
public class Flight {
    private static final long FAR = 1L << 62;

    private static final class Trip {
        final int board, alight;
        String status;

        Trip(int board, int alight, String status) {
            this.board = board;
            this.alight = alight;
            this.status = status;
        }
    }

    private final int n, size, h;
    private final int[] seats;
    // Segment tree over legs. Node p covers a run of legs: hi[p] is the most seats taken on one of them,
    // lo[p] the fewest free seats. add[p] (internal nodes) counts seats taken on every leg under p that
    // p's children don't show yet.
    private final long[] hi, lo, add;
    private final Map<String, Trip> trips = new HashMap<>();
    private final LinkedHashMap<String, Trip> waiting = new LinkedHashMap<>(); // oldest request first

    public Flight(int[] seats) {
        n = seats.length;
        int s = 1, hh = 0;
        while (s < n) {
            s *= 2;
            hh++;
        }
        size = s;
        h = hh;
        this.seats = Arrays.copyOf(seats, n);
        hi = new long[2 * size];
        lo = new long[2 * size];
        add = new long[size];
        for (int k = 0; k < n; k++) lo[size + k] = seats[k];
        for (int p = size - 1; p > 0; p--) {
            hi[p] = Math.max(hi[2 * p], hi[2 * p + 1]);
            lo[p] = Math.min(lo[2 * p], lo[2 * p + 1]);
        }
    }

    // ---- segment tree: add seats taken on legs [l, r), read (most taken, fewest free) on legs [l, r)

    private void apply(int p, long v) {
        hi[p] += v;
        lo[p] -= v;
        if (p < size) add[p] += v;
    }

    private void pull(int p) {
        while (p > 1) {
            p >>= 1;
            long a = add[p];
            hi[p] = Math.max(hi[2 * p], hi[2 * p + 1]) + a;
            lo[p] = Math.min(lo[2 * p], lo[2 * p + 1]) - a;
        }
    }

    private void push(int p) {
        for (int s = h; s > 0; s--) {
            int i = p >> s;
            long a = add[i];
            if (a != 0) {
                apply(2 * i, a);
                apply(2 * i + 1, a);
                add[i] = 0;
            }
        }
    }

    private void take(int l, int r, long v) {
        l += size;
        r += size;
        int l0 = l, r0 = r - 1;
        while (l < r) {
            if ((l & 1) == 1) apply(l++, v);
            if ((r & 1) == 1) apply(--r, v);
            l >>= 1;
            r >>= 1;
        }
        pull(l0);
        pull(r0);
    }

    /** {most taken, fewest free} over legs l..r-1. */
    private long[] range(int l, int r) {
        l += size;
        r += size;
        push(l);
        push(r - 1);
        long most = 0, fewest = FAR;
        while (l < r) {
            if ((l & 1) == 1) {
                most = Math.max(most, hi[l]);
                fewest = Math.min(fewest, lo[l]);
                l++;
            }
            if ((r & 1) == 1) {
                r--;
                most = Math.max(most, hi[r]);
                fewest = Math.min(fewest, lo[r]);
            }
            l >>= 1;
            r >>= 1;
        }
        return new long[] {most, fewest};
    }

    private boolean valid(int board, int alight) {
        return 0 <= board && board < alight && alight <= n;
    }

    private boolean fits(int board, int alight) {
        return range(board, alight)[1] >= 1;
    }

    // ---- level 1

    public boolean book(String passenger, int board, int alight) {
        if (trips.containsKey(passenger) || !valid(board, alight) || !fits(board, alight)) return false;
        take(board, alight, 1);
        trips.put(passenger, new Trip(board, alight, "booked"));
        return true;
    }

    public boolean cancel(String passenger) {
        Trip t = trips.remove(passenger);
        if (t == null) return false;
        if (t.status.equals("waitlisted")) waiting.remove(passenger);
        else take(t.board, t.alight, -1);
        return true;
    }

    public Integer freeSeats(int leg) {
        if (leg < 0 || leg >= n) return null;
        return (int) range(leg, leg + 1)[1];
    }

    // ---- level 2

    public String requestUpgrade(String passenger, int board, int alight) {
        if (trips.containsKey(passenger) || !valid(board, alight)) return "";
        if (fits(board, alight)) {
            take(board, alight, 1);
            trips.put(passenger, new Trip(board, alight, "upgraded"));
            return "upgraded";
        }
        Trip t = new Trip(board, alight, "waitlisted");
        trips.put(passenger, t);
        waiting.put(passenger, t);
        return "waitlisted";
    }

    public String status(String passenger) {
        Trip t = trips.get(passenger);
        return t == null ? "" : t.status;
    }

    public List<String> promote() {
        List<String> done = new ArrayList<>();
        var it = waiting.entrySet().iterator();
        while (it.hasNext()) {
            var e = it.next();
            Trip t = e.getValue();
            if (fits(t.board, t.alight)) {
                take(t.board, t.alight, 1);
                t.status = "upgraded";
                it.remove();
                done.add(e.getKey());
            }
        }
        return done;
    }

    // ---- level 3

    public Integer busiest(int fromStop, int toStop) {
        if (!valid(fromStop, toStop)) return null;
        return (int) range(fromStop, toStop)[0];
    }

    // ---- level 4

    public int bestPlan() {
        int[] diff = new int[n + 1];
        List<List<Integer>> starts = new ArrayList<>(n);
        for (int k = 0; k < n; k++) starts.add(null);
        int m = 0;
        for (Trip t : trips.values()) {
            if (t.status.equals("booked")) {
                diff[t.board]++;
                diff[t.alight]--;
            } else {
                if (starts.get(t.board) == null) starts.set(t.board, new ArrayList<>());
                starts.get(t.board).add(t.alight);
                m++;
            }
        }
        // Sweep the legs left to right, taking each request as its boarding leg comes up. When a leg is over its
        // seats, drop the taken request that alights latest: it blocks the most legs still to come.
        int[] ends = new int[n + 1];
        MaxHeap taken = new MaxHeap(m);
        int active = 0, paid = 0, dropped = 0;
        for (int k = 0; k < n; k++) {
            paid += diff[k];
            active -= ends[k];
            if (starts.get(k) != null) {
                for (int alight : starts.get(k)) {
                    taken.push(alight);
                    ends[alight]++;
                    active++;
                }
            }
            while (active > seats[k] - paid) {
                int alight = taken.pop();
                ends[alight]--;
                active--;
                dropped++;
            }
        }
        return m - dropped;
    }

    /** Binary max-heap of ints. */
    private static final class MaxHeap {
        private final int[] a;
        private int size;

        MaxHeap(int cap) {
            a = new int[Math.max(cap, 1)];
        }

        void push(int x) {
            int i = size++;
            while (i > 0 && a[(i - 1) / 2] < x) {
                a[i] = a[(i - 1) / 2];
                i = (i - 1) / 2;
            }
            a[i] = x;
        }

        int pop() {
            int top = a[0], x = a[--size];
            int i = 0;
            while (2 * i + 1 < size) {
                int c = 2 * i + 1;
                if (c + 1 < size && a[c + 1] > a[c]) c++;
                if (a[c] <= x) break;
                a[i] = a[c];
                i = c;
            }
            a[i] = x;
            return top;
        }
    }
}
