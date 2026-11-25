import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;

/** An in-memory configuration store for a platform team. */
public class Store {
    /** One field's value. expiresAt 0 means it never expires. */
    private record Entry(String value, int expiresAt) {
        boolean live(int ts) { return expiresAt == 0 || ts < expiresAt; }
    }

    /** A field as a backup keeps it. remaining 0 means no TTL. */
    private record Saved(String value, int remaining) {}

    /** One step in a field's history. e is null for a removal. */
    private record Change(int ts, Entry e) {}

    private final Map<String, Map<String, Entry>> records = new HashMap<>();
    private final Map<String, List<Change>> history = new HashMap<>();
    private final Map<String, Map<String, Map<String, Saved>>> backups = new HashMap<>();

    public Store() {}

    private Entry lookup(int ts, String key, String field) {
        Map<String, Entry> m = records.get(key);
        Entry e = m == null ? null : m.get(field);
        return e != null && e.live(ts) ? e : null;
    }

    private void put(int ts, String key, String field, Entry e) {
        records.computeIfAbsent(key, k -> new HashMap<>()).put(field, e);
        history.computeIfAbsent(key + "\0" + field, k -> new ArrayList<>()).add(new Change(ts, e));
    }

    private void remove(int ts, String key, String field) {
        Map<String, Entry> m = records.get(key);
        m.remove(field);
        if (m.isEmpty()) records.remove(key);
        history.computeIfAbsent(key + "\0" + field, k -> new ArrayList<>()).add(new Change(ts, null));
    }

    // ---- level 1

    public boolean set(int ts, String key, String field, String value) {
        boolean had = lookup(ts, key, field) != null;
        put(ts, key, field, new Entry(value, 0));
        return !had;
    }

    public String get(int ts, String key, String field) {
        Entry e = lookup(ts, key, field);
        return e == null ? null : e.value();
    }

    public boolean delete(int ts, String key, String field) {
        if (lookup(ts, key, field) == null) return false;
        remove(ts, key, field);
        return true;
    }

    public boolean compareAndSet(int ts, String key, String field, String expected, String value) {
        Entry e = lookup(ts, key, field);
        if (e == null || !e.value().equals(expected)) return false;
        put(ts, key, field, new Entry(value, e.expiresAt()));
        return true;
    }

    // ---- level 2

    public List<String> scan(int ts, String key) {
        return scanPrefix(ts, key, "");
    }

    public List<String> scanPrefix(int ts, String key, String prefix) {
        TreeMap<String, String> fields = new TreeMap<>();
        for (Map.Entry<String, Entry> me : records.getOrDefault(key, Map.of()).entrySet()) {
            if (me.getKey().startsWith(prefix) && me.getValue().live(ts)) fields.put(me.getKey(), me.getValue().value());
        }
        List<String> out = new ArrayList<>();
        fields.forEach((f, v) -> out.add(f + "=" + v));
        return out;
    }

    public List<String> listKeys(int ts, String prefix) {
        TreeSet<String> keys = new TreeSet<>();
        for (String k : records.keySet()) {
            if (k.startsWith(prefix) && !scanPrefix(ts, k, "").isEmpty()) keys.add(k);
        }
        return new ArrayList<>(keys);
    }

    // ---- level 3

    public boolean setWithTtl(int ts, String key, String field, String value, int ttl) {
        boolean had = lookup(ts, key, field) != null;
        put(ts, key, field, new Entry(value, ts + ttl));
        return !had;
    }

    public int remainingTtl(int ts, String key, String field) {
        Entry e = lookup(ts, key, field);
        if (e == null) return -1;
        if (e.expiresAt() == 0) return 0;
        return e.expiresAt() - ts;
    }

    // ---- level 4

    public String backup(int ts) {
        Map<String, Map<String, Saved>> b = new HashMap<>();
        for (var ke : records.entrySet()) {
            for (var fe : ke.getValue().entrySet()) {
                Entry e = fe.getValue();
                if (!e.live(ts)) continue;
                int rem = e.expiresAt() != 0 ? e.expiresAt() - ts : 0;
                b.computeIfAbsent(ke.getKey(), k -> new HashMap<>()).put(fe.getKey(), new Saved(e.value(), rem));
            }
        }
        String id = "b" + (backups.size() + 1);
        backups.put(id, b);
        return id;
    }

    public boolean restore(int ts, String backupId) {
        Map<String, Map<String, Saved>> b = backups.get(backupId);
        if (b == null) return false;
        for (String k : new ArrayList<>(records.keySet())) {
            for (String f : new ArrayList<>(records.get(k).keySet())) {
                if (!b.getOrDefault(k, Map.of()).containsKey(f)) remove(ts, k, f);
            }
        }
        for (var ke : b.entrySet()) {
            for (var fe : ke.getValue().entrySet()) {
                Saved sv = fe.getValue();
                put(ts, ke.getKey(), fe.getKey(), new Entry(sv.value(), sv.remaining() != 0 ? ts + sv.remaining() : 0));
            }
        }
        return true;
    }

    public String getAt(int ts, String key, String field, int atTs) {
        Change last = null;
        for (Change c : history.getOrDefault(key + "\0" + field, List.of())) {
            if (c.ts() <= atTs) last = c;
        }
        if (last == null || last.e() == null || !last.e().live(atTs)) return null;
        return last.e().value();
    }
}
