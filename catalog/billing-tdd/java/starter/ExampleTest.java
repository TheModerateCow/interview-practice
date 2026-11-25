// An example to copy. Write your own tests in this style and run them with My tests.
public class ExampleTest {
    static void test_example_renew() {
        var s = new Subscription();
        s.start(0, "starter", "monthly", 2);
        Expect.eq(2598, s.renew()); // 2 seats x 12.99
        Expect.eq(60, s.periodEnd());
    }
}
