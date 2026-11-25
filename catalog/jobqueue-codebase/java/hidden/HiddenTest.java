import java.util.ArrayList;
import java.util.List;

// The app compiles one phase's tests at a time: helpers use only the phase-1 API.
public class HiddenTest {
    static String hiddenCode(Runnable r) {
        try {
            r.run();
            return "ok";
        } catch (QueueException e) {
            return e.code.name();
        }
    }

    static JobQueue hiddenQueue(long visibility, long baseDelay, long maxDelay, int maxAttempts) {
        return new JobQueue(new JobQueue.Options(visibility, baseDelay, maxDelay, maxAttempts, 3600));
    }

    static String hiddenLease(JobQueue.Lease l) {
        return l == null ? "empty" : l.jobId() + "#" + l.attempt() + "@" + l.until();
    }

    /** Leases and acks every job that is ready at now; returns their payloads in lease order. */
    static String hiddenDrain(JobQueue q, String queue, long now) {
        List<String> out = new ArrayList<>();
        for (JobQueue.Lease l = q.lease(queue, now); l != null; l = q.lease(queue, now)) {
            out.add(l.payload());
            q.ack(l.jobId(), l.token(), now);
        }
        return String.join(",", out);
    }

    static String hiddenStatus(JobQueue q, String id) {
        Job j = q.job(id);
        return j == null ? "gone" : j.status() + "/" + j.attempts();
    }

    // ---------------------------------------------------------------- phase 1

    static void test_p1_heartbeat_keeps_the_lease() {
        JobQueue q = new JobQueue();
        String id = q.enqueue("payments", "capture-981", 100);
        JobQueue.Lease a = q.lease("payments", 100);
        q.extend(id, a.token(), 60, 120);
        Expect.eq("empty", hiddenLease(q.lease("payments", 135)));
        q.extend(id, a.token(), 30, 170);
        Expect.eq("empty", hiddenLease(q.lease("payments", 185)));
        Expect.eq("ok", hiddenCode(() -> q.ack(id, a.token(), 195)));
        Expect.eq("gone", hiddenStatus(q, id));
    }

    static void test_p1_quick_retry_keeps_the_new_lease() {
        JobQueue q = hiddenQueue(30, 5, 600, 3);
        String id = q.enqueue("payments", "capture-982", 0);
        JobQueue.Lease a = q.lease("payments", 0);
        q.fail(id, a.token(), "gateway 503", 2);
        JobQueue.Lease b = q.lease("payments", 10);
        Expect.eq(id + "#2@40", hiddenLease(b));
        Expect.eq("empty", hiddenLease(q.lease("payments", 35)));
        Expect.eq("ok", hiddenCode(() -> q.ack(id, b.token(), 38)));
    }

    static void test_p1_expired_lease_moves_to_the_next_worker() {
        JobQueue q = new JobQueue();
        String id = q.enqueue("webhooks", "deliver-7", 0);
        JobQueue.Lease a = q.lease("webhooks", 0);
        Expect.eq("empty", hiddenLease(q.lease("webhooks", 29)));
        JobQueue.Lease b = q.lease("webhooks", 30);
        Expect.eq(id + "#2@60", hiddenLease(b));
        Expect.eq("LEASE_LOST", hiddenCode(() -> q.ack(id, a.token(), 31)));
        Expect.eq("LEASE_LOST", hiddenCode(() -> q.extend(id, a.token(), 30, 31)));
        Expect.eq("LEASE_LOST", hiddenCode(() -> q.fail(id, a.token(), "late", 31)));
        q.extend(id, b.token(), 10, 40);
        Expect.eq("empty", hiddenLease(q.lease("webhooks", 49)));
        JobQueue.Lease c = q.lease("webhooks", 50);
        Expect.eq(id + "#3@80", hiddenLease(c));
        Expect.eq("LEASE_LOST", hiddenCode(() -> q.ack(id, b.token(), 51)));
        Expect.eq("ok", hiddenCode(() -> q.ack(id, c.token(), 52)));
    }

    static void test_p1_crashing_job_is_dead_lettered() {
        JobQueue q = hiddenQueue(30, 10, 600, 2);
        String a = q.enqueue("imports", "csv-1", 0);
        Expect.eq(a + "#1@30", hiddenLease(q.lease("imports", 0)));
        Expect.eq("empty", hiddenLease(q.lease("imports", 29)));
        Expect.eq(a + "#2@60", hiddenLease(q.lease("imports", 30)));
        Expect.eq("empty", hiddenLease(q.lease("imports", 60)));
        Expect.eq("DEAD/2", hiddenStatus(q, a));
        Expect.eq("lease expired", q.job(a).lastError());
        String b = q.enqueue("imports", "csv-2", 61);
        q.fail(b, q.lease("imports", 61).token(), "parse error", 62);
        q.fail(b, q.lease("imports", 72).token(), "parse error", 73);
        Expect.eq("[" + a + " DEAD attempts=2 lastError=lease expired, " + b + " DEAD attempts=2 lastError=parse error]",
                q.deadLetters("imports").toString());
        Expect.eq("empty", hiddenLease(q.lease("imports", 500)));
    }

