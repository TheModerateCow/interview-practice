import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Drives the notification service from stdin, one command per line, and prints each result
 * (or "error: ..."):
 *
 * <pre>
 *   user &lt;id&gt; &lt;offsetMinutes&gt;
 *   channels &lt;id&gt; [&lt;channel&gt; ...]        email, push, sms; none = digest only
 *   quiet &lt;id&gt; &lt;fromHour&gt; &lt;toHour&gt;
 *   send &lt;user&gt; &lt;at&gt; &lt;topic&gt; &lt;key&gt; &lt;title&gt; [urgent]
 *                                        prints "sent &lt;ch,ch&gt;", "held" or "duplicate"
 *   digest &lt;user&gt; &lt;now&gt;                  prints one "&lt;topic&gt; &lt;count&gt; &lt;latest&gt;" line per topic
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
            List<String> out;
            try {
                out = handle(s, f);
            } catch (RuntimeException e) {
                out = List.of("error: " + e.getMessage());
            }
            for (String l : out) System.out.println(l);
        }
    }

    private static List<String> handle(Service s, String[] f) {
        String cmd = f[0];
        String[] a = Arrays.copyOfRange(f, 1, f.length);
        if (cmd.equals("user") && a.length == 2) {
            s.addUser(a[0], Integer.parseInt(a[1]));
        } else if (cmd.equals("channels") && a.length >= 1) {
            s.setChannels(a[0], new ArrayList<>(Arrays.asList(a).subList(1, a.length)));
        } else if (cmd.equals("quiet") && a.length == 3) {
            s.setQuietHours(a[0], Integer.parseInt(a[1]), Integer.parseInt(a[2]));
        } else if (cmd.equals("send") && (a.length == 5 || a.length == 6 && a[5].equals("urgent"))) {
            Result res = s.send(new Notification(a[0], a[2], a[3], a[4], Long.parseLong(a[1]), a.length == 6));
            return List.of(res.status() + (res.status().equals(Notify.SENT) ? " " + String.join(",", res.channels()) : ""));
        } else if (cmd.equals("digest") && a.length == 2) {
            List<String> out = new ArrayList<>();
            for (DigestLine ln : s.digest(a[0], Long.parseLong(a[1]))) {
                out.add(ln.topic() + " " + ln.count() + " " + ln.latest());
            }
            return out;
        } else {
            return List.of("unknown command: " + String.join(" ", f));
        }
        return List.of("ok");
    }
}
