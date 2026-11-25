import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** A multi-storey parking garage: spots of three sizes, vehicles that park and leave, short reservations, and the stay history behind billing. */
public class Garage {
    /** Spot and vehicle sizes, smallest first. A vehicle fits a spot of its size or larger. */
    private static final List<String> SIZES = List.of("small", "medium", "large");
    /** Cents per started hour, by the size of the spot used. */
    private static final int[] RATES = {200, 300, 500};

    /** One visit of a plate to a spot; to is -1 while the vehicle is still there. */
    private static final class Stay {
        final String plate;
        final int from;
        int to = -1;
        Stay(String plate, int from) { this.plate = plate; this.from = from; }
    }

    private static final class Spot {
        final String id;
        final int size;
        String plate = "";
        final List<Stay> stays = new ArrayList<>();
        Spot(String id, int size) { this.id = id; this.size = size; }
    }

    private record Reservation(String spotId, int expiresAt) {}

    private final Map<String, Spot> spots = new HashMap<>();
    private final Map<String, String> parked = new HashMap<>();
    private final Map<String, Integer> visits = new HashMap<>();
    private final Map<String, Reservation> reserved = new HashMap<>();

    public Garage() {}

    /** True if nobody is parked in s and no live reservation holds it at ts. */
    private boolean free(int ts, Spot s) {
        if (!s.plate.isEmpty()) return false;
        for (Reservation r : reserved.values()) {
            if (r.spotId().equals(s.id) && ts < r.expiresAt()) return false;
        }
        return true;
    }

    /** The free spot a vehicle of size would get: smallest fitting size, then lowest id. */
    private Spot pick(int ts, int size) {
        Spot best = null;
        for (Spot s : spots.values()) {
            if (s.size < size || !free(ts, s)) continue;
            if (best == null || s.size < best.size || (s.size == best.size && s.id.compareTo(best.id) < 0)) best = s;
        }
        return best;
    }

    public boolean addSpot(int ts, String spotId, String size) {
        int n = SIZES.indexOf(size);
        if (spots.containsKey(spotId) || n < 0) return false;
        spots.put(spotId, new Spot(spotId, n));
        return true;
    }

    public String park(int ts, String plate, String size) {
        int n = SIZES.indexOf(size);
        if (n < 0 || parked.containsKey(plate)) return "";
        Reservation r = reserved.get(plate);
        Spot s = (r != null && ts < r.expiresAt()) ? spots.get(r.spotId()) : pick(ts, n);
        if (s == null) return "";
        reserved.remove(plate);
        s.plate = plate;
        s.stays.add(new Stay(plate, ts));
        parked.put(plate, s.id);
        visits.merge(plate, 1, Integer::sum);
        return s.id;
    }

    public boolean leave(int ts, String plate) {
        String id = parked.get(plate);
        if (id == null) return false;
        Spot s = spots.get(id);
        s.stays.get(s.stays.size() - 1).to = ts;
        s.plate = "";
        parked.remove(plate);
        return true;
    }

    public String spotOf(int ts, String plate) {
        return parked.getOrDefault(plate, "");
    }

    public int freeSpots(int ts, String size) {
        int n = SIZES.indexOf(size);
        if (n < 0) return -1;
        int c = 0;
        for (Spot s : spots.values()) {
            if (s.size == n && free(ts, s)) c++;
        }
        return c;
    }

    public List<String> topVisitors(int ts, int n) {
        List<String> plates = new ArrayList<>(visits.keySet());
        plates.sort((a, b) -> {
            int c = Integer.compare(visits.get(b), visits.get(a));
            if (c != 0) return c;
            return a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (int i = 0; i < plates.size() && i < n; i++) out.add(plates.get(i) + "(" + visits.get(plates.get(i)) + ")");
        return out;
    }

    public String reserve(int ts, String plate, String size, int ttl) {
        int n = SIZES.indexOf(size);
        Reservation r = reserved.get(plate);
        if (n < 0 || ttl <= 0 || parked.containsKey(plate) || (r != null && ts < r.expiresAt())) return "";
        Spot s = pick(ts, n);
        if (s == null) return "";
        reserved.put(plate, new Reservation(s.id, ts + ttl));
        return s.id;
    }

    public boolean cancel(int ts, String plate) {
        Reservation r = reserved.get(plate);
        if (r == null || ts >= r.expiresAt()) return false;
        reserved.remove(plate);
        return true;
    }

    public String occupantAt(int ts, String spotId, int atTs) {
        Spot s = spots.get(spotId);
        if (s == null) return "";
        for (Stay st : s.stays) {
            if (st.from <= atTs && (st.to == -1 || atTs < st.to)) return st.plate;
        }
        return "";
    }

    public int charges(int ts, String plate) {
        int total = 0;
        for (Spot s : spots.values()) {
            for (Stay st : s.stays) {
                if (st.plate.equals(plate) && st.to != -1) total += RATES[s.size] * ((st.to - st.from + 59) / 60);
            }
        }
        return total;
    }
}
