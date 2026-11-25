import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.List;

/**
 * Drives the inventory service from stdin, one command per line, and prints each result:
 *
 * <pre>
 *   warehouse &lt;id&gt;
 *   rule &lt;warehouse&gt; &lt;sku&gt; &lt;min&gt; &lt;max&gt; &lt;pack&gt;
 *   receive &lt;ts&gt; &lt;warehouse&gt; &lt;bin&gt; &lt;sku&gt; &lt;qty&gt;
 *   reserve &lt;ts&gt; &lt;id&gt; &lt;warehouse&gt; &lt;sku&gt; &lt;qty&gt; &lt;ttl&gt;
 *   release &lt;ts&gt; &lt;id&gt;
 *   commit &lt;ts&gt; &lt;id&gt;
 *   transfer &lt;ts&gt; &lt;id&gt; &lt;from&gt; &lt;to&gt; &lt;sku&gt; &lt;qty&gt;
 *   arrive &lt;ts&gt; &lt;transfer&gt; &lt;bin&gt;
 *   available &lt;ts&gt; &lt;warehouse&gt; &lt;sku&gt;
 *   onhand &lt;warehouse&gt; &lt;sku&gt;
 *   bin &lt;warehouse&gt; &lt;bin&gt; &lt;sku&gt;
 *   replenish &lt;ts&gt; &lt;warehouse&gt;
 * </pre>
 *
 * Times are Unix seconds; ttl is in seconds. Add your own commands as you need them.
 */
public class Main {
    public static void main(String[] args) throws IOException {
        Inventory s = new Inventory();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line = in.readLine(); line != null; line = in.readLine()) {
            String[] f = line.trim().split("\\s+");
            if (f[0].isEmpty()) continue;
            try {
                run(s, f, line);
            } catch (RuntimeException e) {
                System.out.println("error: " + e.getMessage());
            }
        }
    }

    private static long num(String[] f, int i) {
        return Long.parseLong(f[i]);
    }

    private static void run(Inventory s, String[] f, String line) {
        switch (f[0]) {
            case "warehouse" -> { s.addWarehouse(f[1]); System.out.println("ok"); }
            case "rule" -> {
                s.setRule(f[1], f[2], new Rule((int) num(f, 3), (int) num(f, 4), (int) num(f, 5)));
                System.out.println("ok");
            }
            case "receive" -> { s.receive(f[2], f[3], f[4], (int) num(f, 5), num(f, 1)); System.out.println("ok"); }
            case "reserve" -> {
                s.reserve(f[2], f[3], f[4], (int) num(f, 5), num(f, 6), num(f, 1));
                System.out.println("ok");
            }
            case "release" -> { s.release(f[2], num(f, 1)); System.out.println("ok"); }
            case "commit" -> { s.commit(f[2], num(f, 1)); System.out.println("ok"); }
            case "transfer" -> {
                s.startTransfer(f[2], f[3], f[4], f[5], (int) num(f, 6), num(f, 1));
                System.out.println("ok");
            }
            case "arrive" -> { s.receiveTransfer(f[2], f[3], num(f, 1)); System.out.println("ok"); }
            case "available" -> System.out.println(s.available(f[2], f[3], num(f, 1)));
            case "onhand" -> System.out.println(s.onHand(f[1], f[2]));
            case "bin" -> System.out.println(s.binQty(f[1], f[2], f[3]));
            case "replenish" -> {
                List<Suggestion> plan = s.replenishment(f[2], num(f, 1));
                for (Suggestion sg : plan) {
                    System.out.println(sg.sku() + " position=" + sg.position() + " qty=" + sg.qty()
                            + " from=" + (sg.from().isEmpty() ? "supplier" : sg.from()));
                }
                if (plan.isEmpty()) System.out.println("nothing to replenish");
            }
            default -> System.out.println("unknown command: " + line);
        }
    }
}
