import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

/**
 * Drives the dispatcher from stdin, one command per line, and prints each result (or "error: ..."):
 *
 * <pre>
 *   courier &lt;id&gt; &lt;x&gt; &lt;y&gt; &lt;capacity&gt;
 *   order &lt;id&gt; &lt;restaurantX&gt; &lt;restaurantY&gt; &lt;customerX&gt; &lt;customerY&gt; &lt;placedAt&gt; &lt;prepMinutes&gt;
 *   assign &lt;order&gt;
 *   advance &lt;order&gt; &lt;picked_up|delivered|cancelled&gt;
 *   eta &lt;order&gt; &lt;now&gt;
 *   dispatch &lt;now&gt;
 *   bag &lt;courier&gt;
 * </pre>
 *
 * Add your own commands here if they help.
 */
public class Main {
    public static void main(String[] args) throws IOException {
        Dispatcher d = new Dispatcher();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line = in.readLine(); line != null; line = in.readLine()) {
            String[] f = line.trim().split("\\s+");
            if (f[0].isEmpty()) continue;
            try {
                System.out.println(run(d, f, line));
            } catch (DispatchException e) {
                System.out.println("error: " + e.getMessage());
            }
        }
    }

    private static String run(Dispatcher d, String[] f, String line) {
        switch (f[0]) {
            case "courier" -> {
                if (f.length != 5) break;
                d.addCourier(f[1], pt(f, 2), num(f, 4));
                return "ok";
            }
            case "order" -> {
                if (f.length != 8) break;
                d.placeOrder(f[1], pt(f, 2), pt(f, 4), num(f, 6), num(f, 7));
                return "ok";
            }
            case "assign" -> {
                if (f.length != 2) break;
                return d.assign(f[1]);
            }
            case "advance" -> {
                if (f.length != 3) break;
                State s = State.parse(f[2]);
                if (s == null) return "error: unknown state " + f[2];
                d.advance(f[1], s);
                return "ok";
            }
            case "eta" -> {
                if (f.length != 3) break;
                return String.valueOf(d.eta(f[1], num(f, 2)));
            }
            case "dispatch" -> {
                if (f.length != 2) break;
                List<String> parts = new ArrayList<>();
                for (Assignment a : d.dispatchPending(num(f, 1))) parts.add(a.orderId() + "->" + a.courierId());
                return "[" + String.join(" ", parts) + "]";
            }
            case "bag" -> {
                if (f.length != 2) break;
                return "[" + String.join(" ", d.courierOrders(f[1])) + "]";
            }
            default -> { }
        }
        return "unknown command: " + line;
    }

    private static int num(String[] f, int i) {
        return Integer.parseInt(f[i]);
    }

    private static Point pt(String[] f, int i) {
        return new Point(num(f, i), num(f, i + 1));
    }
}
