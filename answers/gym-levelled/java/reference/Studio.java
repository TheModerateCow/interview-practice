import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/** The class booking desk of a gym: classes with a fixed number of spots, members who book them, waitlists, class credits and weekly series. */
public class Studio {
    private static final int REFUND_WINDOW = 60; // minutes before the start a cancellation still gets its credits back
    private static final int WEEK = 7 * 24 * 60;

    private static final class GymClass {
        final int start, capacity;
        int price;
        final Map<String, Integer> booked = new LinkedHashMap<>(); // member -> credits paid
        final List<String> waiting = new ArrayList<>();
        boolean cancelled;
        GymClass(int start, int capacity) { this.start = start; this.capacity = capacity; }
    }

    private final Map<String, GymClass> classes = new HashMap<>();
    private final Map<String, Integer> credits = new HashMap<>();
    private final Map<String, List<String>> series = new HashMap<>();

    public Studio() {}

    /** The class if it exists, isn't cancelled and hasn't started. */
    private GymClass open(int ts, String classId) {
        GymClass c = classes.get(classId);
        if (c == null || c.cancelled || ts >= c.start) return null;
        return c;
    }

    private int balance(String member) {
        return credits.getOrDefault(member, 0);
    }

    private void promote(GymClass c) {
        while (!c.waiting.isEmpty() && c.booked.size() < c.capacity) {
            String m = c.waiting.remove(0);
            if (balance(m) >= c.price) {
                credits.put(m, balance(m) - c.price);
                c.booked.put(m, c.price);
            }
        }
    }

    private List<String> memberClasses(String member, Predicate<GymClass> keep) {
        List<String> ids = new ArrayList<>();
        for (Map.Entry<String, GymClass> e : classes.entrySet()) {
            GymClass c = e.getValue();
            if (!c.cancelled && c.booked.containsKey(member) && keep.test(c)) ids.add(e.getKey());
        }
        ids.sort((a, b) -> {
            int x = classes.get(a).start, y = classes.get(b).start;
            if (x != y) return Integer.compare(x, y);
            return a.compareTo(b);
        });
        return ids;
    }

    public boolean addClass(int ts, String classId, int start, int capacity) {
        if (classes.containsKey(classId) || capacity <= 0 || start <= ts) return false;
        classes.put(classId, new GymClass(start, capacity));
        return true;
    }

    public boolean book(int ts, String classId, String member) {
        GymClass c = open(ts, classId);
        if (c == null || c.booked.containsKey(member) || c.booked.size() >= c.capacity) return false;
        if (balance(member) < c.price) return false;
        credits.put(member, balance(member) - c.price);
        c.booked.put(member, c.price);
        return true;
    }

    public boolean cancel(int ts, String classId, String member) {
        GymClass c = open(ts, classId);
        if (c == null) return false;
        if (c.waiting.remove(member)) return true;
        Integer paid = c.booked.remove(member);
        if (paid == null) return false;
        if (c.start - ts >= REFUND_WINDOW) credits.put(member, balance(member) + paid);
        promote(c);
        return true;
    }

    public int spotsLeft(int ts, String classId) {
        GymClass c = classes.get(classId);
        if (c == null || c.cancelled) return -1;
        return c.capacity - c.booked.size();
    }

    public List<String> upcoming(int ts, String member) {
        return memberClasses(member, c -> c.start > ts);
    }

    public int joinWaitlist(int ts, String classId, String member) {
        GymClass c = open(ts, classId);
        if (c == null || c.booked.containsKey(member) || c.waiting.contains(member) || c.booked.size() < c.capacity) return -1;
        c.waiting.add(member);
        return c.waiting.size();
    }

    public List<String> waitlist(int ts, String classId) {
        GymClass c = classes.get(classId);
        if (c == null || c.cancelled) return new ArrayList<>();
        return new ArrayList<>(c.waiting);
    }

    public int addCredits(int ts, String member, int n) {
        if (n <= 0) return -1;
        credits.put(member, balance(member) + n);
        return balance(member);
    }

    public int credits(int ts, String member) {
        return balance(member);
    }

    public boolean setPrice(int ts, String classId, int price) {
        GymClass c = open(ts, classId);
        if (c == null || price < 0) return false;
        c.price = price;
        return true;
    }

    public boolean addSeries(int ts, String seriesId, int firstStart, int capacity, int weeks) {
        if (series.containsKey(seriesId) || weeks <= 0 || capacity <= 0 || firstStart <= ts) return false;
        List<String> ids = new ArrayList<>();
        for (int k = 1; k <= weeks; k++) {
            String id = seriesId + "-" + k;
            if (classes.containsKey(id)) return false;
            ids.add(id);
        }
        for (int k = 0; k < weeks; k++) classes.put(ids.get(k), new GymClass(firstStart + k * WEEK, capacity));
        series.put(seriesId, ids);
        return true;
    }

    public boolean cancelClass(int ts, String classId) {
        GymClass c = open(ts, classId);
        if (c == null) return false;
        for (Map.Entry<String, Integer> e : c.booked.entrySet()) credits.put(e.getKey(), balance(e.getKey()) + e.getValue());
        c.booked.clear();
        c.waiting.clear();
        c.cancelled = true;
        return true;
    }

    public int cancelSeries(int ts, String seriesId) {
        List<String> ids = series.get(seriesId);
        if (ids == null) return -1;
        int n = 0;
        for (String id : ids) if (cancelClass(ts, id)) n++;
        return n;
    }

    public List<String> history(int ts, String member) {
        return memberClasses(member, c -> c.start <= ts);
    }
}
