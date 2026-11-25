import java.util.ArrayList;
import java.util.List;

// The app compiles one phase's tests at a time: helpers use only the phase-1 API.
public class HiddenTest {
    static final long hiddenH = 3600;
    static final long hiddenDAY = 24 * hiddenH;

    static void hiddenUser(Service s, String id, int offsetMin, String... chans) {
        s.addUser(id, offsetMin);
        s.setChannels(id, new ArrayList<>(List.of(chans)));
    }

    static String hiddenResult(Result r) {
        return r.status().equals(Notify.SENT) ? "sent " + String.join(",", r.channels()) : r.status();
    }

    /** Sends a notification and renders the result as "sent push,sms", "held" or "duplicate". */
    static String hiddenSend(Service s, String user, long at, String topic, String key, boolean urgent) {
        return hiddenResult(s.send(new Notification(user, topic, key, topic + ":" + key, at, urgent)));
    }

    static String hiddenSend(Service s, String user, long at, String topic, String key) {
        return hiddenSend(s, user, at, topic, key, false);
    }

    static String hiddenUrgent(Service s, String user, long at, String topic, String key) {
        return hiddenSend(s, user, at, topic, key, true);
    }

    static List<String> hiddenChannels(Service s, String id) {
        return s.user(id).channels();
    }

    static List<String> hiddenDigest(Service s, String id, long now) {
        List<String> out = new ArrayList<>();
        for (DigestLine ln : s.digest(id, now)) out.add(ln.topic() + ":" + ln.count() + ":" + ln.latest());
        return out;
    }

    static String hiddenCode(Runnable r) {
        try {
            r.run();
            return "ok";
        } catch (NotifyException e) {
            return e.code.name();
        }
    }

    // ---------------------------------------------------------------- phase 1

    static void test_p1_new_user_defaults() {
        Service s = new Service();
        s.addUser("ana", 0);
        Expect.eq(List.of(Notify.EMAIL), hiddenChannels(s, "ana"));
        Expect.eq("sent email", hiddenSend(s, "ana", 3 * hiddenH, "billing", "inv-1"));
    }

