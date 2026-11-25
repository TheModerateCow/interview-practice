import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** The notification fan-out for one region. */
public class Service {
    private final Store store = new Store();

    private static NotifyException err(NotifyException.Code code, Object what) {
        return new NotifyException(code, String.valueOf(what));
    }

    /** Registers a user at a fixed UTC offset. New users get email only and no quiet hours. */
    public void addUser(String id, int offsetMin) {
        if (offsetMin < -720 || offsetMin > 840) {
            throw err(NotifyException.Code.BAD_OFFSET, offsetMin);
        }
        if (store.user(id) != null) {
            throw err(NotifyException.Code.DUPLICATE_USER, id);
        }
        store.putUser(new User(id, offsetMin));
    }

    /** A copy of the user's current settings. */
    public User user(String id) {
        User u = store.user(id);
        if (u == null) {
            throw err(NotifyException.Code.UNKNOWN_USER, id);
        }
        User c = new User(u.id, u.offsetMin);
        c.channels = new ArrayList<>(u.channels);
        c.quietFrom = u.quietFrom;
        c.quietTo = u.quietTo;
        return c;
    }

    /** Replaces the user's enabled channels. An empty list means everything goes to the digest. */
    public void setChannels(String id, List<String> chans) {
        if (store.user(id) == null) {
            throw err(NotifyException.Code.UNKNOWN_USER, id);
        }
        Set<String> seen = new HashSet<>();
        for (String ch : chans) {
            if (!Notify.HOURLY_CAP.containsKey(ch) || seen.contains(ch)) {
                throw err(NotifyException.Code.BAD_CHANNEL, ch);
            }
            seen.add(ch);
        }
        store.setChannels(id, chans);
    }

    /** Sets the local hours [start, end) during which only urgent notifications go out. start == end turns them off. */
    public void setQuietHours(String id, int start, int end) {
        User u = store.user(id);
        if (u == null) {
            throw err(NotifyException.Code.UNKNOWN_USER, id);
        }
        if (start < 0 || start > 23 || end < 0 || end > 23) {
            throw err(NotifyException.Code.BAD_QUIET_HOURS, start + "," + end);
        }
        u.quietFrom = start;
        u.quietTo = end;
    }

    /** Fans one notification out to the user's channels and logs the result. Sends for one user must come in time order. */
    public Result send(Notification n) {
        User u = store.user(n.user());
        if (u == null) {
            throw err(NotifyException.Code.UNKNOWN_USER, n.user());
        }
        if (n.topic() == null || n.topic().isEmpty() || n.key() == null || n.key().isEmpty()) {
            throw err(NotifyException.Code.BAD_NOTIFICATION, n);
        }
        Long last = store.lastAccepted(n.user(), n.key());
        if (last != null && n.at() - last < Notify.DEDUPE_WINDOW) {
            Result res = new Result(Notify.DUPLICATE, List.of());
            store.record(new Entry(n, res));
            return res;
        }
        store.accept(n.user(), n.key(), n.at());
        List<String> out = new ArrayList<>();
        if (n.urgent() || !Clock.inQuietHours(u, n.at())) {
            for (String ch : u.channels) {
                if (store.deliveriesSince(n.user(), ch, n.at() - Notify.CAP_WINDOW) < Notify.HOURLY_CAP.get(ch)) {
                    store.delivered(n.user(), ch, n.at());
                    out.add(ch);
                }
            }
        }
        Result res = new Result(out.isEmpty() ? Notify.HELD : Notify.SENT, out);
        store.record(new Entry(n, res));
        return res;
    }

    /** The user's daily digest of held notifications. See problem.md. */
    public List<DigestLine> digest(String id, long now) {
        return Digest.build(store, id, now);
    }
}
