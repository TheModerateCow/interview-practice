import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;

/** Delivery routing on a road network: junctions and two-way roads, closures, fastest routes and an electric van. */
public class Network {
    private static final class Road {
        final int a, b; // junction indexes
        int minutes, energy;
        boolean open = true;
        Road(int a, int b, int minutes) { this.a = a; this.b = b; this.minutes = minutes; }
        int other(int u) { return a == u ? b : a; }
    }

    private final Map<String, Integer> index = new HashMap<>(); // junction id -> index
    private final List<String> names = new ArrayList<>();       // index -> junction id
    private final List<List<String>> at = new ArrayList<>();    // index -> ids of the roads touching it
    private final List<Integer> rate = new ArrayList<>();       // index -> minutes per unit, 0 = no charger
    private final Map<String, Road> roads = new HashMap<>();

    public Network() {}

    // Level 1

    public boolean addJunction(int ts, String id) {
        if (index.containsKey(id)) return false;
        index.put(id, names.size());
        names.add(id);
        at.add(new ArrayList<>());
        rate.add(0);
        return true;
    }

    public boolean addRoad(int ts, String road, String a, String b, int minutes) {
        Integer ia = index.get(a), ib = index.get(b);
        if (roads.containsKey(road) || ia == null || ib == null || a.equals(b)) return false;
        roads.put(road, new Road(ia, ib, minutes));
        at.get(ia).add(road);
        at.get(ib).add(road);
        return true;
    }

    public List<String> roadsAt(int ts, String junction) {
        List<String> out = new ArrayList<>();
        Integer u = index.get(junction);
        if (u == null) return out;
        List<String> ids = new ArrayList<>(at.get(u));
        Collections.sort(ids);
        for (String id : ids) {
            Road r = roads.get(id);
            if (r.open) out.add(id + ":" + names.get(r.other(u)) + ":" + r.minutes);
        }
        return out;
    }

    /** The open roads at u. */
    private List<Road> next(int u) {
        List<Road> out = new ArrayList<>();
        for (String id : at.get(u)) {
            Road r = roads.get(id);
            if (r.open) out.add(r);
        }
        return out;
    }

    private boolean[] component(int start) {
        boolean[] seen = new boolean[names.size()];
        seen[start] = true;
        ArrayDeque<Integer> todo = new ArrayDeque<>();
        todo.push(start);
        while (!todo.isEmpty()) {
            int u = todo.pop();
            for (Road r : next(u)) {
                int v = r.other(u);
                if (!seen[v]) {
                    seen[v] = true;
                    todo.push(v);
                }
            }
        }
        return seen;
    }

    public boolean reachable(int ts, String origin, String dest) {
        Integer o = index.get(origin), d = index.get(dest);
        if (o == null || d == null) return false;
        return component(o)[d];
    }

    // Level 2

    public boolean closeRoad(int ts, String road) {
        Road r = roads.get(road);
        if (r == null || !r.open) return false;
        r.open = false;
        return true;
    }

    public boolean reopenRoad(int ts, String road) {
        Road r = roads.get(road);
        if (r == null || r.open) return false;
        r.open = true;
        return true;
    }

    public List<String> reachableFrom(int ts, String junction) {
        List<String> out = new ArrayList<>();
        Integer u = index.get(junction);
        if (u == null) return out;
        boolean[] seen = component(u);
        for (int v = 0; v < seen.length; v++) {
            if (seen[v]) out.add(names.get(v));
        }
        Collections.sort(out);
        return out;
    }

    // Level 3

    public boolean setMinutes(int ts, String road, int minutes) {
        Road r = roads.get(road);
        if (r == null) return false;
        r.minutes = minutes;
        return true;
    }

    public int fastestRoute(int ts, String origin, String dest) {
        Integer o = index.get(origin), t = index.get(dest);
        if (o == null || t == null) return -1;
        int[] best = new int[names.size()];
        Arrays.fill(best, -1);
        best[o] = 0;
        PriorityQueue<int[]> heap = new PriorityQueue<>((x, y) -> Integer.compare(x[0], y[0]));
        heap.add(new int[] {0, o});
        while (!heap.isEmpty()) {
            int[] it = heap.poll();
            int d = it[0], u = it[1];
            if (d > best[u]) continue;
            if (u == t) return d;
            for (Road r : next(u)) {
                int v = r.other(u), nd = d + r.minutes;
                if (best[v] == -1 || nd < best[v]) {
                    best[v] = nd;
                    heap.add(new int[] {nd, v});
                }
            }
        }
        return -1;
    }

    // Level 4

    public boolean addCharger(int ts, String junction, int rate) {
        Integer u = index.get(junction);
        if (u == null || this.rate.get(u) != 0) return false;
        this.rate.set(u, rate);
        return true;
    }

    public boolean setEnergy(int ts, String road, int units) {
        Road r = roads.get(road);
        if (r == null) return false;
        r.energy = units;
        return true;
    }

    /** Fewest minutes over (junction, units in the battery) states. Charging one unit is a move to the state with
     *  one unit more, so every partial charge is covered. */
    public int fastestDelivery(int ts, String origin, String dest, int capacity, int charge) {
        Integer o = index.get(origin), t = index.get(dest);
        if (o == null || t == null) return -1;
        int w = capacity + 1;
        int[] best = new int[names.size() * w];
        Arrays.fill(best, -1);
        PriorityQueue<int[]> heap = new PriorityQueue<>((x, y) -> Integer.compare(x[0], y[0]));
        best[o * w + charge] = 0;
        heap.add(new int[] {0, o * w + charge});
        while (!heap.isEmpty()) {
            int[] it = heap.poll();
            int d = it[0], s = it[1], u = s / w, b = s % w;
            if (d > best[s]) continue;
            if (u == t) return d;
            List<int[]> moves = new ArrayList<>();
            int rt = rate.get(u);
            if (rt > 0 && b < capacity) moves.add(new int[] {s + 1, d + rt});
            for (Road r : next(u)) {
                if (r.energy <= b) moves.add(new int[] {r.other(u) * w + b - r.energy, d + r.minutes});
            }
            for (int[] m : moves) {
                if (best[m[0]] == -1 || m[1] < best[m[0]]) {
                    best[m[0]] = m[1];
                    heap.add(new int[] {m[1], m[0]});
                }
            }
        }
        return -1;
    }
}
