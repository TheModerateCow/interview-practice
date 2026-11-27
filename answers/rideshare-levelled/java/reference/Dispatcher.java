import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Ride-share dispatch along one highway corridor: riders, drivers, trips, a dispatch radius and capacity planning. */
public class Dispatcher {
    private final Map<String, Integer> idle = new HashMap<>();   // idle driver id -> km
    private final Set<String> busy = new HashSet<>();             // drivers on a trip
    private final Map<String, Integer> riders = new HashMap<>(); // waiting rider id -> km
    private Integer radius = null;                                // null = no limit

    public Dispatcher() {}

    // Level 1

    public boolean addDriver(int ts, String id, int km) {
        if (idle.containsKey(id) || busy.contains(id)) return false;
        idle.put(id, km);
        return true;
    }

    public boolean addRider(int ts, String id, int km) {
        if (riders.containsKey(id)) return false;
        riders.put(id, km);
        return true;
    }

    public boolean moveDriver(int ts, String id, int km) {
        if (!idle.containsKey(id)) return false;
        idle.put(id, km);
        return true;
    }

    public boolean removeDriver(int ts, String id) {
        return idle.remove(id) != null;
    }

    public boolean cancelRider(int ts, String id) {
        return riders.remove(id) != null;
    }

    public String nearestDriver(int ts, String rider) {
        Integer x = riders.get(rider);
        if (x == null) return null;
        String best = null;
        int bestKm = 0;
        for (Map.Entry<String, Integer> e : idle.entrySet()) {
            String id = e.getKey();
            int km = e.getValue();
            int dist = Math.abs(km - x);
            if (radius != null && dist > radius) continue;
            if (best == null) { best = id; bestKm = km; continue; }
            int bd = Math.abs(bestKm - x);
            if (dist < bd || (dist == bd && (km < bestKm || (km == bestKm && id.compareTo(best) < 0)))) {
                best = id;
                bestKm = km;
            }
        }
        return best;
    }

    // Level 2

    public String dispatch(int ts, String rider) {
        String d = nearestDriver(ts, rider);
        if (d == null) return null;
        riders.remove(rider);
        idle.remove(d);
        busy.add(d);
        return d;
    }

    public boolean completeTrip(int ts, String driver, int km) {
        if (!busy.contains(driver)) return false;
        busy.remove(driver);
        idle.put(driver, km);
        return true;
    }

    public List<String> idleBetween(int ts, int lo, int hi) {
        List<Map.Entry<String, Integer>> hits = new ArrayList<>();
        for (Map.Entry<String, Integer> e : idle.entrySet()) {
            if (lo <= e.getValue() && e.getValue() <= hi) hits.add(e);
        }
        hits.sort((a, b) -> !a.getValue().equals(b.getValue())
                ? Integer.compare(a.getValue(), b.getValue()) : a.getKey().compareTo(b.getKey()));
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, Integer> e : hits) out.add(e.getKey() + ":" + e.getValue());
        return out;
    }

    // Level 3

    public void setRadius(int ts, int radius) {
        this.radius = radius;
    }

    private static int[] sorted(Map<String, Integer> m) {
        int[] a = new int[m.size()];
        int i = 0;
        for (int v : m.values()) a[i++] = v;
        Arrays.sort(a);
        return a;
    }

    public int maxServed(int ts) {
        int[] r = sorted(riders), d = sorted(idle);
        if (radius == null) return Math.min(r.length, d.length);
        return served(r, d, radius);
    }

    /** Most riders picked up at once, every pickup within radius. Both arrays sorted; each rider, left to right,
     *  takes the leftmost free driver in reach (drivers too far left are skipped for good). */
    private static int served(int[] r, int[] d, int radius) {
        int count = 0, j = 0;
        for (int x : r) {
            while (j < d.length && d[j] < x - radius) j++;
            if (j == d.length) break;
            if (d[j] <= x + radius) {
                count++;
                j++;
            }
        }
        return count;
    }

    // Level 4

    public int minRadius(int ts, int need) {
        if (need <= 0) return 0;
        if (need > riders.size() || need > idle.size()) return -1;
        int[] r = sorted(riders), d = sorted(idle);
        int lo = 0, hi = Math.max(r[r.length - 1], d[d.length - 1]) - Math.min(r[0], d[0]);
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if (served(r, d, mid) >= need) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        return lo;
    }
}
