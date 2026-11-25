import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

/**
 * Drives the quota service from stdin, one command per line, and prints each result (or "error: ..."):
 *
 * <pre>
 *   plan &lt;name&gt; &lt;limit&gt; &lt;windowSeconds&gt; &lt;burst&gt;
 *   key &lt;id&gt; &lt;org&gt; &lt;plan&gt;
 *   allow &lt;key&gt; &lt;now&gt; &lt;cost&gt;     prints "allowed &lt;remaining&gt;" or "denied &lt;remaining&gt; retry &lt;seconds&gt;"
 *   usage &lt;key&gt; &lt;now&gt;            prints "&lt;used&gt;/&lt;limit&gt;"
 *   revoke &lt;key&gt;
 *   setplan &lt;key&gt; &lt;plan&gt;
 *   report &lt;org&gt; &lt;from&gt; &lt;to&gt;     prints one "&lt;key&gt; &lt;plan&gt; &lt;requests&gt; &lt;units&gt; &lt;denied&gt;" line per key
 * </pre>
 *
 * Add your own commands here if they help.
 */
public class Main {
    public static void main(String[] args) throws IOException {
        Service s = new Service();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line = in.readLine(); line != null; line = in.readLine()) {
            String[] f = line.trim().split("\\s+");
            if (f[0].isEmpty()) continue;
            try {
                for (String o : run(s, f)) System.out.println(o);
            } catch (QuotaException | NumberFormatException e) {
                System.out.println("error: " + e.getMessage());
            }
        }
    }

    private static List<String> run(Service s, String[] f) {
        int n = f.length - 1;
        if (f[0].equals("plan") && n == 4) {
            s.addPlan(new Plan(f[1], Long.parseLong(f[2]), Long.parseLong(f[3]), Long.parseLong(f[4])));
        } else if (f[0].equals("key") && n == 3) {
            s.issueKey(f[1], f[2], f[3]);
        } else if (f[0].equals("allow") && n == 3) {
            Decision d = s.allow(f[1], Long.parseLong(f[2]), Long.parseLong(f[3]));
            return List.of(d.allowed() ? "allowed " + d.remaining() : "denied " + d.remaining() + " retry " + d.retryAfter());
        } else if (f[0].equals("usage") && n == 2) {
            Service.Usage u = s.usage(f[1], Long.parseLong(f[2]));
            return List.of(u.used() + "/" + u.limit());
        } else if (f[0].equals("revoke") && n == 1) {
            s.revoke(f[1]);
        } else if (f[0].equals("setplan") && n == 2) {
            s.changePlan(f[1], f[2]);
        } else if (f[0].equals("report") && n == 3) {
            List<String> out = new ArrayList<>();
            for (UsageLine l : s.report(f[1], Long.parseLong(f[2]), Long.parseLong(f[3]))) {
                out.add(l.keyId() + " " + l.plan() + " " + l.requests() + " " + l.units() + " " + l.denied());
            }
            return out;
        } else {
            return List.of("unknown command: " + String.join(" ", f));
        }
        return List.of("ok");
    }
}
