// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testFeedShowsFollowedAccounts() {
        FeedService svc = new FeedService();
        for (String user : new String[] {"ana", "ben", "cy"}) svc.addUser(user);
        svc.follow("ana", "ben");
        svc.publish("b1", "ben", 1_000, "hello");
        svc.publish("c1", "cy", 1_100, "not followed");
        Page page = svc.homeFeed("ana", 2_000);
        Expect.eq(java.util.List.of("b1"), page.postIds());
        Expect.eq(null, page.nextCursor());
    }
}
