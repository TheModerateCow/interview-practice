import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** In-memory storage: plans, keys and each key's request log. */
final class Store {
    private final Map<String, Plan> plans = new HashMap<>();
    private final Map<String, Key> keys = new HashMap<>();
    private final Map<String, List<Event>> events = new HashMap<>(); // per key, oldest first

    Plan plan(String name) {
        return plans.get(name);
    }

    void addPlan(Plan p) {
        plans.put(p.name(), p);
    }

    Key key(String id) {
        return keys.get(id);
    }

    void addKey(Key k) {
        keys.put(k.id(), k);
    }

    /** Move a key to another plan. */
    void setPlan(String id, String plan) {
        Key k = keys.get(id);
        keys.put(id, new Key(k.id(), k.org(), plan, k.revoked()));
    }

    void revoke(String id) {
        Key k = keys.get(id);
        keys.put(id, new Key(k.id(), k.org(), k.plan(), true));
    }

    /** Ids of an organisation's keys, sorted. */
    List<String> keysOf(String org) {
        List<String> out = new ArrayList<>();
        for (Key k : keys.values()) if (k.org().equals(org)) out.add(k.id());
        out.sort(null);
        return out;
    }

    /** Append a decision to the key's log. Requests for one key arrive in time order, so the log stays sorted by {@code at}. */
    void record(String id, Event e) {
        events.computeIfAbsent(id, k -> new ArrayList<>()).add(e);
    }

    /** The key's events with start <= at < end. */
    List<Event> eventsBetween(String id, long start, long end) {
        List<Event> log = events.getOrDefault(id, List.of());
        return log.subList(lowerBound(log, start), lowerBound(log, end));
    }

    /** Units the key spent with start <= at < end. */
    long unitsBetween(String id, long start, long end) {
        long sum = 0;
        for (Event e : eventsBetween(id, start, end)) if (e.allowed()) sum += e.cost();
        return sum;
    }

    /** Index of the first event with at >= t. */
    private static int lowerBound(List<Event> log, long t) {
        int lo = 0, hi = log.size();
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (log.get(mid).at() < t) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }
}
