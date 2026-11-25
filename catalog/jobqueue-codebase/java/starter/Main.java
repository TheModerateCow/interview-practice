import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

/**
 * Drives the job queue from stdin, one command per line, and prints each result:
 *
 * <pre>
 *   enqueue &lt;ts&gt; &lt;queue&gt; &lt;payload&gt; [priority=N] [runAt=N] [attempts=N] [key=K]
 *   lease &lt;ts&gt; &lt;queue&gt; [visibility]
 *   ack &lt;ts&gt; &lt;job&gt; &lt;token&gt;
 *   fail &lt;ts&gt; &lt;job&gt; &lt;token&gt; &lt;error&gt;
 *   extend &lt;ts&gt; &lt;job&gt; &lt;token&gt; &lt;seconds&gt;
 *   cancel &lt;ts&gt; &lt;job&gt;
 *   redrive &lt;ts&gt; &lt;job&gt;
 *   job &lt;job&gt;
 *   dead &lt;queue&gt;
 *   stats &lt;ts&gt; &lt;queue&gt;
 * </pre>
 *
 * Times are Unix seconds. The queue uses the default options. Add your own commands as you need them.
 */
public class Main {
    public static void main(String[] args) throws IOException {
        JobQueue q = new JobQueue();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        for (String line = in.readLine(); line != null; line = in.readLine()) {
            String[] f = line.trim().split("\\s+");
            if (f[0].isEmpty()) continue;
            try {
                System.out.println(run(q, f));
            } catch (RuntimeException e) {
                System.out.println("error: " + e.getMessage());
            }
        }
    }

    private static String run(JobQueue q, String[] f) {
        switch (f[0]) {
            case "enqueue": {
                JobQueue.Opts o = JobQueue.opts();
                for (int i = 4; i < f.length; i++) {
                    String[] kv = f[i].split("=", 2);
                    switch (kv[0]) {
                        case "priority" -> o.priority(Integer.parseInt(kv[1]));
                        case "runAt" -> o.runAt(Long.parseLong(kv[1]));
                        case "attempts" -> o.maxAttempts(Integer.parseInt(kv[1]));
                        case "key" -> o.key(kv[1]);
                        default -> throw new IllegalArgumentException("unknown option " + kv[0]);
                    }
                }
                return q.enqueue(f[2], f[3], ts(f), o);
            }
            case "lease": {
                JobQueue.Lease l = f.length > 3 ? q.lease(f[2], ts(f), Long.parseLong(f[3])) : q.lease(f[2], ts(f));
                return l == null ? "empty" : l.jobId() + " " + l.token() + " attempt=" + l.attempt() + " until=" + l.until() + " " + l.payload();
            }
            case "ack": q.ack(f[2], f[3], ts(f)); return "ok";
            case "fail": q.fail(f[2], f[3], f[4], ts(f)); return "ok";
            case "extend": q.extend(f[2], f[3], Long.parseLong(f[4]), ts(f)); return "ok";
            case "cancel": q.cancel(f[2], ts(f)); return "ok";
            case "redrive": q.redrive(f[2], ts(f)); return "ok";
            case "job": {
                Job j = q.job(f[1]);
                return j == null ? "none" : j.toString();
            }
            case "dead": return q.deadLetters(f[1]).toString();
            case "stats": return q.stats(f[2], ts(f)).toString();
            default: throw new IllegalArgumentException("unknown command " + f[0]);
        }
    }

    private static long ts(String[] f) {
        return Long.parseLong(f[1]);
    }
}
