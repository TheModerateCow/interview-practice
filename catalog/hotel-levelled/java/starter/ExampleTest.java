// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_booking_cost() {
        var h = new Hotel();
        Expect.isTrue(h.addRoom(1, "7", "twin", 5000));
        Expect.eq("b1", h.book(2, "kit", "7", 30, 32));
        Expect.eq(10000, h.cost(3, "b1"));
    }
}
