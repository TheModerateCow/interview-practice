// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_set_get() {
        var s = new Store();
        Expect.isTrue(s.set(1, "svc-api", "replicas", "3"));
        Expect.eq("3", s.get(2, "svc-api", "replicas"));
    }
}
