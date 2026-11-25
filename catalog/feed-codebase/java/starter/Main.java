import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Drives the feed service from stdin, one command per line, and prints each result (or "error: ..."):
 *
 * <pre>
 *   user &lt;id&gt;
 *   follow &lt;follower&gt; &lt;followee&gt;
 *   unfollow &lt;follower&gt; &lt;followee&gt;
 *   mute &lt;viewer&gt; &lt;target&gt; &lt;now&gt; [hours]
 *   post &lt;id&gt; &lt;author&gt; &lt;created_at&gt; [text ...]
 *   like &lt;post&gt; &lt;user&gt;                     prints the like count
 *   feed &lt;viewer&gt; &lt;now&gt; &lt;limit&gt;            first page: [ids] more|end
 *   more &lt;viewer&gt; &lt;now&gt; &lt;limit&gt;            the page after the viewer's last feed/more
 *   catchup &lt;viewer&gt; &lt;since&gt; &lt;now&gt; [limit]
 * </pre>
 *
 * Add your own commands here if they help.
 */
public class Main {
    public static void main(String[] args) throws IOException {
        FeedService svc = new FeedService();
        Map<String, String> cursors = new HashMap<>();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line = in.readLine(); line != null; line = in.readLine()) {
            String[] f = line.trim().split("\\s+");
            if (f[0].isEmpty()) continue;
            try {
                System.out.println(run(svc, cursors, f));
            } catch (RuntimeException e) {
                System.out.println("error: " + e.getMessage());
            }
        }
    }

    private static String run(FeedService svc, Map<String, String> cursors, String[] f) {
        int n = f.length - 1;
        switch (f[0]) {
            case "user" -> { svc.addUser(f[1]); return "ok"; }
            case "follow" -> { svc.follow(f[1], f[2]); return "ok"; }
            case "unfollow" -> { svc.unfollow(f[1], f[2]); return "ok"; }
            case "mute" -> {
                svc.mute(f[1], f[2], Long.parseLong(f[3]), n == 4 ? Double.valueOf(f[4]) : null);
                return "ok";
            }
            case "post" -> {
                svc.publish(f[1], f[2], Long.parseLong(f[3]), String.join(" ", java.util.Arrays.asList(f).subList(4, f.length)));
                return "ok";
            }
            case "like" -> { return String.valueOf(svc.like(f[1], f[2])); }
            case "feed", "more" -> {
                if (f[0].equals("more") && cursors.get(f[1]) == null) return "[] end";
                Page p = svc.homeFeed(f[1], Long.parseLong(f[2]), Integer.parseInt(f[3]), f[0].equals("more") ? cursors.get(f[1]) : null);
                cursors.put(f[1], p.nextCursor());
                return "[" + String.join(" ", p.postIds()) + "] " + (p.nextCursor() != null ? "more" : "end");
            }
            case "catchup" -> {
                List<String> ids = n == 4
                        ? svc.catchUp(f[1], Long.parseLong(f[2]), Long.parseLong(f[3]), Integer.parseInt(f[4]))
                        : svc.catchUp(f[1], Long.parseLong(f[2]), Long.parseLong(f[3]));
                return "[" + String.join(" ", ids) + "]";
            }
            default -> { return "unknown command: " + String.join(" ", f); }
        }
    }
}