    static void test_p1_redriven_job_gets_fresh_attempts() {
        JobQueue q = hiddenQueue(30, 10, 600, 2);
        String id = q.enqueue("exports", "report-31", 0);
        q.fail(id, q.lease("exports", 0).token(), "disk full", 1);
        q.fail(id, q.lease("exports", 11).token(), "disk full", 12);
        Expect.eq("DEAD/2", hiddenStatus(q, id));
        q.redrive(id, 100);
        Expect.eq("[]", q.deadLetters("exports").toString());
        JobQueue.Lease l = q.lease("exports", 100);
        Expect.eq(id + "#1@130", hiddenLease(l));
        q.fail(id, l.token(), "disk full", 101);
        Expect.eq("SCHEDULED/1", hiddenStatus(q, id));
        Expect.eq(id + "#2@141", hiddenLease(q.lease("exports", 111)));
    }

    static void test_p1_idempotency_keys_belong_to_their_queue() {
        JobQueue q = new JobQueue();
        String e1 = q.enqueue("emails", "welcome-42", 100, JobQueue.opts().key("signup-42"));
        String b1 = q.enqueue("billing", "trial-42", 100, JobQueue.opts().key("signup-42"));
        Expect.isTrue(!e1.equals(b1), "billing reused the emails job " + e1);
        Expect.eq(e1, q.enqueue("emails", "welcome-42", 105, JobQueue.opts().key("signup-42")));
        Expect.eq(b1, q.enqueue("billing", "trial-42", 105, JobQueue.opts().key("signup-42")));
        Expect.eq("trial-42", hiddenDrain(q, "billing", 110));
        Expect.eq("welcome-42", hiddenDrain(q, "emails", 110));
    }

    static void test_p1_idempotency_window() {
        JobQueue q = new JobQueue();
        String a = q.enqueue("webhooks", "evt-1", 100, JobQueue.opts().key("evt-1"));
        JobQueue.Lease l = q.lease("webhooks", 200);
        q.ack(a, l.token(), 201);
        Expect.eq(a, q.enqueue("webhooks", "evt-1", 3699, JobQueue.opts().key("evt-1")));
        Expect.eq("", hiddenDrain(q, "webhooks", 3699));
        String b = q.enqueue("webhooks", "evt-1", 3700, JobQueue.opts().key("evt-1"));
        Expect.isTrue(!a.equals(b), "key should have lapsed at 3700");
        Expect.eq(b, q.enqueue("webhooks", "evt-1", 3800, JobQueue.opts().key("evt-1")));
        Expect.eq("evt-1", hiddenDrain(q, "webhooks", 3800));
    }

    static void test_p1_retry_backoff_doubles_up_to_the_cap() {
        JobQueue q = hiddenQueue(30, 10, 25, 5);
        String id = q.enqueue("reports", "weekly", 0);
        List<String> seen = new ArrayList<>();
        long[][] steps = {{0, 0}, {9, 10}, {29, 30}, {54, 55}, {79, 80}};
        for (long[] s : steps) {
            if (s[0] != s[1]) seen.add(hiddenLease(q.lease("reports", s[0])));
            JobQueue.Lease l = q.lease("reports", s[1]);
            seen.add(hiddenLease(l));
            q.fail(id, l.token(), "timeout", s[1]);
        }
        Expect.eq("job-1#1@30,empty,job-1#2@40,empty,job-1#3@60,empty,job-1#4@85,empty,job-1#5@110", String.join(",", seen));
        Expect.eq("DEAD/5", hiddenStatus(q, id));
        Expect.eq("timeout", q.job(id).lastError());
    }

    static void test_p1_lease_order() {
        JobQueue q = new JobQueue();
        q.enqueue("jobs", "a", 0, JobQueue.opts().runAt(50));
        q.enqueue("jobs", "b", 10);
        q.enqueue("jobs", "c", 20, JobQueue.opts().priority(5));
        q.enqueue("jobs", "d", 30, JobQueue.opts().priority(5).runAt(40));
        q.enqueue("jobs", "e", 30);
        q.enqueue("jobs", "f", 30, JobQueue.opts().priority(-1));
        Expect.eq("c,b,e,f", hiddenDrain(q, "jobs", 30));
        q.enqueue("jobs", "g", 45);
        q.enqueue("jobs", "h", 45, JobQueue.opts().runAt(5));
        Expect.eq("d,g,h,a", hiddenDrain(q, "jobs", 60));
    }

