import java.util.Arrays;

public class Upgrades {
    /**
     * cap[k] = free business seats on leg k (stop k to stop k+1).
     * requests[i] = {board, alight}: the passenger flies legs board .. alight-1.
     * Returns the most passengers that can be upgraded on every leg they fly.
     */
    public static int maxUpgrades(int[] cap, int[][] requests) {
        int n = cap.length;
        int[][] byAlight = requests.clone();
        Arrays.sort(byAlight, (x, y) -> Integer.compare(x[1], y[1]));
        Tree seats = new Tree(cap);
        int upgraded = 0;
        for (int[] r : byAlight) {
            int lo = r[0], hi = r[1] - 1;
            if (seats.min(1, 0, n - 1, lo, hi) >= 1) {
                seats.add(1, 0, n - 1, lo, hi, -1);
                upgraded++;
            }
        }
        return upgraded;
    }

    /** Range add, range min. mn[x] includes lz[x] but not the ancestors' lazies. */
    private static final class Tree {
        final int[] mn, lz;

        Tree(int[] cap) {
            mn = new int[4 * cap.length];
            lz = new int[4 * cap.length];
            build(1, 0, cap.length - 1, cap);
        }

        void build(int x, int l, int r, int[] cap) {
            if (l == r) { mn[x] = cap[l]; return; }
            int m = (l + r) / 2;
            build(2 * x, l, m, cap);
            build(2 * x + 1, m + 1, r, cap);
            mn[x] = Math.min(mn[2 * x], mn[2 * x + 1]);
        }

        int min(int x, int l, int r, int lo, int hi) {
            if (hi < l || r < lo) return Integer.MAX_VALUE;
            if (lo <= l && r <= hi) return mn[x];
            int m = (l + r) / 2;
            return lz[x] + Math.min(min(2 * x, l, m, lo, hi), min(2 * x + 1, m + 1, r, lo, hi));
        }

        void add(int x, int l, int r, int lo, int hi, int v) {
            if (hi < l || r < lo) return;
            if (lo <= l && r <= hi) { mn[x] += v; lz[x] += v; return; }
            int m = (l + r) / 2;
            add(2 * x, l, m, lo, hi, v);
            add(2 * x + 1, m + 1, r, lo, hi, v);
            mn[x] = lz[x] + Math.min(mn[2 * x], mn[2 * x + 1]);
        }
    }
}