    static void test_p1_fan_out_in_user_order() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.SMS, Notify.EMAIL, Notify.PUSH);
        Expect.eq("sent sms,email,push", hiddenSend(s, "ana", 1000, "security", "login-1"));
        hiddenUser(s, "ben", 0);
        Expect.eq("held", hiddenSend(s, "ben", 1000, "security", "login-1"));
        Expect.eq("held", hiddenUrgent(s, "ben", 1001, "security", "login-2"));
    }

    static void test_p1_quiet_hours_utc() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.PUSH);
        s.setQuietHours("ana", 22, 7);
        Expect.eq("sent push", hiddenSend(s, "ana", 22 * hiddenH - 60, "promo", "a"));
        Expect.eq("held", hiddenSend(s, "ana", 22 * hiddenH, "promo", "b"));
        Expect.eq("held", hiddenSend(s, "ana", hiddenDAY + 3 * hiddenH, "promo", "c"));
        Expect.eq("held", hiddenSend(s, "ana", hiddenDAY + 7 * hiddenH - 1, "promo", "d"));
        Expect.eq("sent push", hiddenSend(s, "ana", hiddenDAY + 7 * hiddenH, "promo", "e"));
        Expect.eq("sent push", hiddenUrgent(s, "ana", hiddenDAY + 23 * hiddenH + 1800, "security", "f"));
    }

    static void test_p1_quiet_hours_east_of_utc() {
        Service s = new Service();
        hiddenUser(s, "kai", 8 * 60, Notify.PUSH, Notify.SMS);
        s.setQuietHours("kai", 22, 7);
        Expect.eq("held", hiddenSend(s, "kai", 15 * hiddenH, "promo", "a")); // 23:00 local
        Expect.eq("held", hiddenSend(s, "kai", 22 * hiddenH + 1800, "promo", "b")); // 06:30 local
        Expect.eq("sent push,sms", hiddenSend(s, "kai", 23 * hiddenH, "promo", "c")); // 07:00 local
        Expect.eq("sent push,sms", hiddenSend(s, "kai", hiddenDAY + 13 * hiddenH, "promo", "d")); // 21:00 local
    }

    static void test_p1_quiet_hours_west_and_half_hour_offsets() {
        Service s = new Service();
        hiddenUser(s, "lee", -5 * 60, Notify.EMAIL);
        s.setQuietHours("lee", 22, 7);
        Expect.eq("held", hiddenSend(s, "lee", hiddenDAY + 3 * hiddenH, "promo", "a")); // 22:00 local
        Expect.eq("held", hiddenSend(s, "lee", hiddenDAY + 12 * hiddenH - 60, "promo", "b")); // 06:59 local
        Expect.eq("sent email", hiddenSend(s, "lee", hiddenDAY + 12 * hiddenH, "promo", "c")); // 07:00 local
        hiddenUser(s, "ria", 5 * 60 + 30, Notify.EMAIL);
        s.setQuietHours("ria", 9, 17);
        Expect.eq("held", hiddenSend(s, "ria", 3 * hiddenH + 1800, "promo", "a")); // 09:00 local
        Expect.eq("sent email", hiddenSend(s, "ria", hiddenDAY + 3 * hiddenH + 1740, "promo", "b")); // 08:59 local
        Expect.eq("sent email", hiddenSend(s, "ria", hiddenDAY + 11 * hiddenH + 1800, "promo", "c")); // 17:00 local
    }

    static void test_p1_dedupe_window() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.EMAIL);
        Expect.eq("sent email", hiddenSend(s, "ana", 0, "billing", "pay-due"));
        Expect.eq("duplicate", hiddenSend(s, "ana", 1800, "billing", "pay-due"));
        Expect.eq("duplicate", hiddenSend(s, "ana", 3599, "billing", "pay-due"));
        Expect.eq("sent email", hiddenSend(s, "ana", 3600, "billing", "pay-due"));
        Expect.eq("sent email", hiddenSend(s, "ana", 3601, "billing", "pay-late"));
        Expect.eq("sent email", hiddenSend(s, "ana", 7200, "billing", "pay-due"));
    }

    static void test_p1_dedupe_keys_are_per_user() {
        Service s = new Service();
        for (String id : List.of("ana", "ben", "cy")) hiddenUser(s, id, 0, Notify.PUSH);
        Expect.eq("sent push", hiddenSend(s, "ana", 100, "news", "launch-2026"));
        Expect.eq("sent push", hiddenSend(s, "ben", 101, "news", "launch-2026"));
        Expect.eq("sent push", hiddenSend(s, "cy", 102, "news", "launch-2026"));
        Expect.eq("duplicate", hiddenSend(s, "ana", 200, "news", "launch-2026"));
    }

    static void test_p1_held_notification_still_dedupes() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.PUSH);
        s.setQuietHours("ana", 0, 6);
        Expect.eq("held", hiddenSend(s, "ana", 5 * hiddenH + 1800, "social", "like-9"));
        Expect.eq("duplicate", hiddenSend(s, "ana", 6 * hiddenH + 600, "social", "like-9"));
        Expect.eq("sent push", hiddenSend(s, "ana", 6 * hiddenH + 1800, "social", "like-9"));
    }

    static void test_p1_hourly_caps() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.PUSH, Notify.SMS);
        List<String> got = new ArrayList<>();
        for (int i = 0; i < 6; i++) got.add(hiddenSend(s, "ana", 600L * i, "chat", "m" + i));
        Expect.eq(List.of("sent push,sms", "sent push,sms", "sent push", "sent push", "held", "held"), got);
        Expect.eq("sent push,sms", hiddenSend(s, "ana", 3600, "chat", "m6")); // first push leaves the window
        Expect.eq("sent push,sms", hiddenSend(s, "ana", 4200, "chat", "m7")); // second slot frees
        Expect.eq("sent push,sms", hiddenSend(s, "ana", 7800, "chat", "m8")); // an hour later all clear
    }

    static void test_p1_caps_are_per_user() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.SMS);
        hiddenUser(s, "ben", 0, Notify.SMS);
        hiddenSend(s, "ana", 0, "otp", "1");
        hiddenSend(s, "ana", 1, "otp", "2");
        Expect.eq("held", hiddenUrgent(s, "ana", 2, "otp", "3"));
        Expect.eq("sent sms", hiddenSend(s, "ben", 3, "otp", "1"));
    }

    static void test_p1_channels_are_not_shared_between_users() {
        Service s = new Service();
        s.addUser("ana", 0);
        s.addUser("ben", 0);
        List<String> row = new ArrayList<>(List.of(Notify.PUSH, Notify.SMS));
        s.setChannels("ana", row);
        row.set(0, Notify.EMAIL); // the import tool reuses its row buffer
        row.set(1, Notify.PUSH);
        s.setChannels("ben", row);
        Expect.eq(List.of(Notify.PUSH, Notify.SMS), hiddenChannels(s, "ana"));
        Expect.eq("sent push,sms", hiddenSend(s, "ana", 10, "security", "new-device"));
        Expect.eq("sent email,push", hiddenSend(s, "ben", 10, "security", "new-device"));
    }

    static void test_p1_errors() {
        Service s = new Service();
        hiddenUser(s, "ana", 60, Notify.PUSH);
        s.setQuietHours("ana", 23, 6);
        Expect.eq("DUPLICATE_USER", hiddenCode(() -> s.addUser("ana", 0)));
        Expect.eq("BAD_OFFSET", hiddenCode(() -> s.addUser("x", 841)));
        Expect.eq("BAD_OFFSET", hiddenCode(() -> s.addUser("x", -721)));
        s.addUser("e", 840);
        s.addUser("w", -720);
        Expect.eq("BAD_CHANNEL", hiddenCode(() -> s.setChannels("ana", List.of(Notify.PUSH, "fax"))));
        Expect.eq("BAD_CHANNEL", hiddenCode(() -> s.setChannels("ana", List.of(Notify.SMS, Notify.SMS))));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> s.setChannels("nope", List.of())));
        Expect.eq("BAD_QUIET_HOURS", hiddenCode(() -> s.setQuietHours("ana", 22, 24)));
        Expect.eq("BAD_QUIET_HOURS", hiddenCode(() -> s.setQuietHours("ana", -1, 6)));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> s.setQuietHours("nope", 1, 2)));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> s.send(new Notification("nope", "t", "k", "", 1))));
        Expect.eq("BAD_NOTIFICATION", hiddenCode(() -> s.send(new Notification("ana", "", "k", "", 1))));
        Expect.eq("BAD_NOTIFICATION", hiddenCode(() -> s.send(new Notification("ana", "t", "", "", 1))));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> s.user("nope")));
        User u = s.user("ana");
        Expect.eq("ana/60/[push]/23/6", u.id() + "/" + u.offsetMin() + "/" + u.channels() + "/" + u.quietFrom() + "/" + u.quietTo());
    }

    // ---------------------------------------------------------------- phase 2

    static void test_p2_digest_groups_by_topic() {
        Service s = new Service();
        hiddenUser(s, "ana", 0);
        hiddenSend(s, "ana", 100, "billing", "b1");
        hiddenSend(s, "ana", 200, "promo", "p1");
        hiddenSend(s, "ana", 300, "security", "s1");
        hiddenSend(s, "ana", 400, "promo", "p2");
        hiddenSend(s, "ana", 500, "billing", "b2");
        hiddenSend(s, "ana", 600, "promo", "p3");
        Expect.eq(List.of("promo:3:promo:p3", "billing:2:billing:b2", "security:1:security:s1"),
                hiddenDigest(s, "ana", hiddenDAY + 9 * hiddenH));
    }

    static void test_p2_digest_covers_only_the_day_before() {
        Service s = new Service();
        hiddenUser(s, "ana", 0);
        hiddenSend(s, "ana", 10, "news", "d0");
        hiddenSend(s, "ana", hiddenDAY - 1, "news", "d0-late");
        hiddenSend(s, "ana", hiddenDAY, "news", "d1");
        hiddenSend(s, "ana", 2 * hiddenDAY - 1, "social", "d1-late");
        hiddenSend(s, "ana", 2 * hiddenDAY, "news", "d2");
        Expect.eq(List.of("news:2:news:d0-late"), hiddenDigest(s, "ana", hiddenDAY + 5));
        Expect.eq(List.of("news:1:news:d1", "social:1:social:d1-late"), hiddenDigest(s, "ana", 2 * hiddenDAY + 20 * hiddenH));
        Expect.eq(List.of("news:1:news:d1", "social:1:social:d1-late"), hiddenDigest(s, "ana", 2 * hiddenDAY));
        Expect.eq(List.<String>of(), hiddenDigest(s, "ana", 50));
        Expect.eq(List.<String>of(), hiddenDigest(s, "ana", 4 * hiddenDAY));
    }

    static void test_p2_digest_uses_the_users_local_day() {
        Service s = new Service();
        hiddenUser(s, "kai", 9 * 60);
        hiddenUser(s, "lee", -7 * 60);
        for (String id : List.of("kai", "lee")) {
            hiddenSend(s, id, hiddenDAY + 14 * hiddenH, "news", id + "-a");
            hiddenSend(s, id, hiddenDAY + 16 * hiddenH, "news", id + "-b");
            hiddenSend(s, id, 2 * hiddenDAY + 6 * hiddenH, "news", id + "-c");
            hiddenSend(s, id, 2 * hiddenDAY + 8 * hiddenH, "news", id + "-d");
        }
        Expect.eq(List.of("news:1:news:kai-a"), hiddenDigest(s, "kai", 2 * hiddenDAY + 10 * hiddenH));
        Expect.eq(List.of("news:3:news:kai-d"), hiddenDigest(s, "kai", 2 * hiddenDAY + 16 * hiddenH));
        Expect.eq(List.of("news:1:news:lee-d"), hiddenDigest(s, "lee", 3 * hiddenDAY + 10 * hiddenH));
        Expect.eq(List.of("news:3:news:lee-c"), hiddenDigest(s, "lee", 3 * hiddenDAY + 6 * hiddenH));
    }

    static void test_p2_digest_has_only_held_notifications() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.SMS);
        hiddenSend(s, "ana", 100, "otp", "c1");
        hiddenSend(s, "ana", 200, "otp", "c2");
        hiddenSend(s, "ana", 300, "otp", "c3");
        hiddenSend(s, "ana", 400, "otp", "c3");
        hiddenSend(s, "ana", 500, "alerts", "a1");
        hiddenUrgent(s, "ana", 600, "alerts", "a2");
        hiddenSend(s, "ana", 3700, "alerts", "a3");
        Expect.eq(List.of("alerts:2:alerts:a2", "otp:1:otp:c3"), hiddenDigest(s, "ana", hiddenDAY));
    }

    static void test_p2_digest_latest_title_and_ties() {
        Service s = new Service();
        hiddenUser(s, "ana", 60);
        String[] topics = {"zeta", "alpha", "mid", "alpha", "zeta", "mid"};
        for (int i = 0; i < topics.length; i++) hiddenSend(s, "ana", 1000 + i, topics[i], "k" + i);
        s.send(new Notification("ana", "mid", "same-second", "last in", 1005));
        Expect.eq(List.of("mid:3:last in", "alpha:2:alpha:k3", "zeta:2:zeta:k4"), hiddenDigest(s, "ana", hiddenDAY));
    }

    static void test_p2_digest_empty_and_unknown() {
        Service s = new Service();
        hiddenUser(s, "ana", 0, Notify.EMAIL);
        hiddenSend(s, "ana", 100, "billing", "b1");
        Expect.eq(List.<DigestLine>of(), s.digest("ana", hiddenDAY));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> s.digest("nope", hiddenDAY)));
    }

    // ---------------------------------------------------------------- phase 3

    /**
     * Replays half-days of traffic for n users on every channel, with quiet hours 23 -> 6 UTC: each sends
     * a notification every 5 seconds and every key is sent twice in a row. Returns the count of each
     * status and the total number of channel deliveries.
     */
    static String hiddenChattyUsers(Service s, int n, int halfDays) {
        int sent = 0, held = 0, duplicate = 0, deliveries = 0;
        List<String> ids = new ArrayList<>();
        for (int u = 0; u < n; u++) {
            String id = "u" + u;
            ids.add(id);
            hiddenUser(s, id, 0, Notify.PUSH, Notify.EMAIL, Notify.SMS);
            s.setQuietHours(id, 23, 6);
        }
        String[] topics = {"chat", "social", "billing", "security", "promo"};
        for (int i = 0; i < halfDays * hiddenDAY / 2 / 5; i++) {
            for (String id : ids) {
                Result r = s.send(new Notification(id, topics[(i / 2) % 5], id + "-" + (i / 2), "", i * 5L, i % 97 == 0));
                switch (r.status()) {
                    case Notify.SENT -> sent++;
                    case Notify.HELD -> held++;
                    default -> duplicate++;
                }
                deliveries += r.channels().size();
            }
        }
        return "sent " + sent + " held " + held + " duplicate " + duplicate + " deliveries " + deliveries;
    }

    static void test_p3_chatty_user_five_days() {
        Service s = new Service();
        long start = System.nanoTime();
        String got = hiddenChattyUsers(s, 1, 10);
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq("sent 641 held 42559 duplicate 43200 deliveries 1348", got);
        Expect.isTrue(ms < 2500, "86,400 sends took " + ms + " ms (budget 2500 ms)");
    }
}
