import java.util.ArrayList;
import java.util.List;

// The app compiles one phase's tests at a time: helpers use only the phase-1 API.
public class HiddenTest {
    static String hiddenCode(Runnable r) {
        try {
            r.run();
            return "ok";
        } catch (QuotaException e) {
            return e.code.name();
        }
    }

    /** Plans basic (10/min, burst 4), strict (10/min, no burst) and pro (50/min, burst 20). */
    static Service hiddenService() {
        Service s = new Service();
        s.addPlan(new Plan("basic", 10, 60, 4));
        s.addPlan(new Plan("strict", 10, 60, 0));
        s.addPlan(new Plan("pro", 50, 60, 20));
        return s;
    }

    /** Runs one request and renders the decision as "ok R" or "no R +S". */
    static String hiddenAllow(Service s, String key, long now, long cost) {
        Decision d = s.allow(key, now, cost);
        return d.allowed() ? "ok " + d.remaining() : "no " + d.remaining() + " +" + d.retryAfter();
    }

    static String hiddenUsage(Service s, String key, long now) {
        Service.Usage u = s.usage(key, now);
        return u.used() + "/" + u.limit();
    }

    static String hiddenReport(Service s, String org, long start, long end) {
        List<String> out = new ArrayList<>();
        for (UsageLine l : s.report(org, start, end)) out.add(l.keyId() + ":" + l.plan() + ":" + l.requests() + "/" + l.units() + "/" + l.denied());
        return "[" + String.join(", ", out) + "]";
    }

    // ---------------------------------------------------------------- phase 1

