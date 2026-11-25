public class ExampleTest {
    // Charge at 3, discharge at 7 and pay 1 of wear: 7 - 1 - 3 = 3.
    static void test_example_one_cycle() {
        Expect.eq(3, Meters.bestBatteryProfit(new int[]{3, 7}, 1, 1));
    }
}
