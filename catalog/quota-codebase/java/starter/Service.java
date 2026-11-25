import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** The quota service for one gateway region. */
public class Service {
    /** Units spent in a window, and the total the key may spend there. */
    public record Usage(long used, long limit) {}

    private final Store store = new Store();

    /** Register a pricing tier. */
    public void addPlan(Plan p) {
        if (p.limit() <= 0 || p.window() <= 0 || p.burst() < 0) throw QuotaException.invalidPlan();
        if (store.plan(p.name()) != null) throw QuotaException.duplicatePlan();
        store.addPlan(p);
    }

    /** Create an API key for org on the named plan. */
    public void issueKey(String id, String org, String plan) {
        if (store.plan(plan) == null) throw QuotaException.unknownPlan();
        if (store.key(id) != null) throw QuotaException.duplicateKey();
        store.addKey(new Key(id, org, plan));
    }

    /** A key's current record. */
    public Key key(String id) {
        Key k = store.key(id);
        if (k == null) throw QuotaException.unknownKey();
        return k;
    }

    /** Disable a key for good. Its usage stays in the log. */
    public void revoke(String id) {
        key(id);
        store.revoke(id);
    }

    /** Move a key to another plan; the new limit applies from the next request on. */
    public void changePlan(String id, String plan) {
        key(id);
        if (store.plan(plan) == null) throw QuotaException.unknownPlan();
        store.setPlan(id, plan);
    }

    /**
     * Decide whether a request costing {@code cost} units, made at {@code now}, fits the key's plan, and log the
     * decision. A denied request spends nothing.
     */
    public Decision allow(String id, long now, long cost) {
        Key k = key(id);
        if (k.revoked()) throw QuotaException.revoked();
        if (cost <= 0) throw QuotaException.badCost();
        Plan p = store.plan(k.plan());
        Usage u = window(id, p, now);
        if (u.used() + cost > u.limit()) {
            store.record(id, new Event(now, cost, false));
            return new Decision(false, u.limit() - u.used(), Window.resetIn(now, p.window()));
        }
        store.record(id, new Event(now, cost, true));
        return new Decision(true, u.limit() - u.used() - cost);
    }

    /** Units spent in the window containing now, and the total the key may spend there. */
    public Usage usage(String id, long now) {
        Key k = key(id);
        return window(id, store.plan(k.plan()), now);
    }

    /**
     * Summarise an organisation's traffic with start <= at < end, one line per key that made a request in that
     * range. See problem.md for the rules.
     */
    public List<UsageLine> report(String org, long start, long end) {
        throw new UnsupportedOperationException("not implemented");
    }

    /** Units a key has spent in the window containing now, and that window's capacity. */
    private Usage window(String id, Plan p, long now) {
        long start = Window.start(now, p.window());
        long used = store.unitsBetween(id, start, start + p.window());
        long prev = store.unitsBetween(id, start - p.window(), start);
        return new Usage(used, Window.capacity(p, prev));
    }
}
