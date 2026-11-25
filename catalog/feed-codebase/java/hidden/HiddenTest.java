import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;

// The app compiles one phase's tests at a time: helpers use only the phase-1 API.
public class HiddenTest {
    static final long hiddenT0 = 1_750_000_000L;
    static final long hiddenH = 60 * 60;
    static final long hiddenDay = 24 * hiddenH;

    static FeedService hiddenSvc(String... users) {
        FeedService svc = new FeedService();
        for (String u : users) svc.addUser(u);
        return svc;
    }

    static String hiddenCode(Runnable r) {
        try {
            r.run();
            return "ok";
        } catch (FeedException e) {
            return e.code.name();
        }
    }

    static List<String> hiddenIds(String... ids) {
        return List.of(ids);
    }

    /** Pages through the whole feed; returns the ids followed by the page count. */
    static List<String> hiddenAllPages(FeedService svc, String viewer, long now, int limit) {
        List<String> ids = new ArrayList<>();
        String cursor = null;
        int pages = 0;
        while (true) {
            Page page = svc.homeFeed(viewer, now, limit, cursor);
            ids.addAll(page.postIds());
            pages++;
            Expect.isTrue(pages < 100, "paging never ended");
            if (page.nextCursor() == null) {
                ids.add("pages=" + pages);
                return ids;
            }
            cursor = page.nextCursor();
        }
    }

    // ---------------------------------------------------------------- phase 1

    static void test_p1_feed_is_followed_and_own_posts_newest_first() {
        FeedService svc = hiddenSvc("ana", "ben", "cy", "dee");
        svc.follow("ana", "ben");
        svc.follow("ana", "dee");
        svc.publish("b1", "ben", hiddenT0);
        svc.publish("c1", "cy", hiddenT0 + 10);
        svc.publish("a1", "ana", hiddenT0 + 20);
        svc.publish("d1", "dee", hiddenT0 + 30);
        svc.publish("b2", "ben", hiddenT0 + 40);
        Page page = svc.homeFeed("ana", hiddenT0 + 100);
        Expect.eq(hiddenIds("b2", "d1", "a1", "b1"), page.postIds());
        Expect.eq(null, page.nextCursor());
        Expect.eq(hiddenIds("c1"), svc.homeFeed("cy", hiddenT0 + 100).postIds());
    }

    static void test_p1_likes_trade_against_recency() {
        FeedService svc = hiddenSvc("ana", "ben", "u1", "u2", "u3");
        svc.follow("ana", "ben");
        svc.publish("old", "ben", hiddenT0);
        svc.publish("mid", "ben", hiddenT0 + 11 * hiddenH);
        svc.publish("new", "ben", hiddenT0 + 13 * hiddenH);
        for (String u : new String[] {"u1", "u2", "u3"}) Expect.isTrue(svc.like("old", u) >= 1, "like count");
        Expect.eq(3, svc.post("old").likes());
        Expect.eq(hiddenIds("new", "old", "mid"), svc.homeFeed("ana", hiddenT0 + 14 * hiddenH).postIds());
    }

    static void test_p1_equal_scores_tie_on_post_id() {
        FeedService svc = hiddenSvc("ana", "ben", "cy");
        svc.follow("ana", "ben");
        svc.follow("ana", "cy");
        svc.publish("p-c", "cy", hiddenT0);
        svc.publish("p-a", "ben", hiddenT0);
        svc.publish("p-b", "ben", hiddenT0);
        Expect.eq(hiddenIds("p-a", "p-b", "p-c"), svc.homeFeed("ana", hiddenT0 + 5).postIds());
    }

    static void test_p1_retried_like_counts_once() {
        FeedService svc = hiddenSvc("ana", "ben", "cy");
        svc.follow("ana", "ben");
        svc.publish("x", "ben", hiddenT0);
        svc.publish("y", "ben", hiddenT0 + 7 * hiddenH);
        Expect.eq(1, svc.like("x", "cy"));
        Expect.eq(1, svc.like("x", "cy"));
        Expect.eq(1, svc.like("x", "cy"));
        Expect.eq(1, svc.post("x").likes());
        Expect.eq(hiddenIds("y", "x"), svc.homeFeed("ana", hiddenT0 + 8 * hiddenH).postIds());
        Expect.eq(2, svc.like("x", "ana"));
        Expect.eq(hiddenIds("x", "y"), svc.homeFeed("ana", hiddenT0 + 8 * hiddenH).postIds());
    }