    static void test_p1_allow_until_limit() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "strict");
        Expect.eq("ok 6", hiddenAllow(s, "k1", 0, 4));
        Expect.eq("ok 0", hiddenAllow(s, "k1", 10, 6));
        Expect.eq("no 0 +15", hiddenAllow(s, "k1", 45, 1));
        Expect.eq("10/10", hiddenUsage(s, "k1", 59));
        Expect.eq("ok 0", hiddenAllow(s, "k1", 60, 10));
    }

    static void test_p1_window_edges() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "strict");
        Expect.eq("ok 0", hiddenAllow(s, "k1", 119, 10));
        Expect.eq("ok 0", hiddenAllow(s, "k1", 120, 10));
        Expect.eq("no 0 +60", hiddenAllow(s, "k1", 120, 1));
        Expect.eq("10/10", hiddenUsage(s, "k1", 179));
        Expect.eq("0/10", hiddenUsage(s, "k1", 180));
    }

    static void test_p1_burst_from_quiet_window() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "basic");
        Expect.eq("0/14", hiddenUsage(s, "k1", 0)); // idle before: full burst
        Expect.eq("ok 7", hiddenAllow(s, "k1", 5, 7));
        Expect.eq("0/13", hiddenUsage(s, "k1", 60)); // 3 unused roll over
        Expect.eq("0/14", hiddenUsage(s, "k1", 120)); // only the window before counts
    }

    static void test_p1_no_burst_after_burst_window() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "basic");
        Expect.eq("ok 0", hiddenAllow(s, "k1", 10, 14)); // limit + burst
        Expect.eq("0/10", hiddenUsage(s, "k1", 60)); // next window has the plain limit
        Expect.eq("ok 0", hiddenAllow(s, "k1", 61, 10));
        Expect.eq("no 0 +58", hiddenAllow(s, "k1", 62, 1));
        Expect.eq("0/10", hiddenUsage(s, "k1", 120));
    }

    static void test_p1_pro_burst_window() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "pro");
        Expect.eq("ok 5", hiddenAllow(s, "k1", 0, 65));
        Expect.eq("ok 0", hiddenAllow(s, "k1", 60, 50));
        Expect.eq("no 0 +59", hiddenAllow(s, "k1", 61, 1));
    }

    static void test_p1_denied_request_spends_nothing() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "strict");
        Expect.eq("ok 2", hiddenAllow(s, "k1", 0, 8));
        Expect.eq("no 2 +59", hiddenAllow(s, "k1", 1, 5)); // batch call too big
        Expect.eq("ok 0", hiddenAllow(s, "k1", 2, 2)); // small call still fits
        Expect.eq("10/10", hiddenUsage(s, "k1", 3));
    }

    static void test_p1_denied_requests_keep_burst() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "pro");
        Expect.eq("ok 30", hiddenAllow(s, "k1", 0, 40));
        for (int i = 1; i < 6; i++) {
            Expect.eq("no 30 +" + (60 - i), hiddenAllow(s, "k1", i, 50)); // retry storm
        }
        Expect.eq("0/60", hiddenUsage(s, "k1", 60)); // 10 unused roll over
    }

    static void test_p1_errors() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "basic");
        Expect.eq("UNKNOWN_KEY", hiddenCode(() -> s.allow("nope", 0, 1)));
        Expect.eq("BAD_COST", hiddenCode(() -> s.allow("k1", 0, 0)));
        Expect.eq("DUPLICATE_KEY", hiddenCode(() -> s.issueKey("k1", "org-b", "pro")));
        Expect.eq("UNKNOWN_PLAN", hiddenCode(() -> s.issueKey("k2", "org-a", "gold")));
        Expect.eq("DUPLICATE_PLAN", hiddenCode(() -> s.addPlan(new Plan("pro", 1, 1))));
        Expect.eq("INVALID_PLAN", hiddenCode(() -> s.addPlan(new Plan("x", 0, 60))));
        Expect.eq("INVALID_PLAN", hiddenCode(() -> s.addPlan(new Plan("x", 5, 0))));
        Expect.eq("INVALID_PLAN", hiddenCode(() -> s.addPlan(new Plan("x", 5, 60, -1))));
        Expect.eq("UNKNOWN_PLAN", hiddenCode(() -> s.changePlan("k1", "gold")));
        Expect.eq("UNKNOWN_KEY", hiddenCode(() -> s.changePlan("nope", "pro")));
        Expect.eq("UNKNOWN_KEY", hiddenCode(() -> s.revoke("nope")));
        Expect.eq(new Key("k1", "org-a", "basic", false), s.key("k1")); // untouched by the failed calls
    }

    static void test_p1_revoked_key_rejected() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "pro");
        Expect.eq("ok 69", hiddenAllow(s, "k1", 0, 1));
        s.revoke("k1");
        Expect.eq("REVOKED", hiddenCode(() -> s.allow("k1", 1, 1)));
        Expect.eq("1/70", hiddenUsage(s, "k1", 2)); // usage of a revoked key
    }

    static void test_p1_revoked_key_stays_revoked_after_plan_change() {
        Service s = hiddenService();
        s.issueKey("leaked", "org-a", "basic");
        s.revoke("leaked");
        s.changePlan("leaked", "pro");
        Expect.eq("REVOKED", hiddenCode(() -> s.allow("leaked", 100, 1)));
        Expect.eq(new Key("leaked", "org-a", "pro", true), s.key("leaked"));
    }

    static void test_p1_plan_change_applies_to_next_request() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "strict");
        Expect.eq("ok 0", hiddenAllow(s, "k1", 0, 10));
        Expect.eq("no 0 +59", hiddenAllow(s, "k1", 1, 5)); // strict is full
        s.changePlan("k1", "pro");
        Expect.eq("ok 55", hiddenAllow(s, "k1", 2, 5)); // on pro, same window
        Expect.eq("15/70", hiddenUsage(s, "k1", 3));
    }

    static void test_p1_keys_are_independent() {
        Service s = hiddenService();
        s.issueKey("a", "org-a", "strict");
        s.issueKey("b", "org-a", "strict");
        Expect.eq("ok 0", hiddenAllow(s, "a", 0, 10));
        Expect.eq("ok 7", hiddenAllow(s, "b", 1, 3));
        Expect.eq("no 0 +58", hiddenAllow(s, "a", 2, 1));
        Expect.eq("3/10", hiddenUsage(s, "b", 2));
    }

    // ---------------------------------------------------------------- phase 2

    static void test_p2_report_counts() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "strict");
        long[][] reqs = {{0, 4}, {10, 3}, {20, 2}, {30, 5}, {70, 6}};
        for (long[] r : reqs) s.allow("k1", r[0], r[1]);
        Expect.eq("[k1:strict:4/15/1]", hiddenReport(s, "org-a", 0, 120));
    }

    static void test_p2_report_order() {
        Service s = hiddenService();
        String[][] keys = {{"mid", "pro"}, {"big", "pro"}, {"tie-b", "basic"}, {"tie-a", "strict"}};
        for (String[] k : keys) s.issueKey(k[0], "org-a", k[1]);
        Object[][] reqs = {{"mid", 0, 20}, {"big", 0, 30}, {"big", 1, 1}, {"tie-b", 2, 5}, {"tie-a", 3, 2}, {"tie-a", 4, 3}};
        for (Object[] r : reqs) s.allow((String) r[0], (int) r[1], (int) r[2]);
        // most units first, ties by key id
        Expect.eq("[big:pro:2/31/0, mid:pro:1/20/0, tie-a:strict:2/5/0, tie-b:basic:1/5/0]", hiddenReport(s, "org-a", 0, 60));
    }

    static void test_p2_report_range_is_half_open() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "pro");
        for (long at : new long[] {99, 100, 150, 199, 200}) s.allow("k1", at, 1);
        Expect.eq("[k1:pro:3/3/0]", hiddenReport(s, "org-a", 100, 200));
        Expect.eq("[k1:pro:1/1/0]", hiddenReport(s, "org-a", 200, 201));
        Expect.eq("[]", hiddenReport(s, "org-a", 0, 99));
    }

    static void test_p2_report_only_active_keys_of_the_org() {
        Service s = hiddenService();
        String[][] keys = {{"a1", "org-a"}, {"a2", "org-a"}, {"b1", "org-b"}};
        for (String[] k : keys) s.issueKey(k[0], k[1], "pro");
        s.allow("a1", 10, 2);
        s.allow("a2", 500, 2);
        s.allow("b1", 10, 9);
        Expect.eq("[a1:pro:1/2/0]", hiddenReport(s, "org-a", 0, 60));
        Expect.eq("[b1:pro:1/9/0]", hiddenReport(s, "org-b", 0, 1000));
    }

    static void test_p2_report_revoked_and_denied_only_keys() {
        Service s = hiddenService();
        s.issueKey("old", "org-a", "basic");
        s.issueKey("noisy", "org-a", "strict");
        s.allow("old", 0, 3);
        s.revoke("old");
        Expect.eq("REVOKED", hiddenCode(() -> s.allow("old", 1, 3)));
        s.allow("noisy", 2, 11);
        s.allow("noisy", 3, 12);
        s.changePlan("noisy", "pro");
        // a revoked key is still billed; a denied-only key is listed with its current plan
        Expect.eq("[old:basic:1/3/0, noisy:pro:0/0/2]", hiddenReport(s, "org-a", 0, 60));
    }

    static void test_p2_report_empty_and_bad_range() {
        Service s = hiddenService();
        s.issueKey("k1", "org-a", "pro");
        s.allow("k1", 10, 1);
        List<UsageLine> got = s.report("org-z", 0, 100);
        Expect.isTrue(got != null && got.isEmpty());
        Expect.eq("BAD_RANGE", hiddenCode(() -> s.report("org-a", 50, 50)));
        Expect.eq("BAD_RANGE", hiddenCode(() -> s.report("org-a", 60, 0)));
    }

    // ---------------------------------------------------------------- phase 3

    /**
     * Replays a busy day for one customer: n keys on "standard" sending one request a second, plus a "hog" key on
     * "metered" that hammers its limit, for the given number of seconds. Returns allowed and denied counts and the
     * sum of remaining over the allowed decisions.
     */
    static String hiddenBusyDay(Service s, int n, int seconds) {
        s.addPlan(new Plan("standard", 600, 60, 100));
        s.addPlan(new Plan("metered", 100, 60, 0));
        List<String> ids = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            ids.add("k" + i);
            s.issueKey("k" + i, "org-big", "standard");
        }
        ids.add("hog");
        s.issueKey("hog", "org-big", "metered");
        long seed = 2024;
        long allowed = 0, denied = 0, remaining = 0;
        for (int now = 0; now < seconds; now++) {
            for (String key : ids) {
                long cost = 7;
                if (!key.equals("hog")) {
                    seed = (seed * 1664525 + 1013904223) % (1L << 32);
                    cost = 1 + (seed >> 8) % 9;
                }
                Decision d = s.allow(key, now, cost);
                if (d.allowed()) {
                    allowed++;
                    remaining += d.remaining();
                } else {
                    denied++;
                }
            }
        }
        return "allowed=" + allowed + " denied=" + denied + " remaining=" + remaining;
    }

    static void test_p3_busy_day_traffic() {
        Service s = new Service();
        long start = System.nanoTime();
        String got = hiddenBusyDay(s, 1, 35000);
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq("allowed=43176 denied=26824 remaining=19550588", got); // remaining: sum over the allowed calls
        Expect.eq("104/700", hiddenUsage(s, "k0", 34999));
        Expect.isTrue(ms < 1000, "70,000 allow calls took " + ms + " ms (budget 1000 ms)");
    }

    static void test_p3_hourly_reports() {
        Service s = new Service();
        long start = System.nanoTime();
        hiddenBusyDay(s, 1, 35000);
        String[] hours = new String[10];
        for (int h = 0; h < 10; h++) hours[h] = hiddenReport(s, "org-big", h * 3600L, (h + 1) * 3600L);
        String day = hiddenReport(s, "org-big", 0, 35000);
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq("[k0:standard:3600/18030/0, hog:metered:840/5880/2760]", hours[0]);
        Expect.eq("[k0:standard:3600/17858/0, hog:metered:840/5880/2760]", hours[7]);
        Expect.eq("[k0:standard:2600/13071/0, hog:metered:616/4312/1984]", hours[9]);
        Expect.eq("[k0:standard:35000/175050/0, hog:metered:8176/57232/26824]", day);
        Expect.isTrue(ms < 1000, "70,000 allow calls plus 11 reports took " + ms + " ms (budget 1000 ms)");
    }
}
