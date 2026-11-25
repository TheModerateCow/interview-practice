import java.util.Arrays;
import java.util.List;
import java.util.TreeSet;

public class Book {
    /** Replays ask-book events; returns one number per "quote" and "buy" event, in order. */
    public static long[] runBook(List<Event> events) {
        TreeSet<Long> distinct = new TreeSet<>();
        for (Event e : events) {
            if (e.kind().equals("add") || e.kind().equals("cancel")) distinct.add(e.price());
        }
        Ladder lad = new Ladder(distinct);
        long total = 0;
        long[] out = new long[events.size()];
        int m = 0;
        for (Event e : events) {
            if (e.kind().equals("add")) {
                lad.change(lad.level(e.price()), e.qty());
                total += e.qty();
            } else if (e.kind().equals("cancel")) {
                lad.change(lad.level(e.price()), -e.qty());
                total -= e.qty();
            } else if (e.kind().equals("quote")) {
                if (e.qty() > total) {
                    out[m++] = -1;
                } else {
                    long[] s = lad.sweep(e.qty());
                    out[m++] = s[1] + s[2] * lad.price[(int) s[0]];
                }
            } else { // buy: fill what is there, the rest is cancelled
                long q = Math.min(e.qty(), total);
                if (q == 0) {
                    out[m++] = 0;
                    continue;
                }
                long[] s = lad.sweep(q);
                int k = (int) s[0];
                out[m++] = s[1] + s[2] * lad.price[k];
                while (true) { // empty every cheaper level; each emptied level was paid for by an add
                    int j = (int) lad.sweep(1)[0];
                    if (j == k) break;
                    lad.change(j, -lad.resting[j]);
                }
                lad.change(k, -s[2]);
                total -= q;
            }
        }
        return Arrays.copyOf(out, m);
    }

    /** Fenwick trees over the distinct prices (1-based levels): shares and price*shares per level, plus plain shares. */
    private static final class Ladder {
        final int n, top;
        final long[] price, shares, notional, resting;

        Ladder(TreeSet<Long> prices) {
            n = prices.size();
            price = new long[n + 1];
            shares = new long[n + 1];
            notional = new long[n + 1];
            resting = new long[n + 1];
            int t = 1;
            while (t <= n) t <<= 1;
            top = t;
            int i = 0;
            for (long p : prices) price[++i] = p;
        }

        int level(long p) {
            return Arrays.binarySearch(price, 1, n + 1, p);
        }

        void change(int i, long dq) {
            resting[i] += dq;
            long dn = dq * price[i];
            for (int j = i; j <= n; j += j & -j) {
                shares[j] += dq;
                notional[j] += dn;
            }
        }

        /** 0 < q <= total: {level holding the q-th cheapest share, cost of cheaper levels, shares taken from that level}. */
        long[] sweep(long q) {
            int pos = 0;
            long got = 0, cost = 0;
            for (int step = top; step > 0; step >>= 1) {
                int nxt = pos + step;
                if (nxt <= n && got + shares[nxt] < q) {
                    pos = nxt;
                    got += shares[nxt];
                    cost += notional[nxt];
                }
            }
            return new long[] {pos + 1, cost, q - got};
        }
    }
}
