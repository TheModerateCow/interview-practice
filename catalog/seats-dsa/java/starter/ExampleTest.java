// An example to copy. My tests runs every *Test.java: each static void test... method is a test.
// Expect.eq(expected, actual), Expect.isTrue(cond), Expect.raises(Exception.class, () -> ...) are provided.
public class ExampleTest {
    static void test_two_passengers_one_seat() {
        // One leg with a single free seat, two passengers want it.
        Expect.eq(1, Upgrades.maxUpgrades(new int[]{1}, new int[][]{{0, 1}, {0, 1}}));
    }
}
