import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Transaction risk screen of a payment provider: blocklists, velocity rules, rule priorities with an allowlist, and a manual review queue whose declines block the card for a while. Every method takes ts first: the time of the call. Timestamps never go down. */
public class RiskScreen {
    private static final Set<String> KINDS = Set.of("card", "merchant", "country");
    private static final Map<String, String> OUTCOME = Map.of("block", "decline", "velocity", "review", "allow", "approve");
    /** Priority ties: the stricter outcome wins. */
    private static final Map<String, Integer> STRICTNESS = Map.of("decline", 0, "review", 1, "approve", 2);

    private static final class Rule {
        final String type; // block, allow, velocity
        int priority;
        Integer until; // block only: expiry time, null = permanent
        String metric;
        int limit, window;
        Rule(String type) { this.type = type; }
    }

    private static final class Txn {
        final int ts, amount;
        final String card;
        String decision, rule = "";
        Txn(int ts, String card, int amount) { this.ts = ts; this.card = card; this.amount = amount; }
    }

    private record Hit(int priority, String name, String outcome) {
        /** True if this hit beats o. */
        boolean beats(Hit o) {
            if (priority != o.priority) return priority > o.priority;
            int s = STRICTNESS.get(outcome), t = STRICTNESS.get(o.outcome);
            if (s != t) return s < t;
            return name.compareTo(o.name) < 0;
        }
    }

    // names: "block:<kind>:<value>", "allow:<kind>:<value>", or the velocity rule's id (no colon)
    private final Map<String, Rule> rules = new HashMap<>();
    private final Map<String, Txn> txns = new LinkedHashMap<>(); // screen order

    public RiskScreen() {}

    /** The rule called name, or null if there is none or it is a temporary block that has expired. */
    private Rule get(int ts, String name) {
        Rule r = rules.get(name);
        if (r == null || (r.until != null && ts >= r.until)) return null;
        return r;
    }

    // ---------------------------------------------------------------- level 1

    public boolean block(int ts, String kind, String value) {
        String name = "block:" + kind + ":" + value;
        if (!KINDS.contains(kind) || get(ts, name) != null) return false;
        rules.put(name, new Rule("block"));
        return true;
    }

    public boolean unblock(int ts, String kind, String value) {
        String name = "block:" + kind + ":" + value;
        if (get(ts, name) == null) return false;
        rules.remove(name);
        return true;
    }

    public String screen(int ts, String txnId, String card, String merchant, int amount, String country) {
        if (txns.containsKey(txnId) || amount <= 0) return "";
        Txn t = new Txn(ts, card, amount);
        txns.put(txnId, t);
        List<Hit> hits = new ArrayList<>();
        String[][] fields = {{"card", card}, {"merchant", merchant}, {"country", country}};
        for (String[] kv : fields) {
            for (String type : new String[] {"block", "allow"}) {
                String name = type + ":" + kv[0] + ":" + kv[1];
                Rule r = get(ts, name);
                if (r != null) hits.add(new Hit(r.priority, name, OUTCOME.get(type)));
            }
        }
        for (Map.Entry<String, Rule> e : rules.entrySet()) {
            Rule r = e.getValue();
            if (!r.type.equals("velocity")) continue;
            int used = 0;
            for (Txn o : txns.values()) { // includes this one
                if (o.card.equals(card) && o.ts > ts - r.window) used += r.metric.equals("count") ? 1 : o.amount;
            }
            if (used > r.limit) hits.add(new Hit(r.priority, e.getKey(), "review"));
        }
        t.decision = "approve";
        Hit best = null;
        for (Hit h : hits) if (best == null || h.beats(best)) best = h;
        if (best != null) { t.decision = best.outcome(); t.rule = best.name(); }
        return t.decision;
    }

    public String decision(int ts, String txnId) {
        Txn t = txns.get(txnId);
        return t == null ? "" : t.decision;
    }

    // ---------------------------------------------------------------- level 2

    public boolean addVelocityRule(int ts, String ruleId, String metric, int limit, int window) {
        if (rules.containsKey(ruleId) || !(metric.equals("count") || metric.equals("amount")) || limit <= 0 || window <= 0) return false;
        Rule r = new Rule("velocity");
        r.metric = metric; r.limit = limit; r.window = window;
        rules.put(ruleId, r);
        return true;
    }

    public boolean removeRule(int ts, String ruleId) {
        Rule r = rules.get(ruleId);
        if (r == null || !r.type.equals("velocity")) return false;
        rules.remove(ruleId);
        return true;
    }

    // ---------------------------------------------------------------- level 3

    public boolean allow(int ts, String kind, String value, int priority) {
        String name = "allow:" + kind + ":" + value;
        if (!KINDS.contains(kind) || rules.containsKey(name)) return false;
        Rule r = new Rule("allow");
        r.priority = priority;
        rules.put(name, r);
        return true;
    }

    public boolean setPriority(int ts, String rule, int priority) {
        Rule r = get(ts, rule);
        if (r == null) return false;
        r.priority = priority;
        return true;
    }

    public String explain(int ts, String txnId) {
        Txn t = txns.get(txnId);
        return t == null ? "" : t.rule;
    }

    // ---------------------------------------------------------------- level 4

    public List<String> pendingReviews(int ts) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, Txn> e : txns.entrySet()) if (e.getValue().decision.equals("review")) out.add(e.getKey());
        return out;
    }

    public boolean approveReview(int ts, String txnId) {
        Txn t = txns.get(txnId);
        if (t == null || !t.decision.equals("review")) return false;
        t.decision = "approve";
        t.rule = "analyst";
        return true;
    }

    public boolean declineReview(int ts, String txnId, int blockFor) {
        Txn t = txns.get(txnId);
        if (t == null || !t.decision.equals("review") || blockFor <= 0) return false;
        t.decision = "decline";
        t.rule = "analyst";
        String name = "block:card:" + t.card;
        Rule r = get(ts, name);
        if (r == null) {
            Rule b = new Rule("block");
            b.until = ts + blockFor;
            rules.put(name, b);
        } else if (r.until != null) {
            r.until = Math.max(r.until, ts + blockFor);
        }
        return true;
    }
}
