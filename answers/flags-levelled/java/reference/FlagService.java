import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** A feature-flag service: flags switched on or off per environment, user targeting,
 *  percentage rollouts, scheduled changes and an audit history with rollback. */
public class FlagService {
    private record Stamp(int ts, int v) {}  // v: 1/0 for on/off, or the percent

    private static final class Env {
        boolean on;
        int rollout = 100;
        final Set<String> targets = new HashSet<>();
        int evals;
        final List<Stamp> stateLog = new ArrayList<>();    // (time, on) after each on/off change
        final List<Stamp> rolloutLog = new ArrayList<>();  // (time, percent) after each rollout change
    }

    private static final class Schedule {
        final String id, flag, env;
        final int seq, at;
        final boolean on;
        boolean done;
        Schedule(String id, int seq, String flag, String env, boolean on, int at) {
            this.id = id; this.seq = seq; this.flag = flag; this.env = env; this.on = on; this.at = at;
        }
    }

    private final Map<String, Map<String, Env>> flags = new HashMap<>();
    private final Map<String, Schedule> schedules = new HashMap<>();
    private int nextSeq = 1;

    public FlagService() {}

    /** Stable bucket in [0, 100) for a user of a flag. */
    private static int bucket(String flagId, String userId) {
        long h = 0;
        for (int c : (flagId + ":" + userId).codePoints().toArray()) h = (h * 31 + c) % 1000000007L;
        return (int) (h % 100);
    }

    // ---- level 1

    public boolean createFlag(int ts, String flagId) {
        advance(ts);
        if (flags.containsKey(flagId)) return false;
        flags.put(flagId, new HashMap<>());
        return true;
    }

    public boolean setEnabled(int ts, String flagId, String env, boolean on) {
        advance(ts);
        Env e = env(flagId, env);
        if (e == null) return false;
        apply(e, ts, on);
        return true;
    }

    public boolean addTarget(int ts, String flagId, String env, String userId) {
        advance(ts);
        Env e = env(flagId, env);
        return e != null && e.targets.add(userId);
    }

    public boolean removeTarget(int ts, String flagId, String env, String userId) {
        advance(ts);
        Env e = env(flagId, env);
        return e != null && e.targets.remove(userId);
    }

    public boolean isEnabled(int ts, String flagId, String env, String userId) {
        advance(ts);
        Env e = env(flagId, env);
        if (e == null) return false;
        e.evals++;
        return sees(flagId, e, userId);
    }

    // ---- level 2

    public boolean setRollout(int ts, String flagId, String env, int percent) {
        advance(ts);
        Env e = env(flagId, env);
        if (e == null || percent < 0 || percent > 100) return false;
        e.rollout = percent;
        e.rolloutLog.add(new Stamp(ts, percent));
        return true;
    }

    public List<String> enabledFlags(int ts, String env, String userId) {
        advance(ts);
        List<String> out = new ArrayList<>();
        for (String id : flags.keySet()) if (sees(id, env(id, env), userId)) out.add(id);
        out.sort(null);
        return out;
    }

    public List<String> mostEvaluated(int ts, String env, int n) {
        advance(ts);
        List<Map.Entry<String, Integer>> rows = new ArrayList<>();
        for (var en : flags.entrySet()) {
            Env e = en.getValue().get(env);
            if (e != null && e.evals > 0) rows.add(Map.entry(en.getKey(), e.evals));
        }
        rows.sort(Comparator.<Map.Entry<String, Integer>>comparingInt(r -> -r.getValue()).thenComparing(Map.Entry::getKey));
        List<String> out = new ArrayList<>();
        for (int i = 0; i < rows.size() && i < n; i++) out.add(rows.get(i).getKey() + "(" + rows.get(i).getValue() + ")");
        return out;
    }

    // ---- level 3

    public String scheduleChange(int ts, String flagId, String env, boolean on, int atTs) {
        advance(ts);
        if (!flags.containsKey(flagId) || atTs <= ts) return "";
        int seq = nextSeq++;
        String id = "s" + seq;
        schedules.put(id, new Schedule(id, seq, flagId, env, on, atTs));
        return id;
    }

    public boolean cancelSchedule(int ts, String scheduleId) {
        advance(ts);
        Schedule s = schedules.get(scheduleId);
        if (s == null || s.done) return false;
        schedules.remove(scheduleId);
        return true;
    }

    public List<String> pending(int ts, String flagId) {
        advance(ts);
        List<String> out = new ArrayList<>();
        for (Schedule s : due(Integer.MAX_VALUE)) if (s.flag.equals(flagId)) out.add(s.id);
        return out;
    }

    // ---- level 4

    public List<String> history(int ts, String flagId, String env) {
        advance(ts);
        List<String> out = new ArrayList<>();
        Env e = env(flagId, env);
        if (e == null) return out;
        for (Stamp s : e.stateLog) out.add(s.ts() + ":" + (s.v() == 1 ? "on" : "off"));
        return out;
    }

    public boolean rollback(int ts, String flagId, String env, int toTs) {
        advance(ts);
        Env e = env(flagId, env);
        if (e == null) return false;
        boolean on = false;
        int percent = 100;
        for (Stamp s : e.stateLog) if (s.ts() <= toTs) on = s.v() == 1;
        for (Stamp s : e.rolloutLog) if (s.ts() <= toTs) percent = s.v();
        apply(e, ts, on);
        e.rollout = percent;
        e.rolloutLog.add(new Stamp(ts, percent));
        return true;
    }

    // ---- internals

    private Env env(String flagId, String name) {
        Map<String, Env> envs = flags.get(flagId);
        return envs == null ? null : envs.computeIfAbsent(name, k -> new Env());
    }

    private static boolean sees(String flagId, Env e, String userId) {
        return e.targets.contains(userId) || (e.on && bucket(flagId, userId) < e.rollout);
    }

    private static void apply(Env e, int ts, boolean on) {
        e.on = on;
        e.stateLog.add(new Stamp(ts, on ? 1 : 0));
    }

    /** Pending scheduled changes due at or before ts, by at then scheduling order. */
    private List<Schedule> due(int ts) {
        List<Schedule> out = new ArrayList<>();
        for (Schedule s : schedules.values()) if (!s.done && s.at <= ts) out.add(s);
        out.sort(Comparator.<Schedule>comparingInt(s -> s.at).thenComparingInt(s -> s.seq));
        return out;
    }

    /** Applies every scheduled change due at or before ts, before the call at ts runs. */
    private void advance(int ts) {
        for (Schedule s : due(ts)) {
            s.done = true;
            apply(env(s.flag, s.env), s.at, s.on);
        }
    }
}
