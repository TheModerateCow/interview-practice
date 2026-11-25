import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class Fixture {
    public static List<Entry> netByAccount(List<Entry> entries) {
        Map<String, Long> tot = new TreeMap<>();
        for (Entry e : entries) tot.merge(e.accountId(), e.amountCents(), Long::sum);
        List<Entry> out = new ArrayList<>();
        tot.forEach((a, s) -> out.add(new Entry(a, s)));
        return out;
    }

    public static long maxWindow(int[] values, int k) {
        if (k < 1 || k > values.length) throw new InvalidWindowException("k=" + k);
        long s = 0;
        for (int i = 0; i < k; i++) s += values[i];
        long best = s;
        for (int i = k; i < values.length; i++) {
            s += values[i] - values[i - k];
            best = Math.max(best, s);
        }
        return best;
    }

    public static Integer firstNegative(int[] values) {
        for (int i = 0; i < values.length; i++) if (values[i] < 0) return i;
        return null;
    }

    public static int[][] grid(int n) {
        int[][] g = new int[n][n];
        for (int r = 0; r < n; r++) for (int c = 0; c < n; c++) g[r][c] = r * n + c + 1;
        return g;
    }
}
