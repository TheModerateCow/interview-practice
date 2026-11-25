import java.util.List;

public class ExampleTest {
    static void test_example_two_levels() {
        // 1 share at 40 is cheapest, then 1 of the 2 shares at 50.
        long[] got = Book.runBook(List.of(new Event("add", 50, 2), new Event("add", 40, 1), new Event("quote", 0, 2)));
        Expect.eq(1, got.length);
        Expect.eq(90L, got[0]);
    }
}