    static void test_p1_cancel_errors_and_clock() {
        JobQueue q = new JobQueue();
        String a = q.enqueue("jobs", "a", 10);
        String b = q.enqueue("jobs", "b", 10, JobQueue.opts().runAt(100));
        String c = q.enqueue("jobs", "c", 10);
        q.cancel(a, 11);
        q.cancel(b, 12);
        JobQueue.Lease l = q.lease("jobs", 13);
        Expect.eq(c, l.jobId());
        Expect.eq("INVALID", hiddenCode(() -> q.cancel(c, 14)));
        Expect.eq("NOT_FOUND", hiddenCode(() -> q.cancel(a, 14)));
        Expect.eq("LEASE_LOST", hiddenCode(() -> q.ack(c, "lease-999", 14)));
        Expect.eq("INVALID", hiddenCode(() -> q.redrive(c, 14)));
        Expect.eq("INVALID", hiddenCode(() -> q.enqueue("", "x", 14)));
        Expect.eq("INVALID", hiddenCode(() -> q.enqueue("jobs", "x", 14, JobQueue.opts().maxAttempts(-1))));
        Expect.eq("INVALID", hiddenCode(() -> q.lease("jobs", 14, 0)));
        Expect.eq("INVALID", hiddenCode(() -> q.extend(c, l.token(), 0, 14)));
        Expect.eq("BACKDATED", hiddenCode(() -> q.lease("jobs", 13)));
        Expect.eq("ok", hiddenCode(() -> q.ack(c, l.token(), 15)));
        Expect.eq("NOT_FOUND", hiddenCode(() -> q.ack(c, l.token(), 15)));
        Expect.eq("", hiddenDrain(q, "jobs", 200));
        Expect.eq("gone", hiddenStatus(q, a));
    }

    // ---------------------------------------------------------------- phase 2

    static void test_p2_counts_jobs_by_state() {
        JobQueue q = hiddenQueue(30, 100, 600, 2);
        q.enqueue("emails", "a", 10);
        q.enqueue("emails", "b", 12);
        q.enqueue("emails", "c", 12, JobQueue.opts().runAt(500));
        q.enqueue("emails", "d", 13, JobQueue.opts().priority(9));
        String e = q.enqueue("emails", "e", 14, JobQueue.opts().priority(8));
        String f = q.enqueue("emails", "f", 15, JobQueue.opts().priority(7).maxAttempts(1));
        String g = q.enqueue("emails", "g", 16, JobQueue.opts().priority(6));
        String h = q.enqueue("emails", "h", 17);
        q.enqueue("billing", "x", 17);
        q.lease("emails", 20);
        JobQueue.Lease le = q.lease("emails", 20);
        JobQueue.Lease lf = q.lease("emails", 20);
        JobQueue.Lease lg = q.lease("emails", 20);
        q.fail(e, le.token(), "500", 21);
        q.fail(f, lf.token(), "400", 21);
        q.ack(g, lg.token(), 22);
        q.cancel(h, 23);
        Expect.eq("Stats[ready=2, scheduled=1, retrying=1, inFlight=1, dead=1, completed=1, oldestReadyAge=30, nextRunAt=121]",
                q.stats("emails", 40).toString());
        Expect.eq("Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=23, nextRunAt=null]",
                q.stats("billing", 40).toString());
    }

    static void test_p2_moves_the_clock_first() {
        JobQueue q = new JobQueue();
        q.enqueue("webhooks", "a", 0);
        q.enqueue("webhooks", "b", 0, JobQueue.opts().runAt(50));
        q.lease("webhooks", 5);
        Expect.eq("Stats[ready=0, scheduled=1, retrying=0, inFlight=1, dead=0, completed=0, oldestReadyAge=0, nextRunAt=50]",
                q.stats("webhooks", 20).toString());
        Expect.eq("Stats[ready=2, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=25, nextRunAt=null]",
                q.stats("webhooks", 60).toString());
        Expect.eq("BACKDATED", hiddenCode(() -> q.stats("webhooks", 59)));
    }

    static void test_p2_age_counts_from_when_the_job_became_ready() {
        JobQueue q = hiddenQueue(30, 40, 600, 3);
        String id = q.enqueue("reports", "monthly", 0, JobQueue.opts().runAt(100));
        Expect.eq("Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=50, nextRunAt=null]",
                q.stats("reports", 150).toString());
        q.fail(id, q.lease("reports", 150).token(), "timeout", 160);
        Expect.eq("Stats[ready=0, scheduled=0, retrying=1, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=200]",
                q.stats("reports", 199).toString());
        Expect.eq("Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=30, nextRunAt=null]",
                q.stats("reports", 230).toString());
    }

