public class ExampleTest {
    static void test_example_two_pickups() {
        Expect.eq(3, Dispatch.minDispatchRadius(new int[]{0, 10}, new int[]{3, 12}, 2));
    }
}
