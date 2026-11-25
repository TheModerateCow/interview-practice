import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** In-memory users, per-user log and the indexes the fan-out checks on every send. */
final class Store {
    private record Pair(String user, String channel) {}

    /** The index key for a user's dedupe key. */
    static String dedupeId(String user, String key) {
        return key;
    }

    private final Map<String, User> users = new HashMap<>();
    private final Map<String, Long> seen = new HashMap<>(); // dedupeId -> `at` of the last accepted notification
    private final Map<Pair, ArrayDeque<Long>> recent = new HashMap<>(); // delivery times, oldest first
    private final Map<String, List<Entry>> logs = new HashMap<>(); // per user, oldest first

    User user(String id) {
        return users.get(id);
    }

    void putUser(User u) {
        users.put(u.id, u);
    }

    void setChannels(String id, List<String> chans) {
        users.get(id).channels = chans;
    }

    /** When the user last had a non-duplicate notification with this dedupe key, or null. */
    Long lastAccepted(String user, String key) {
        return seen.get(dedupeId(user, key));
    }

    void accept(String user, String key, long at) {
        seen.put(dedupeId(user, key), at);
    }

    /** Counts the user's deliveries on {@code ch} with time &gt; since. */
    int deliveriesSince(String user, String ch, long since) {
        int n = 0;
        for (Entry e : log(user)) {
            if (e.notification().at() > since && e.result().channels().contains(ch)) n++;
        }
        return n;
    }

    void delivered(String user, String ch, long at) {
        recent.computeIfAbsent(new Pair(user, ch), k -> new ArrayDeque<>()).addLast(at);
    }

    void record(Entry e) {
        logs.computeIfAbsent(e.notification().user(), k -> new ArrayList<>()).add(e);
    }

    /** The user's records, oldest first. */
    List<Entry> log(String user) {
        return logs.computeIfAbsent(user, k -> new ArrayList<>());
    }
}
