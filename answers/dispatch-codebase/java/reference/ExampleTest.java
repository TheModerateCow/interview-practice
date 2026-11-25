// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testExampleAssignNearest() {
        Dispatcher d = new Dispatcher();
        d.addCourier("near", new Point(100, 0), 1);
        d.addCourier("far", new Point(900, 900), 1);
        d.placeOrder("o1", new Point(0, 0), new Point(500, 0), 0, 5);
        Expect.eq("near", d.assign("o1"));
    }
}
