import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** SLO monitor for API services: per-minute samples, error budgets, compliance stretches and burn-rate alerts. */
public class SloMonitor {
    private static final long PPM = 1_000_000L;

    private static final class Service {
        int[] req = new int[16], err = new int[16]; // per minute, index = minute; gaps hold 0
        int size; // minutes recorded: 0..size-1
        Integer budget;
        int longW, shortW, burn;
        boolean hasAlert;

        void grow(int need) {
            if (need <= req.length) return;
            int cap = Math.max(need, req.length * 2);
            req = java.util.Arrays.copyOf(req, cap);
            err = java.util.Arrays.copyOf(err, cap);
        }

        long[] sums(int start, int end) {
            long r = 0, e = 0;
            for (int t = Math.max(start, 0); t <= end && t < size; t++) { r += req[t]; e += err[t]; }
            return new long[] {r, e};
        }
    }

    private final Map<String, Service> svc = new HashMap<>();

    public SloMonitor() {}

    // ---- level 1 ----

    public boolean addService(String service) {
        if (svc.containsKey(service)) return false;
        svc.put(service, new Service());
        return true;
    }

    public boolean ingest(String service, int firstMinute, int[] requests, int[] errors) {
        Service s = svc.get(service);
        if (s == null || requests.length == 0 || requests.length != errors.length || firstMinute < s.size) return false;
        for (int i = 0; i < requests.length; i++) if (errors[i] > requests[i]) return false;
        s.grow(firstMinute + requests.length);
        // the gap firstMinute-size is already zero: slots past size are never written
        System.arraycopy(requests, 0, s.req, firstMinute, requests.length);
        System.arraycopy(errors, 0, s.err, firstMinute, errors.length);
        s.size = firstMinute + requests.length;
        return true;
    }

    public Integer errorRate(String service, int start, int end) {
        Service s = svc.get(service);
        if (s == null) return null;
        long[] t = s.sums(start, end);
        return t[0] == 0 ? null : (int) (t[1] * PPM / t[0]);
    }

    public Integer latestMinute(String service) {
        Service s = svc.get(service);
        return s == null || s.size == 0 ? null : s.size - 1;
    }

    // ---- level 2 ----

    public boolean setBudget(String service, int budgetPpm) {
        Service s = svc.get(service);
        if (s == null) return false;
        s.budget = budgetPpm;
        return true;
    }

    public Long budgetLeft(String service, int start, int end) {
        Service s = svc.get(service);
        if (s == null || s.budget == null) return null;
        long[] t = s.sums(start, end);
        return t[0] * s.budget / PPM - t[1];
    }

    public List<String> overBudget(int end, int window) {
        List<Object[]> hits = new ArrayList<>();
        for (Map.Entry<String, Service> en : svc.entrySet()) {
            Service s = en.getValue();
            if (s.budget == null) continue;
            long[] t = s.sums(end - window + 1, end);
            if (t[0] > 0 && t[1] * PPM > t[0] * s.budget) hits.add(new Object[] {t[1] * PPM / t[0], en.getKey()});
        }
        hits.sort((x, y) -> {
            int c = Long.compare((Long) y[0], (Long) x[0]);
            return c != 0 ? c : ((String) x[1]).compareTo((String) y[1]);
        });
        List<String> out = new ArrayList<>();
        for (Object[] h : hits) out.add(h[1] + ":" + h[0]);
        return out;
    }

    // ---- level 3 ----

    public String longestWithinBudget(String service, int start, int end) {
        Service s = svc.get(service);
        if (s == null || s.budget == null) return null;
        int n = end - start + 1;
        // prefix[k]: errors*1e6 - requests*budget over minutes start..start+k-1 (minutes past the data are empty)
        long[] prefix = new long[n + 1];
        long acc = 0;
        for (int k = 0; k < n; k++) {
            int t = start + k;
            if (t < s.size) acc += s.err[t] * PPM - (long) s.req[t] * s.budget;
            prefix[k + 1] = acc;
        }
        // Stretch i..j-1 is within budget when prefix[j] <= prefix[i]. Only a strict running maximum can be the
        // best start: an earlier start that is at least as high reaches every end it reaches, and is longer.
        int[] starts = new int[n + 1];
        int top = 0;
        for (int i = 0; i <= n; i++) if (top == 0 || prefix[i] > prefix[starts[top - 1]]) starts[top++] = i;
        int bestLen = 0, bestStart = 0;
        for (int j = n; j >= 0 && top > 0; j--) {
            while (top > 0 && prefix[starts[top - 1]] >= prefix[j]) {
                int i = starts[--top];
                if (j - i >= bestLen) { bestLen = j - i; bestStart = i; } // starts pop latest first: >= keeps the earliest
            }
        }
        if (bestLen == 0) return "";
        return (start + bestStart) + "-" + (start + bestStart + bestLen - 1);
    }

    // ---- level 4 ----

    public boolean amend(String service, int minute, int requests, int errors) {
        Service s = svc.get(service);
        if (s == null || minute >= s.size || errors > requests) return false;
        s.req[minute] = requests;
        s.err[minute] = errors;
        return true;
    }

    public boolean setAlert(String service, int longWindow, int shortWindow, int burn) {
        Service s = svc.get(service);
        if (s == null || s.budget == null) return false;
        s.longW = longWindow; s.shortW = shortWindow; s.burn = burn; s.hasAlert = true;
        return true;
    }

    public List<String> alertTimeline(String service, int start, int end) {
        List<String> out = new ArrayList<>();
        Service s = svc.get(service);
        if (s == null || !s.hasAlert) return out;
        long limit = (long) s.budget * s.burn;
        int lo = Math.max(0, start - s.longW + 1);
        // R[k], E[k]: requests and errors over minutes lo..lo+k-1
        long[] R = new long[end - lo + 2], E = new long[end - lo + 2];
        for (int t = lo; t <= end; t++) {
            int r = t < s.size ? s.req[t] : 0, e = t < s.size ? s.err[t] : 0;
            R[t - lo + 1] = R[t - lo] + r;
            E[t - lo + 1] = E[t - lo] + e;
        }
        int run = -1;
        for (int t = start; t <= end; t++) {
            if (burning(R, E, lo, t, s.longW, limit) && burning(R, E, lo, t, s.shortW, limit)) {
                if (run < 0) run = t;
            } else if (run >= 0) {
                out.add(run + "-" + (t - 1));
                run = -1;
            }
        }
        if (run >= 0) out.add(run + "-" + end);
        return out;
    }

    private static boolean burning(long[] R, long[] E, int lo, int t, int w, long limit) {
        int a = Math.max(lo, t - w + 1) - lo, b = t + 1 - lo;
        return (E[b] - E[a]) * PPM > (R[b] - R[a]) * limit;
    }
}
