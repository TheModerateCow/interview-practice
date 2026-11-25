import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Drives the ledger from stdin, one command per line, and prints each result:
 *
 * <pre>
 *   merchant &lt;id&gt; &lt;bps&gt; [&lt;CUR&gt;=&lt;fixed fee&gt; ...]
 *   capture &lt;ts&gt; &lt;charge&gt; &lt;merchant&gt; &lt;cur&gt; &lt;amount&gt; &lt;card|bank&gt;
 *   refund &lt;ts&gt; &lt;charge&gt; &lt;amount&gt;
 *   settle &lt;ts&gt; &lt;merchant&gt;
 *   post &lt;ts&gt; &lt;account&gt; &lt;cur&gt; &lt;amount&gt; [&lt;account&gt; &lt;cur&gt; &lt;amount&gt; ...]
 *   payout &lt;ts&gt; &lt;payout&gt; &lt;merchant&gt; &lt;cur&gt; &lt;amount&gt;
 *   paid &lt;ts&gt; &lt;payout&gt;
 *   failed &lt;ts&gt; &lt;payout&gt;
 *   balance &lt;account&gt; &lt;cur&gt;
 * </pre>
 *
 * Amounts are integer minor units. Accounts are names like merchant:m1:available or platform:fees.
 * Add your own commands as you need them.
 */
public class Main {
    public static void main(String[] args) throws IOException {
        Ledger l = new Ledger();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line = in.readLine(); line != null; line = in.readLine()) {
            String[] f = line.trim().split("\\s+");
            if (f[0].isEmpty()) continue;
            try {
                System.out.println(String.join("\n", handle(l, f)));
            } catch (RuntimeException e) {
                System.out.println("error: " + e.getMessage());
            }
        }
    }

    private static List<String> handle(Ledger l, String[] f) {
        int n = f.length - 1;
        switch (f[0]) {
            case "merchant":
                if (n >= 2) {
                    Map<String, Long> fixed = new HashMap<>();
                    for (int i = 3; i < f.length; i++) {
                        String[] kv = f[i].split("=", 2);
                        fixed.put(kv[0], Long.parseLong(kv[1]));
                    }
                    l.addMerchant(f[1], new Pricing(Long.parseLong(f[2]), fixed));
                    return List.of("ok");
                }
                break;
            case "capture":
                if (n == 6) {
                    l.capture(f[2], f[3], f[4], Long.parseLong(f[5]), f[6], Long.parseLong(f[1]));
                    return List.of("ok");
                }
                break;
            case "refund":
                if (n == 3) {
                    l.refund(f[2], Long.parseLong(f[3]), Long.parseLong(f[1]));
                    return List.of("ok");
                }
                break;
            case "settle":
                if (n == 2) {
                    List<String> out = new ArrayList<>();
                    for (Batch b : l.settle(f[2], Long.parseLong(f[1]))) {
                        out.add(b.id + " " + b.currency + " gross=" + b.gross + " fees=" + b.fees + " net=" + b.net
                                + " charges=" + String.join(",", b.charges));
                    }
                    return out;
                }
                break;
            case "post":
                if (n >= 4 && (n - 1) % 3 == 0) {
                    List<Posting> ps = new ArrayList<>();
                    for (int i = 2; i < f.length; i += 3) ps.add(new Posting(f[i], f[i + 1], Long.parseLong(f[i + 2])));
                    l.post(new Entry(Long.parseLong(f[1]), ps));
                    return List.of("ok");
                }
                break;
            case "payout":
                if (n == 5) {
                    l.requestPayout(f[2], f[3], f[4], Long.parseLong(f[5]), Long.parseLong(f[1]));
                    return List.of("ok");
                }
                break;
            case "paid":
                if (n == 2) {
                    l.payoutPaid(f[2], Long.parseLong(f[1]));
                    return List.of("ok");
                }
                break;
            case "failed":
                if (n == 2) {
                    l.payoutFailed(f[2], Long.parseLong(f[1]));
                    return List.of("ok");
                }
                break;
            case "balance":
                if (n == 2) return List.of(Money.formatAmount(l.balance(f[1], f[2]), f[2]));
                break;
            default:
                break;
        }
        return List.of("unknown command: " + String.join(" ", f));
    }
}