    static void test_p2_dead_letters_and_redrive() {
        JobQueue q = hiddenQueue(30, 10, 600, 1);
        String a = q.enqueue("payments", "a", 0);
        q.enqueue("payments", "b", 0);
        JobQueue.Lease la = q.lease("payments", 0);
        q.lease("payments", 0);
        q.fail(a, la.token(), "card declined", 5);
        Expect.eq("Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=2, completed=0, oldestReadyAge=0, nextRunAt=null]",
                q.stats("payments", 40).toString());
        q.redrive(a, 50);
        Expect.eq("Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=1, completed=0, oldestReadyAge=20, nextRunAt=null]",
                q.stats("payments", 70).toString());
    }

    static void test_p2_completed_per_queue_and_unknown_queue() {
        JobQueue q = new JobQueue();
        for (int i = 0; i < 3; i++) q.enqueue("emails", "e" + i, i, JobQueue.opts().key("k" + i));
        q.enqueue("emails", "e0-again", 3, JobQueue.opts().key("k0"));
        q.enqueue("billing", "b0", 3);
        for (int i = 0; i < 2; i++) {
            JobQueue.Lease l = q.lease("emails", 10);
            q.ack(l.jobId(), l.token(), 10);
        }
        JobQueue.Lease l = q.lease("billing", 12);
        q.ack(l.jobId(), l.token(), 12);
        Expect.eq("Stats[ready=1, scheduled=0, retrying=0, inFlight=0, dead=0, completed=2, oldestReadyAge=18, nextRunAt=null]",
                q.stats("emails", 20).toString());
        Expect.eq("Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=0, completed=1, oldestReadyAge=0, nextRunAt=null]",
                q.stats("billing", 20).toString());
        Expect.eq("Stats[ready=0, scheduled=0, retrying=0, inFlight=0, dead=0, completed=0, oldestReadyAge=0, nextRunAt=null]",
                q.stats("nope", 20).toString());
    }

    // ---------------------------------------------------------------- phase 3

    static void test_p3_backlog_after_an_outage() {
        JobQueue q = hiddenQueue(30, 30, 600, 3);
        int backlog = 80_000, steps = 112_000;
        // A partner endpoint was down for two hours: webhook events piled up, a few of them
        // delivered twice, some deferred by ten minutes, a quarter flagged urgent.
        for (int i = 0; i < backlog; i++) {
            JobQueue.Opts o = JobQueue.opts().key("evt-" + (i % 25 == 24 ? i - 1 : i)).priority(i % 4 == 0 ? 1 : 0);
            if (i % 10 == 3) o.runAt(i / 10 + 600);
            q.enqueue("webhooks", "evt-" + i, i / 10, o);
        }
        // It's back. Workers drain the backlog while live traffic keeps arriving.
        long start = System.nanoTime();
        int acked = 0, failed = 0, abandoned = 0, cancelled = 0, refused = 0, idle = 0;
        long checksum = 0;
        for (int s = 0; s < steps; s++) {
            long now = 10_000 + s / 20;
            if (s % 3 == 0) q.enqueue("webhooks", "live-" + s, now, JobQueue.opts().priority(s % 9 == 0 ? 2 : 0));
            if (s % 997 == 0) {
                String victim = "job-" + (1 + (s * 31L) % backlog);
                if (hiddenCode(() -> q.cancel(victim, now)).equals("ok")) cancelled++;
                else refused++;
            }
            JobQueue.Lease l = q.lease("webhooks", now);
            if (l == null) {
                idle++;
            } else {
                int n = Integer.parseInt(l.jobId().substring(4));
                if (n % 41 == 0) abandoned++;
                else if ((n + l.attempt()) % 7 == 0) {
                    q.fail(l.jobId(), l.token(), "502", now);
                    failed++;
                } else {
                    q.ack(l.jobId(), l.token(), now);
                    acked++;
                }
            }
            if (s % 5000 == 4999) {
                Stats st = q.stats("webhooks", now);
                checksum = checksum * 31 + st.ready() + 7L * st.retrying() + 13L * st.inFlight() + 17L * st.dead() + st.oldestReadyAge();
            }
        }
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq("acked=93158 failed=14187 abandoned=4655 cancelled=56 refused=57 idle=0 checksum=4859009841139023553 "
                + "Stats[ready=20150, scheduled=0, retrying=0, inFlight=0, dead=770, completed=93158, oldestReadyAge=3762, nextRunAt=null]",
                "acked=" + acked + " failed=" + failed + " abandoned=" + abandoned + " cancelled=" + cancelled + " refused=" + refused
                + " idle=" + idle + " checksum=" + checksum + " " + q.stats("webhooks", 10_000 + steps / 20 + 1000));
        Expect.isTrue(ms < 2500, "too slow: draining took " + ms + " ms (budget 2500 ms)");
    }
}
