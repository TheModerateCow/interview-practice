import java.util.Arrays;

public class HiddenTest {
    static void hiddenCheck(int[] cap, int[][] trips, int want) {
        int got = Upgrades.maxUpgrades(cap, trips);
        if (got != want) throw new AssertionError("maxUpgrades(cap=" + Arrays.toString(cap) + ", requests="
                + Arrays.deepToString(trips) + ") = " + got + ", want " + want);
    }

    static int[] hiddenFill(int n, int v) { int[] a = new int[n]; Arrays.fill(a, v); return a; }

    static long hiddenSeed;
    static int hiddenNext(int k) {
        hiddenSeed = hiddenSeed * 6364136223846793005L + 1442695040888963407L;
        return (int) ((hiddenSeed >>> 33) % k);
    }
    static int[] hiddenCaps(long seed, int n, int lo, int hi) {
        hiddenSeed = seed; int[] c = new int[n];
        for (int i = 0; i < n; i++) c[i] = lo + hiddenNext(hi - lo + 1);
        return c;
    }
    static int[][] hiddenTrips(long seed, int n, int m, int maxLen) {
        hiddenSeed = seed; int[][] r = new int[m][];
        for (int i = 0; i < m; i++) { int a = hiddenNext(n); r[i] = new int[]{a, a + 1 + hiddenNext(Math.min(maxLen, n - a))}; }
        return r;
    }

    static void test_p1_worked_example() {
        hiddenCheck(new int[]{2, 1, 2, 1, 2}, new int[][]{{2, 4}, {3, 5}, {2, 3}, {0, 4}, {4, 5}, {1, 3}}, 4);
    }
    static void test_p1_no_requests() {
        hiddenCheck(new int[]{3, 3}, new int[][]{}, 0);
    }
    static void test_p1_single_leg_fills_up() {
        hiddenCheck(new int[]{3}, new int[][]{{0, 1}, {0, 1}, {0, 1}, {0, 1}, {0, 1}}, 3);
    }
    static void test_p1_leg_with_no_free_seat() {
        hiddenCheck(new int[]{2, 0, 2}, new int[][]{{0, 1}, {0, 3}, {2, 3}, {1, 2}, {0, 1}, {0, 2}}, 3);
    }
    static void test_p1_alight_and_board_at_same_stop() {
        hiddenCheck(hiddenFill(4, 1), new int[][]{{0, 2}, {2, 4}, {1, 2}, {2, 3}}, 2);
    }
    static void test_p1_long_early_trip_is_not_best() {
        hiddenCheck(hiddenFill(10, 1), new int[][]{{0, 10}, {1, 2}, {2, 3}, {5, 9}}, 3);
    }
    static void test_p1_shortest_trip_is_not_best() {
        hiddenCheck(hiddenFill(6, 1), new int[][]{{2, 4}, {0, 3}, {3, 6}}, 2);
    }
    static void test_p1_whole_route_trips() {
        hiddenCheck(new int[]{5, 3, 4}, new int[][]{{0, 3}, {0, 3}, {0, 3}, {0, 3}, {1, 2}, {0, 1}, {2, 3}}, 5);
    }
    static void test_p1_request_order_does_not_matter() {
        hiddenCheck(new int[]{2, 1, 2, 1, 2}, new int[][]{{1, 3}, {4, 5}, {0, 4}, {2, 3}, {3, 5}, {2, 4}}, 4);
    }
    static void test_p1_dense_short_trips() {
        hiddenCheck(hiddenCaps(11, 40, 0, 3), hiddenTrips(12, 40, 120, 15), 16);
    }
    static void test_p1_dense_long_trips() {
        hiddenCheck(hiddenCaps(21, 60, 0, 5), hiddenTrips(22, 60, 300, 60), 34);
    }
    static void test_p1_large_route() {
        int n = 200000;
        int[] cap = hiddenCaps(31, n, 60000, 100000);
        int[][] trips = new int[200000][];
        hiddenSeed = 32;
        for (int i = 0; i < trips.length; i++) {
            if (i % 2 == 0) { int a = hiddenNext(n / 4); trips[i] = new int[]{a, n - hiddenNext(n / 4)}; }
            else { int a = hiddenNext(n); trips[i] = new int[]{a, a + 1 + hiddenNext(Math.min(1000, n - a))}; }
        }
        long start = System.nanoTime();
        int got = Upgrades.maxUpgrades(cap, trips);
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq(159724, got);
        Expect.isTrue(ms <= 2000, "took " + ms + " ms on 200000 legs and 200000 requests; expected well under 2000 ms");
    }
}
