import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** The daily digest. */
final class Digest {
    private Digest() {}

    /** The user's held notifications from their local day before the one containing {@code now}. */
    static List<DigestLine> build(Store store, String id, long now) {
        User u = store.user(id);
        if (u == null) {
            throw new NotifyException(NotifyException.Code.UNKNOWN_USER, id);
        }
        long to = Clock.localMidnight(now, u.offsetMin);
        long start = to - Clock.DAY_SECONDS;
        Map<String, DigestLine> lines = new LinkedHashMap<>();
        for (Entry r : store.log(id)) {
            Notification n = r.notification();
            if (!r.result().status().equals(Notify.HELD) || n.at() < start || n.at() >= to) {
                continue;
            }
            DigestLine line = lines.computeIfAbsent(n.topic(), DigestLine::new);
            line.count++;
            line.latest = n.title();
        }
        List<DigestLine> out = new ArrayList<>(lines.values());
        out.sort(Comparator.comparingInt((DigestLine l) -> -l.count).thenComparing(l -> l.topic));
        return out;
    }
}
