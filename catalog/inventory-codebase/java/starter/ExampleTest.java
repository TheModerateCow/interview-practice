// An example to copy. Run your tests with the My tests button: every static void method whose
// name starts with "test" runs; use Expect.eq, Expect.isTrue and Expect.raises to check things.
public class ExampleTest {
    static void testReceiveAndReserve() {
        Inventory s = new Inventory();
        s.addWarehouse("north");
        s.receive("north", "B-07", "MUG-RED", 12, 100);
        s.reserve("o1", "north", "MUG-RED", 5, 900, 200);
        Expect.eq(7, s.available("north", "MUG-RED", 300));
        Expect.eq(12, s.onHand("north", "MUG-RED"));
    }
}
