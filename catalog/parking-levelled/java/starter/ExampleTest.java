// An example to copy. Run your tests with the My tests button.
public class ExampleTest {
    static void test_example_park() {
        var g = new Garage();
        Expect.isTrue(g.addSpot(1, "P1", "medium"));
        Expect.eq("P1", g.park(2, "AB-123", "small"));
        Expect.eq("P1", g.spotOf(3, "AB-123"));
    }
}
