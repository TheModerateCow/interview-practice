import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;

/** A monorepo release pipeline: consumer links, a run tracker, cycle checks, finish-time estimates and warm caches. */
public class Pipeline {
    private static final class Job {
        final int minutes;
        Integer warm; // null = no warm time
        String consumer; // null = none
        final Set<String> inputs = new HashSet<>();
        boolean done;
        Job(int minutes) { this.minutes = minutes; }
    }

    private final Map<String, Job> jobs = new HashMap<>();

    public Pipeline() {}

    public boolean addJob(String name, int minutes) {
        if (jobs.containsKey(name)) return false;
        jobs.put(name, new Job(minutes));
        return true;
    }

    public boolean setConsumer(String name, String consumer) {
        Job j = jobs.get(name), c = jobs.get(consumer);
        if (j == null || c == null || c.done) return false;
        if (j.consumer != null) jobs.get(j.consumer).inputs.remove(name);
        j.consumer = consumer;
        c.inputs.add(name);
        return true;
    }

    public List<String> inputs(String name) {
        Job j = jobs.get(name);
        List<String> out = j == null ? new ArrayList<>() : new ArrayList<>(j.inputs);
        Collections.sort(out);
        return out;
    }

    private boolean isReady(Job j) {
        if (j.done) return false;
        for (String i : j.inputs) if (!jobs.get(i).done) return false;
        return true;
    }

    public List<String> ready() {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, Job> e : jobs.entrySet()) if (isReady(e.getValue())) out.add(e.getKey());
        Collections.sort(out);
        return out;
    }

    public boolean finish(String name) {
        Job j = jobs.get(name);
        if (j == null || !isReady(j)) return false;
        j.done = true;
        return true;
    }

    public List<String> stuck() {
        // Each job has at most one consumer: follow the links from every job; a walk that meets itself found a cycle.
        Map<String, Integer> state = new HashMap<>(); // 1 = on the current walk, 2 = settled
        List<String> out = new ArrayList<>();
        for (String start : jobs.keySet()) {
            List<String> walk = new ArrayList<>();
            String v = start;
            while (v != null && !state.containsKey(v)) {
                state.put(v, 1);
                walk.add(v);
                v = jobs.get(v).consumer;
            }
            if (v != null && state.get(v) == 1) out.addAll(walk.subList(walk.indexOf(v), walk.size()));
            for (String w : walk) state.put(w, 2);
        }
        Collections.sort(out);
        return out;
    }

    public List<String> runOrder() {
        Map<String, Integer> waiting = new HashMap<>();
        PriorityQueue<String> heap = new PriorityQueue<>();
        for (Map.Entry<String, Job> e : jobs.entrySet()) {
            if (e.getValue().done) continue;
            int w = 0;
            for (String i : e.getValue().inputs) if (!jobs.get(i).done) w++;
            waiting.put(e.getKey(), w);
            if (w == 0) heap.add(e.getKey());
        }
        List<String> out = new ArrayList<>();
        while (!heap.isEmpty()) {
            String name = heap.poll();
            out.add(name);
            String c = jobs.get(name).consumer;
            if (c != null && waiting.containsKey(c)) {
                int w = waiting.get(c) - 1;
                waiting.put(c, w);
                if (w == 0) heap.add(c);
            }
        }
        return out;
    }

    /** Unfinished jobs feeding name (name first, each before its inputs); null if name is on a cycle. */
    private List<String> upstream(String name) {
        List<String> order = new ArrayList<>();
        order.add(name);
        for (int k = 0; k < order.size(); k++) {
            for (String i : jobs.get(order.get(k)).inputs) {
                if (jobs.get(i).done) continue;
                if (i.equals(name)) return null;
                order.add(i);
            }
        }
        return order;
    }

    private Map<String, Integer> times(String name) {
        List<String> order = upstream(name);
        if (order == null) return null;
        Map<String, Integer> t = new HashMap<>();
        for (int k = order.size() - 1; k >= 0; k--) {
            String v = order.get(k);
            int longest = 0;
            for (String i : jobs.get(v).inputs) if (!jobs.get(i).done) longest = Math.max(longest, t.get(i));
            t.put(v, jobs.get(v).minutes + longest);
        }
        return t;
    }

    public Integer finishTime(String name) {
        Job j = jobs.get(name);
        if (j == null) return null;
        if (j.done) return 0;
        Map<String, Integer> t = times(name);
        return t == null ? null : t.get(name);
    }

    public List<String> criticalPath(String name) {
        List<String> path = new ArrayList<>();
        Job j = jobs.get(name);
        if (j == null || j.done) return path;
        Map<String, Integer> t = times(name);
        if (t == null) return path;
        path.add(name);
        while (true) {
            String next = null;
            for (String i : jobs.get(path.get(path.size() - 1)).inputs) {
                if (jobs.get(i).done) continue;
                if (next == null || t.get(i) > t.get(next) || t.get(i).equals(t.get(next)) && i.compareTo(next) < 0) next = i;
            }
            if (next == null) break;
            path.add(next);
        }
        Collections.reverse(path);
        return path;
    }

    public boolean setWarm(String name, int minutes) {
        Job j = jobs.get(name);
        if (j == null || minutes > j.minutes) return false;
        j.warm = minutes;
        return true;
    }

    public Integer fastestFinish(String name, int k) {
        Job j = jobs.get(name);
        if (j == null) return null;
        if (j.done) return 0;
        List<String> order = upstream(name);
        if (order == null) return null;
        k = Math.min(k, order.size());
        // f[v][b]: fewest minutes to finish v with at most b of its upstream jobs warmed.
        Map<String, int[]> f = new HashMap<>();
        for (int x = order.size() - 1; x >= 0; x--) {
            String v = order.get(x);
            int[] g = new int[k + 1]; // when v's inputs are all done, with at most b warmed among them
            for (String c : jobs.get(v).inputs) {
                if (jobs.get(c).done) continue;
                int[] fc = f.remove(c);
                int[] ng = new int[k + 1];
                for (int b = 0; b <= k; b++) {
                    // inputs run in parallel: split b between those so far and c, and wait for the slower side
                    int best = Integer.MAX_VALUE;
                    for (int a = 0; a <= b; a++) best = Math.min(best, Math.max(g[a], fc[b - a]));
                    ng[b] = best;
                }
                g = ng;
            }
            Job jv = jobs.get(v);
            int warm = jv.warm == null ? jv.minutes : jv.warm;
            int[] fv = new int[k + 1];
            fv[0] = jv.minutes + g[0];
            for (int b = 1; b <= k; b++) fv[b] = Math.min(jv.minutes + g[b], warm + g[b - 1]);
            f.put(v, fv);
        }
        return f.get(name)[k];
    }
}
