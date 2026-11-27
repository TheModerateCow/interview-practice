import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Reservation book for a restaurant: tables with seat counts, reservations per seating slot, a walk-in waitlist, joined tables for large parties, and no-shows with a booking ban for repeat offenders. Every method takes ts first: the time of the call in minutes. */
public class Restaurant {
    private static final int GRACE = 15; // minutes after its slot an unseated reservation is still held
    private static final int BAN = 1440; // minutes a repeat no-show can't book ahead

    private record Party(String name, int size) {}

    private static final class Reservation {
        final String name;
        final int size, slot;
        final List<String> tables;
        String status = "booked"; // booked, cancelled, seated
        Reservation(String name, int size, int slot, List<String> tables) {
            this.name = name; this.size = size; this.slot = slot; this.tables = tables;
        }
    }

    private final Map<String, Integer> tables = new HashMap<>();
    private final Set<List<String>> links = new HashSet<>(); // [lower id, higher id]
    private final Map<String, Reservation> res = new HashMap<>();
    private final Map<Integer, List<Party>> waiting = new HashMap<>();
    private int nextId;

    public Restaurant() {}

    /** True while r still holds its tables: not cancelled and not a no-show. */
    private boolean live(int ts, Reservation r) {
        if (r.status.equals("cancelled")) return false;
        return !(r.status.equals("booked") && ts >= r.slot + GRACE);
    }

    private Set<String> taken(int ts, int slot) {
        Set<String> out = new HashSet<>();
        for (Reservation r : res.values()) if (r.slot == slot && live(ts, r)) out.addAll(r.tables);
        return out;
    }

    /** The tables the booking rule gives a party of size at slot, or null. */
    private List<String> fit(int ts, int size, int slot) {
        Set<String> taken = taken(ts, slot);
        String best = null;
        for (var e : tables.entrySet()) {
            String t = e.getKey();
            int seats = e.getValue();
            if (!taken.contains(t) && seats >= size) {
                if (best == null || seats < tables.get(best) || seats == tables.get(best) && t.compareTo(best) < 0) best = t;
            }
        }
        if (best != null) return List.of(best);
        List<String> bp = null;
        int bs = -1;
        for (List<String> p : links) {
            int s = tables.get(p.get(0)) + tables.get(p.get(1));
            if (!taken.contains(p.get(0)) && !taken.contains(p.get(1)) && s >= size) {
                if (bs < 0 || s < bs || s == bs && (p.get(0).compareTo(bp.get(0)) < 0 || p.get(0).equals(bp.get(0)) && p.get(1).compareTo(bp.get(1)) < 0)) {
                    bp = p;
                    bs = s;
                }
            }
        }
        return bp;
    }

    private String add(String name, int size, int slot, List<String> t) {
        String id = "r" + (++nextId);
        res.put(id, new Reservation(name, size, slot, t));
        return id;
    }

    /** Books every waiting party at slot that now fits, front first. */
    private void walk(int ts, int slot) {
        List<Party> keep = new ArrayList<>();
        for (Party p : waiting.getOrDefault(slot, List.of())) {
            List<String> t = fit(ts, p.size(), slot);
            if (t != null) add(p.name(), p.size(), slot, t);
            else keep.add(p);
        }
        waiting.put(slot, keep);
    }

    private List<Integer> noShowTimes(int ts, String name) {
        List<Integer> out = new ArrayList<>();
        for (Reservation r : res.values())
            if (r.name.equals(name) && r.status.equals("booked") && ts >= r.slot + GRACE) out.add(r.slot + GRACE);
        return out;
    }

    // ---------------------------------------------------------------- level 1

    public boolean addTable(int ts, String tableId, int seats) {
        if (tables.containsKey(tableId) || seats <= 0) return false;
        tables.put(tableId, seats);
        return true;
    }

    public String book(int ts, String name, int size, int slot) {
        if (size <= 0 || ts >= slot + GRACE) return "";
        List<Integer> times = noShowTimes(ts, name);
        if (times.size() >= 2 && ts < java.util.Collections.max(times) + BAN) return "";
        List<String> t = fit(ts, size, slot);
        return t != null ? add(name, size, slot, t) : "";
    }

    public boolean cancel(int ts, String reservationId) {
        Reservation r = res.get(reservationId);
        if (r == null || !r.status.equals("booked") || !live(ts, r)) return false;
        r.status = "cancelled";
        walk(ts, r.slot);
        return true;
    }

    public String tableOf(int ts, String reservationId) {
        Reservation r = res.get(reservationId);
        if (r == null || !live(ts, r)) return "";
        return String.join("+", r.tables);
    }

    public String partyAt(int ts, String tableId, int slot) {
        for (Reservation r : res.values())
            if (r.slot == slot && r.tables.contains(tableId) && live(ts, r)) return r.name;
        return "";
    }

    // ---------------------------------------------------------------- level 2

    public boolean joinWaitlist(int ts, String name, int size, int slot) {
        List<Party> queue = waiting.computeIfAbsent(slot, k -> new ArrayList<>());
        if (size <= 0 || ts >= slot + GRACE || queue.stream().anyMatch(p -> p.name().equals(name))) return false;
        List<String> t = fit(ts, size, slot);
        if (t != null) add(name, size, slot, t);
        else queue.add(new Party(name, size));
        return true;
    }

    public List<String> waitlist(int ts, int slot) {
        List<String> out = new ArrayList<>();
        for (Party p : waiting.getOrDefault(slot, List.of())) out.add(p.name() + "(" + p.size() + ")");
        return out;
    }

    public List<String> freeTables(int ts, int slot) {
        Set<String> taken = taken(ts, slot);
        List<String> out = new ArrayList<>();
        for (String t : tables.keySet()) if (!taken.contains(t)) out.add(t);
        out.sort((a, b) -> {
            int c = Integer.compare(tables.get(a), tables.get(b));
            return c != 0 ? c : a.compareTo(b);
        });
        return out;
    }

    // ---------------------------------------------------------------- level 3

    public boolean linkTables(int ts, String tableA, String tableB) {
        List<String> pair = tableA.compareTo(tableB) < 0 ? List.of(tableA, tableB) : List.of(tableB, tableA);
        if (!tables.containsKey(tableA) || !tables.containsKey(tableB) || tableA.equals(tableB) || links.contains(pair)) return false;
        links.add(pair);
        return true;
    }

    // ---------------------------------------------------------------- level 4

    public boolean seat(int ts, String reservationId) {
        Reservation r = res.get(reservationId);
        if (r == null || !r.status.equals("booked") || !live(ts, r)) return false;
        r.status = "seated";
        return true;
    }

    public int noShows(int ts, String name) {
        return noShowTimes(ts, name).size();
    }
}
