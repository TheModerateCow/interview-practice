import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** The box office for a concert promoter: events with a fixed number of seats, buyers who own tickets, and short seat holds at checkout. */
public class Office {
    private record Change(int ts, String buyer, int delta) {}

    private static final class Hold {
        final String eventId, buyer;
        final int qty, expiresAt;
        boolean confirmed;
        Hold(String eventId, String buyer, int qty, int expiresAt) {
            this.eventId = eventId; this.buyer = buyer; this.qty = qty; this.expiresAt = expiresAt;
        }
    }

    private static final class Event {
        final int capacity;
        final Map<String, Integer> owned = new HashMap<>();
        int sold;
        final List<Change> log = new ArrayList<>();
        Event(int capacity) { this.capacity = capacity; }
    }

    private final Map<String, Event> events = new HashMap<>();
    private final Map<String, Hold> holds = new HashMap<>();
    private int nextId;

    public Office() {}

    private void own(int ts, Event e, String buyer, int delta) {
        e.owned.merge(buyer, delta, Integer::sum);
        e.sold += delta;
        e.log.add(new Change(ts, buyer, delta));
    }

    private int held(int ts, String eventId) {
        int n = 0;
        for (Hold h : holds.values()) {
            if (h.eventId.equals(eventId) && !h.confirmed && ts < h.expiresAt) n += h.qty;
        }
        return n;
    }

    public boolean createEvent(int ts, String eventId, int capacity) {
        if (events.containsKey(eventId) || capacity <= 0) return false;
        events.put(eventId, new Event(capacity));
        return true;
    }

    public boolean buy(int ts, String eventId, String buyer, int qty) {
        Event e = events.get(eventId);
        if (e == null || qty <= 0 || qty > available(ts, eventId)) return false;
        own(ts, e, buyer, qty);
        return true;
    }

    public boolean refund(int ts, String eventId, String buyer, int qty) {
        Event e = events.get(eventId);
        if (e == null || qty <= 0 || e.owned.getOrDefault(buyer, 0) < qty) return false;
        own(ts, e, buyer, -qty);
        return true;
    }

    public int available(int ts, String eventId) {
        Event e = events.get(eventId);
        if (e == null) return -1;
        return e.capacity - e.sold - held(ts, eventId);
    }

    public List<String> topBuyers(int ts, String eventId, int n) {
        List<String> out = new ArrayList<>();
        Event e = events.get(eventId);
        if (e == null) return out;
        List<String> names = new ArrayList<>();
        for (Map.Entry<String, Integer> en : e.owned.entrySet()) {
            if (en.getValue() > 0) names.add(en.getKey());
        }
        names.sort((a, b) -> {
            if (!e.owned.get(a).equals(e.owned.get(b))) return e.owned.get(b) - e.owned.get(a);
            return a.compareTo(b);
        });
        for (int i = 0; i < names.size() && i < n; i++) out.add(names.get(i) + "(" + e.owned.get(names.get(i)) + ")");
        return out;
    }

    public List<String> busiestEvents(int ts, int n) {
        List<String> ids = new ArrayList<>(events.keySet());
        ids.sort((a, b) -> {
            int x = events.get(a).sold, y = events.get(b).sold;
            if (x != y) return y - x;
            return a.compareTo(b);
        });
        List<String> out = new ArrayList<>();
        for (int i = 0; i < ids.size() && i < n; i++) out.add(ids.get(i) + "(" + events.get(ids.get(i)).sold + ")");
        return out;
    }

    public String hold(int ts, String eventId, String buyer, int qty, int ttl) {
        if (!events.containsKey(eventId) || qty <= 0 || ttl <= 0 || qty > available(ts, eventId)) return "";
        String id = "h" + (++nextId);
        holds.put(id, new Hold(eventId, buyer, qty, ts + ttl));
        return id;
    }

    public boolean confirm(int ts, String holdId) {
        Hold h = holds.get(holdId);
        if (h == null || h.confirmed || ts >= h.expiresAt) return false;
        h.confirmed = true;
        own(ts, events.get(h.eventId), h.buyer, h.qty);
        return true;
    }

    public int ownedAt(int ts, String eventId, String buyer, int atTs) {
        Event e = events.get(eventId);
        if (e == null) return -1;
        int n = 0;
        for (Change c : e.log) {
            if (c.ts <= atTs && c.buyer.equals(buyer)) n += c.delta;
        }
        return n;
    }

    public int soldAt(int ts, String eventId, int atTs) {
        Event e = events.get(eventId);
        if (e == null) return -1;
        int n = 0;
        for (Change c : e.log) {
            if (c.ts <= atTs) n += c.delta;
        }
        return n;
    }
}