    static void test_p1_like_errors() {
        FeedService svc = hiddenSvc("ana", "ben");
        svc.publish("x", "ben", hiddenT0);
        Expect.eq("UNKNOWN_POST", hiddenCode(() -> svc.like("nope", "ana")));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> svc.like("x", "ghost")));
        Expect.eq(0, svc.post("x").likes());
    }

    static void test_p1_paging_a_thread_shows_each_post_once() {
        FeedService svc = hiddenSvc("ana", "ben");
        svc.follow("ana", "ben");
        for (int i = 0; i < 14; i++) svc.publish(String.format("t%02d", i), "ben", hiddenT0 + i);
        svc.publish("t06b", "ben", hiddenT0 + 6);
        long now = hiddenT0 + 60;
        List<String> everything = svc.homeFeed("ana", now, 100, null).postIds();
        Expect.eq(hiddenIds("t13", "t12", "t11", "t10"), everything.subList(0, 4));
        Expect.eq(everything.indexOf("t06") + 1, everything.indexOf("t06b"));
        for (int limit : new int[] {2, 3, 4}) {
            List<String> got = new ArrayList<>(everything);
            got.add("pages=" + (everything.size() + limit - 1) / limit);
            Expect.eq(got, hiddenAllPages(svc, "ana", now, limit));
        }
    }

    static void test_p1_paging_mixed_engagement() {
        FeedService svc = hiddenSvc("ana", "ben", "cy", "l0", "l1", "l2");
        svc.follow("ana", "ben");
        svc.follow("ana", "cy");
        for (int i = 0; i < 9; i++) {
            svc.publish("b" + i, "ben", hiddenT0 + 3 * i);
            svc.publish("c" + i, "cy", hiddenT0 + 3 * i + 1);
        }
        String[] likers = {"l0", "l1", "l2"};
        for (int i = 0; i < 3; i++) {
            svc.like("b" + i, likers[i]);
            svc.like("c" + (i + 4), likers[i]);
        }
        long now = hiddenT0 + 100;
        List<String> everything = svc.homeFeed("ana", now, 50, null).postIds();
        Expect.eq(18, everything.size());
        List<String> got = new ArrayList<>(everything);
        got.add("pages=5");
        Expect.eq(got, hiddenAllPages(svc, "ana", now, 4));
    }

    static void test_p1_last_page_and_bad_cursor() {
        FeedService svc = hiddenSvc("ana");
        for (int i = 0; i < 4; i++) svc.publish("a" + i, "ana", hiddenT0 + i * 10L);
        Page first = svc.homeFeed("ana", hiddenT0 + 100, 2, null);
        Expect.eq(hiddenIds("a3", "a2"), first.postIds());
        Expect.isTrue(first.nextCursor() != null, "first page has a cursor");
        Page second = svc.homeFeed("ana", hiddenT0 + 100, 2, first.nextCursor());
        Expect.eq(hiddenIds("a1", "a0"), second.postIds());
        Expect.eq(null, second.nextCursor());
        Expect.eq(null, svc.homeFeed("ana", hiddenT0 + 100, 4, null).nextCursor());
        Expect.eq("BAD_CURSOR", hiddenCode(() -> svc.homeFeed("ana", hiddenT0 + 100, 2, "not-a-cursor")));
        Expect.eq("BAD_LIMIT", hiddenCode(() -> svc.homeFeed("ana", hiddenT0 + 100, 0, null)));
    }

    static void test_p1_feed_window_edges() {
        FeedService svc = hiddenSvc("ana", "ben");
        svc.follow("ana", "ben");
        long now = hiddenT0 + 30 * hiddenDay;
        svc.publish("too-old", "ben", now - 7 * hiddenDay - 1);
        svc.publish("oldest", "ben", now - 7 * hiddenDay);
        svc.publish("mid", "ben", now - 3 * hiddenDay);
        svc.publish("now", "ben", now);
        svc.publish("scheduled", "ben", now + 1);
        Expect.eq(hiddenIds("now", "mid", "oldest"), svc.homeFeed("ana", now).postIds());
        Expect.eq(hiddenIds("scheduled", "now", "mid"), svc.homeFeed("ana", now + 1).postIds());
    }

    static void test_p1_permanent_mute_is_per_viewer() {
        FeedService svc = hiddenSvc("ana", "ben", "cy");
        svc.follow("ana", "ben");
        svc.follow("ana", "cy");
        svc.follow("cy", "ben");
        svc.publish("b1", "ben", hiddenT0);
        svc.publish("c1", "cy", hiddenT0 + 1);
        svc.mute("ana", "ben", hiddenT0 + 2);
        Expect.eq(hiddenIds("c1"), svc.homeFeed("ana", hiddenT0 + 3).postIds());
        Expect.eq(hiddenIds("c1"), svc.homeFeed("ana", hiddenT0 + 6 * hiddenDay).postIds());
        Expect.eq(hiddenIds("c1", "b1"), svc.homeFeed("cy", hiddenT0 + 3).postIds());
    }

    static void test_p1_timed_mute_lasts_its_hours() {
        FeedService svc = hiddenSvc("ana", "ben");
        svc.follow("ana", "ben");
        svc.publish("b1", "ben", hiddenT0);
        long start = hiddenT0 + hiddenH;
        svc.mute("ana", "ben", start, 24.0);
        Expect.eq(hiddenIds(), svc.homeFeed("ana", start + 2 * hiddenH).postIds());
        Expect.eq(hiddenIds(), svc.homeFeed("ana", start + 24 * hiddenH - 1).postIds());
        Expect.eq(hiddenIds("b1"), svc.homeFeed("ana", start + 24 * hiddenH).postIds());
    }

    static void test_p1_short_mute_and_remute() {
        FeedService svc = hiddenSvc("ana", "ben");
        svc.follow("ana", "ben");
        svc.publish("b1", "ben", hiddenT0);
        svc.mute("ana", "ben", hiddenT0, 1.5);
        Expect.eq(hiddenIds(), svc.homeFeed("ana", hiddenT0 + 89 * 60).postIds());
        Expect.eq(hiddenIds("b1"), svc.homeFeed("ana", hiddenT0 + 90 * 60).postIds());
        svc.mute("ana", "ben", hiddenT0 + 2 * hiddenH, 3.0);
        Expect.eq(hiddenIds(), svc.homeFeed("ana", hiddenT0 + 4 * hiddenH).postIds());
        Expect.eq(hiddenIds("b1"), svc.homeFeed("ana", hiddenT0 + 5 * hiddenH).postIds());
    }

    static void test_p1_unfollow_and_account_errors() {
        FeedService svc = hiddenSvc("ana", "ben");
        svc.follow("ana", "ben");
        svc.publish("b1", "ben", hiddenT0, "first");
        svc.unfollow("ana", "ben");
        Expect.eq(hiddenIds(), svc.homeFeed("ana", hiddenT0 + 1).postIds());
        Expect.eq("SELF_FOLLOW", hiddenCode(() -> svc.follow("ana", "ana")));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> svc.follow("ana", "ghost")));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> svc.homeFeed("ghost", hiddenT0)));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> svc.publish("g1", "ghost", hiddenT0)));
        svc.like("b1", "ana");
        Expect.eq("DUPLICATE_POST", hiddenCode(() -> svc.publish("b1", "ben", hiddenT0 + 5, "retry")));
        Expect.eq("first", svc.post("b1").text());
        Expect.eq(1, svc.post("b1").likes());
    }

    // ---------------------------------------------------------------- phase 2

    static long hiddenSince = hiddenT0 + 10 * hiddenH;

    static FeedService hiddenAway() {
        FeedService svc = hiddenSvc("ana", "ben", "cy", "dee", "l1", "l2", "l3");
        for (String f : new String[] {"ben", "cy", "dee"}) svc.follow("ana", f);
        long since = hiddenSince;
        svc.publish("a-own", "ana", since + 50);
        svc.publish("b-before", "ben", since - 100);
        svc.publish("b-at", "ben", since);
        svc.publish("b1", "ben", since + 1);
        svc.publish("b2", "ben", since + 2 * hiddenH);
        svc.publish("b3", "ben", since + 3 * hiddenH);
        svc.publish("c1", "cy", since + 30 * 60);
        svc.publish("d1", "dee", since + 4 * hiddenH);
        svc.publish("d2", "dee", since + 5 * hiddenH);
        return svc;
    }

    static void test_p2_catch_up_ranks_new_posts_from_followed_accounts() {
        FeedService svc = hiddenAway();
        long since = hiddenSince, now = since + 6 * hiddenH;
        Expect.eq(hiddenIds("d2", "d1", "b3", "b2", "c1"), svc.catchUp("ana", since, now, 10));
    }

    static void test_p2_catch_up_two_per_account_by_rank() {
        FeedService svc = hiddenAway();
        long since = hiddenSince, now = since + 6 * hiddenH;
        for (String liker : new String[] {"l1", "l2", "l3"}) svc.like("b1", liker);
        Expect.eq(hiddenIds("b1", "d2", "d1", "b3", "c1"), svc.catchUp("ana", since, now, 10));
        Expect.eq(hiddenIds("b1", "d2", "d1", "b3", "c1"), svc.catchUp("ana", since - 200, now, 10));
    }

    static void test_p2_catch_up_limit_and_default() {
        FeedService svc = hiddenAway();
        long since = hiddenSince, now = since + 6 * hiddenH;
        svc.publish("c2", "cy", since + 5 * hiddenH + 30 * 60);
        Expect.eq(hiddenIds("c2", "d2", "d1", "b3", "b2"), svc.catchUp("ana", since, now));
        Expect.eq(hiddenIds("c2", "d2"), svc.catchUp("ana", since, now, 2));
        Expect.eq(hiddenIds("c2"), svc.catchUp("ana", since, now, 1));
    }

    static void test_p2_catch_up_skips_muted_unfollowed_and_future() {
        FeedService svc = hiddenAway();
        long since = hiddenSince, now = since + 4 * hiddenH;
        svc.mute("ana", "dee", since);
        svc.unfollow("ana", "cy");
        svc.publish("b-later", "ben", now + 1);
        Expect.eq(hiddenIds("b3", "b2"), svc.catchUp("ana", since, now, 10));
    }

    static void test_p2_catch_up_never_reaches_past_the_feed_window() {
        FeedService svc = hiddenSvc("ana", "ben", "cy");
        svc.follow("ana", "ben");
        svc.follow("ana", "cy");
        long now = hiddenT0 + 20 * hiddenDay;
        svc.publish("ancient", "cy", now - 7 * hiddenDay - 1);
        svc.publish("edge", "ben", now - 7 * hiddenDay);
        svc.publish("recent", "ben", now - hiddenDay);
        Expect.eq(hiddenIds("recent", "edge"), svc.catchUp("ana", hiddenT0, now));
        Expect.eq(hiddenIds("recent"), svc.catchUp("ana", now - 7 * hiddenDay, now));
    }

    static void test_p2_catch_up_empty_and_errors() {
        FeedService svc = hiddenAway();
        long since = hiddenSince, late = since + 10 * hiddenH;
        Expect.eq(hiddenIds(), svc.catchUp("ana", late, late + hiddenH));
        Expect.eq(hiddenIds(), svc.catchUp("cy", since, late));
        Expect.eq("UNKNOWN_USER", hiddenCode(() -> svc.catchUp("ghost", since, late)));
        Expect.eq("BAD_LIMIT", hiddenCode(() -> svc.catchUp("ana", since, late, 0)));
    }

    // ---------------------------------------------------------------- phase 3

    static Set<Integer> hiddenPick(Random rng, int count, int bound, int offset) {
        Set<Integer> out = new LinkedHashSet<>();
        while (out.size() < count) out.add(offset + rng.nextInt(bound));
        return out;
    }

    static FeedService hiddenRush(List<String> viewers) {
        Random rng = new Random(42);
        FeedService svc = new FeedService();
        String[] users = new String[2000];
        for (int i = 0; i < users.length; i++) {
            users[i] = String.format("u%04d", i);
            svc.addUser(users[i]);
        }
        int n = 0;
        for (int day = 0; day < 30; day++) {
            for (String u : users) {
                String pid = String.format("p%06d", n++);
                svc.publish(pid, u, hiddenT0 + day * hiddenDay + rng.nextInt((int) hiddenDay));
                for (int i : hiddenPick(rng, rng.nextInt(6), users.length, 0)) svc.like(pid, users[i]);
            }
        }
        for (int v = 0; v < 40; v++) {
            viewers.add(users[v]);
            for (int i : hiddenPick(rng, 150, users.length - 40, 40)) svc.follow(users[v], users[i]);
        }
        return svc;
    }

    static void test_p3_morning_peak_home_feeds() {
        List<String> viewers = new ArrayList<>();
        FeedService svc = hiddenRush(viewers);
        long now = hiddenT0 + 30 * hiddenDay;
        long start = System.nanoTime();
        List<Page> pages = new ArrayList<>();
        for (String v : viewers) pages.add(svc.homeFeed(v, now, 20, null));
        long ms = (System.nanoTime() - start) / 1_000_000;
        for (Page p : pages) Expect.eq(20, p.postIds().size());
        Expect.eq(hiddenIds("p058734", "p059062", "p058332"), pages.get(0).postIds().subList(0, 3));
        Expect.eq("p059975", pages.get(21).postIds().get(7));
        Expect.eq("p059023", pages.get(39).postIds().get(19));
        Expect.isTrue(ms < 500, "40 home feeds took " + ms + " ms, budget 500 ms");
    }

    static void test_p3_morning_peak_catch_up() {
        List<String> viewers = new ArrayList<>();
        FeedService svc = hiddenRush(viewers);
        long now = hiddenT0 + 30 * hiddenDay;
        long start = System.nanoTime();
        List<List<String>> lists = new ArrayList<>();
        for (String v : viewers) lists.add(svc.catchUp(v, now - 2 * hiddenDay, now, 5));
        long ms = (System.nanoTime() - start) / 1_000_000;
        Expect.eq(hiddenIds("p058734", "p059062", "p058332", "p058259", "p059795"), lists.get(0));
        Expect.eq(hiddenIds("p058369", "p058409", "p058561", "p059543", "p058375"), lists.get(17));
        Expect.eq(hiddenIds("p059423", "p059526", "p058541", "p059095", "p058681"), lists.get(39));
        Expect.isTrue(ms < 500, "40 catch-ups took " + ms + " ms, budget 500 ms");
    }
}
