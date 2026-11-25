// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testAllowWithinLimit() {
        Service s = new Service();
        s.addPlan(new Plan("starter", 5, 60, 0));
        s.issueKey("key-1", "org-1", "starter");
        Decision d = s.allow("key-1", 30, 2);
        Expect.isTrue(d.allowed() && d.remaining() == 3);
    }
}
