// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_buy() {
        var o = new Office();
        Expect.isTrue(o.createEvent(1, "jazz-night", 3));
        Expect.isTrue(o.buy(2, "jazz-night", "maya", 2));
        Expect.eq(1, o.available(3, "jazz-night"));
    }
}
