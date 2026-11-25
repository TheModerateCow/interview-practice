import java.util.Arrays;

public class Meters {
    /** Most money the battery can make over the day: it starts empty, holds up to capacity kWh, and each
     *  half-hour charges 1 kWh (paying the price), discharges 1 kWh (earning the price minus wear) or idles.
     *  Energy left at the end is worth nothing. */
    public static int bestBatteryProfit(int[] prices, int capacity, int wear) {
        // best[c] = most money made so far while holding c kWh. Levels above 0 start unreachable.
        final int unreachable = Integer.MIN_VALUE / 2;
        int[] best = new int[capacity + 1];
        Arrays.fill(best, 1, capacity + 1, unreachable);
        int[] next = new int[capacity + 1];
        for (int p : prices) {
            for (int c = 0; c <= capacity; c++) {
                int v = best[c];
                if (c > 0) v = Math.max(v, best[c - 1] - p);
                if (c < capacity) v = Math.max(v, best[c + 1] + p - wear);
                next[c] = v;
            }
            int[] t = best;
            best = next;
            next = t;
        }
        return Arrays.stream(best).max().getAsInt();
    }
}
