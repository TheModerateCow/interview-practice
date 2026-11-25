import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.PriorityQueue;

public class Route {
    /** Dijkstra over (junction, battery) states: n * (capacity + 1) states; charging one unit at a time
     *  covers every partial charge. O(states log states + roads * capacity). */
    public static int fastestDelivery(int n, int capacity, int charge, int[] rate, List<Road> roads) {
        List<List<Road>> adj = new ArrayList<>();
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        for (Road r : roads) {
            adj.get(r.a()).add(r);
            adj.get(r.b()).add(new Road(r.b(), r.a(), r.minutes(), r.energy()));
        }
        int w = capacity + 1;
        int[] dist = new int[n * w];
        Arrays.fill(dist, -1);
        PriorityQueue<int[]> pq = new PriorityQueue<>(Comparator.comparingInt(x -> x[0]));
        push(dist, pq, charge, 0);
        while (!pq.isEmpty()) {
            int[] it = pq.poll();
            if (it[0] != dist[it[1]]) continue;
            int u = it[1] / w, b = it[1] % w;
            if (u == n - 1) return it[0];
            if (rate[u] > 0 && b < capacity) push(dist, pq, u * w + b + 1, it[0] + rate[u]);
            for (Road r : adj.get(u)) {
                int nb = b - r.energy();
                if (nb >= 0) push(dist, pq, r.b() * w + nb, it[0] + r.minutes());
            }
        }
        return -1;
    }

    private static void push(int[] dist, PriorityQueue<int[]> pq, int s, int d) {
        if (dist[s] == -1 || d < dist[s]) {
            dist[s] = d;
            pq.add(new int[]{d, s});
        }
    }
}
