import java.util.Arrays;

public class Dispatch {
    /** Smallest radius R >= 0 such that at least need riders can each be picked up by a different
     *  driver standing within distance R of them, or -1 if that is impossible. */
    public static int minDispatchRadius(int[] riders, int[] drivers, int need) {
        if (need <= 0) return 0;
        if (need > riders.length || need > drivers.length) return -1;
        long[] r = sortedCopy(riders), d = sortedCopy(drivers);
        long lo = 0, hi = Math.max(r[r.length - 1], d[d.length - 1]) - Math.min(r[0], d[0]);
        while (lo < hi) {
            long mid = lo + (hi - lo) / 2;
            if (matched(r, d, mid) >= need) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        return (int) lo;
    }

    /** Sorted copy as longs: x - radius and x + radius cannot overflow int. */
    private static long[] sortedCopy(int[] a) {
        long[] s = new long[a.length];
        for (int i = 0; i < a.length; i++) s[i] = a[i];
        Arrays.sort(s);
        return s;
    }

    /** Most riders served when every pickup is within radius. Both arrays are sorted; each rider
     *  takes the leftmost free driver in reach. */
    private static int matched(long[] r, long[] d, long radius) {
        int count = 0, j = 0;
        for (long x : r) {
            while (j < d.length && d[j] < x - radius) j++;
            if (j == d.length) break;
            if (d[j] <= x + radius) {
                count++;
                j++;
            }
        }
        return count;
    }
}
